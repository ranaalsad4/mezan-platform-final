"""Phase A4 - missing-data intelligence (all data synthetic)."""
import json

import numpy as np
import pandas as pd
import pytest

from carbon_iq import uncertainty as U
from carbon_iq.assumptions import base_values, use_profile
from carbon_iq.dataquality import estimate as ES, integrate as I, quality as Q, synth, validate as VA

SITE = "PLANT-01"


@pytest.fixture
def v12():
    """Tests that document the A4 findings on the v1.2 register (knife-edge D3) run under profile 'v1.2' since A5."""
    with use_profile("v1.2"):
        yield


@pytest.fixture(scope="module")
def demo():
    raw, changes = synth.demo_incomplete()
    return raw, changes, ES.Ledger(raw, 2026, source_name="demo")


def cell(L, period, stream):
    return L.table[(L.table.period == period) & (L.table.stream == stream)].iloc[0]


def test_truth_totals_equal_register():
    t = synth.truth_case(); b = base_values()
    cur = t[t.period.str.startswith("2026")].groupby("stream").value.sum()
    assert cur["electricity"] == pytest.approx(b["elec_mwh"]) and cur["natural_gas"] == pytest.approx(b["gas_gj"])
    assert cur["steel_purchased"] == pytest.approx(b["steel_t"]) and cur["production"] == pytest.approx(b["production_t"])


def test_every_injected_problem_is_detected(demo):
    _, _, L = demo
    exp = {("2026-06", "electricity"): "MISSING_ROW", ("2026-07", "electricity"): "MISSING_ROW",
           ("2026-10", "electricity"): "UNIT_CONVERTED", ("2026-12", "electricity"): "SUSPECTED_MISSING_ZERO",
           ("2026-03", "natural_gas"): "BLANK_OR_NONNUMERIC", ("2026-09", "natural_gas"): "DUPLICATE_CONFLICT",
           ("2026-05", "natural_gas"): "OUTLIER", ("2026-11", "diesel_forklift"): "MISSING_ROW",
           ("2026-04", "diesel_forklift"): "DUPLICATE_IDENTICAL", ("2026-02", "production"): "NEGATIVE_VALUE",
           ("2026-08", "steel_purchased"): "MISSING_ROW"}
    for (per, s), code in exp.items():
        assert any(i.startswith(code) for i in cell(L, per, s).issues), (per, s, code)
    assert cell(L, "2026-10", "electricity").status == "converted"
    assert cell(L, "2026-04", "diesel_forklift").status == "measured"       # identical duplicate collapsed, value kept
    assert cell(L, "2026-09", "natural_gas").status == "missing"            # conflicting duplicate: no value chosen


def test_kwh_conversion_exact(demo):
    raw, _, L = demo
    r = raw[(raw.period == "2026-10") & (raw.stream == "electricity")].iloc[0]
    assert cell(L, "2026-10", "electricity").value == pytest.approx(r.value / 1000)


def test_zero_rules():
    t = synth.truth_case()
    # generator zeros (intermittent) are legitimate and stay measured zeros
    L = ES.Ledger(t, 2026)
    g = L.table[(L.table.stream == "diesel_genset") & (L.table.period == "2026-01")].iloc[0]
    assert g.status == "measured" and g.value == 0 and any(i.startswith("LEGITIMATE_ZERO") for i in g.issues)
    # a continuous stream at zero while production is positive is suspected missing, not zero
    t2 = t.copy(); m = (t2.stream == "electricity") & (t2.period == "2026-03"); t2.loc[m, "value"] = 0.0
    L2 = ES.Ledger(t2, 2026)
    assert cell(L2, "2026-03", "electricity").status == "suspected_zero"
    # the same zero with a documented shutdown (production zero + note) is legitimate
    t3 = t2.copy(); t3.loc[(t3.stream == "production") & (t3.period == "2026-03"), "value"] = 0.0
    t3.loc[m, "note"] = "plant shutdown"
    L3 = ES.Ledger(t3, 2026)
    assert cell(L3, "2026-03", "electricity").status == "measured"
    # a suspected zero can only become zero through an explicit user confirmation
    L2.decide(SITE, "2026-03", "electricity", "confirm_zero", "tester")
    f = L2.final(); assert f[(f.stream == "electricity") & (f.period == "2026-03")].final_label.iloc[0] == "zero confirmed (user)"


