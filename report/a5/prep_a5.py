"""Bundle A5 outputs for the methodology report. Usage: python prep_a5.py <project dir> <checks.json> <out.json>"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT, CHECKS, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
O = ROOT / "outputs"
S = json.load(open(O / "a5" / "a5_summary.json"))
R = json.load(open(O / "results.json"))
rd = lambda f: json.loads(pd.read_csv(f).to_json(orient="records"))  # noqa: E731
a4 = O / "a4"
X = dict(S=S, R={k: R[k] for k in ("scope_totals", "uncertainty_totals", "target_t", "projects", "decision_scenarios", "knife_edge",
                                     "evpi", "voi", "evsi_audit", "timing_tree", "discount_robustness", "switch_points", "budget_analysis",
                                     "tariff_evidence", "ef_evidence", "meta", "sobol_decision", "sobol_decision_pair")},
         a4_stab=rd(a4 / "stability_rules.csv"), a4_voi=rd(a4 / "information_value.csv"), a4_dec=rd(a4 / "decision_comparison.csv"),
         a4_res=json.load(open(a4 / "a4_results.json")).get("complete_data_reproduces_pipeline"),
         checks=json.load(open(CHECKS)) if CHECKS.exists() else [])
json.dump(X, open(OUT, "w"), indent=1, default=str)
print("ok", len(X["checks"]))
