"""Phase A5 (model v1.3): source register, revised inputs, financial formulas and the v1.2 comparison profile."""
import numpy as np
import pytest

from carbon_iq import decisions as D
from carbon_iq import engine as E
from carbon_iq import optimize as O
from carbon_iq import timing as TM
from carbon_iq import uncertainty as U
from carbon_iq.assumptions import (EF_GRID_EVIDENCE, EF_GRID_SCENARIOS, EVIDENCE, GAS_SCENARIOS, MODEL_VERSION, P,
                                   PV_CAPEX_SCENARIOS, V12_CHANGES, base_values, use_profile, v)

B, ALPHA = v("budget"), v("chance_level")


def test_register_has_evidence_class_and_sources():
    assert MODEL_VERSION == "1.3"
    for k, p in P.items():
        assert p.evidence in EVIDENCE, k
        assert p.evidence != "measured"                     # the facility is synthetic: nothing is a factory observation
        if p.evidence in ("external", "derived") and p.status != "derived":
            assert p.source, k
    for k in ("ef_grid", "gas_price_usd", "pv_capex_kw", "pv_degradation", "diesel_price", "c_saving_frac", "b_saving_frac",
              "d_saving_frac", "tariff"):
        assert P[k].url.startswith("http") and P[k].published, k
    hyp = [k for k, p in P.items() if p.status == "hypothetical"]
    assert all(P[k].evidence == "hypothetical" for k in hyp) and "elec_mwh" in hyp and "c_om" in hyp


def test_grid_factor_derived_from_official_statistics():
    assert v("ef_grid") == pytest.approx(205_579 / 358_640, abs=0.0005) and P["ef_grid"].status == "derived"
    vals = {s["id"]: s["value"] for s in EF_GRID_SCENARIOS}
    assert vals == {"E0": 0.55, "E1": 0.568, "E2": 0.573}
    assert EF_GRID_EVIDENCE[0]["value"] == 0.573 and any(e["value"] == 0.682 for e in EF_GRID_EVIDENCE)


def test_v12_profile_reproduces_v12_and_restores():
    with use_profile("v1.2"):
        assert v("ef_grid") == 0.55 and v("pv_capex_kw") == 3750 and v("c_om") == 0 and v("pv_degradation") == 0
        sc = U.Scenarios(params=U.sample(20000, 20261024), basis="reporting")
        r = D._run_case(base_values(), sc, B, ALPHA, 0.9)
        assert (r["deterministic"], r["best_expected"], r["chance_constrained"], r["joint"]) == ("A+B", "A+B", "A+C+D", "none feasible")
        assert r["det_npv"] == pytest.approx(337930.7073, abs=0.01) and r["joint_min_budget"] == pytest.approx(5202422.81, abs=0.01)
    assert v("ef_grid") == 0.573 and v("pv_capex_kw") == 2500             # restored after the block
    with pytest.raises(RuntimeError):
        with use_profile("v1.2"):
            raise RuntimeError
    assert v("ef_grid") == 0.573                                            # restored after an exception too


def test_degraded_annuity_and_mac():
    r, n, d = 0.06, 25, 0.005
    direct = sum((1 - d) ** (t - 1) / (1 + r) ** t for t in range(1, n + 1))
    assert float(E.degraded_annuity_factor(r, n, d)) == pytest.approx(direct, rel=1e-12)
    prj, _ = E.projects()
    a = prj["A"]
    assert float(a["af_t"]) == pytest.approx(direct) and float(a["af_t"]) < float(a["af"])
    assert float(E.mac(a)) == pytest.approx(-float(a["npv"]) / (direct * float(a["scope12_t"])))
    c = prj["C"]
    assert float(E.mac(c)) == pytest.approx(-float(c["npv"]) / (float(c["af"]) * float(c["scope12_t"])))


def test_milp_equals_enumeration_on_v13():
    prj, inter = E.projects()
    T = E.target_t()
    for budget in (2e6, 3e6, 4e6, 5e6, 6e6):
        best, _ = O.enumerate_best(prj, inter, budget, T)
        m = O.solve_milp(prj, inter, budget, T)
        assert (best is None and m is None) or m["npv"] == pytest.approx(best["npv"], abs=1e-3)


