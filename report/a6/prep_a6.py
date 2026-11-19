"""Bundle A6 outputs for the validation report. Usage: python report/a6/prep_a6.py <project dir> <checks.json> <out.json>"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT, CHECKS, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
A6 = ROOT / "outputs" / "a6"
rd = lambda f: json.loads(pd.read_csv(A6 / f).to_json(orient="records"))  # noqa: E731
R = json.load(open(ROOT / "outputs" / "results.json"))
X = dict(A=json.load(open(A6 / "a6_results.json")), wb=json.load(open(A6 / "a6_workbook_check.json")),
         cons=json.load(open(A6 / "a6_consistency.json")) if (A6 / "a6_consistency.json").exists() else {},
         emissions=rd("a6_emissions.csv"), finance=rd("a6_finance.csv"), mc=rd("a6_mc_independent.csv"),
         conv=rd("a6_mc_convergence_summary.csv"), budget=rd("a6_chance_budget_analytic.csv"), evppi=rd("a6_voi_evppi.csv"),
         missing=rd("a6_missing_coverage.csv"), change=rd("a6_change_detection_independent.csv"), sobol=rd("a6_gsa_sobol.csv"),
         R={k: R[k] for k in ("decision_scenarios", "voi", "evpi", "evsi_audit", "timing_tree", "timing_gbm", "timing_lsmc_now", "projects", "meta",
                              "scope_totals", "target_t", "mc_chance_constrained")},
         a4=json.load(open(ROOT / "outputs" / "a4" / "a4_results.json")).get("complete_data_reproduces_pipeline"),
         tests=json.load(open(ROOT / "outputs" / "test_summary.json")), faults=json.load(open(ROOT / "outputs" / "fault_injection.json")),
         checks=json.load(open(CHECKS)) if CHECKS.exists() else [])
opt = pd.read_csv(A6 / "a6_optimization.csv")
X["opt_by_rule"] = json.loads(opt.groupby("exclusive").agg(cases=("budget", "size"), identical_choice=("same_choice", "sum"),
                                                           identical_npv=("same_value", "sum"), infeasible=("milp", lambda x: int(x.isna().sum())),
                                                           optima=("milp", lambda x: int(x.dropna().nunique()))).reset_index().to_json(orient="records"))
json.dump(X, open(OUT, "w"), indent=1, default=str)
print("ok")