def test_missing_never_becomes_zero(demo):
    _, _, L = demo
    f = L.final()
    gaps = f[f.decision == "pending"]
    assert gaps.final_value.isna().all() and gaps.final_label.str.startswith("UNRESOLVED").all()
    a = L.annual()
    assert a[~a.complete].total.isna().all()
    with pytest.raises(I.IncompleteData):
        I.activity_from_annual(a)


def test_estimates_have_methods_intervals_and_cover_demo_truth(demo):
    _, _, L = demo
    tv = synth.truth_case().set_index(["period", "stream"]).value
    t = L.table[L.table.decision == "pending"]
    assert len(t) == 9
    # forklift Nov: the synthetic truth happens to rise ~12% in Sep-Dec; the change test flags it and, with only
    # three months in the 'new regime', refuses - a documented false alarm that a reviewer may override
    fk = cell(L, "2026-11", "diesel_forklift")
    assert fk.refusal.startswith("OPERATIONAL_CHANGE") and "OPERATIONAL_CHANGE" in fk.warning and fk.fallback_estimate > 0
    t = t[t.refusal == ""]
    assert len(t) == 8
    for _, r in t.iterrows():
        assert r.method in ES.METHODS[r.stream] and r.sd > 0 and r.low95 < r.estimate < r.high95
        assert set(json.loads(r.candidates)) <= set(ES.METHODS[r.stream])
        assert abs(r.estimate / tv[(r.period, r.stream)] - 1) < 0.10
    covered = sum(r.low95 <= tv[(r.period, r.stream)] <= r.high95 for _, r in t.iterrows())
    assert covered == 8


def test_refusal_rules():
    L = ES.Ledger(synth.demo_severe(), 2026)
    assert cell(L, "2026-05", "electricity").refusal.startswith("GAP_TOO_LONG")
    t = synth.truth_case(); t = t[t.period.str.startswith("2026")]
    keep = t[(t.stream != "electricity") | t.period.isin([f"2026-{m:02d}" for m in range(1, 6)])]
    L2 = ES.Ledger(keep, 2026)
    assert cell(L2, "2026-08", "electricity").refusal.startswith("TOO_FEW_MEASURED")
    with pytest.raises(ValueError):
        L2.decide(SITE, "2026-08", "electricity", "approve", "tester")


def test_lineage_preserves_original_and_records_decisions(demo):
    raw, _, _ = demo
    before = raw.copy(deep=True)
    L = ES.Ledger(raw, 2026)
    h = L.raw_hash
    L.approve_all("tester")
    L.decide(SITE, "2026-05", "natural_gas", "keep", "tester", "verified meter reading")
    pd.testing.assert_frame_equal(raw, before)                   # caller's data untouched
    pd.testing.assert_frame_equal(L.raw, before)                 # ledger copy untouched
    assert L.raw_hash == h
    lin = L.lineage()
    g = lin[(lin.stream == "natural_gas") & (lin.period == "2026-05")].iloc[0]
    assert g.final_label == "outlier kept (user)" and g.value == g.final_value and g.decided_by == "tester"
    e = lin[(lin.stream == "electricity") & (lin.period == "2026-06")].iloc[0]
    assert e.final_label.startswith("estimated") and e.method_text and e.decision == "approved"
    assert np.isnan(e.value)                                     # the observed value column stays empty
    assert [x["action"] for x in L.events][0] == "load" and len(L.events) >= 9    # load + 7 bulk approvals + keep


def test_decision_rules_reject_invalid_actions(demo):
    _, _, L0 = demo
    import copy
    L = copy.deepcopy(L0)
    with pytest.raises(ValueError):
        L.decide(SITE, "2026-06", "electricity", "confirm_zero", "t")     # not a suspected zero
    with pytest.raises(ValueError):
        L.decide(SITE, "2026-01", "electricity", "approve", "t")          # measured month needs no decision


