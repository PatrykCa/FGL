"""Chiba Plant CAPEX scope calculator.

Files next to this script:
  budget.xlsx          the phased budget workbook (first sheet is read)
  render_mapping.csv   item_id,render  -> first render on which the item is visible
  renders/             PNG renders from Blender, named exactly as in RENDERS below
"""
import re
from pathlib import Path

import pandas as pd
import streamlit as st
from openpyxl import load_workbook

HERE = Path(__file__).parent
BUDGET = HERE / "budget.xlsx"
MAPPING = HERE / "render_mapping.csv"
RENDER_DIR = HERE / "renders"

# Cumulative renders, earliest build stage first.
RENDERS = [f"{n} to Last Phase" for n in range(14, 1, -1)] + ["Last Phase"]

_V = tuple(int(x) for x in st.__version__.split(".")[:2])
FULL = {"width": "stretch"} if _V >= (1, 52) else {"use_container_width": True}

st.set_page_config(page_title="Chiba CAPEX Calculator", layout="wide")


@st.cache_data
def load_budget(path: str, mtime: float):
    """Read items, phase names and exchange rates from the budget sheet."""
    ws = load_workbook(path, data_only=True).worksheets[0]
    eur = float(ws["B5"].value or 186.73)   # 1 EUR = x JPY
    pln = float(ws["B6"].value or 2.66)     # 100 JPY = x PLN
    phases, rows = {}, []
    for r in ws.iter_rows(min_row=1, max_col=10, values_only=True):
        a = "" if r[0] is None else str(r[0]).strip()
        head = re.match(r"^Phase\s+(\w+)\s*:\s*(.+)$", a)
        if head and r[2] is None:
            name = head.group(2)
            inner = re.search(r"\(([^()]+)\)\s*$", name)   # keep the English name in brackets
            phases[len(phases) + 1] = inner.group(1) if inner else name
            continue
        if re.match(r"^\d+\.\d+$", a) and r[2]:
            rows.append({
                "ID": a, "Phase": int(a.split(".")[0]), "Item": str(r[2]).strip(),
                "Qty": float(r[3] or 0), "Unit": r[4] or "", "Unit price (JPY)": float(r[5] or 0),
                "Note": r[9] if isinstance(r[9], str) else "",
            })
    df = pd.DataFrame(rows)
    df["Total (JPY)"] = df["Qty"] * df["Unit price (JPY)"]
    return df, phases, eur, pln


@st.cache_data
def load_mapping(path: str, mtime: float):
    m = pd.read_csv(path, dtype=str).fillna("")
    return dict(zip(m["item_id"].str.strip(), m["render"].str.strip()))


if not BUDGET.exists():
    st.error(f"Budget file not found: {BUDGET.name}. Upload it next to app.py.")
    st.stop()

items, phase_names, eur_default, pln_default = load_budget(str(BUDGET), BUDGET.stat().st_mtime)
mapping = load_mapping(str(MAPPING), MAPPING.stat().st_mtime) if MAPPING.exists() else {}
items["Render"] = items["ID"].map(mapping).fillna("")
ids = items["ID"].tolist()

# ---------- scope state ----------
ss = st.session_state
if "scope" not in ss:
    ss.scope = {i: True for i in ids}
    ss.base_scope = dict(ss.scope)
    ss.editor_version = 0


def set_scope(new_scope):
    """Change the scope from a button: reset the table so it shows the new ticks."""
    ss.scope = new_scope
    ss.base_scope = dict(new_scope)
    ss.editor_version += 1


def stage_of(item_id):
    r = mapping.get(item_id, "")
    return RENDERS.index(r) if r in RENDERS else None


# ---------- sidebar ----------
with st.sidebar:
    st.header("Scope shortcuts")
    c1, c2 = st.columns(2)
    if c1.button("Select all", **FULL):
        set_scope({i: True for i in ids})
    if c2.button("Clear all", **FULL):
        set_scope({i: False for i in ids})
    used = [r for r in RENDERS if r in set(mapping.values())]
    if used:
        target = st.selectbox("Build up to render", used, index=len(used) - 1)
        if st.button("Apply build stage", **FULL):
            t = RENDERS.index(target)
            set_scope({i: (ss.scope[i] if stage_of(i) is None else stage_of(i) <= t) for i in ids})
    st.header("Exchange rates")
    eur = st.number_input("1 EUR = ... JPY", value=eur_default, min_value=0.01, step=0.01, format="%.2f")
    pln = st.number_input("100 JPY = ... PLN", value=pln_default, min_value=0.0, step=0.01, format="%.2f")
    factor = st.number_input("Factor (column '1,3 ration')", value=1.3, min_value=0.0, step=0.05, format="%.2f")
    st.caption("Rates start from cells B5 and B6 of the budget file.")

