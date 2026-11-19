"""Tests for the v1.1 (Phase A1) corrections: activity uncertainty, decision objectives, reporting basis,
capital-cost risk, tariff and grid-factor scenarios, workbook/chart builders, documentation and packaging."""
import re
from pathlib import Path

import numpy as np
import pytest

from carbon_iq import decisions as D
from carbon_iq import engine as E
from carbon_iq import optimize as O
from carbon_iq import uncertainty as U
from carbon_iq.assumptions import use_profile, EF_GRID_EVIDENCE, P, TARIFF_SCENARIOS, Z95, base_values, v


@pytest.fixture(scope="module", autouse=True)
def _v12_register():
    """Since A5 (model v1.3) these tests document behaviour of the v1.2 register, kept as profile 'v1.2' for comparison
    (knife-edge chance constraint, infeasible joint rule, motor-audit value). v1.3 equivalents: tests/test_a5.py."""
    with use_profile("v1.2"):
        yield

ROOT = Path(__file__).resolve().parents[1]
B, ALPHA = v("budget"), v("chance_level")


@pytest.fixture(scope="module")
def sc():
    return U.Scenarios(8000, seed=3)


# ------------------------------------------------------------------ activity-data uncertainty (A1-09)
def test_activity_uncertainty_in_register_and_used_by_both_methods():
    v10 = {"diesel_forklift_l": 5.0, "diesel_genset_l": 10.0, "steel_t": 2.0, "freight_tkm": 20.0}   # v1.0 hard-coded values
    rows, _ = E.uncertainty_table()
    ua = {E.ACTIVITY_KEY[r["source_id"]][0]: r["u_activity_pct"] for r in rows}
    for k, u in v10.items():
        assert P[k].dist is not None and P[k].dist[0] == "normal_rel"
        assert E.u95(k) == pytest.approx(u, rel=1e-9)
        assert ua[k] == pytest.approx(u, rel=1e-9)
    s = U.sample(20000, seed=1)
    for k, u in v10.items():
        assert s[k].std() / s[k].mean() * 100 * Z95 == pytest.approx(u, rel=0.05)   # Monte Carlo uses the same input


def test_stream_one_draws_unchanged_by_new_distributions():
    n, seed = 3000, 42
    s = U.sample(n, seed)
    rng = np.random.default_rng(seed)
    for k, p in P.items():
        if p.stream == 1:
            assert np.array_equal(s[k], U._draw(rng, p, n)), k


def test_fixed_input_keeps_other_draws_aligned():
    a = U.sample(2000, 9)
    b = U.sample(2000, 9, fixed={"tariff": 0.23})
    assert np.all(b["tariff"] == 0.23)
    for k in ("b_saving_frac", "pv_yield", "ef_grid", "diesel_forklift_l"):
        assert np.array_equal(a[k], b[k]), k


# ------------------------------------------------------------------ decision rules (v1.2)
@pytest.fixture(scope="module")
def rules():
    from carbon_iq import pipeline
    phys = U.Scenarios(6000, seed=4)
    rep = U.Scenarios(params=phys.p, basis="reporting")
    base = U.Scenarios(params=phys.p, basis="baseline")
    val = U.Scenarios(30000, seed=5, basis="reporting")
    T = E.target_t()
    prj, inter = E.projects()
    best, _ = O.enumerate_best(prj, inter, B, T)
    prv = D.portfolio_probs(val, B, T)
    rows, lv = D.decision_scenarios(best, rep, phys, base, prv, B, T, ALPHA, 0.9)
    return {r["id"]: r for r in rows}, lv, rep, val, T


def test_decision_rules_structure_and_comparisons_preserved(rules):
    r, lv, rep, val, T = rules
    assert list(r) == ["D1", "D2", "D3a", "D3", "D4", "S1", "S2"]
    prj, inter = E.projects()
    assert r["D1"]["portfolio"] == O.enumerate_best(prj, inter, B, T)[0]["portfolio"]
    pr = D.portfolio_probs(rep, B, T)
    assert r["D2"]["e_npv"] == pytest.approx(max(pr["e_npv"][k] for k in range(64) if pr["quote"][k] <= B))
    for x in r.values():                       # both probabilities reported for every recommended portfolio
        if x["portfolio"] != "none feasible":
            for key in ("p_target", "p_budget", "p_target_val", "p_budget_val", "p_both"):
                assert 0 <= x[key] <= 1


def test_tightened_chance_constraint_and_validation(rules):
    r, lv, rep, val, T = rules
    assert lv["alpha_saa"] > ALPHA and lv["alpha_saa"] == pytest.approx(U.alpha_saa(ALPHA, rep.n))
    d3 = r["D3"]
    assert d3["p_target"] >= lv["alpha_saa"] and d3["capex_quote"] <= B
    assert d3["e_npv"] <= r["D3a"]["e_npv"] + 1e-6      # tightening can only cost expected NPV
    assert d3["e_npv"] <= r["D2"]["e_npv"] + 1e-6


