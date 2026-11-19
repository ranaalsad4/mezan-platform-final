"""Phase A6: independent recomputation, optimisation cross-checks, boundary cases and numerical stability."""
import json
import math
from pathlib import Path

import numpy as np
import pytest

from carbon_iq import engine as E
from carbon_iq import optimize as O
from carbon_iq import timing as TM
from carbon_iq import uncertainty as U
from carbon_iq.assumptions import base_values
from independent import indep as I

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def reg(tmp_path_factory):
    """Export the live register the way run_all.py does, so the independent code reads only the CSV."""
    import pandas as pd
    from carbon_iq.assumptions import P
    d = pd.DataFrame([dict(key=k, value=p.value, dist=str(p.dist) if p.dist else "") for k, p in P.items()])
    f = tmp_path_factory.mktemp("a6") / "assumptions.csv"
    d.to_csv(f, index=False)
    return I.load_register(f)


def test_independent_code_does_not_import_the_model():
    src = (ROOT / "independent" / "indep.py").read_text()
    assert "carbon_iq" not in src.replace("imports NOTHING from carbon_iq", "").replace("carbon_iq/", "")


def test_inventory_and_target_recomputed_independently(reg):
    vals, _ = reg
    inv = I.inventory(vals)
    m = E.scope_totals(E.baseline(base_values()))
    for k in ("Scope 1", "Scope 2", "Scope 3", "Scope 1+2", "Total"):
        assert inv[k] == pytest.approx(m[k], rel=1e-12)
    assert inv["target"] == pytest.approx(E.target_t(), rel=1e-12)


def test_factors_rederived_from_primary_data(reg):
    vals, _ = reg
    f = I.derived_factors()
    assert f["ef_gas"] == pytest.approx(vals["ef_gas"], rel=1e-9)
    assert f["ef_grid"] == pytest.approx(vals["ef_grid"], abs=0.0005)
    assert f["ef_diesel_ipcc"] == pytest.approx(vals["ef_diesel"], rel=0.02)


def test_all_64_portfolios_ledger_npv_and_reduction(reg):
    vals, _ = reg
    prj, inter = E.projects(base_values())
    for c in I.PORTS:
        a, b = I.portfolio(c, vals), E.portfolio(c, prj, inter)
        assert a["npv"] == pytest.approx(float(b["npv"]), rel=1e-9, abs=1e-6)
        assert a["red12"] == pytest.approx(float(b["scope12_t"]), rel=1e-9, abs=1e-9)


def test_project_irr_accounts_for_pv_degradation(reg):
    """A6 finding: the constant-flow IRR overstated A (11.5% vs 11.0%)."""
    vals, _ = reg
    prj, _ = E.projects(base_values())
    ind = I.project_metrics("A", vals)["irr"]
    assert E.project_irr(prj["A"], base_values()["pv_degradation"]) == pytest.approx(ind, abs=1e-8)
    assert E.irr(prj["A"]["capex"], prj["A"]["annual_cf"], 25) > ind + 0.004       # the old value was too high


def test_milp_equals_independent_enumeration_on_random_parameter_sets(reg):
    vals, dists = reg
    s = I.sample(vals, dists, 25, seed=4, method="mt")
    for j in range(25):
        p = {k: (float(v[j]) if np.ndim(v) else float(v)) for k, v in s.items()}
        pm = base_values(); pm.update({k: p[k] for k in pm})
        prj, inter = E.projects(pm)
        T = I.inventory(p)["target"]
        for budget in (2.5e6, 4.0e6, 6.0e6):
            m = O.solve_milp(prj, inter, budget, T)
            i = I.enumerate_best(p, budget, T)
            assert (m is None) == (i is None)
            if m:
                assert m["npv"] == pytest.approx(i[1], rel=1e-7, abs=1e-3)


def test_boundary_budget_zero_and_unreachable_target():
    prj, inter = E.projects(base_values())
    assert O.solve_milp(prj, inter, 0, 0)["portfolio"] == "(none)" == O.enumerate_best(prj, inter, 0, 0)[0]["portfolio"]
    assert O.solve_milp(prj, inter, 5e6, 1e6) is None and O.enumerate_best(prj, inter, 5e6, 1e6)[0] is None
    big = O.solve_milp(prj, inter, 1e12, 0)
    assert big["npv"] == pytest.approx(O.enumerate_best(prj, inter, 1e12, 0)[0]["npv"])


def test_non_finite_inputs_are_refused_not_silently_optimised():
    """A6 finding: a NaN input made the enumeration return an arbitrary portfolio."""
    p = base_values(); p["tariff"] = float("nan")
    prj, inter = E.projects(p)
    with pytest.raises(ValueError, match="non-finite"):
        O.enumerate_best(prj, inter, 5e6, E.target_t(p))
    with pytest.raises(ValueError, match="non-finite"):
        O.solve_milp(prj, inter, 5e6, E.target_t(p))


