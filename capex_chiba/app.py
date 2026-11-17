"""CAPEX calculator: investment scope and timing (Streamlit wrapper around page.html).

Files next to this script:
  budget.xlsx   project budget in the standard template (sheets Config, Packages, Renders,
                Budget, Timeline)
  page.html     the calculator page (layout, styling and logic)
  renders/      renders from Blender (PNG or JPG), named as in the Renders sheet
"""
import base64
import io
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from openpyxl import load_workbook
from PIL import Image

HERE = Path(__file__).parent
BUDGET = HERE / "budget.xlsx"
PAGE = HERE / "page.html"
RENDER_DIR = HERE / "renders"

st.set_page_config(page_title="CAPEX Calculator", layout="wide")
st.markdown(
    """<style>
    .block-container, [data-testid="stMainBlockContainer"]{padding:0 !important;max-width:100% !important}
    header[data-testid="stHeader"], footer{display:none !important}
    iframe{height:100vh !important;display:block}
    </style>""",
    unsafe_allow_html=True,
)


def txt(v):
    return "" if v is None else str(v).strip()


def num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


@st.cache_data
def load_project(path: str, mtime: float):
    wb = load_workbook(path, data_only=True)
    need = ["Config", "Packages", "Renders", "Budget", "Timeline"]
    missing = [s for s in need if s not in wb.sheetnames]
    if missing:
        raise ValueError("Sheets missing in budget.xlsx: " + ", ".join(missing))
    cf = wb["Config"]
    rates = {}
    for r in range(18, 26):
        c, v = txt(cf.cell(r, 1).value).upper(), cf.cell(r, 2).value
        if c and v:
            rates[c] = float(v)
    report = txt(cf["B8"].value).upper() or "EUR"
    if report not in rates:
        raise ValueError(f"No exchange rate for the reporting currency {report} (Config)")
    to_rep = lambda cur: rates.get(cur.upper(), 0) / rates[report]
    cfg = {
        "project": txt(cf["B4"].value), "local": txt(cf["B7"].value), "report": report,
        "factor": num(cf["B9"].value, 1), "start": int(num(cf["B10"].value, 2027)),
        "period": int(num(cf["B11"].value, 5)), "limit": num(cf["B12"].value),
        "horizon": max(1, min(10, int(num(cf["B13"].value, 10)))),
    }
    pk = wb["Packages"]
    packages = [{"name": txt(pk.cell(r, 1).value), "locked": txt(pk.cell(r, 2).value).upper() == "YES"}
                for r in range(4, 16) if txt(pk.cell(r, 1).value)]
    rd = wb["Renders"]
    renders = [txt(rd.cell(r, 2).value) for r in range(4, 31) if txt(rd.cell(r, 2).value)]

    def year(v):
        return int(num(v)) if v not in (None, "") else None

    bd, tl = wb["Budget"], wb["Timeline"]
    lines, problems = [], []
    for r in range(5, 200):
        lid = txt(bd.cell(r, 1).value)
        if not lid:
            if r > 5 and not txt(bd.cell(r + 1, 1).value) and not txt(bd.cell(r + 2, 1).value):
                break
            continue
        cur = txt(bd.cell(r, 10).value).upper() or cfg["local"].upper()
        if cur not in rates:
            problems.append(f"{lid}: no exchange rate for {cur}")
        steps = []
        for part in txt(bd.cell(r, 12).value).split(";"):
            if "=" in part:
                n, name = part.split("=", 1)
                if n.strip().isdigit():
                    steps.append([int(n), name.strip()])
        tr = r + 3  # Timeline rows mirror Budget rows
        typ = txt(bd.cell(r, 5).value) or "Fixed"
        qty, mx = num(bd.cell(r, 6).value), num(bd.cell(r, 7).value)
        lines.append({
            "id": lid, "pkg": txt(bd.cell(r, 3).value) or "Base", "desc": txt(bd.cell(r, 4).value), "type": typ,
            "qty": qty, "max": mx or qty, "unit": txt(bd.cell(r, 8).value),
            "price": num(bd.cell(r, 9).value) * to_rep(cur), "render": txt(bd.cell(r, 11).value), "steps": sorted(steps),
            "cap": num(bd.cell(r, 18).value),
            "start": year(tl.cell(tr, 8).value), "dur": max(1, int(num(tl.cell(tr, 9).value, 1))),
            "t1u": num(tl.cell(tr, 10).value), "t1y": year(tl.cell(tr, 11).value),
            "t2u": num(tl.cell(tr, 12).value), "t2y": year(tl.cell(tr, 13).value),
        })
    names = [p["name"] for p in packages]
    for ln in lines:
        if ln["pkg"] not in names:
            packages.append({"name": ln["pkg"], "locked": False}); names.append(ln["pkg"])
    return {"cfg": cfg, "packages": packages, "renders": renders, "lines": lines}, problems


@st.cache_data(show_spinner="Preparing renders...")
def render_uri(path: str, mtime: float) -> str:
    im = Image.open(path).convert("RGB")
    im.thumbnail((1600, 1600))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=84)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


if not BUDGET.exists() or not PAGE.exists():
    st.error("budget.xlsx and page.html must sit next to app.py.")
    st.stop()
try:
    data, problems = load_project(str(BUDGET), BUDGET.stat().st_mtime)
except ValueError as e:
    st.error(f"{e}. Check that budget.xlsx follows the standard template.")
    st.stop()

norm = lambda s: " ".join(s.lower().replace("_", " ").split())
files = {norm(p.stem): p for p in RENDER_DIR.glob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg")} if RENDER_DIR.exists() else {}
data["images"] = {n: render_uri(str(files[norm(n)]), files[norm(n)].stat().st_mtime) for n in data["renders"] if norm(n) in files}
if problems:
    st.warning("  \n".join(problems))

payload = "const DATA = " + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + ";"
html = PAGE.read_text(encoding="utf-8").replace("/*__DATA__*/", payload)
components.html(html, height=900, scrolling=True)