def test_joint_budget_constraint_infeasible_and_not_forced(rules):
    r, lv, rep, val, T = rules
    d4 = r["D4"]
    pr = D.portfolio_probs(rep, B, T)
    feas = [k for k in range(64) if pr["quote"][k] <= B and pr["p_target"][k] >= lv["alpha_saa"] and pr["p_budget"][k] >= lv["beta_saa"]]
    if feas:
        assert d4["portfolio"] == rep.name(max(feas, key=lambda k: pr["e_npv"][k]))
    else:
        assert d4["portfolio"] == "none feasible" and d4["status"] == "infeasible"


def test_minimum_budget_makes_rule_feasible(rules):
    r, lv, rep, val, T = rules
    ba = D.budget_analysis(rep, val, T, ALPHA, 0.9, B, budgets=np.arange(B, B * 1.25, 25_000))
    mb = ba["min_budget_by_portfolio"][0]
    need = mb["budget_needed"]
    pr = D.portfolio_probs(rep, need + 1, T)
    k = rep.index(tuple(mb["portfolio"].split("+")))
    assert pr["p_budget"][k] >= lv["beta_saa"] and pr["p_target"][k] >= lv["alpha_saa"]
    assert D.portfolio_probs(rep, need * 0.99, T)["p_budget"][k] < lv["beta_saa"]
    assert len(ba["thresholds"]) == 24 and ba["curve"][0]["budget"] == B


def test_baseline_uncertainty_basis():
    z = U.Scenarios(4000, seed=8, basis="baseline")
    ph = U.Scenarios(params=z.p, basis="physical")
    k = z.index(("A", "B"))
    ratio = z.PT12[k] / ph.PT12[k]
    assert ratio.std() > 0.01                        # target scales with the simulated baseline
    s12 = z.baseline_s12
    assert np.corrcoef(ratio, s12)[0, 1] < -0.99


def test_mean_inputs_use_distribution_means():
    m = D.mean_inputs()
    assert m["tariff"] == pytest.approx((0.18 + 0.18 + 0.26) / 3)
    assert m["b_saving_frac"] == pytest.approx((0.08 + 0.25) / 2)
    assert m["elec_mwh"] == base_values()["elec_mwh"]


# ------------------------------------------------------------------ reporting basis (A1-02)
def test_reporting_basis_uses_fixed_factors(sc):
    rep = U.Scenarios(params=sc.p, basis="reporting")
    base = base_values()
    q = dict(sc.p)
    q.update({k: np.full(sc.n, base[k]) for k in U.EF_KEYS})
    z = U.Scenarios(params=q)
    assert np.allclose(rep.PT12, z.PT12)
    assert np.array_equal(rep.PNPV, sc.PNPV)            # money is unaffected by the counting basis
    k = sc.index(("A", "B"))
    assert abs(np.corrcoef(rep.PT12[k], sc.p["ef_grid"])[0, 1]) < 0.05
    assert np.corrcoef(sc.PT12[k], sc.p["ef_grid"])[0, 1] > 0.3


# ------------------------------------------------------------------ capital-cost uncertainty (priority 6)
def test_capex_risk_separates_quote_and_actual(sc):
    T = E.target_t()
    for r in sc.table(B, T):
        k = sc.index(tuple(r["portfolio"].split("+")) if r["portfolio"] != "(none)" else ())
        assert r["capex"] <= B + 1e-6                                   # baseline (quoted) feasibility
        assert r["p_over_budget"] == pytest.approx((sc.PCAP[k] > B + 1e-6).mean())
    k = sc.index(("A", "B"))
    assert sc.PCAP[k].std() > 0 and abs(sc.PCAP[k].mean() / sc.capex[k] - 1) < 0.02
    assert 0.3 < sc.stats(k, T, budget=B)["p_over_budget"] < 0.6       # quote is 99% of budget, +/-10-15% cost risk


def test_budget_reliability_constraint(sc):
    T = E.target_t()
    k0 = sc.decide(B, T, ALPHA)[0]
    assert sc.decide(B, T, ALPHA, budget_reliability=0.0)[0] == k0
    k, e, pt, ok = sc.decide(B, T, 0.0, budget_reliability=0.999)
    assert k is not None and sc.p_within_budget(k, B) >= 0.999
    cr = D.capex_risk(sc, B, T, ALPHA)
    assert cr["cc_contingency_p90"] == pytest.approx(max(0.0, np.percentile(sc.PCAP[k0], 90) - B))


# ------------------------------------------------------------------ tariff and grid-factor scenarios (priorities 4-5)
def test_tariff_scenarios_documented():
    ids = [s["id"] for s in TARIFF_SCENARIOS]
    assert ids == ["T0", "T1", "T2", "T3"]
    for s in TARIFF_SCENARIOS:
        assert s["status"] and s["effective"] and s["source"]
    assert {s["value"] for s in TARIFF_SCENARIOS} == {0.18, 0.20, 0.23, 0.26}
    assert P["tariff"].status == "provisional" and P["tariff"].value == 0.18


