"""Compare key results of two runs (e.g. v1.0 vs v1.1) and list every assumption whose value, status or distribution
changed.   python tools/compare_versions.py <old results.json> <new results.json> <out.csv>"""
import csv
import json
import sys


def get(r, path):
    for k in path.split("."):
        if r is None:
            return None
        r = r.get(k) if isinstance(r, dict) else None
    return r


KEYS = [
    ("Scope 1+2 baseline (t)", "scope_totals.Scope 1+2"), ("Total baseline (t)", "scope_totals.Total"),
    ("Target (t/yr)", "target_t"),
    ("Scope 1+2 uncertainty, analytic (±%)", "uncertainty_totals.Scope 1+2.u95_pct"),
    ("Total uncertainty, analytic (±%)", "uncertainty_totals.Total.u95_pct"),
    ("Scope 1+2 uncertainty, Monte Carlo (±%)", "mc_baseline_scope12.u95_pct"),
    ("Deterministic optimum", "optimal.portfolio"), ("Deterministic optimum NPV (SAR)", "optimal.npv"),
    ("Highest expected NPV portfolio", "mc_best_expected.portfolio"), ("Highest E[NPV] (SAR)", "mc_best_expected.e_npv"),
    ("Highest E[NPV]: P(target)", "mc_best_expected.p_target"),
    ("Chance-constrained portfolio", "mc_chance_constrained.portfolio"), ("Chance-constrained E[NPV] (SAR)", "mc_chance_constrained.e_npv"),
    ("Chance-constrained P(target)", "mc_chance_constrained.p_target"),
    ("Chance-constrained P(actual capex > budget)", "mc_chance_constrained.p_over_budget"),
    ("Primary rule: carbon 90% + budget 90%", "mc_joint.portfolio"), ("Carbon rule, P(target) on validation", "mc_chance_constrained.p_target_val"),
    ("EVPI (SAR)", "evpi"), ("EVSI motor audit (SAR)", "evsi_audit.evsi"), ("VOI noise floor (SAR)", "voi_noise_floor"),
    ("Decision tree option premium (SAR)", "timing_tree.option_premium"), ("Static break-even gas (USD/MMBtu)", "timing_tree.static_breakeven_usd"),
    ("GBM trigger (USD/MMBtu)", "timing_gbm.trigger_usd"), ("LSMC trigger (USD/MMBtu)", "timing_scan.trigger_usd"),
]


def main(a, b, out):
    A, Bn = json.load(open(a)), json.load(open(b))
    rows = []
    for label, path in KEYS:
        x, y = get(A, path), get(Bn, path)
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            d = y - x
            rel = d / abs(x) if x else None
            changed = abs(d) > 1e-9 * max(1, abs(x))
        else:
            d, rel, changed = None, None, x != y
        rows.append({"kind": "result", "item": label, "old": x, "new": y, "difference": d,
                     "relative": rel, "changed": changed})
    pa = {p["key"]: p for p in A["assumptions"]}
    for p in Bn["assumptions"]:
        q = pa.get(p["key"])
        if q is None:
            rows.append({"kind": "assumption", "item": p["key"], "old": None, "new": p["value"], "changed": True,
                         "detail": "new parameter"})
            continue
        diffs = [f"{f}: {q[f]!r} -> {p[f]!r}" for f in ("value", "status", "dist") if q[f] != p[f]]
        if diffs:
            rows.append({"kind": "assumption", "item": p["key"], "old": q["value"], "new": p["value"], "changed": True,
                         "detail": "; ".join(diffs)})
    keys = ["kind", "item", "old", "new", "difference", "relative", "changed", "detail"]
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in keys})
    for r in rows:
        if r["changed"]:
            print(r["kind"], "|", r["item"], "|", r.get("old"), "->", r.get("new"), "|", r.get("detail") or "")


if __name__ == "__main__":
    main(*sys.argv[1:4])