def test_missing_input_raises_named_error():
    p = base_values(); del p["tariff"]
    with pytest.raises(KeyError, match="tariff"):
        E.projects(p)


def test_contradictory_chance_constraints_report_infeasible_without_forcing():
    n = 4000
    sc = U.Scenarios(params=U.sample(n, 11), basis="reporting")
    k, e, pt, ok = sc.decide(5e6, E.target_t(), 1.0, budget_reliability=1.0)
    assert k is None or not ok or (sc.PT12[k] >= E.target_t()).all()
    k, e, pt, ok = sc.decide(1e5, E.target_t(), 0.9)            # budget too small for any reducing portfolio
    assert not ok


@pytest.mark.parametrize("r,n,d", [(0.0, 10, 0.0), (1e-14, 10, 0.0), (-0.01, 10, 0.01), (0.06, 1, 0.005), (0.06, 25, 0.0)])
def test_annuity_factors_stable_at_edges(r, n, d):
    direct = sum((1 - d) ** (t - 1) / (1 + r) ** t for t in range(1, n + 1))
    assert float(E.degraded_annuity_factor(r, n, d)) == pytest.approx(direct, rel=1e-9)
    if d == 0:
        assert float(E.annuity_factor(r, n)) == pytest.approx(direct, rel=1e-9)


def test_alpha_saa_limits():
    assert U.alpha_saa(0.9, 1) == 1.0
    assert U.alpha_saa(0.9, 10 ** 9) == pytest.approx(0.9, abs=1e-4)
    assert U.alpha_saa(0.9, 20000) == pytest.approx(I.alpha_saa(0.9, 20000), abs=1e-6)


def test_budget_probability_matches_normal_closed_form():
    """P(actual capex <= budget) for A+B+C: sum of independent normals (s.d. 15% each) - checked against the model."""
    from scipy.stats import norm
    p = base_values()
    caps = [p["pv_kwp"] * p["pv_capex_kw"], p["b_capex"], p["c_capex"]]
    sd = math.sqrt(sum((0.15 * c) ** 2 for c in caps))
    exact = norm.cdf((p["budget"] - sum(caps)) / sd)
    sc = U.Scenarios(params=U.sample(200000, 99), basis="reporting")
    est = sc.p_within_budget(sc.index(("A", "B", "C")), p["budget"])
    assert est == pytest.approx(exact, abs=4 * math.sqrt(exact * (1 - exact) / 200000))


def test_lsmc_engine_reproduces_published_american_put():
    """Longstaff & Schwartz (2001) Table 1: S0 36, K 40, r 6%, sigma 20%, T 1, 50 dates: LSM 4.472."""
    g = np.random.default_rng(3)
    def paths(seed):
        r = np.random.default_rng(seed)
        z = r.standard_normal((20000, 50)); z = np.vstack([z, -z])
        x = np.cumsum((0.06 - 0.02) / 50 + 0.2 * math.sqrt(1 / 50) * z, axis=1)
        return np.hstack([np.full((40000, 1), 36.0), 36 * np.exp(x)])
    Gf, Ge = paths(1), paths(2)
    disc = math.exp(-0.06 / 50)
    betas = TM._fit_policy(Gf, np.maximum(40 - Gf, 0), disc)
    val, _ = TM._apply_policy(Ge, np.maximum(40 - Ge, 0), disc, betas)
    assert val.mean() == pytest.approx(4.472, abs=0.03)
    del g


def test_gbm_lambda_is_root_and_trigger_is_optimal():
    g = TM.gbm_trigger()
    lam, mu, s, r = g["lambda"], g["mu"], g["sigma"], g["r_continuous"]
    assert 0.5 * s * s * lam * (lam - 1) + mu * lam - r == pytest.approx(0, abs=1e-12)
    d = TM.project_d()
    unit = d["q_gj"] * 3.75 / 1.055056
    A = (1 - math.exp(-(r - mu) * d["life"])) / (r - mu)
    Icost = d["capex"] + d["om"] * (1 - math.exp(-r * d["life"])) / r
    th = np.linspace(g["breakeven_usd"] * 1.001, g["breakeven_usd"] * 8, 40001)
    val = (2.15 / th) ** lam * (A * unit * th - Icost)
    assert th[np.argmax(val)] == pytest.approx(g["trigger_usd"], rel=1e-3)


def test_a6_outputs_if_present():
    f = ROOT / "outputs" / "a6" / "a6_results.json"
    if not f.exists():
        pytest.skip("run tools/run_a6.py first")
    r = json.load(open(f))
    assert r["optimization"]["identical_value"] == r["optimization"]["cases"]
    assert r["finance"]["passed"] == r["finance"]["n"]
    assert r["emissions"]["passed"] == r["emissions"]["n"]
