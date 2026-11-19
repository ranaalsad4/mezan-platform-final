"""Collect refined-A4 outputs into one JSON for the report, issue log and workbook notes.
Usage: python prep_a4r.py <project dir> <out.json>"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(sys.argv[1]); OUT = Path(sys.argv[2])
sys.path.insert(0, str(ROOT))
for _up in Path(__file__).resolve().parents:
    if (_up / "a3" / "a3_data.py").exists():
        sys.path.insert(0, str(_up / "a3")); break
from carbon_iq.dataquality import quality as Q  # noqa: E402
import a3_data as A3  # noqa: E402

A4 = ROOT / "outputs" / "a4"
R = json.load(open(A4 / "a4_results.json"))
rd = lambda f: json.loads(pd.read_csv(A4 / f).to_json(orient="records"))  # noqa: E731
dec = pd.read_csv(A4 / "decision_comparison.csv")
short = {"C0": "complete (truth)", "C1": "as uploaded", "C2": "estimates approved", "C2f": "C2, target fixed (A4 v1)",
         "C3": "gaps = zero (wrong)", "C4": "electricity bills obtained", "C5": "severe gap"}
cases = []
for _, r in dec.iterrows():
    d = {k: (None if pd.isna(v) else v) for k, v in r.items()}
    d["short"] = short[r.case]
    cases.append(d)
c0 = dec[dec.case == "C0"].iloc[0]
for c in R["decisions"]:
    R["decisions"][c]["scope12_check"] = float(dec[dec.case == c].scope12.iloc[0] / c0.scope12)

est = pd.read_csv(A4 / "demo_estimates_vs_truth.csv")
ch = pd.read_csv(A4 / "demo_changes_applied.csv")
iss = pd.read_csv(A4 / "demo_issues.csv")
rows = []
for _, c in ch.iterrows():
    e = est[(est.period == c.period) & (est.stream == c.stream)]
    code = ", ".join(dict.fromkeys(iss[(iss.period == c.period) & (iss.stream == c.stream)].code.tolist()))
    if len(e):
        e = e.iloc[0]
        rows.append(dict(period=c.period, stream=c.stream, change=c.change, code=code, label=e.final_label,
                         rel_err=float(e.rel_err), covered=bool(e.covered95),
                         warning=(e.warning if isinstance(e.warning, str) else "")))
    else:
        rows.append(dict(period=c.period, stream=c.stream, change=c.change, code=code + " (auto-resolved)", label="—", rel_err=None,
                         covered=None, warning=""))

checks = json.load(open(OUT.parent / "checks.json")) if (OUT.parent / "checks.json").exists() else []
cov = pd.read_csv(A4 / "calibration_coverage.csv")
allcov = cov[cov.scenario == "all"]
g = lambda ds, st, col: float(allcov[(allcov.dataset.str.startswith(ds)) & (allcov.setting.str.startswith(st))][col].iloc[0])  # noqa: E731
chg = pd.read_csv(A4 / "change_detection_summary.csv").set_index("dataset")
base_ds = [d for d in chg.index if d.startswith("base")][0]

ISSUES_A4 = [
    dict(id="A4-01", priority="High", title="All A4 validation uses synthetic data from our own generator; accuracy on real industrial records unknown",
         status="Open (requires real data)", next="A5 pilot: run the engine on real monthly bills and fuel records, mask known months, report the same metrics"),
    dict(id="A4-02", priority="Medium", title="Monthly 95% prediction intervals under-covered (93.3% on the held-out base set)",
         status=f"Fixed for the synthetic generator family: {g('base','after','monthly_coverage'):.1%} (95% CI {g('base','after','monthly_ci_low'):.1%}-{g('base','after','monthly_ci_high'):.1%}) after split-conformal calibration; open for production-change data and real data",
         next="Re-fit CAL_MONTHLY on real data (A5)"),
    dict(id="A4-03", priority="Medium", title="Annual intervals from the linear (fully correlated) sum were overly wide: 96.9-98.6% coverage on held-out sets",
         status=f"Fixed (synthetic evidence): calibrated within-stream correlation 0.12 (directly estimated 0.13) gives {g('base','after','annual_coverage'):.1%} on the base set and 94.4-95.3% on the other no-change sets, with {1 - g('base','after','annual_halfwidth') / g('base','before','annual_halfwidth'):.0%} narrower intervals",
         next="Re-fit on real data"),
    dict(id="A4-04", priority="Medium", title="Structural breaks (process or production changes) not detected; estimates after a change biased",
         status=f"Partly fixed: change detection with regime-restricted estimation or refusal; after-change error {chg.loc['break_intensity','after_break_mape_old']:.1%} -> {chg.loc['break_intensity','after_break_mape_new']:.1%} (energy-use changes); 10% shifts detected in only 17% of cases; changes in the last 1-2 months are not detectable",
         next="Reviewer flag for known process changes; real-data test"),
    dict(id="A4-05", priority="High", title="Carbon-only rule D3 flipped between A+C+D and A+B with ~1% data changes or Monte Carlo resampling (knife-edge under the v1.2 register, linked to A1-25)",
         status="Resolved under v1.3 inputs: D3 = A+B+C on all seeds and plausible datasets; the stability check now flags D1 instead (project C marginal, A5-10)", next="Keep the stability warnings"),
    dict(id="A4-06", priority="Medium", title="Data value-of-information estimator noisy (binning noise floor, same estimator as A1-26)",
         status="Fixed for data VOI: pre-posterior conditioning gives exactly zero value for irrelevant measurements; Monte Carlo variation across seeds remains (A4-14)",
         next="—"),
    dict(id="A4-07", priority="Low", title="Costs of obtaining missing records are hypothetical (staff time at an assumed SAR 150/h)", status="Documented",
         next="Replace with team estimates"),
    dict(id="A4-08", priority="Low", title="Scope limits: monthly granularity, single-site decisions, fixed unit list, no meter-interval data, no Arabic interface",
         status="Documented", next="Extend when real data formats are known (A5)"),
    dict(id="A4-09", priority="Low", title="Outlier test flags about 1% of clean synthetic cells (false alarms) - reviewer workload on real data unknown",
         status="Documented", next="Measure on real data"),
    dict(id="A4-10", priority="Medium", title="Found and fixed during A4 development: production totals were silently dropped from the activity mapping",
         status="Fixed", next="Tested"),
    dict(id="A4-11", priority="Medium", title=f"Change detection raises false alarms: {chg.loc[base_ds,'change_warning_rate']:.1%} of stream-years with gaps in clean synthetic data ({chg.loc[base_ds,'change_refusal_rate']:.1%} refused), including the demo's forklift diesel",
         status="Documented; reviewer override available and labelled", next="Measure on real data; reviewer guidance"),
    dict(id="A4-12", priority="Medium", title=f"Intervals under-cover when production shifts mid-year: monthly {g('break_production','after','monthly_coverage'):.1%}, annual {g('break_production','after','annual_coverage'):.1%}",
         status="Open (documented)", next="Production-linked regime model; real-data check"),
    dict(id="A4-13", priority="Medium", title="Calibration factors fitted on one synthetic generator family; transfer to real data unproven",
         status="Open (requires real data)", next="Re-run tools/calibrate_a4.py on masked real data (A5)"),
    dict(id="A4-14", priority="Medium", title="Information value of electricity records varied strongly across Monte Carlo seeds because of the v1.2 knife-edge",
         status="Resolved under v1.3 inputs: no missing record has decision value (exactly zero on every seed)", next="—"),
]
open_a1 = [
    dict(id="A1-01", priority="Critical", title="Run on real Google Colab not yet confirmed", status="Open: simulated Colab environment only; real Colab run still required"),
    dict(id="A1-27", priority="High", title="Primary rule (90% carbon + 90% budget) infeasible at SAR 5M", status="Feasible under v1.3 inputs, dependent on the PV cost benchmark (A5-04)"),
    dict(id="A1-26", priority="High", title="Value-of-information estimator noisy", status="Re-checked in A6: nested Monte Carlo EVPPI agrees with the binned value within 0.3%; data VOI uses pre-posterior conditioning"),
    dict(id="A1-25", priority="Critical", title="Carbon chance constraint decided by sampling noise near 90%", status="Fixed (tightened level); no longer binding under v1.3 inputs"),
    dict(id="A1-24", priority="High", title="Positive expected NPVs rely on upward-skewed tariff range", status="Open (documented); E[NPV] positive with the tariff fixed at 0.18"),
    dict(id="A1-08", priority="High", title="Official 2027 industrial tariff schedule not obtained", status="Partly resolved (A5-01)"),
    dict(id="A1-07", priority="High", title="Grid emission factor primary source", status="Fixed in A5 (0.573 from BTR1/GASTAT); re-derived in A6"),
    dict(id="A1-16", priority="Medium", title="EVPPI binning error and LSMC trigger noise not quantified", status="Partly fixed in A6: EVPPI binning error quantified; LSMC engine checked on a published benchmark"),
    dict(id="A1-19", priority="Low", title="PV self-consumption not checked against load profile", status="Open (annual check only)"),
    dict(id="A1-20", priority="Low", title="UK proxy emission factors", status="Open (A5-08)"),
    dict(id="A1-23", priority="Low", title="Outputs not bit-identical at minimum NumPy/SciPy versions", status="Open (documented)"),
]
carried = open_a1 + [i for i in A3.CARRIED if i["id"].startswith("A2")] + [
    {**i, "status": ("Partly addressed by A4: detection, estimation, calibration and change detection implemented; connectors, supplier engagement, Arabic interface and in-Kingdom hosting open"
                     if i["id"] == "A3-05" else i["status"])} for i in A3.ISSUES_A3]

M = json.load(open(ROOT / "outputs" / "results.json"))
main = dict(evpi=M["evpi"], evsi=M["evsi_audit"]["evsi"], c_npv=next(p["npv"] for p in M["projects"] if p["id"] == "C"),
            evppi_c=next(v["evppi_sar"] for v in M["voi"] if v["parameter"] == "c_saving_frac"))
out = dict(main=main, results=R, cases=cases, changes=ch.to_dict("records"), demo_rows=rows,
           validation=rd("validation_summary.csv"), by_stream=rd("validation_by_stream.csv"), by_method=rd("validation_by_method.csv"),
           failures=rd("failure_cases.csv"), sens=rd("estimate_sensitivity_bounds.csv"),
           coverage=rd("calibration_coverage.csv"), reliability=rd("calibration_reliability.csv"),
           change=rd("change_detection_summary.csv"), change_size=rd("change_detection_by_size.csv"),
           stab_rules=rd("stability_rules.csv"), stab_margins=rd("stability_margins.csv"), stab_switch=rd("stability_switch_points.csv"),
           stab_seed=rd("stability_seed_check.csv"), voi=rd("information_value.csv"),
           calibration=json.load(open(A4 / "calibration.json")),
           streams=[[k, c["unit"], c["kind"]] for k, c in Q.STREAMS.items()],
           wb=R["workbook_recalc"], checks=checks, issues_a4=ISSUES_A4, carried=carried)
json.dump(out, open(OUT, "w"), indent=1, default=str)
print("ok", len(cases), len(rows), len(carried), len(ISSUES_A4))