def test_complete_data_reproduce_v12_exactly(v12):
    L = ES.Ledger(synth.truth_case(), 2026)
    assert (L.table.decision == "").all()
    r, _ = I.run_decisions(I.activity_from_annual(L.annual()))
    assert (r["D1"], r["D2"], r["D3"], r["D4"]) == ("A+B", "A+B", "A+C+D", "none feasible")
    assert r["target_sd"] == 0.0
    assert r["D1_npv"] == pytest.approx(337930.7073, abs=0.01) and r["D2_e_npv"] == pytest.approx(1278455.6591, abs=0.01)
    assert r["p_target[A+B]"] == 0.90275 and r["min_budget"] == pytest.approx(5202422.81, abs=0.01)
    assert r["scope12"] == pytest.approx(8778.3315, abs=1e-3) and r["target_t"] == pytest.approx(1316.7497, abs=1e-3)


def test_estimated_case_and_naive_zero(demo, v12):
    import copy
    L = copy.deepcopy(demo[2]); L.approve_all("t"); L.decide(SITE, "2026-05", "natural_gas", "approve", "t")
    with pytest.raises(I.IncompleteData):                           # the change refusal still blocks the decision
        I.activity_from_annual(L.annual())
    L.decide(SITE, "2026-11", "diesel_forklift", "override_change", "t", "no change at the plant")
    assert cell(L, "2026-11", "diesel_forklift").decision == "change_overridden"
    assert L.final().set_index(["period", "stream"]).final_label[("2026-11", "diesel_forklift")].endswith("change override)")
    act = I.activity_from_annual(L.annual())
    assert set(act) == set(I.ACTIVITY_KEYS)                         # every register stream mapped (incl. production_t)
    assert all(s > 0 for k, (v, s) in act.items() if k in ("elec_mwh", "gas_gj", "diesel_forklift_l", "steel_t"))
    r, _ = I.run_decisions(act)
    assert (r["D1"], r["D2"], r["D4"]) == ("A+B", "A+B", "none feasible")
    assert r["target_sd"] > 0                                       # an estimated baseline makes the target uncertain
    z, _ = I.run_decisions(I.naive_zero_activity(L))
    assert z["scope12"] < r["scope12"] * 0.8                       # zeros understate emissions
    assert z["D4"] != "none feasible"                              # and make an unaffordable rule look feasible


def test_estimation_uncertainty_widens_simulation():
    b = base_values()
    act = {k: (float(b[k]), 0.0) for k in I.ACTIVITY_KEYS}
    _, prm, z = I.params_for(act, n=4000)
    p0, _ = I._apply(act, prm, z, b)
    act["elec_mwh"] = (float(b["elec_mwh"]), 300.0)
    p1, _ = I._apply(act, prm, z, b)
    assert p1["elec_mwh"].std() > p0["elec_mwh"].std()
    assert p1["elec_mwh"].mean() == pytest.approx(p0["elec_mwh"].mean(), rel=0.01)


def _demo_activity():
    raw, _ = synth.demo_incomplete(); L = ES.Ledger(raw, 2026); L.approve_all("t")
    L.decide(SITE, "2026-05", "natural_gas", "approve", "t")
    L.decide(SITE, "2026-11", "diesel_forklift", "override_change", "t")
    return I.activity_from_annual(L.annual())


def test_preposterior_value_of_information(v12):
    act = _demo_activity()
    pp = I.preposterior(act, ("elec_mwh",), n=20000, n_nodes=8)
    assert pp["D3"]["prior_choice"] == "A+C+D" and pp["D3"]["d_npv"] > 0       # bills can reveal that A+B suffices
    assert pp["D4"]["d_npv"] == 0 and pp["D4"]["choices"] == {"none feasible": 1.0}   # capex risk is not data-driven
    assert pp["D2"]["d_npv"] == pytest.approx(0, abs=1e-6)
    # an irrelevant measurement (production does not enter the emissions) has exactly zero value: no noise floor
    pz = I.preposterior(act, ("production_t",), n=20000, n_nodes=8)
    assert all(pz[r]["d_npv"] == pytest.approx(0, abs=1e-6) and pz[r]["d_p_target"] == pytest.approx(0, abs=1e-12) for r in pz)
    # the adaptive policy still meets the carbon chance constraint overall
    assert pp["D3"]["p_post"] >= U.alpha_saa(0.9, 20000) - 1e-9


