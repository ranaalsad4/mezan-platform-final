"""Carbon accounting, uncertainty propagation, finance and the shared activity ledger."""
import math

import pytest

from carbon_iq import engine as E
from carbon_iq.assumptions import STATUSES, P, base_values, gas_price_sar_per_gj, v
from carbon_iq.optimize import all_portfolios


def test_baseline_activity_times_factor():
    rows = {r["source_id"]: r["emissions_t"] for r in E.baseline()}
    assert rows["S2-ELEC"] == pytest.approx(12_000 * v("ef_grid"))
    assert rows["S1-GAS"] == pytest.approx(35_000 * (56_100 + 28 + 0.1 * 265) / 1e6)
    assert rows["S1-DSL-FL"] == pytest.approx(60_000 * 2.66155 / 1000)
    assert rows["S3-C1-STEEL"] == pytest.approx(6_000 * 1.92)
    assert rows["S3-C4-FRT"] == pytest.approx(2_000_000 * 0.10163 / 1000)


def test_scope_totals_and_target():
    t = E.scope_totals(E.baseline())
    assert t["Scope 1+2"] == pytest.approx(t["Scope 1"] + t["Scope 2"])
    assert t["Total"] == pytest.approx(sum(r["emissions_t"] for r in E.baseline()))
    assert E.target_t() == pytest.approx(0.15 * t["Scope 1+2"])


def test_gas_factor_matches_ipcc_components():
    assert v("ef_gas") == pytest.approx((56_100 + 1 * 28 + 0.1 * 265) / 1e6, rel=1e-9)


def test_ghg_protocol_worked_example():
    # Guidance example: 110 t +/-4% plus 90 t +/-24% -> 200 t with ~11% uncertainty
    assert E.u_add([(110, 4), (90, 24)]) == pytest.approx(11.02, abs=0.01)
    assert E.u_mult(3, 4) == pytest.approx(5.0)


def test_uncertainty_table_rules():
    rows, tot = E.uncertainty_table()
    for r in rows:
        assert r["u_combined_pct"] == pytest.approx(math.hypot(r["u_activity_pct"], r["u_ef_pct"]))
        assert r["first_order_valid"]
    assert tot["Total"][1] <= max(r["u_combined_pct"] for r in rows)
    assert tot["Total"][1] >= min(r["u_combined_pct"] for r in rows)
    labels = {r["source_id"]: r["quality"] for r in rows}
    assert labels["S1-GAS"] == "High" and labels["S3-C4-FRT"] == "Poor"


def test_annuity_npv_irr_payback():
    assert float(E.annuity_factor(0.06, 15)) == pytest.approx((1 - 1.06 ** -15) / 0.06)
    assert float(E.annuity_factor(0.0, 10)) == pytest.approx(10)
    assert float(E.npv(1000, 100, 0.0, 10)) == pytest.approx(0.0)
    assert E.irr(1000, 200, 10) == pytest.approx(0.15098, abs=1e-4)
    assert E.simple_payback(1000, 250) == pytest.approx(4.0)
    assert E.irr(1000, 50, 10) is None or E.irr(1000, 50, 10) < 0


def test_project_a_by_hand():
    prj, _ = E.projects()
    mwh = 1000 * v("pv_yield") / 1000
    capex = 1000 * v("pv_capex_kw")
    om = 0.01 * capex
    d = v("pv_degradation")
    # year-by-year sum with declining output (v1.3)
    npv = -capex + sum((mwh * (1 - d) ** (t - 1) * v("tariff") * 1000 - om) / 1.06 ** t for t in range(1, 26))
    assert float(prj["A"]["npv"]) == pytest.approx(npv)
    assert float(prj["A"]["scope12_t"]) == pytest.approx(mwh * v("ef_grid"))
    assert float(E.degraded_annuity_factor(0.06, 25, 0.0)) == pytest.approx(float(E.annuity_factor(0.06, 25)))


def test_project_d_and_e_by_hand():
    prj, _ = E.projects()
    gj = 35_000 * 0.15
    cf_d = gj * gas_price_sar_per_gj(v("gas_price_usd")) - 10_000
    assert float(prj["D"]["annual_cf"]) == pytest.approx(cf_d)
    e_mwh = 60_000 * 3.5 / 1000
    assert float(prj["E"]["scope12_t"]) == pytest.approx(60_000 * 0.00266155 - e_mwh * v("ef_grid"))
    c_mwh = 12_000 * 0.15 * v("c_saving_frac")
    assert float(prj["C"]["annual_cf"]) == pytest.approx(c_mwh * v("tariff") * 1000 - v("c_om"))
    assert float(prj["F"]["scope12_t"]) == pytest.approx(0.0)
    assert float(prj["F"]["scope3_t"]) == pytest.approx(3_000 * (1.92 - 1.47))


def test_mac_definition():
    prj, _ = E.projects()
    d = prj["C"]
    assert float(E.mac(d)) == pytest.approx(-float(d["npv"]) / (float(d["af"]) * float(d["scope12_t"])))
    assert float(E.mac(prj["C"])) < 0 < float(E.mac(prj["E"]))


def test_ledger_equals_portfolio_for_all_64_no_double_counting():
    p = base_values()
    prj, inter = E.projects(p)
    base = E.ledger((), p)
    for c in all_portfolios():
        led = E.ledger(c, p)
        tot = E.portfolio(c, prj, inter)
        assert base["scope12_t"] - led["scope12_t"] == pytest.approx(float(tot["scope12_t"]), abs=1e-9)
        assert base["scope3_t"] - led["scope3_t"] == pytest.approx(float(tot["scope3_t"]), abs=1e-9)


def test_overlap_removed_only_when_b_and_c_together():
    prj, inter = E.projects()
    naive = float(prj["B"]["scope12_t"] + prj["C"]["scope12_t"])
    assert float(E.portfolio("BC", prj, inter)["scope12_t"]) == pytest.approx(naive - float(inter["BC"]["scope12_t"]))
    assert float(E.portfolio("AB", prj, inter)["scope12_t"]) == pytest.approx(float(prj["A"]["scope12_t"] + prj["B"]["scope12_t"]))
    assert float(inter["BC"]["scope12_t"]) > 0


def test_every_parameter_documented():
    for k, p in P.items():
        assert p.status in STATUSES, k
        assert p.source and p.unit, k
        if p.status in ("verified", "transferred", "provisional"):
            assert p.url, f"{p.status} parameter {k} needs a source link"
