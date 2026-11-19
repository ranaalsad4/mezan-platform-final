"""v2 deliverables generated from the same code the app uses (so they cannot drift apart):
  docs/v2/learning.json                         data for the Word learning guide (report/v2/learning_guide.js)
  docs/v2/Mezan_Learning_Guide.md           learning guide (Markdown)
  docs/v2/methods_flow.png                      'how the methods connect' diagram (Graphviz, if installed)
  docs/v2/Mezan_MRC_Source_Register.xlsx    MRC source-to-variable register (+ .csv)
Run:  python tools/build_v2_docs.py
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

H = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(H))
from carbon_iq import learning as LC  # noqa: E402
from carbon_iq import mrc as M  # noqa: E402
from carbon_iq.ui.learn_ui import code_of, method_markdown, ref_md  # noqa: E402
from carbon_iq.ui.learning_center import _examples  # noqa: E402

OUT = H / "docs" / "v2"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- learning.json + Markdown guide
s1, g = M.scope1_recalc(), M.implied_grid_factor()
ex = _examples()
methods = [dict(m, code_src=code_of(m["code"][0][0], m["code"][0][1], max_lines=28)) for m in LC.METHODS]
data = dict(methods=methods, glossary=LC.GLOSSARY, proves=LC.PROVES, needs=LC.NEEDS_VALIDATION,
            refs={k: list(v) for k, v in LC.R.items()}, examples=ex.values.tolist(), example_cols=list(ex.columns),
            mrc=dict(scope1_calc=s1["total_t"], scope1_rep=s1["reported_t"], diff_pct=s1["diff_pct"], implied=g["implied_t_per_mwh"],
                     national=g["national_t_per_mwh"], s2_national=g["scope2_at_national_t"], mwh=g["electricity_mwh"]))
json.dump(data, open(OUT / "learning.json", "w"), indent=1, default=str)

md = ["# Mezan | ميزان v2 — Learning guide: every method, how it works and how Mezan implements it", "",
      "Generated from `carbon_iq/learning.py` (the same content as the app's Learning Center). Status is judged from the code. "
      "All synthetic-plant numbers are modelled on hypothetical data; MRC energy and emissions are Ma'aden's reported 2025 values "
      "(Sustainability Data Book 2025, PDF page 5) and every MRC investment figure is hypothetical.", "",
      "## Method status", "", "| # | Method | Status | What exactly |", "|---|---|---|---|"]
md += [f"| {i} | {m['title']} | {m['status']} | {m['status_note']} |" for i, m in enumerate(LC.METHODS, 1)]
md += ["", "## How the methods connect", "", "![How the methods connect](methods_flow.png)", "",
       "Data are checked and completed, converted to emissions, valued as projects, combined into the best portfolio, then tested in "
       "simulated futures against the target and the budget. Value of information can send you back to collect better data; "
       "sensitivity, stability and timing check how robust and urgent the recommendation is. (Teaching order; in the code, "
       "optimisation, simulation and the confidence rules run together on the same scenarios.)", ""]
for i, m in enumerate(LC.METHODS, 1):
    md += [f"## {i}. {m['title']}", "", f"**Status: {m['status']}.**", ""]
    for b in method_markdown(m):
        md += [b, ""]
    md += ["**The actual Python code** (main function; read from the source):", "", "```python",
           code_of(m["code"][0][0], m["code"][0][1], max_lines=28), "```", ""]
    if m.get("advanced"):
        md += [f"*Advanced:* {m['advanced']}", ""]
md += ["## Examples: synthetic plant and MRC", "", "| " + " | ".join(ex.columns) + " |", "|---|---|---|"]
md += ["| " + " | ".join(str(x) for x in r) + " |" for r in ex.values.tolist()]
md += ["", "## Glossary", "", "| Term | Meaning |", "|---|---|"] + [f"| {a} | {b} |" for a, b in LC.GLOSSARY]
md += ["", "## What the prototype proves", ""] + [f"- {x}" for x in LC.PROVES]
md += ["", "## What still needs real-world validation", ""] + [f"- {x}" for x in LC.NEEDS_VALIDATION]
md += ["", "## References", ""] + [f"- {ref_md(k)}" for k in LC.R]
(OUT / "Mezan_Learning_Guide.md").write_text("\n".join(md), encoding="utf-8")

if shutil.which("dot"):
    subprocess.run(["dot", "-Tpng", "-Gdpi=170", "-o", str(OUT / "methods_flow.png")], input=LC.CONNECTIONS_DOT.encode(), check=True)

# ---------------------------------------------------------------- MRC source-to-variable register
reg = pd.DataFrame(M.source_register())
reg.to_csv(OUT / "Mezan_MRC_Source_Register.csv", index=False)
from openpyxl import Workbook  # noqa: E402
from openpyxl.styles import Alignment, Font, PatternFill  # noqa: E402

wb = Workbook()
ws = wb.active
ws.title = "MRC register"
ws["A1"] = "Mezan | ميزان v2 — MRC source-to-variable register"
ws["A1"].font = Font(bold=True, size=14, color="0E2A25")
ws["A2"] = (f"{M.DATABOOK}. {M.DATABOOK_NOTE} kind: reported = Ma'aden value; calculated = derived by Mezan; benchmark = external "
            "source; hypothetical = Mezan assumption, NOT a Ma'aden value.")
ws["A2"].alignment = Alignment(wrap_text=True)
ws.merge_cells("A2:K2")
ws.row_dimensions[2].height = 60
cols = list(reg.columns)
fills = {"reported": "E3F1EC", "calculated": "E6ECF7", "benchmark": "FCF0DC", "hypothetical": "FBE9E3"}
for j, c in enumerate(cols, 1):
    x = ws.cell(4, j, c)
    x.font, x.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F6B5C")
for i, r in enumerate(reg.itertuples(index=False), 5):
    for j, v in enumerate(r, 1):
        x = ws.cell(i, j, v if not isinstance(v, (list, tuple)) else str(v))
        x.alignment = Alignment(wrap_text=True, vertical="top")
        x.fill = PatternFill("solid", fgColor=fills.get(r.kind, "FFFFFF"))
for col, w in zip("ABCDEFGHIJK", [30, 42, 14, 14, 13, 24, 40, 18, 40, 34, 26]):
    ws.column_dimensions[col].width = w
ws.freeze_panes = "A5"
s2 = wb.create_sheet("MRC checks")
rows = [("Check", "Value", "Basis"),
        ("Sum of energy lines (GJ)", M.energy_check()["sum_of_lines"], "PDF page 5"),
        ("Reported total energy (GJ)", M.v("energy_total_gj"), "PDF page 5"),
        ("Electricity (MWh)", g["electricity_mwh"], "1,040,392 GJ ÷ 3.6"),
        ("Scope 1 recalculated (tCO2e)", s1["total_t"], "IPCC 2006 Table 2.3 factors × reported GJ"),
        ("Scope 1 reported (tCO2e)", s1["reported_t"], "PDF page 5"),
        ("Difference (%)", s1["diff_pct"], "recalculated vs reported"),
        ("Implied Scope 2 factor (tCO2e/MWh)", g["implied_t_per_mwh"], "reported Scope 2 ÷ MWh"),
        ("Saudi national grid factor (tCO2e/MWh)", g["national_t_per_mwh"], "Mezan register (BTR1 2021 inventory / GASTAT)"),
        ("Scope 2 at national factor (tCO2e)", g["scope2_at_national_t"], "MWh × national factor (comparison only)")]
for r in rows:
    s2.append(r)
for c in s2[1]:
    c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F6B5C")
s2.column_dimensions["A"].width, s2.column_dimensions["B"].width, s2.column_dimensions["C"].width = 40, 18, 55
wb.save(OUT / "Mezan_MRC_Source_Register.xlsx")
print("written:", ", ".join(p.name for p in sorted(OUT.iterdir())))