def test_information_value_table_has_costs_and_net(v12):
    rows = I.information_value(_demo_activity(), measurements=[I.MEASUREMENTS[0], I.MEASUREMENTS[4]], n=20000,
                               seeds=(20261024,), n_nodes=8)
    d3 = {r["measurement"]: r for r in rows if r["rule"] == "D3"}
    assert d3["M1"]["cost_sar"] == 4 * I.STAFF_RATE_SAR_H and d3["M1"]["net_value"] == pytest.approx(d3["M1"]["value_npv"] - d3["M1"]["cost_sar"])
    assert d3["M5"]["value_npv"] == pytest.approx(0, abs=1e-6) and d3["M5"]["net_value"] < 0


def test_uncertain_target_offset_is_exact():
    b = base_values(); p = dict(b); p["elec_mwh"] += 100; p["gas_gj"] += 500; p["diesel_forklift_l"] += 1000
    expect = b["target_share"] * (b["ef_grid"] * 100 + b["ef_gas"] * 500 + b["ef_diesel"] * 1000)
    from carbon_iq import engine as E
    assert E.target_t(p) - E.target_t(b) == pytest.approx(expect, rel=1e-12)
    act = I.register_activity(); act["elec_mwh"] = (float(b["elec_mwh"]), 300.0)
    r1, _ = I.run_decisions(act); r0, _ = I.run_decisions(act, uncertain_target=False)
    assert r1["target_sd"] == pytest.approx(b["target_share"] * b["ef_grid"] * 300, rel=0.02)
    assert r1["p_target[A+B]"] != r0["p_target[A+B]"]                  # the target uncertainty enters the chance constraint


def test_stability_flags_knife_edge_but_not_robust_rules(v12):
    from carbon_iq.dataquality import stability as ST
    a = ST.assess(I.register_activity(), K=3, with_switch=False)
    st = {r["rule"]: r for r in a["rules"]}
    assert st["D3"]["sampling_unstable"] and st["D3"]["status"].startswith("UNSTABLE")      # A+B at 0.90275 vs 0.9035
    assert st["D1"]["status"] == st["D2"]["status"] == st["D4"]["status"] == "STABLE"
    d4 = [m for m in a["margins"] if m["rule"] == "D4" and m["threshold"].startswith("best P(capex")][0]
    assert d4["margin_se"] < -20                                                              # infeasibility is robust


def test_switch_point_is_bracketed(v12):
    from carbon_iq.dataquality import stability as ST
    act = _demo_activity()
    sw = [s for s in ST.switch_points(act, keys=["elec_mwh"]) if s["rule"] == "D3" and s["switch_rel"]]
    assert sw
    s = sw[0]
    val, sd = act["elec_mwh"]
    sign = -1 if s["direction"] == "down" else 1
    a = dict(act); a["elec_mwh"] = (val * (1 + sign * s["switch_rel"]), sd)
    assert I.run_decisions(a)[0]["D3"] != s["choice"]
    a["elec_mwh"] = (val * (1 + sign * s["switch_rel"] * 0.9), sd)
    assert I.run_decisions(a)[0]["D3"] == s["choice"] or s["switch_rel"] < 0.003


def test_supplier_proxy_labelled_and_missing_quantity_refused():
    s, r = ES.supplier_factors(synth.suppliers_demo(), 1.92, 1.47, 2.34, "worldsteel proxy")
    assert r["complete"] and r["share_proxy"] == 1.0 and (s.ef_label.str.startswith("proxy")).all()
    assert r["ef_weighted"] == pytest.approx(1.92)
    bad = synth.suppliers_demo(); bad.loc[0, "quantity_t"] = None
    _, r2 = ES.supplier_factors(bad, 1.92, 1.47, 2.34, "worldsteel proxy")
    assert not r2["complete"]


def test_unknown_unit_is_not_guessed():
    t = synth.truth_case(); m = (t.stream == "natural_gas") & (t.period == "2026-06"); t.loc[m, "unit"] = "therm"
    L = ES.Ledger(t, 2026)
    c = cell(L, "2026-06", "natural_gas")
    assert c.status == "missing" and any(i.startswith("UNKNOWN_UNIT") for i in c.issues)


