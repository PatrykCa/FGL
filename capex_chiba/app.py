"""CAPEX scope calculator (Streamlit wrapper around page.html).

Files next to this script:
  budget.xlsx   the phased budget workbook. First sheet = budget lines, with two extra columns:
                  "Render"   first render on which the item is visible
                  "Package"  object the item belongs to (Base, Tank Farm, Office ...)
                Sheets "Packages", "Scalable items" and "Config" define the object buttons,
                items built in steps (e.g. tanks) and extra exchange rates.
  page.html     the calculator page (layout, styling and logic)
  renders/      renders from Blender (PNG or JPG), named as in RENDERS below
"""
import base64
import io
import json
import re
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from openpyxl import load_workbook
from PIL import Image

HERE = Path(__file__).parent
BUDGET = HERE / "budget.xlsx"
PAGE = HERE / "page.html"
RENDER_DIR = HERE / "renders"

# Cumulative renders, earliest build stage first.
RENDERS = [f"{n} to Last Phase" for n in range(14, 1, -1)] + ["Last Phase"]
FACTOR = 1.3  # the "1,3 ration" column of the budget sheet

st.set_page_config(page_title="Chiba CAPEX Calculator", layout="wide")
st.markdown(
    """<style>
    .block-container, [data-testid="stMainBlockContainer"]{padding:0 !important;max-width:100% !important}
    header[data-testid="stHeader"], footer{display:none !important}
    iframe{height:100vh !important;display:block}
    </style>""",
    unsafe_allow_html=True,
)


def _txt(v):
    return "" if v is None else str(v).strip()


@st.cache_data
def load_budget(path: str, mtime: float):
    """Read rates, budget lines, packages and scalable items from the workbook."""
    wb = load_workbook(path, data_only=True)
    ws = wb.worksheets[0]
    rates = {"eur": float(ws["B5"].value or 186.73), "pln": float(ws["B6"].value or 2.66), "mult": FACTOR}

    usd = None
    if "Config" in wb.sheetnames:
        for k, v, *_ in wb["Config"].iter_rows(min_row=2, max_col=3, values_only=True):
            if _txt(k).upper().startswith("1 USD") and v:
                usd = float(v)
    to_jpy = {"JPY": 1.0, "EUR": rates["eur"], "USD": usd}

    # budget lines
    phase_names, items, col = {}, [], {}
    for r in ws.iter_rows(min_row=1, max_col=20, values_only=True):
        a = _txt(r[0])
        if a == "ID":
            heads = [_txt(h).lower() for h in r]
            col = {name: heads.index(name) for name in ("render", "package") if name in heads}
            continue
        head = re.match(r"^Phase\s+\w+\s*:\s*(.+)$", a)
        if head and r[2] is None:
            name = head.group(1)
            inner = re.search(r"\(([^()]+)\)\s*$", name)
            phase_names[len(phase_names) + 1] = inner.group(1) if inner else name
            continue
        if re.match(r"^\d+\.\d+$", a) and r[2]:
            ph = len(phase_names)
            items.append({
                "id": a, "desc": _txt(r[2]), "qty": float(r[3] or 0), "unit": _txt(r[4]), "price": float(r[5] or 0),
                "flag": r[9] if isinstance(r[9], str) else "",
                "stage": _txt(r[col["render"]]) if "render" in col else "",
                "group": (_txt(r[col["package"]]) if "package" in col else "") or f"Phase {ph}: {phase_names.get(ph, '')}",
                "scal": None,
            })

    # items built in steps
    problems = []
    if "Scalable items" in wb.sheetnames:
        for r in wb["Scalable items"].iter_rows(min_row=2, max_col=9, values_only=True):
            if not r[0] or not r[1] or not r[3]:
                continue
            cur = _txt(r[7]).upper() or "JPY"
            if not to_jpy.get(cur):
                problems.append(f"{r[0]}: no exchange rate for {cur} (sheet Config)")
                continue
            steps = []
            for part in _txt(r[8]).split(";"):
                m = re.match(r"^\s*(\d+)\s*=\s*(.+?)\s*$", part)
                if m:
                    steps.append([int(m.group(1)), m.group(2)])
            unit_cost = float(r[6] or 0)
            note = "" if cur == "JPY" else f"{cur} {unit_cost:,.0f} each at 1 {cur} = {to_jpy[cur]:g} JPY"
            items.append({
                "id": _txt(r[0]), "desc": _txt(r[2]), "qty": float(r[4] if r[4] is not None else r[3]), "unit": _txt(r[5]) or "pc",
                "price": unit_cost * to_jpy[cur], "flag": "", "stage": "", "group": _txt(r[1]),
                "scal": {"max": int(r[3]), "steps": sorted(steps), "note": note},
            })

    # packages: order and which are always included
    order, locked = [], set()
    if "Packages" in wb.sheetnames:
        for r in wb["Packages"].iter_rows(min_row=2, max_col=2, values_only=True):
            if r[0] and r[1] is not None:
                order.append(_txt(r[0]))
                if _txt(r[1]).upper() == "YES":
                    locked.add(_txt(r[0]))
    for it in items:
        if it["group"] not in order:
            order.append(it["group"])
    groups = [{"name": g, "locked": g in locked, "items": [it for it in items if it["group"] == g]} for g in order]
    return rates, [g for g in groups if g["items"]], problems


@st.cache_data(show_spinner="Preparing renders...")
def render_uri(path: str, mtime: float) -> str:
    """Downscale a render and return it as a data URI, so the page loads quickly."""
    im = Image.open(path).convert("RGB")
    im.thumbnail((1600, 1600))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=84)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


if not BUDGET.exists() or not PAGE.exists():
    st.error("budget.xlsx and page.html must sit next to app.py.")
    st.stop()

rates, groups, problems = load_budget(str(BUDGET), BUDGET.stat().st_mtime)

files = {" ".join(p.stem.lower().replace("_", " ").split()): p for p in RENDER_DIR.glob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg")} if RENDER_DIR.exists() else {}
images = {name: render_uri(str(files[name.lower()]), files[name.lower()].stat().st_mtime) for name in RENDERS if name.lower() in files}

linked = {it["stage"] for g in groups for it in g["items"] if it["stage"]}
linked |= {s[1] for g in groups for it in g["items"] if it["scal"] for s in it["scal"]["steps"]}
unknown = sorted(linked - set(RENDERS))
if unknown:
    problems.append("Render names in budget.xlsx that match no render: " + ", ".join(unknown))
if problems:
    st.warning("  \n".join(problems))

data = {"rates": rates, "groups": groups, "renders": RENDERS, "images": images}
payload = "const DATA = " + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + ";"
html = PAGE.read_text(encoding="utf-8").replace("/*__DATA__*/", payload)
components.html(html, height=900, scrolling=True)