def test_tariff_scenarios_rerun_full_analysis():
    out = D.tariff_scenarios(3000, 5, B, ALPHA, 0.9)
    t0 = out[0]
    prj, inter = E.projects()
    best, _ = O.enumerate_best(prj, inter, B, E.target_t())
    assert t0["deterministic"] == best["portfolio"] and t0["det_npv"] == pytest.approx(best["npv"])
    npvs = [r["det_npv"] for r in out]
    assert npvs == sorted(npvs)                                  # higher tariff -> more valuable electricity savings


def test_grid_factor_not_replaced_and_scenario_consistent():
    assert P["ef_grid"].value == 0.55 and P["ef_grid"].status == "provisional"
    assert any(e["value"] == 0.568 for e in EF_GRID_EVIDENCE)
    out = D.ef_scenarios(3000, 5, B, ALPHA, 0.9)
    assert out[0]["target_t"] == pytest.approx(E.target_t())
    p = base_values(); p["ef_grid"] = 0.568
    assert out[1]["target_t"] == pytest.approx(E.target_t(p))


# ------------------------------------------------------------------ workbook and chart builders (A1-14)
@pytest.fixture(scope="module")
def quick_res():
    from carbon_iq import pipeline
    res, _ = pipeline.run(n=2000, timing_detail=False, n_validation=20000)
    return res


def test_workbook_builder(tmp_path, quick_res):
    import openpyxl
    from carbon_iq import recalc, workbook
    path = tmp_path / "wb.xlsx"
    workbook.build(quick_res, path)
    wb = openpyxl.load_workbook(path)
    assert "Decision Objectives" in wb.sheetnames and len(wb.sheetnames) == 19          # 17 + Source Register, A5 Changes (A5)
    assert "Source Register" in wb.sheetnames and "A5 Changes" in wb.sheetnames
    n = sum(1 for ws in wb for r in ws.iter_rows() for c in r if isinstance(c.value, str) and c.value.startswith("="))
    assert n >= 900
    assert wb.calculation.fullCalcOnLoad
    rc = recalc.recalc(path)
    if rc["status"] == "skipped":
        pytest.skip("LibreOffice not installed: formula evaluation not checked here")
    assert rc["status"] == "success" and rc["total_errors"] == 0
    wv = openpyxl.load_workbook(path, data_only=True)
    obj = wv["Decision Objectives"]
    assert obj["F6"].value == pytest.approx(quick_res["decision_scenarios"][0]["npv_base_inputs"])


def test_chart_builder(tmp_path, quick_res):
    from carbon_iq import charts
    res = dict(quick_res)
    if "timing_scan" not in res:
        pytest.importorskip("matplotlib")
    charts.make_all(res, tmp_path)
    pngs = list(tmp_path.glob("*.png"))
    assert len(pngs) >= 8 and all(p.stat().st_size > 5000 for p in pngs)


# ------------------------------------------------------------------ documentation, claims and packaging
def _colab_lines():
    txt = (ROOT / "README.md").read_text(encoding="utf-8")
    block = re.search(r"### Google Colab.*?```python\n(.*?)```", txt, re.S)
    assert block, "README must contain a Google Colab code block"
    return [l for l in block.group(1).splitlines() if l.strip()]


def test_colab_cell_is_valid_ipython():
    lines = _colab_lines()
    for l in lines:
        if l.startswith("!"):
            assert "%" not in l.split("#")[0].replace("%%", ""), f"magic inside a shell line: {l}"
    cd = [i for i, l in enumerate(lines) if l.startswith("%cd")]
    assert cd, "the cell must change directory with a separate %cd line"
    pip = [i for i, l in enumerate(lines) if "pip install" in l and "requirements.txt" in l]
    assert pip and pip[0] > cd[0], "requirements are installed after changing into the project folder"
    assert (ROOT / "Mezan_Colab.ipynb").exists()


def test_requirement_floors_match_tested_versions():
    req = {l.split(">=")[0].strip(): l.split(">=")[1].strip() for l in (ROOT / "requirements.txt").read_text().splitlines()
           if ">=" in l and not l.startswith("#")}
    major = lambda s: tuple(int(x) for x in s.split(".")[:2])
    assert major(req["numpy"]) >= (2, 0)          # pyarrow (via Streamlit) needs NumPy >= 2
    assert major(req["streamlit"]) >= (1, 49)     # width="stretch" needs Streamlit >= 1.49
    assert (ROOT / "requirements-lock.txt").exists()


def test_no_ai_or_ml_claims():
    """v3 adds a labelled AI layer (mezan_ai). The calculation engine itself still contains no machine-learning model."""
    pat = re.compile(r"AI[- ]enabled|AI[- ]powered|machine[- ]learning model|trained model", re.I)
    for f in sorted((ROOT / "carbon_iq").glob("*.py")):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if pat.search(line):
                assert re.search(r"\bno\b|\bnot\b|does not|without", line, re.I), f"{f.name}:{i}: {line.strip()}"