def test_validation_small_study_is_calibrated_reasonably():
    cells, ann = VA.study(n_facilities=6, seed=77, scenarios=("random_1", "block_3", "block_6"))
    s = VA.summarise(cells, ann, ES.CAL_MONTHLY, ES.RHO_ANNUAL).set_index("scenario")
    assert s.loc["block_6", "refused_share"] == 1.0
    assert s.loc["random_1", "monthly_coverage95"] >= 0.8
    assert s.loc["random_1", "annual_mape"] < 0.03
    assert (s.naive_zero_annual_mape > s.annual_mape.fillna(0)).all()


def test_failure_cases_documented():
    fc = VA.failure_cases()
    assert len(fc) == 9 and fc.outcome.str.contains("refused").sum() == 3
    assert fc.outcome.str.contains("FALSE ALARM").sum() == 1


def test_app_has_data_gap_tab_and_blocks_unresolved():
    """v3: the A4 workflow lives in the Plant Data workspace; the full approval sequence is in tests/test_app_v3.py."""
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=300)
    at.session_state["nav"] = "Plant Data"
    at.run()
    assert not at.exception
    assert any("Baseline blocked" in e.value for e in at.error)
    at.button(key="bulk_approve").click().run()
    assert not at.exception and any("natural_gas (1 month(s))" in e.value for e in at.error)
    at.session_state["nav"] = "Emissions"
    at.run()
    assert not at.exception
    assert any("Plant-data baseline status" in w.value for w in at.warning)

def test_a4_workbook_formulas_match_python(tmp_path):
    import shutil
    import openpyxl
    from carbon_iq.dataquality import workbook_a4
    from carbon_iq.recalc import recalc
    raw, _ = synth.demo_incomplete(); L = ES.Ledger(raw, 2026); L.approve_all("t")
    L.decide(SITE, "2026-05", "natural_gas", "approve", "t")
    L.decide(SITE, "2026-11", "diesel_forklift", "override_change", "t")
    p = workbook_a4.build(L, synth.truth_case(), pd.DataFrame([dict(case="C0", description="x", status="computed")]),
                          [("s", pd.DataFrame([dict(a=1.0)]))], tmp_path / "a4.xlsx")
    if shutil.which("soffice") is None and shutil.which("libreoffice") is None:
        pytest.skip("LibreOffice not installed; formulas not recalculated")
    rc = recalc(p)
    assert rc["status"] == "success" and rc["total_errors"] == 0
    ws = openpyxl.load_workbook(p, data_only=True)["Annual & emissions"]
    ann = L.annual().set_index("stream")
    for r in range(5, 13):
        assert ws.cell(r, 6).value == pytest.approx(ann.loc[ws.cell(r, 1).value, "total"], rel=1e-9)
        assert ws.cell(r, 7).value == pytest.approx(ann.loc[ws.cell(r, 1).value, "sd_estimate"], rel=1e-9)
    # rejecting an estimate makes the stream total #N/A (never zero)
    wb = openpyxl.load_workbook(p); rv = wb["Review"]
    for r in range(2, rv.max_row + 1):
        if rv.cell(r, 3).value == "electricity" and rv.cell(r, 2).value == "2026-06":
            rv.cell(r, 14).value = "rejected"
    wb.save(tmp_path / "b.xlsx"); rc2 = recalc(tmp_path / "b.xlsx")
    assert any(e.startswith("Annual & emissions!F7: #N/A") for e in rc2["errors"])



# ------------------------------------------------------------------ A4 refinement: change detection and calibration
def _break_case(start, size=1.30, gap="2026-10", stream="electricity"):
    t = synth.truth_case()
    m = (t.stream == stream) & (t.period >= start)
    t.loc[m, "value"] *= size
    true = float(t[(t.stream == stream) & (t.period == gap)].value.iloc[0])
    return t.drop(t[(t.stream == stream) & (t.period == gap)].index), true


def test_operational_change_detected_and_estimation_restricted():
    raw, true = _break_case("2026-06")
    new = cell(ES.Ledger(raw, 2026), "2026-10", "electricity")
    old = cell(ES.Ledger(raw, 2026, detect_changes=False), "2026-10", "electricity")
    assert "OPERATIONAL_CHANGE" in new.warning and not new.refusal
    assert abs(new.estimate / true - 1) < 0.03 < abs(old.estimate / true - 1)


