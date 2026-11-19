"""Optimization, Monte Carlo, value of information and sensitivity."""
import numpy as np
import pytest

from carbon_iq import engine as E
from carbon_iq import optimize as O
from carbon_iq import sensitivity as S
from carbon_iq import uncertainty as U
from carbon_iq import voi as V
from carbon_iq.assumptions import use_profile, base_values, v


@pytest.fixture(scope="module", autouse=True)
def _v12_register():
    """Since A5 (model v1.3) these tests document behaviour of the v1.2 register, kept as profile 'v1.2' for comparison
    (knife-edge chance constraint, infeasible joint rule, motor-audit value). v1.3 equivalents: tests/test_a5.py."""
    with use_profile("v1.2"):
        yield


@pytest.fixture(scope="module")
def det():
    prj, inter = E.projects()
    return prj, inter, v("budget"), E.target_t()


@pytest.fixture(scope="module")
def sc():
    return U.Scenarios(12000, seed=11)


def test_optimum_and_milp_agree(det):
    prj, inter, B, T = det
    best, _ = O.enumerate_best(prj, inter, B, T)
    assert best["portfolio"] == "A+B"
    assert O.solve_milp(prj, inter, B, T)["portfolio"] == "A+B"


@pytest.mark.parametrize("budget,target", [(2e6, 0), (3e6, 500), (4e6, 900), (5e6, 1000), (5e6, 1500), (6.5e6, 1700), (8e6, 0)])
def test_milp_equals_enumeration_across_cases(det, budget, target):
    prj, inter, _, _ = det
    best, _ = O.enumerate_best(prj, inter, budget, target)
    m = O.solve_milp(prj, inter, budget, target)
    if best is None:
        assert m is None
    else:
        assert m["npv"] == pytest.approx(best["npv"], abs=1e-3)


def test_optimum_is_feasible_and_beats_rankings(det):
    prj, inter, B, T = det
    best, rows = O.enumerate_best(prj, inter, B, T)
    assert best["capex"] <= B and best["scope12_t"] >= T
    assert all(r["npv"] <= best["npv"] + 1e-6 for r in rows if r["feasible"])
    for b in O.baselines(prj, inter, B, T):
        assert not b["meets_target"]          # one-by-one rankings miss the target in this case


def test_exclusive_rule(det):
    prj, inter, B, T = det
    best, _ = O.enumerate_best(prj, inter, B, T, exclusive=[("A", "B")])
    assert best is None or not {"A", "B"} <= set(best["ids"])
    m = O.solve_milp(prj, inter, B, T, exclusive=[("A", "B")])
    assert (best is None and m is None) or m["npv"] == pytest.approx(best["npv"])


def test_infeasible_target(det):
    prj, inter, B, _ = det
    best, _ = O.enumerate_best(prj, inter, B, 5000)
    assert best is None and O.solve_milp(prj, inter, B, 5000) is None


def test_mc_reproducible_and_zero_dispersion_equals_deterministic(det):
    a, b = U.Scenarios(2000, seed=5), U.Scenarios(2000, seed=5)
    assert np.array_equal(a.PNPV, b.PNPV)
    fixed = {k: val for k, val in base_values().items()}
    z = U.Scenarios(params=U.sample(500, fixed=fixed))
    prj, inter, _, _ = det
    k = z.index(("A", "B"))
    assert z.PNPV[k].std() == pytest.approx(0, abs=1e-6)
    assert z.PNPV[k].mean() == pytest.approx(float(E.portfolio("AB", prj, inter)["npv"]))


def test_chance_constraint_respected(sc, det):
    _, _, B, T = det
    k, e, pt, ok = sc.decide(B, T, 0.9)
    assert ok and pt >= 0.9 and sc.capex[k] <= B
    kb = sc.best_expected(B)
    assert sc.PNPV[kb].mean() >= e - 1e-6


def test_voi_properties(sc, det):
    _, _, B, T = det
    evpi = V.evpi(sc, B, T, 0.9)
    rk, noise = V.ranking(sc, B, T, 0.9)
    assert evpi >= -1e-6
    assert all(r["evppi_sar"] >= -1e-6 for r in rk)
    assert all(r["evppi_sar"] <= evpi + 1e-6 for r in rk)
    steel = next(r for r in rk if r["parameter"] == "ef_steel_alt")
    assert steel["evppi_sar"] == pytest.approx(0, abs=1e-6)       # Scope 3 data cannot change this decision
    top = rk[0]
    assert top["parameter"] == "b_saving_frac" and top["evppi_sar"] > v("cost_motor_audit")
    evsi, _, _ = V.evsi_audit(sc, B, T, 0.9)
    assert 0 <= evsi <= top["evppi_sar"] * 1.05


def test_no_uncertainty_no_information_value(det):
    _, _, B, T = det
    z = U.Scenarios(params=U.sample(400, fixed=base_values()))
    assert V.evpi(z, B, T, 0.9) == pytest.approx(0, abs=1e-6)


def test_tornado_and_first_order(sc):
    tor = S.tornado(("A", "B"))
    assert [r["swing"] for r in tor] == sorted([r["swing"] for r in tor], reverse=True)
    assert tor[0]["parameter"] in ("tariff", "b_saving_frac", "pv_capex_kw")
    s1 = S.first_order(sc, sc.PNPV[sc.index(("A", "B"))] - sc.PNPV[sc.index(("A", "C", "D"))])
    assert next(iter(s1)) == "b_saving_frac"
    assert sum(s1.values()) < 1.15


def test_switch_point_motor_savings(det):
    prj, inter, B, T = det
    q = base_values()
    for frac, expect in ((0.125, "A+C+D"), (0.14, "A+B")):
        q["b_saving_frac"] = frac
        p2, i2 = E.projects(q)
        assert O.enumerate_best(p2, i2, B, T)[0]["portfolio"] == expect
