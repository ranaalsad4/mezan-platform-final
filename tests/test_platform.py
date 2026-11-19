"""App v3 service layer: reproduces the saved model v1.3 run, keeps the two chance constraints separate, is reproducible,
and never changes the original calculations."""
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from carbon_iq.dataquality import integrate as DI
from mezan_platform import analysis as A
from mezan_platform import report as R

ROOT = Path(__file__).resolve().parents[1]
RES = json.load(open(ROOT / "outputs" / "results.json"))
DS = {d["id"]: d for d in RES["decision_scenarios"]}


@pytest.fixture(scope="module")
def base():
    return A.run()


def test_defaults_reproduce_saved_run(base):
    rec = base["recommended"]
    assert rec["portfolio"] == DS["D4"]["portfolio"] == "A+B+C"
    assert rec["e_npv"] == pytest.approx(DS["D4"]["e_npv"], rel=1e-12)
    assert rec["p_target"] == pytest.approx(DS["D4"]["p_target"], abs=1e-12)
    assert rec["p_budget"] == pytest.approx(DS["D4"]["p_budget"], abs=1e-12)
    assert rec["npv_base_inputs"] == pytest.approx(RES["optimal"]["npv"], rel=1e-12)
    assert base["totals"]["Scope 1+2"] == pytest.approx(RES["scope_totals"]["Scope 1+2"], rel=1e-12)
    assert base["target_t"] == pytest.approx(RES["target_t"], rel=1e-12)
    for rule in ("D1", "D2", "D3", "D4"):
        assert base["choice_names"][rule] == DS[rule]["portfolio"]
    assert base["a_eff"] == pytest.approx(RES["decision_levels"]["alpha_saa"])


def test_value_of_information_matches_saved_run(base):
    v = A.value_of_information(base)
    assert v["evpi"] == pytest.approx(RES["evpi"], rel=1e-9)
    saved = {r["parameter"]: r["evppi_sar"] for r in RES["voi"]}
    for r in v["ranking"]:
        assert r["evppi_sar"] == pytest.approx(saved[r["parameter"]], rel=1e-9, abs=1e-6)
    assert v["evsi_audit"]["evsi"] == pytest.approx(RES["evsi_audit"]["evsi"], abs=1e-6)


def test_chance_constraints_are_separate_tests():
    r = A.run(replace(A.DEFAULTS, budget=4.2e6, n=5000))
    d3, d4 = r["table"][r["choice"]["D3"]], r["table"][r["choice"]["D4"]]
    assert d3["portfolio"] == "A+B+C" and d4["portfolio"] != "A+B+C"       # A+B+C passes carbon but fails the budget test
    assert d3["passes_carbon"] and not d3["passes_budget"]
    assert d4["passes_carbon"] and d4["passes_budget"]
    for row in r["table"]:
        assert row["passes_carbon"] == (row["p_target"] >= r["a_eff"] - 1e-12)
        assert row["passes_budget"] == (row["p_budget"] >= r["b_eff"] - 1e-12)


def test_monte_carlo_reproducible_and_seed_sensitive():
    s = replace(A.DEFAULTS, n=5000)
    a, b = A.run(s), A.run(s)
    assert np.array_equal(a["sc"].PNPV, b["sc"].PNPV) and a["recommended"] == b["recommended"]
    c = A.run(replace(s, seed=7))
    assert not np.array_equal(a["sc"].PNPV, c["sc"].PNPV)


def test_infeasible_budget_is_not_raised():
    r = A.run(replace(A.DEFAULTS, budget=1.0e6, n=5000))
    assert r["recommended"] is None and r["settings"]["budget"] == 1.0e6
    assert r["min_budget"]["budget"] > 1.0e6


def test_complete_register_activity_reproduces_reference_run(base):
    r = A.run(A.DEFAULTS, DI.register_activity(), "register as plant data")
    assert r["recommended"]["portfolio"] == base["recommended"]["portfolio"]
    assert r["recommended"]["e_npv"] == pytest.approx(base["recommended"]["e_npv"], rel=1e-12)
    assert r["recommended"]["p_target"] == pytest.approx(base["recommended"]["p_target"], abs=1e-12)


def test_switch_points_bracket_a_real_change(base):
    sw = {x["parameter"]: x for x in A.switching(base)}
    c = sw["c_saving_frac"]["changes"][0]
    lo, hi = c["bracket"]
    assert A._det_choice(base["p"], 5e6, base["target_t"], "c_saving_frac", lo) == c["below"]
    assert A._det_choice(base["p"], 5e6, base["target_t"], "c_saving_frac", hi) == c["above"]
    assert 0.195 < c["threshold"] < 0.2 and sw["tariff"]["robust"]


def test_discount_rate_switch_d4_vs_d1():
    d = A.discount_switch(replace(A.DEFAULTS, n=5000))
    assert d["changes_D1"] and 0.06 < d["changes_D1"][0]["threshold"] < 0.07
    assert d["changes_D4"] and d["changes_D4"][0]["threshold"] > d["changes_D1"][0]["threshold"]


def test_settings_validation():
    assert A.validate(A.DEFAULTS) == []
    assert A.validate(replace(A.DEFAULTS, budget=-1))
    assert A.validate(replace(A.DEFAULTS, alpha=1.5))
    with pytest.raises(ValueError):
        A.run(replace(A.DEFAULTS, basis="nonsense"))


def test_report_numbers_come_from_the_run(base):
    from mezan_ai import explain as X
    from mezan_platform import datasets as DSet
    ex = X.explain(base, use_llm=False)
    html = R.executive_html(base, DSet.FACILITIES["SYN"], ex)
    assert "A+B+C" in html and "SAR 2.56 M" in html and "99.99%" in html and "98.88%" in html
    j = json.loads(R.results_json(base, explanation=ex))
    assert j["recommended"]["portfolio"] == "A+B+C" and j["reproducibility"]["seed"] == 20261024
    assert "limitations" in html.lower() and "not externally" in html
