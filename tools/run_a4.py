"""Phase A4 (refined) - missing-data intelligence on SYNTHETIC data: demonstration, decision stability, value of
information, calibration and change-detection validation.

    python tools/run_a4.py            # full study (about 15-20 minutes on 2 cores) -> outputs/a4/ + Mezan_A4_Data_Quality.xlsx
    python tools/run_a4.py --fast     # small samples (quick check, about 3 minutes)

Requires outputs/a4/calibration.json (tools/calibrate_a4.py). Does not touch run_all.py or the v1.2 outputs.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from carbon_iq.assumptions import MODEL_VERSION, P  # noqa: E402
from carbon_iq.dataquality import estimate as ES, integrate as I, quality as Q, stability as ST, synth, validate as VA  # noqa: E402

OUT = HERE / "outputs" / "a4"
CASE_TEXT = {
    "C0": "Complete synthetic records (truth) - must reproduce the register model",
    "C1": "Demo dataset as uploaded (gaps unresolved) - decision blocked",
    "C2": "Demo dataset, estimates approved (with uncertainty; target uncertain)",
    "C2f": "As C2 but target held fixed at the estimated baseline (first A4 release treatment)",
    "C3": "Demo dataset, missing months counted as zero - INCORRECT PRACTICE, shown for comparison only",
    "C4": "Demo dataset, missing electricity bills obtained (other estimates kept)",
    "C5": "Severe dataset (6 months of electricity missing) - estimation refused, decision blocked",
}
REVIEW_NOTES = {
    ("2026-05", "natural_gas"): ("approve", "x10 typing error confirmed; use estimate"),
    ("2026-11", "diesel_forklift"): ("override_change", "reviewer confirms no operational change at the plant (the synthetic truth contains none); "
                                                         "fallback estimate used"),
}


def _round(d):
    return {k: (round(v, 6) if isinstance(v, float) else v) for k, v in d.items()}


def demo_ledger():
    raw, changes = synth.demo_incomplete()
    L = ES.Ledger(raw, 2026, source_name="SYNTHETIC demo dataset")
    before = L.annual()
    L.approve_all("demo reviewer")
    for (per, st), (dec, note) in REVIEW_NOTES.items():
        L.decide("PLANT-01", per, st, dec, "demo reviewer", note)
    return raw, changes, L, before


def demo(truth):
    raw, changes, L, before = demo_ledger()
    L.export(str(OUT / "demo"))
    raw.to_csv(OUT / "demo_raw.csv", index=False)
    changes.to_csv(OUT / "demo_changes_applied.csv", index=False)
    L.issues.to_csv(OUT / "demo_issues.csv", index=False)
    Q.summary(L.cells).reset_index().to_csv(OUT / "demo_status_summary.csv", index=False)
    tv = truth.set_index(["period", "stream"]).value
    f = L.final()
    t = f[f.decision != ""].copy()
    t["true_value_synthetic"] = [tv[(p, s)] for p, s in zip(t.period, t.stream)]
    t["used_value"] = t.final_value
    t["rel_err"] = t.final_value / t.true_value_synthetic - 1
    t["covered95"] = (t.final_value - 1.96 * t.final_sd <= t.true_value_synthetic) & (t.true_value_synthetic <= t.final_value + 1.96 * t.final_sd)
    t[["period", "stream", "status", "issues", "value", "method", "estimate", "sd", "low95", "high95", "refusal", "warning",
       "fallback_method", "fallback_estimate", "decision", "final_label", "used_value", "final_sd", "true_value_synthetic", "rel_err",
       "covered95"]].to_csv(OUT / "demo_estimates_vs_truth.csv", index=False)
    ann = L.annual()
    ann.insert(0, "phase", "after review"); before.insert(0, "phase", "as uploaded")
    pd.concat([before, ann]).to_csv(OUT / "demo_annual_totals.csv", index=False)
    return L


def cases(L, truth):
    rows, blocked, act = [], {}, {}
    Lt = ES.Ledger(truth, 2026, source_name="truth")
    act["C0"] = I.activity_from_annual(Lt.annual())
    raw, _ = synth.demo_incomplete()
    try:
        I.activity_from_annual(ES.Ledger(raw, 2026).annual())
    except I.IncompleteData as e:
        blocked["C1"] = str(e)
    act["C2"] = I.activity_from_annual(L.annual())
    act["C2f"] = act["C2"]
    act["C3"] = I.naive_zero_activity(L)
    fin = L.final(); el = fin[fin.stream == "electricity"]
    tv = truth.set_index(["period", "stream"]).value
    imp = dict(act["C2"])
    imp["elec_mwh"] = (float(sum(tv[(p, "electricity")] if lab.startswith("estimated") else val
                                 for p, lab, val in zip(el.period, el.final_label, el.final_value))), 0.0)
    act["C4"] = imp
    Ls = ES.Ledger(synth.demo_severe(), 2026); Ls.approve_all("demo reviewer")
    try:
        I.activity_from_annual(Ls.annual())
    except I.IncompleteData as e:
        blocked["C5"] = str(e) + " | " + Ls.table[(Ls.table.stream == "electricity") & (Ls.table.refusal != "")].refusal.iloc[0]
    results = {}
    for c in CASE_TEXT:
        if c in blocked:
            rows.append(dict(case=c, description=CASE_TEXT[c], status="BLOCKED", detail=blocked[c])); continue
        r, _ = I.run_decisions(act[c], uncertain_target=(c != "C2f"))
        results[c] = r
        sd = {k: s for k, (_, s) in act[c].items() if s > 0}
        rows.append(dict(case=c, description=CASE_TEXT[c], status="computed",
                         detail="estimated sd: " + ", ".join(f"{k} {s:,.1f}" for k, s in sd.items()) if sd else "no estimated values",
                         **_round(r)))
    return pd.DataFrame(rows), act, results


def stability(act, fast):
    K = 15 if fast else 40
    out, rules, margins, switches, pert = {}, [], [], [], []
    for c in ("C0", "C2", "C4"):
        a = ST.assess(act[c], K=K if c != "C0" else 1, with_switch=(c == "C2"))
        out[c] = a
        rules += [dict(case=c, **r) for r in a["rules"]]
        margins += [dict(case=c, **m) for m in a["margins"]]
        switches += [dict(case=c, **s) for s in a["switch_points"]]
        pert += [dict(case=c, draw=i, **d) for i, d in enumerate(a["draws"])]
    pd.DataFrame(rules).to_csv(OUT / "stability_rules.csv", index=False)
    pd.DataFrame(margins).to_csv(OUT / "stability_margins.csv", index=False)
    pd.DataFrame(switches).to_csv(OUT / "stability_switch_points.csv", index=False)
    pd.DataFrame(pert).to_csv(OUT / "stability_perturbation_draws.csv", index=False)
    # Monte Carlo sampling check of the knife-edge: A+B target probability on other scenario seeds (complete data)
    seeds = [20261024, 20261026, 20261027, 20261028, 20261029] if not fast else [20261024, 20261026]
    mc = [dict(seed=s, **{k: v for k, v in I.run_decisions(act["C0"], seed=s)[0].items()
                          if k in ("D3", "D4", "p_target[A+B]", "p_target[A+C+D]", "p_target[A+B+C]")}) for s in seeds]
    pd.DataFrame(mc).to_csv(OUT / "stability_seed_check.csv", index=False)
    return out, rules, mc


def information(act, fast):
    rows = I.information_value(act["C2"], n=20000,
                               seeds=(20261024, 20261026, 20261027) if not fast else (20261024, 20261026),
                               n_nodes=16 if not fast else 8)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "information_value.csv", index=False)
    v12 = json.load(open(HERE / "outputs" / "results.json"))
    ctx = dict(evpi_v12=v12.get("evpi"), evsi_motor_audit_v12=(v12.get("evsi_audit") or {}).get("evsi") if isinstance(v12.get("evsi_audit"), dict) else v12.get("evsi_audit"),
               staff_rate_sar_per_hour=I.STAFF_RATE_SAR_H)
    return df, ctx


def validation(fast, cal):
    nb, nv, nbr = (20, 10, 16) if fast else (150, 50, 80)
    CAL, RHO = cal["cal_monthly"], cal["rho_annual"]
    sets = [("base (held-out, seed 4404)", "base", 4404, nb, tuple(VA.SCENARIOS)[:6]),
            ("high_noise", "high_noise", 6601, nv, ("random_3", "block_3", "rate_25")),
            ("flat_season", "flat_season", 6602, nv, ("random_3", "block_3", "rate_25")),
            ("trend", "trend", 6603, nv, ("random_3", "block_3", "rate_25")),
            ("break_intensity", "break_intensity", 7701, nbr, ("after_break", "random_3")),
            ("break_production", "break_production", 7702, nbr, ("after_break", "random_3"))]
    cov, rel, summ, chg, store = [], [], [], [], {}
    for label, variant, seed, n, scen in sets:
        cn, an = VA.study(n, seed=seed, scenarios=scen, variant=variant, detect_changes=True, workers=2)
        co, ao = VA.study(n, seed=seed, scenarios=scen, variant=variant, detect_changes=False, workers=2)
        store[label] = (cn, an, co, ao)
        for setting, c, a, f, r in (("before (A4 v1: no change detection, t-interval, linear annual sum)", co, ao, 1.0, 1.0),
                                    ("after (refined: change detection, calibrated)", cn, an, CAL, RHO)):
            for row in VA.coverage_rows(c, a, f, r, setting):
                cov.append(dict(dataset=label, **row))
            for row in VA.reliability(c, f, setting):
                rel.append(dict(dataset=label, **row))
            s = VA.summarise(c, a, f, r); s.insert(0, "setting", setting); s.insert(0, "dataset", label)
            summ.append(s)
        chg.append(VA.change_detection_summary(cn, an, co, label))
    cov, rel, summ = pd.DataFrame(cov), pd.DataFrame(rel), pd.concat(summ)
    cov.to_csv(OUT / "calibration_coverage.csv", index=False)
    rel.to_csv(OUT / "calibration_reliability.csv", index=False)
    summ.to_csv(OUT / "validation_summary.csv", index=False)
    chg = pd.DataFrame(chg); chg.to_csv(OUT / "change_detection_summary.csv", index=False)
    size = pd.concat([VA.detection_by_size(store[k][1]).assign(dataset=k) for k in ("break_intensity", "break_production")])
    size.to_csv(OUT / "change_detection_by_size.csv", index=False)
    cn, an, co, ao = store["base (held-out, seed 4404)"]
    cn.to_csv(OUT / "validation_cells.csv", index=False)
    an.to_csv(OUT / "validation_annual.csv", index=False)
    bys = VA.by_stream(cn, CAL); bys.to_csv(OUT / "validation_by_stream.csv", index=False)
    bym = VA.by_method(cn); bym.to_csv(OUT / "validation_by_method.csv", index=False)
    # width check: annual half-width before (linear) vs after (rho) on the base test set
    return cov, rel, summ, chg, size, bys, bym, dict(n_base=nb, n_variant=nv, n_break=nbr)


def main(fast=False):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "charts").mkdir(exist_ok=True)
    cal = json.load(open(OUT / "calibration.json"))
    assert abs(cal["cal_monthly"] - ES.CAL_MONTHLY) < 1e-4 and abs(cal["rho_annual"] - ES.RHO_ANNUAL) < 1e-9, "estimate.py constants differ from calibration.json"
    truth = synth.truth_case()
    L = demo(truth)
    dec, act, res = cases(L, truth)
    dec.to_csv(OUT / "decision_comparison.csv", index=False)
    c0 = res["C0"]
    # complete synthetic data must reproduce the main pipeline on the current register (model v1.3 since A5)
    ds = {d["id"]: d for d in json.load(open(HERE / "outputs" / "results.json"))["decision_scenarios"]}
    reproduces = (c0["D1"], c0["D2"], c0["D3"], c0["D4"]) == (ds["D1"]["portfolio"], ds["D2"]["portfolio"], ds["D3"]["portfolio"],
                                                               ds["D4"]["portfolio"]) and abs(c0["D1_npv"] - ds["D1"]["npv_base_inputs"]) < 0.01
    sens = I.sensitivity_bounds(act["C2"]); pd.DataFrame(sens).to_csv(OUT / "estimate_sensitivity_bounds.csv", index=False)
    stab, stab_rules, seedchk = stability(act, fast)
    voi, voi_ctx = information(act, fast)
    sup, sres = ES.supplier_factors(synth.suppliers_demo(), P["ef_steel_incumbent"].value, 1.47, 2.34,
                                    "worldsteel 2025 global average 1.92 tCO2/t (range DRI-EAF 1.47 - BF-BOF 2.34)")
    sup.to_csv(OUT / "supplier_factors_demo.csv", index=False)
    cov, rel, summ, chg, size, bys, bym, nsz = validation(fast, cal)
    fc = VA.failure_cases(); fc.to_csv(OUT / "failure_cases.csv", index=False)
    est = pd.read_csv(OUT / "demo_estimates_vs_truth.csv")
    out = dict(
        note="All A4 data are SYNTHETIC (generated by carbon_iq/dataquality/synth.py). Results test the logic and calibration "
             "of the engine; they are not evidence of performance on real industrial records.",
        rules=dict(MIN_MEASURED=ES.MIN_MEASURED, MAX_GAP_RUN=ES.MAX_GAP_RUN, MAX_REL_ERR=ES.MAX_REL_ERR, ROBUST_Z=Q.ROBUST_Z,
                   CP_ALPHA=ES.CP_ALPHA, CP_MIN_SHIFT=ES.CP_MIN_SHIFT, CP_MIN_SEGMENT=ES.CP_MIN_SEGMENT,
                   CP_MIN_SEGMENT_END=ES.CP_MIN_SEGMENT_END, MIN_REGIME=ES.MIN_REGIME, PROD_ANOMALY=ES.PROD_ANOMALY,
                   CAL_MONTHLY=ES.CAL_MONTHLY, RHO_ANNUAL=ES.RHO_ANNUAL),
        calibration=cal, complete_data_reproduces_pipeline=bool(reproduces), register_version=__import__("carbon_iq.assumptions", fromlist=["MODEL_VERSION"]).MODEL_VERSION,
        demo=dict(issues=int(len(L.issues)), gaps=int((L.table.decision != "").sum()),
                  covered95=int(est.covered95.sum()), gaps_estimated=int(est.used_value.notna().sum()),
                  max_abs_rel_err=float(est.rel_err.abs().max()), raw_sha256=L.raw_hash,
                  warnings=[w for w in L.table.warning if w], refusals=[r for r in L.table.refusal if r]),
        decisions={c: {k: res[c][k] for k in ("D1", "D2", "D3", "D4", "scope12", "target_t", "target_sd", "p_target[A+B]", "p_budget[A+B]",
                                                "p_target[A+C+D]", "p_target[A+B+C]", "min_budget", "D1_npv")} for c in res},
        blocked=list(dec[dec.status == "BLOCKED"].case),
        stability=stab_rules, seed_check=seedchk, information_value=json.loads(voi.to_json(orient="records")), voi_context=voi_ctx,
        sensitivity_changes=[s for s in sens if (s["D1"], s["D2"], s["D3"], s["D4"]) != (res["C2"]["D1"], res["C2"]["D2"], res["C2"]["D3"], res["C2"]["D4"])],
        supplier=sres, validation_sizes=nsz,
        coverage=json.loads(cov.to_json(orient="records")), reliability=json.loads(rel.to_json(orient="records")),
        change_detection=json.loads(chg.to_json(orient="records")), change_by_size=json.loads(size.to_json(orient="records")),
        failure_cases=json.loads(fc.to_json(orient="records")))
    charts(L, truth, res, rel, cov, voi, chg, seedchk)
    from carbon_iq.dataquality import workbook_a4
    from carbon_iq.recalc import recalc
    wbp = HERE / "Mezan_A4_Data_Quality.xlsx"
    extra = [
        ("Calibration", "Empirical coverage vs nominal confidence (synthetic hold-out sets)",
         [("Calibration fitted on seed 5501 (100 facilities); never on the sets below", pd.DataFrame([cal]).drop(columns=["scenarios"])),
          ("95% coverage with Wilson 95% intervals, by dataset, setting and scenario", cov),
          ("Coverage at several nominal levels (monthly)", rel)]),
        ("Change detection", "Operational-change detection on synthetic data with and without injected changes",
         [("Summary (rates per stream-year with gaps; 'before' = engine without detection on the same data)", chg),
          ("Detection by size of the injected change", size)]),
        ("Stability", "Decision stability: Monte Carlo margins, data perturbation and switch points",
         [("Status by rule", pd.DataFrame(stab_rules)), ("Margins", pd.concat([pd.DataFrame(stab[c]["margins"]).assign(case=c) for c in stab])),
          ("Switch points (C2)", pd.DataFrame(stab["C2"]["switch_points"])), ("Other Monte Carlo seeds (complete data)", pd.DataFrame(seedchk))]),
        ("Information value", "Pre-posterior value of collecting missing records (costs hypothetical)", [("By measurement and rule", voi)]),
    ]
    workbook_a4.build(L, truth, dec, [("Summary by dataset, setting and masking scenario", summ), ("By stream (base, after)", bys),
                                       ("Each candidate method on the same gaps", bym), ("Failure cases", fc)], wbp, extra=extra)
    out["workbook_recalc"] = recalc(wbp)
    with open(OUT / "a4_results.json", "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    print(json.dumps(dict(reproduces_pipeline=reproduces, decisions=out["decisions"], stability=[(r["case"], r["rule"], r["choice"], r["status"])
                                                                                        for r in stab_rules],
                          workbook={k: out["workbook_recalc"].get(k) for k in ("status", "total_formulas", "total_errors")}), indent=1, default=str))
    print(voi[["measurement", "rule", "prior_choice", "value_npv", "value_npv_sd_seeds", "d_p_target", "cost_sar", "net_value"]].round(1).to_string())
    print(cov[(cov.scenario == "all")][["dataset", "setting", "monthly_coverage", "monthly_ci_low", "monthly_ci_high", "annual_coverage",
                                         "annual_ci_low", "annual_halfwidth"]].round(3).to_string())
    print(chg.round(3).T.to_string())
    return out


def charts(L, truth, res, rel, cov, voi, chg, seedchk):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    NAVY, ORANGE, GREEN, RED, GREY = "#1F3A5F", "#E07B39", "#2E8B57", "#C0392B", "#888888"
    # 1. electricity demo
    f = L.final(); e = f[f.stream == "electricity"].sort_values("period")
    tv = truth[(truth.stream == "electricity") & truth.period.str.startswith("2026")].sort_values("period").value.values
    x = np.arange(12); lab = [p[-2:] for p in e.period]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    meas = e.status.isin(["measured", "converted"]).values
    ax.bar(x[meas], e.final_value.values[meas], color=NAVY, label="Measured (incl. kWh converted)")
    est = e.final_label.str.startswith("estimated").values
    ax.bar(x[est], e.final_value.values[est], color=ORANGE, label="Estimated (approved)")
    ax.errorbar(x[est], e.final_value.values[est], yerr=1.96 * e.final_sd.values[est], fmt="none", ecolor="black", capsize=4, label="95% interval (calibrated)")
    ax.scatter(x, tv, color=RED, marker="_", s=250, zorder=4, label="Synthetic truth")
    ax.set_xticks(x, lab); ax.set_xlabel("Month 2026"); ax.set_ylabel("MWh"); ax.set_title("Electricity: gaps detected, estimated and checked (synthetic)")
    ax.legend(fontsize=7, ncol=2, loc="upper left"); ax.set_ylim(0, max(tv) * 1.35)
    fig.tight_layout(); fig.savefig(OUT / "charts" / "a4_1_electricity_demo.png", dpi=160); plt.close(fig)
    # 2. reliability (base) and 95% coverage by dataset
    fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.8))
    b = rel[rel.dataset.str.startswith("base")]
    for setting, col, mk in ((b.setting.unique()[0], GREY, "o"), (b.setting.unique()[1], NAVY, "s")):
        r = b[b.setting == setting]
        ax[0].errorbar(r.nominal, r.empirical, yerr=[r.empirical - r.ci_low, r.ci_high - r.empirical], fmt=mk + "-", color=col,
                       label=setting.split(" (")[0], capsize=3)
    ax[0].plot([0.45, 1], [0.45, 1], color=RED, ls="--", lw=1, label="perfect calibration")
    ax[0].set_xlabel("nominal coverage"); ax[0].set_ylabel("empirical coverage"); ax[0].set_title("Monthly intervals, held-out base set", fontsize=9)
    ax[0].legend(fontsize=7)
    c = cov[cov.scenario == "all"]
    ds = list(dict.fromkeys(c.dataset))
    for i, (setting, col) in enumerate(((c.setting.unique()[0], GREY), (c.setting.unique()[1], NAVY))):
        r = c[c.setting == setting].set_index("dataset").loc[ds]
        xx = np.arange(len(ds)) + (i - 0.5) * 0.35
        ax[1].errorbar(xx, r.monthly_coverage, yerr=[r.monthly_coverage - r.monthly_ci_low, r.monthly_ci_high - r.monthly_coverage],
                       fmt="o", color=col, capsize=3, label=f"monthly, {setting.split(' (')[0]}")
        ax[1].scatter(xx, r.annual_coverage, marker="^", color=col, s=30, label=f"annual, {setting.split(' (')[0]}")
    ax[1].axhline(0.95, color=RED, ls="--", lw=1)
    ax[1].set_xticks(np.arange(len(ds)), [d.split(" (")[0] for d in ds], rotation=25, fontsize=7); ax[1].set_ylim(0.6, 1.01)
    ax[1].set_title("95% intervals: coverage by synthetic dataset", fontsize=9); ax[1].legend(fontsize=6, loc="lower left")
    fig.tight_layout(); fig.savefig(OUT / "charts" / "a4_2_calibration.png", dpi=160); plt.close(fig)
    # 3. decisions across cases with Monte Carlo error bars
    cs = [k for k in ("C0", "C2", "C4", "C3") if k in res]
    fig, ax = plt.subplots(figsize=(8, 3.9))
    w = 0.26; xx = np.arange(len(cs))
    se = lambda p: 2 * np.sqrt(p * (1 - p) / 20000)  # noqa: E731
    for off, port, col in ((-w, "A+B", NAVY), (0, "A+B+C", "#7A5195"), (w, "A+C+D", GREEN)):
        pp = np.array([res[k][f"p_target[{port}]"] for k in cs])
        ax.bar(xx + off, pp, w, color=col, yerr=se(pp), capsize=3, label=f"{port}: P(meet target) ± 2 MC SE")
    ax.axhline(res["C0"]["alpha_saa"], color=RED, ls="--", lw=1, label="tightened 90% requirement (0.9035)")
    ax.set_ylim(0.85, 1.005); ax.set_xticks(xx, ["C0 complete", "C2 estimated", "C4 bills obtained", "C3 zeros (wrong)"])
    for i, k in enumerate(cs):
        ax.text(i, 0.855, f"D3: {res[k]['D3']}\nD1: {res[k]['D1']}", ha="center", fontsize=7)
    ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False)
    ax.set_title(f"Probability of meeting the target by case (synthetic demo; model v{MODEL_VERSION})", fontsize=9)
    fig.tight_layout(); fig.savefig(OUT / "charts" / "a4_3_decisions.png", dpi=160); plt.close(fig)
    # 4. information value under D3
    v = voi[voi.rule == "D3"].copy()
    fig, ax = plt.subplots(figsize=(8, 4.0))
    yy = np.arange(len(v))
    ax.barh(yy, v.value_npv / 1e3, xerr=2 * v.value_npv_sd_seeds.fillna(0) / 1e3, color=NAVY, capsize=3, label="expected-NPV value of the information (± 2 sd across seeds)")
    ax.scatter(v.cost_sar / 1e3, yy, color=RED, marker="|", s=250, zorder=3, label="hypothetical cost")
    ax.set_yticks(yy, [f"{m}: {k}" for m, k in zip(v.measurement, v["keys"].str.replace("_", " ").str.slice(0, 40))], fontsize=7)
    ax.invert_yaxis(); ax.set_xlabel("SAR thousand"); ax.set_title("Value of collecting missing records under the carbon rule D3 (synthetic demo)", fontsize=9)
    ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, frameon=False)
    fig.tight_layout(); fig.savefig(OUT / "charts" / "a4_4_information_value.png", dpi=160); plt.close(fig)
    # 5. change detection: after-break error before/after
    cb = chg[chg.after_break_gaps.notna()] if "after_break_gaps" in chg else chg.iloc[0:0]
    if len(cb):
        fig, ax = plt.subplots(figsize=(7, 3.2))
        xx = np.arange(len(cb))
        ax.bar(xx - 0.2, cb.after_break_mape_old * 100, 0.4, color=GREY, label="without change detection")
        ax.bar(xx + 0.2, cb.after_break_mape_new * 100, 0.4, color=NAVY, label="with change detection (estimated gaps)")
        for i, r in enumerate(cb.itertuples()):
            ax.text(i + 0.2, r.after_break_mape_new * 100 + 0.5, f"refused {r.after_break_refused_new:.0%}", ha="center", fontsize=7)
        ax.set_xticks(xx, cb.dataset); ax.set_ylabel("mean |error| of gaps after the change, %")
        ax.set_title("Gaps after an operational change (synthetic)", fontsize=9); ax.legend(fontsize=7)
        fig.tight_layout(); fig.savefig(OUT / "charts" / "a4_5_change_detection.png", dpi=160); plt.close(fig)


if __name__ == "__main__":
    main(fast="--fast" in sys.argv)
