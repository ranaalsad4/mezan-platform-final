"""A6 consistency scan: are Python, Excel, Streamlit and every Word report on the same (current) results?

    python tools/consistency_a6.py            -> outputs/a6/a6_consistency.csv and a6_consistency.json

1. Key current figures (from outputs/results.json) are searched as printed text in each Word report and in the
   Streamlit app (AppTest rendering of all tabs).
2. Each Word report is scanned for phrases that were only true under the v1.2 register (stale claims); a hit is listed
   with its sentence so it can be judged (historical comparisons such as "in v1.2 ..." are allowed when labelled).
3. The Excel workbooks' cached values are compared with Python (main workbook: tools/crosscheck.py; A6 workbook: Check sheet).
"""
import json
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
R = json.load(open(HERE / "outputs" / "results.json"))
DS = {d["id"]: d for d in R["decision_scenarios"]}
OUT = HERE / "outputs" / "a6"

DOCS = {"Complete project report": HERE / "Mezan_Complete_Project.docx",
        "A4 missing-data report": HERE / "docs" / "Mezan_A4_Missing_Data_Report.docx",
        "A5 methodology report": HERE / "docs" / "Mezan_A5_Carbon_Financial_Methodology.docx",
        "A6 validation report": HERE / "docs" / "Mezan_A6_Mathematical_Validation_Report.docx"}
f0 = lambda x: f"{x:,.0f}"  # noqa: E731
KEY = {"recommended portfolio (D4)": [DS["D4"]["portfolio"]],
       "D1 NPV": [f0(DS["D1"]["npv_base_inputs"]), f"{DS['D1']['npv_base_inputs'] / 1e6:.2f}M"],
       "E[NPV] of the recommendation": [f0(DS["D4"]["e_npv"]), f"{DS['D4']['e_npv'] / 1e6:.2f}M"],
       "Scope 1+2 baseline": [f0(R["scope_totals"]["Scope 1+2"]), f"{R['scope_totals']['Scope 1+2']:,.1f}"],
       "target": [f0(R["target_t"]), f"{R['target_t']:,.1f}"],
       "P(capex <= budget)": [f"{DS['D4']['p_budget']:.1%}"],
       "grid factor": ["0.573"]}
STALE = [r"decision model v1\.2 unchanged", r"0\.55 (tCO2e/MWh )?project factor (is provisional and )?retained", r"No feasible portfolio at SAR 5M",
         r"no portfolio is feasible", r"SAR 654,323", r"584,081", r"D3 is \*?\*?not\*?\*?: A\+B", r"electricity bills? (is|are) the only",
         r"sits on the 90% threshold in every case", r"\$3(\.00)?/MMBtu (reference|base)", r"SAR 3,750/kWp \(reference", r"17 sheets"]


def doc_text(p):
    x = zipfile.ZipFile(p).read("word/document.xml").decode("utf8")
    x = re.sub(r"</w:p>", "\n", x)
    return re.sub(r"<[^>]+>", "", x).replace("&amp;", "&").replace("&apos;", "'").replace("&quot;", '"')


def app_text():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(HERE / "app.py"), default_timeout=600)
    at.session_state["nav"] = "Analysis workspace"               # v2 navigation
    at.run()
    at.select_slider(key="n").set_value(20000).run()            # the report's sample size (app default is 5,000)
    parts = [m.value for m in at.markdown] + [f"{m.value} {m.delta}" for m in at.metric] + [str(c.value) for c in at.caption]
    parts += [d.value.to_string() for d in at.dataframe]
    return "\n".join(parts), bool(at.exception)


rows = []
texts = {k: doc_text(p) for k, p in DOCS.items() if p.exists()}
try:
    texts["Streamlit app"], app_exc = app_text()
except Exception as e:  # pragma: no cover
    texts["Streamlit app"], app_exc = "", repr(e)
for src, t in texts.items():
    for name, forms in KEY.items():
        if src.startswith("A4") and name not in ("recommended portfolio (D4)", "Scope 1+2 baseline"):
            continue                                               # the A4 report covers the data-gap cases only
        found = next((f for f in forms if f in t), None)
        rows.append(dict(check="current figure present", source=src, item=name, expected=" or ".join(forms), result="found" if found else "not found"))
    for pat in STALE:
        for m in re.finditer(pat, t):
            line = t[max(0, t.rfind("\n", 0, m.start())):t.find("\n", m.end())].strip()
            rows.append(dict(check="stale v1.2 phrase", source=src, item=pat, expected="absent or labelled historical", result=line[:300]))
cc = pd.read_csv(HERE / "outputs" / "crosscheck.csv")
xl_mis = int((cc.get("excel_match") == False).sum()) if "excel_match" in cc else None  # noqa: E712
wbc = json.load(open(OUT / "a6_workbook_check.json")) if (OUT / "a6_workbook_check.json").exists() else {}
d = pd.DataFrame(rows)
d.to_csv(OUT / "a6_consistency.csv", index=False)
summary = dict(sources=list(texts), app_exception=app_exc,
               missing=d[(d.check == "current figure present") & (d.result == "not found")][["source", "item"]].to_dict("records"),
               stale_hits=d[d.check == "stale v1.2 phrase"][["source", "item", "result"]].to_dict("records"),
               main_crosscheck_rows=len(cc), independent_workbook=dict(all_pass=wbc.get("all_pass"), checks=wbc.get("checks")))
json.dump(summary, open(OUT / "a6_consistency.json", "w"), indent=1, default=str)
print(json.dumps(summary, indent=1, default=str)[:5000])
