"""Investment timing: decision tree, log-OU expectations, GBM closed form and LSMC."""
import math

import numpy as np
import pytest

from carbon_iq import timing as TM
from carbon_iq.assumptions import v


def test_static_breakeven_gives_zero_npv():
    be = TM.static_breakeven_usd()
    assert TM.static_npv(be) == pytest.approx(0, abs=1e-6)
    assert 3.0 < be < 4.5


def test_logou_long_run_mean():
    # alpha = ln(G_bar) - sigma^2/(4 kappa) => E[G] -> G_bar; expected-price NPV at G_bar equals static NPV at G_bar
    d = TM.project_d()
    g = v("gas_price_usd")
    ev = float(TM.exercise_value(np.array([g]), d=d)[0])
    st = TM.static_npv(g, d)
    assert ev == pytest.approx(st, rel=0.05)
    G, _ = TM.simulate_logou(20000, 30, g0=g)
    assert G[:, -1].mean() == pytest.approx(g, rel=0.03)


def test_decision_tree_by_hand():
    t = TM.decision_tree(p_reform=0.5, g_reform=4.5)
    d = TM.project_d()
    r = v("discount_rate")
    unit = d["q_gj"] * 3.75 / 1.055056
    af = (1 - (1 + r) ** -d["life"]) / r
    hi = -d["capex"] + (unit * 4.5 - d["om"]) * af
    assert t["npv_if_reform_at_t1"] == pytest.approx(hi)
    assert t["value_wait_one_year"] == pytest.approx(0.5 * max(hi, 0) / (1 + r))
    assert t["decision"] == "wait for the price decision"
    assert t["option_premium"] >= 0


def test_tree_waits_for_cheap_deferral_but_invests_when_price_already_high():
    # with a certain future reform but a low price today, deferring capex beats one year of low savings
    assert TM.decision_tree(p_reform=1.0, g_reform=8.0, g_now=3.0)["decision"] == "wait for the price decision"
    # when today's price is already high, the year-1 savings exceed the value of deferral
    assert TM.decision_tree(p_reform=1.0, g_reform=8.0, g_now=6.0)["decision"] == "invest now"


def test_gbm_closed_form_properties():
    g = TM.gbm_trigger()
    assert g["lambda"] > 1 and g["multiplier"] > 1
    assert g["trigger_usd"] == pytest.approx(g["multiplier"] * g["breakeven_usd"])
    low = TM.gbm_trigger(sigma=0.2)
    assert low["multiplier"] < g["multiplier"]            # higher volatility raises the trigger (DP49 C.2)
    b = g["mu"] - g["sigma"] ** 2 / 2
    lam = (-b + math.sqrt(b ** 2 + 2 * g["r_continuous"] * g["sigma"] ** 2)) / g["sigma"] ** 2
    assert g["lambda"] == pytest.approx(lam)


def test_lsmc_value_nonnegative_and_invests_when_deep_in_money():
    r = TM.lsmc(n=1500)
    assert r["value_wait"] >= -1e-9 and not r["invest_now"]
    hi = TM.lsmc(n=1500, g0=12.0, gbar=12.0, sigma=0.2)
    assert hi["invest_now"]