# ---------- page ----------
st.title("CAPEX Calculator, Chiba Plant")
st.caption("Tick the scope in the table. The cost and the 3D view change together.")

left, right = st.columns([3, 2], gap="large")

with left:
    table = items[["ID", "Phase", "Item", "Qty", "Unit", "Unit price (JPY)", "Total (JPY)", "Note"]].copy()
    table.insert(0, "In scope", [ss.base_scope[i] for i in ids])
    table["Phase"] = table["Phase"].map(lambda n: f"{n}. {phase_names.get(n, '')}")
    edited = st.data_editor(
        table,
        key=f"scope_editor_{ss.editor_version}",
        hide_index=True,
        height=38 + 35 * len(table),
        disabled=[c for c in table.columns if c != "In scope"],
        column_config={
            "In scope": st.column_config.CheckboxColumn("In scope", width="small"),
            "ID": st.column_config.TextColumn("ID", width="small"),
            "Item": st.column_config.TextColumn("Item", width="large"),
            "Qty": st.column_config.NumberColumn("Qty", format="localized"),
            "Unit price (JPY)": st.column_config.NumberColumn("Unit price (JPY)", format="localized"),
            "Total (JPY)": st.column_config.NumberColumn("Total (JPY)", format="localized"),
        },
        **FULL,
    )
    ss.scope = dict(zip(ids, edited["In scope"].astype(bool)))

sel = items["ID"].map(ss.scope)
total_jpy = float(items.loc[sel, "Total (JPY)"].sum())
full_jpy = float(items["Total (JPY)"].sum())

# Renders are cumulative: show the furthest one whose items, and all earlier renders' items, are in scope.
current, blocked, missing = None, None, []
for idx, name in enumerate(RENDERS):
    its = [i for i in ids if mapping.get(i) == name]
    if not its:
        continue
    miss = [i for i in its if not ss.scope[i]]
    if miss:
        blocked, missing = name, miss
        break
    current = name

with right:
    if current is None:
        st.info("No render for this scope yet: it does not cover the first rendered stage.")
    else:
        img = RENDER_DIR / f"{current}.png"
        if img.exists():
            st.image(str(img), **FULL)
        else:
            st.warning(f"Render file missing: renders/{current}.png")
        st.markdown(f"**{current}**  ·  stage {RENDERS.index(current) + 1} of {len(RENDERS)}")
    if blocked:
        st.caption(f"Missing for the '{blocked}' view: {', '.join(missing)}")
    elif not mapping:
        st.caption("No render mapping found (render_mapping.csv).")

    m1, m2 = st.columns(2)
    m1.metric("Selected scope (EUR)", f"€{total_jpy / eur:,.0f}")
    m2.metric(f"With factor x{factor:g} (EUR)", f"€{total_jpy / eur * factor:,.0f}")
    m3, m4 = st.columns(2)
    m3.metric("Selected scope (JPY)", f"¥{total_jpy:,.0f}")
    m4.metric("Selected scope (PLN)", f"{total_jpy * pln / 100:,.0f} PLN")
    st.caption(f"{int(sel.sum())} of {len(ids)} items selected. Full budget: €{full_jpy / eur:,.0f}.")

    by_phase = items.assign(sel=sel).groupby("Phase").apply(
        lambda g: g.loc[g["sel"], "Total (JPY)"].sum(), include_groups=False)
    summary = pd.DataFrame({
        "Phase": [f"{n}. {phase_names.get(n, '')}" for n in by_phase.index],
        "JPY": by_phase.values,
        "EUR": by_phase.values / eur,
        "PLN": by_phase.values * pln / 100,
    })
    st.dataframe(
        summary, hide_index=True,
        column_config={c: st.column_config.NumberColumn(c, format="localized") for c in ("JPY", "EUR", "PLN")},
        **FULL,
    )
    st.bar_chart(summary.assign(**{"EUR (selected)": summary["EUR"].round(0)}).set_index("Phase")[["EUR (selected)"]])