def test_operational_change_refused_when_regime_too_short_or_gap_at_change():
    raw, _ = _break_case("2026-09")
    c = cell(ES.Ledger(raw, 2026), "2026-10", "electricity")
    assert c.refusal.startswith("OPERATIONAL_CHANGE") and c.fallback_estimate > 0
    raw, _ = _break_case("2026-06", gap="2026-06")                    # the gap is the first month of the new regime
    c = cell(ES.Ledger(raw, 2026), "2026-06", "electricity")
    assert c.refusal.startswith("OPERATIONAL_CHANGE: gap at the change point")


def test_no_change_flagged_on_clean_electricity_and_gas():
    raw, _ = synth.demo_incomplete()
    L = ES.Ledger(raw, 2026)
    for per, st in (("2026-06", "electricity"), ("2026-03", "natural_gas"), ("2026-08", "steel_purchased")):
        assert "OPERATIONAL_CHANGE" not in cell(L, per, st).warning


def test_change_detection_false_alarm_rate_is_controlled():
    rng = np.random.default_rng(3)
    p = [ES.detect_change({f"m{i:02d}": v for i, v in enumerate(rng.normal(0, 0.05, 20))}, key=str(j)) is not None for j in range(200)]
    assert np.mean(p) <= 0.03                                          # alpha 0.01 plus Monte Carlo slack
    x = np.r_[rng.normal(0, 0.05, 14), rng.normal(0.4, 0.05, 6)]
    d = ES.detect_change({f"m{i:02d}": v for i, v in enumerate(x)}, key="s")
    assert d and d["split"] == "m14" and d["shift"] > 0.3


def test_calibration_constants_match_calibration_study():
    from pathlib import Path
    c = json.load(open(Path(__file__).resolve().parents[1] / "outputs" / "a4" / "calibration.json"))
    assert ES.CAL_MONTHLY == pytest.approx(c["cal_monthly"], abs=1e-4) and ES.RHO_ANNUAL == c["rho_annual"]
    assert ES.CAL_MONTHLY >= 1.0                                       # calibration never narrows the monthly intervals


def test_annual_sd_correlation_formula():
    sds = [3.0, 4.0]
    assert ES.annual_sd(sds, 1.0) == pytest.approx(7.0) and ES.annual_sd(sds, 0.0) == pytest.approx(5.0)
    assert 5.0 < ES.annual_sd(sds, 0.12) < 7.0


def test_calibration_switch_reproduces_first_release():
    raw, _ = synth.demo_incomplete()
    a = cell(ES.Ledger(raw, 2026, detect_changes=False, calibrate=False), "2026-06", "electricity")
    b = cell(ES.Ledger(raw, 2026), "2026-06", "electricity")
    assert b.sd == pytest.approx(a.sd * ES.CAL_MONTHLY) and b.estimate == a.estimate


def test_conformal_factor_and_wilson():
    z = np.random.default_rng(1).standard_normal(4000) * 1.2
    q, n = VA.conformal_factor(z)
    assert q == pytest.approx(1.2, rel=0.06) and n == 4000
    lo, hi = VA.wilson(95, 100)
    assert lo < 0.95 < hi and hi - lo < 0.12



def test_complete_data_reproduce_current_register():
    """Through the A4 path, complete synthetic data give exactly the pipeline's decisions on the current register."""
    from carbon_iq import decisions as D
    L = ES.Ledger(synth.truth_case(), 2026)
    r, _ = I.run_decisions(I.activity_from_annual(L.annual()))
    sc = U.Scenarios(params=U.sample(20000, 20261024), basis="reporting")
    ref = D._run_case(base_values(), sc, 5e6, 0.9, 0.9)
    assert (r["D1"], r["D2"], r["D3"], r["D4"]) == (ref["deterministic"], ref["best_expected"], ref["chance_constrained"], ref["joint"])
    assert r["D1_npv"] == pytest.approx(ref["det_npv"]) and r["min_budget"] == pytest.approx(ref["joint_min_budget"])