def test_attribution_brackets_v12_and_v13():
    rows = D.a5_attribution(6000, 7, B, ALPHA, 0.9)
    with use_profile("v1.2"):
        ref = D._case_metrics(6000, 7, B, ALPHA, 0.9)
    assert rows[0]["det_npv"] == pytest.approx(ref["det_npv"]) and rows[0]["target_t"] == pytest.approx(ref["target_t"])
    cur = D._case_metrics(6000, 7, B, ALPHA, 0.9)
    assert rows[-1]["det_npv"] == pytest.approx(cur["det_npv"])
    only_ef = next(r for r in rows if r["case"] == "only: ef_grid")
    only_pv = next(r for r in rows if r["case"] == "only: pv_capex_kw")
    assert only_ef["target_t"] > rows[0]["target_t"] and only_pv["target_t"] == pytest.approx(rows[0]["target_t"])
    assert only_pv["npv[A+B]"] > rows[0]["npv[A+B]"]


def test_price_and_cost_scenarios():
    gs = D.gas_scenarios(4000, 5, B, ALPHA, 0.9)
    assert [g["id"] for g in gs] == [s["id"] for s in GAS_SCENARIOS] and gs[0]["gas_price_usd"] == v("gas_price_usd")
    ps = D.pv_capex_scenarios(4000, 5, B, ALPHA, 0.9)
    assert [p["pv_capex_kw"] for p in ps] == [s["value"] for s in PV_CAPEX_SCENARIOS]
    p = base_values(); p["pv_capex_kw"] = 3750
    prj, _ = E.projects(p)
    assert float(prj["A"]["npv"]) < float(E.projects()[0]["A"]["npv"])


def test_timing_follows_current_gas_price():
    t = TM.decision_tree()
    assert t["g_now_usd"] == v("gas_price_usd") and t["g_reform_usd"] == pytest.approx(1.5 * v("gas_price_usd"))


def test_sampling_alignment_preserved():
    """A5 changed values but not distribution types on stream 1, so v1.2 draws are reproduced under the profile."""
    for k, ch in V12_CHANGES.items():
        if "dist" in ch and ch["dist"] is not None and P[k].dist is not None:
            assert ch["dist"][0] == P[k].dist[0], k
    assert P["pv_degradation"].stream == 3


def test_external_and_derived_inputs_have_source_and_date():
    """A5 register rule: every externally sourced or derived input carries a URL and a publication date."""
    for k, p in P.items():
        if p.evidence in ("external", "derived"):
            assert p.url and p.published, k
    assert not any(p.evidence in ("measured", "estimated") for p in P.values())   # no real or engine-filled data stored


def test_b_c_overlap_equals_explicit_shared_ledger_cash_flows():
    """B and C together: NPV with the overlap removed equals explicit year-by-year cash flows on one activity ledger
    (B's compressor saving acts on the load left after C while C operates, on the full load after C's life ends)."""
    p = base_values()
    prj, inter = E.projects(p)
    r, tar = p["discount_rate"], p["tariff"] * 1000
    comp, motor = p["elec_mwh"] * p["compressed_air_share"], p["elec_mwh"] * p["motor_share"]
    pv = -(p["b_capex"] + p["c_capex"])
    for t in range(1, int(max(p["b_life"], p["c_life"])) + 1):
        c_on, b_on = t <= p["c_life"], t <= p["b_life"]
        left = comp * (1 - p["c_saving_frac"]) if c_on else comp
        sav = (comp * p["c_saving_frac"] if c_on else 0) + ((motor * p["b_saving_frac"] + left * p["b_comp_frac"]) if b_on else 0)
        pv += (sav * tar - (p["c_om"] if c_on else 0)) / (1 + r) ** t
    assert E.portfolio(("B", "C"), prj, inter)["npv"] == pytest.approx(pv, rel=1e-10)


def test_explanation_text_follows_the_validation_result():
    """A5: the objectives explanation was written for v1.2 (A+B fails validation); it must not claim a sampling artefact
    when the knife-edge portfolio passes validation."""
    rows = [dict(id=i, portfolio=p, npv_base_inputs=1.0, e_npv=2.0) for i, p in
            (("D1", "A+B+C"), ("D2", "A+B+C"), ("D3", "A+B+C"), ("D4", "A+B+C"))]
    ke = dict(portfolio="A+B", p_in_sample=0.937, n=20000, p_validation=0.935, n_validation=200000, ci95_validation=[0.934, 0.936])
    txt = " ".join(D.why_they_differ(rows, dict(portfolio="A+B+C", npv=3.0), ke, 0.9))
    assert "artefact" not in txt and "above 90%" in txt
    ke["p_validation"] = 0.899
    assert "artefact" in " ".join(D.why_they_differ(rows, dict(portfolio="A+B+C", npv=3.0), ke, 0.9))
