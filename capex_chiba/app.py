"""CAPEX calculator: investment path of baskets on a timeline (Streamlit wrapper around page.html).

Files next to this script:
  budget.xlsx   project budget in the standard template (sheets Config, Baskets, Budget, Renders)
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
BUDGET, PAGE, RENDER_DIR = HERE / "budget.xlsx", HERE / "page.html", HERE / "renders"

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
    missing = [s for s in ("Config", "Baskets", "Budget", "Renders") if s not in wb.sheetnames]
    if missing:
        raise ValueError("Sheets missing in budget.xlsx: " + ", ".join(missing))
    cf = wb["Config"]
    rates = {txt(cf.cell(r, 1).value).upper(): float(cf.cell(r, 2).value)
             for r in range(18, 26) if txt(cf.cell(r, 1).value) and cf.cell(r, 2).value}
    report = txt(cf["B8"].value).upper() or "EUR"
    if report not in rates:
        raise ValueError(f"No exchange rate for the reporting currency {report} (Config)")
    cfg = {"project": txt(cf["B4"].value), "report": report, "factor": num(cf["B9"].value, 1),
           "start": int(num(cf["B10"].value, 2027)), "period": int(num(cf["B11"].value, 5)),
           "limit": num(cf["B12"].value), "horizon": max(1, min(10, int(num(cf["B13"].value, 10))))}
    problems = []
    bk = wb["Baskets"]
    baskets = []
    for r in range(5, 45):
        name = txt(bk.cell(r, 1).value)
        if not name:
            continue
        start = bk.cell(r, 2).value
        baskets.append({"name": name, "start": int(num(start)) if start not in (None, "") else None,
                        "dur": max(1, int(num(bk.cell(r, 3).value, 1))),
                        "move": txt(bk.cell(r, 4).value).upper() != "NO", "incl": txt(bk.cell(r, 5).value).upper() != "NO",
                        "pkg": txt(bk.cell(r, 6).value), "desc": txt(bk.cell(r, 7).value)})
    names = {b["name"] for b in baskets}
    bd = wb["Budget"]
    lines = []
    for r in range(5, 400):
        lid = txt(bd.cell(r, 1).value)
        if not lid:
            continue
        cur = txt(bd.cell(r, 9).value).upper() or "JPY"
        if cur not in rates:
            problems.append(f"{lid}: no exchange rate for {cur}")
        basket = txt(bd.cell(r, 4).value)
        if basket not in names:
            problems.append(f"{lid}: basket '{basket}' not found in the Baskets sheet")
        lines.append({"id": lid, "pkg": txt(bd.cell(r, 3).value), "basket": basket, "desc": txt(bd.cell(r, 5).value),
                      "qty": num(bd.cell(r, 6).value), "unit": txt(bd.cell(r, 7).value),
                      "price": num(bd.cell(r, 8).value) * rates.get(cur, 0) / rates[report], "render": txt(bd.cell(r, 10).value)})
    rd = wb["Renders"]
    renders = [txt(rd.cell(r, 2).value) for r in range(4, 40) if txt(rd.cell(r, 2).value)]
    return {"cfg": cfg, "baskets": baskets, "lines": lines, "renders": renders}, problems


@st.cache_data(show_spinner="Preparing renders...")
def render_uri(path: str, mtime: float) -> str:
    im = Image.open(path).convert("RGB")
    im.thumbnail((1800, 1800))
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
components.html(PAGE.read_text(encoding="utf-8").replace("/*__DATA__*/", payload), height=900, scrolling=True)
