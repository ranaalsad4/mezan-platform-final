"""Mezan Phase A6 - independent re-implementation used to check the model (written separately from carbon_iq/).

Independence rules
  * This module imports NOTHING from carbon_iq. Its only input is the exported register (outputs/assumptions.csv),
    i.e. the same INPUT VALUES, recomputed with separately written formulas.
  * Portfolios are evaluated from a year-by-year activity ledger (energy saved per year -> cash flow per year ->
    discounted sum), not as a sum of project NPVs minus an overlap term as in carbon_iq/engine.py.
  * Random inputs are drawn by inverse-CDF transforms of uniforms from a different generator family (numpy MT19937
    or scipy Sobol), not with carbon_iq/uncertainty.py.
What this does NOT make independent: the input values and the project definitions (taken from the register and the
case description) and the decision rules as specified in the README. A wrong specification would be reproduced here.
"""
import ast
import itertools
import math
from pathlib import Path

import numpy as np
from scipy import stats

IDS = ("A", "B", "C", "D", "E", "F")
SAR_PER_USD, GJ_PER_MMBTU = 3.75, 1.055056
PORTS = [c for r in range(7) for c in itertools.combinations(IDS, r)]
Z = stats.norm.ppf


def load_register(path):
    import pandas as pd
    d = pd.read_csv(path)
    vals = {r.key: float(r.value) for r in d.itertuples()}
    dists = {r.key: ast.literal_eval(r.dist) for r in d.itertuples() if isinstance(r.dist, str) and r.dist.startswith("(")}
    return vals, dists


# ------------------------------------------------------------------ emission factors re-derived from primary data
def derived_factors():
    """Factors recomputed from the primary figures quoted in the register sources (AR5 GWPs: CH4 28, N2O 265)."""
    gwp_ch4, gwp_n2o = 28, 265
    gas = (56100 + 1 * gwp_ch4 + 0.1 * gwp_n2o) / 1e6               # IPCC 2006 Vol.2 Table 2.2/2.3 kg/TJ -> t/GJ
    # diesel, IPCC 2006 defaults: 74,100 kg CO2/TJ, CH4 3, N2O 0.6 kg/TJ (stationary), NCV 43.0 TJ/Gg, density 0.84 kg/L
    ncv_gj_per_l = 43.0 * 0.84 / 1000
    diesel_ipcc = (74100 + 3 * gwp_ch4 + 0.6 * gwp_n2o) / 1e6 * ncv_gj_per_l
    grid = 205_579e3 / 358_640e3                                       # t CO2e / MWh (BTR1 2021 1.A.1.a.i / GASTAT 2021)
    grid_consumed = 205_579e3 / 301_600e3
    return dict(ef_gas=gas, ef_diesel_ipcc=diesel_ipcc, ef_grid=grid, ef_grid_consumption=grid_consumed)


# ------------------------------------------------------------------ inventory
def inventory(p):
    """Scope totals in t CO2e with explicit unit conversions (activity unit x factor unit)."""
    rows = [
        ("Scope 1", "natural gas", p["gas_gj"], "GJ", p["ef_gas"], "t/GJ"),
        ("Scope 1", "diesel forklifts", p["diesel_forklift_l"], "L", p["ef_diesel"], "t/L"),
        ("Scope 1", "diesel generators", p["diesel_genset_l"], "L", p["ef_diesel"], "t/L"),
        ("Scope 2", "grid electricity", p["elec_mwh"], "MWh", p["ef_grid"], "t/MWh"),
        ("Scope 3", "purchased steel (Cat 1)", p["steel_t"], "t", p["ef_steel_incumbent"], "t/t"),
        ("Scope 3", "inbound freight (Cat 4)", p["freight_tkm"], "t-km", p["ef_freight"], "t/t-km"),
    ]
    for _, _, _, ua, _, uf in rows:
        assert uf.split("/")[1] == ua, (ua, uf)          # dimensional check: factor denominator = activity unit
    out = {"rows": [(s, n, a * f) for s, n, a, _, f, _ in rows]}
    for s in ("Scope 1", "Scope 2", "Scope 3"):
        out[s] = sum(e for sc, _, e in out["rows"] if sc == s)
    out["Scope 1+2"] = out["Scope 1"] + out["Scope 2"]
    out["Total"] = out["Scope 1+2"] + out["Scope 3"]
    out["target"] = p["target_share"] * out["Scope 1+2"]
    return out


# ------------------------------------------------------------------ year-by-year ledger
def _lives(p):
    # lives are fixed inputs (no distribution); arrays from the sampler are reduced to their single value
    return {k: float(np.max(p[x])) for k, x in (("A", "pv_life"), ("B", "b_life"), ("C", "c_life"), ("D", "d_life"),
                                                 ("E", "e_life"), ("F", "f_life"))}


def ledger_flows(sel, p, horizon=None):
    """Year-by-year activity changes and cash flows of a portfolio (values may be numpy arrays).
    Returns capex, list of yearly cash flows (t = 1..H), year-1 Scope 1+2 reduction (t) and Scope 3 change (t)."""
    sel = set(sel)
    L = _lives(p)
    H = int(max([L[i] for i in sel] + [1])) if horizon is None else horizon
    gas_sar_gj = p["gas_price_usd"] * SAR_PER_USD / GJ_PER_MMBTU
    tariff_mwh = p["tariff"] * 1000.0
    comp = p["elec_mwh"] * p["compressed_air_share"]
    motor = p["elec_mwh"] * p["motor_share"]
    capex = 0.0
    capex = capex + (p["pv_kwp"] * p["pv_capex_kw"] if "A" in sel else 0) + (p["b_capex"] if "B" in sel else 0) \
        + (p["c_capex"] if "C" in sel else 0) + (p["d_capex"] if "D" in sel else 0) + (p["e_capex"] if "E" in sel else 0) \
        + (p["f_onboard"] if "F" in sel else 0)
    flows, red1 = [], None
    for t in range(1, H + 1):
        on = {i: (i in sel) and t <= L[i] for i in IDS}
        d_elec = 0.0                                                    # MWh saved this year (negative = added)
        if on["A"]:
            d_elec = d_elec + p["pv_kwp"] * p["pv_yield"] / 1000 * (1 - p["pv_degradation"]) ** (t - 1)
        comp_left = comp * (1 - p["c_saving_frac"]) if on["C"] else comp
        if on["C"]:
            d_elec = d_elec + comp * p["c_saving_frac"]
        if on["B"]:
            d_elec = d_elec + motor * p["b_saving_frac"] + comp_left * p["b_comp_frac"]
        d_diesel = p["diesel_forklift_l"] if on["E"] else 0.0
        if on["E"]:
            d_elec = d_elec - p["diesel_forklift_l"] * p["e_kwh_per_l"] / 1000
        d_gas = p["gas_gj"] * p["d_saving_frac"] if on["D"] else 0.0
        cash = d_elec * tariff_mwh + d_gas * gas_sar_gj + d_diesel * p["diesel_price"]
        cash = cash - (p["pv_om_frac"] * p["pv_kwp"] * p["pv_capex_kw"] if on["A"] else 0) - (p["c_om"] if on["C"] else 0) \
            - (p["d_om"] if on["D"] else 0) + (p["e_maint_saving"] if on["E"] else 0) - (p["f_steel_t"] * p["f_premium"] if on["F"] else 0)
        flows.append(cash)
        if t == 1:
            red1 = d_elec * p["ef_grid"] + d_gas * p["ef_gas"] + d_diesel * p["ef_diesel"]
            s3 = (p["f_steel_t"] * (p["ef_steel_incumbent"] - p["ef_steel_alt"])) if "F" in sel else 0.0
    if red1 is None:
        red1, s3 = 0.0, 0.0
    return capex, flows, red1, s3


def npv(capex, flows, r):
    return -capex + sum(cf / (1 + r) ** t for t, cf in enumerate(flows, start=1))


def portfolio(sel, p):
    capex, flows, red1, s3 = ledger_flows(sel, p)
    return dict(capex=capex, npv=npv(capex, flows, p["discount_rate"]), red12=red1, red3=s3, flows=flows)


def project_metrics(k, p):
    """Stand-alone metrics: NPV, simple payback (capex / year-1 net cash flow), IRR (root of NPV(r)), MAC."""
    capex, flows, red1, s3 = ledger_flows((k,), p)
    r = p["discount_rate"]
    v = npv(capex, flows, r)
    pb = capex / flows[0] if flows[0] > 0 else math.inf
    try:
        from scipy.optimize import brentq
        f = lambda x: npv(capex, flows, x)  # noqa: E731
        irr = brentq(f, -0.95, 1.0) if f(-0.95) * f(1.0) < 0 else None
    except ValueError:
        irr = None
    # MAC: -NPV / discounted lifetime tonnes, tonnes per year follow the same decline as the energy output
    L = int(_lives(p)[k])
    if k == "A":
        tonnes = [red1 * (1 - p["pv_degradation"]) ** (t - 1) for t in range(1, L + 1)]
    elif k == "F":
        tonnes = [s3] * L
    else:
        tonnes = [red1] * L
    disc_t = sum(x / (1 + r) ** t for t, x in enumerate(tonnes, start=1))
    mac = -v / disc_t if disc_t else math.nan
    return dict(capex=capex, npv=v, payback=pb, irr=irr, red12=red1, red3=s3, mac=mac, cf1=flows[0])


def enumerate_best(p, budget, target, exclusive=()):
    best = None
    for c in PORTS:
        if any(set(x) <= set(c) for x in exclusive):
            continue
        m = portfolio(c, p)
        if m["capex"] <= budget + 1e-6 and m["red12"] >= target - 1e-9:
            if best is None or m["npv"] > best[1] + 1e-9:
                best = ("+".join(c) or "(none)", m["npv"])
    return best


# ------------------------------------------------------------------ independent sampler
def _ppf(dist, value, u):
    k = dist[0]
    if k == "normal_rel":
        return value * np.clip(1 + dist[1] * Z(u), 0.05, None)          # model specification: truncated at 5% of value
    if k == "uniform":
        return dist[1] + (dist[2] - dist[1]) * u
    if k == "triangular":
        lo, mode, hi = dist[1:]
        return stats.triang.ppf(u, (mode - lo) / (hi - lo), loc=lo, scale=hi - lo)
    if k == "lognormal":
        return value * np.exp(dist[1] * Z(u) - dist[1] ** 2 / 2)          # mean-preserving lognormal
    raise ValueError(dist)


def sample(vals, dists, n, seed, method="mt"):
    keys = sorted(dists)
    if method == "sobol":
        U = stats.qmc.Sobol(len(keys), scramble=True, seed=seed).random(n)
    else:
        U = np.random.Generator(np.random.MT19937(seed)).random((n, len(keys)))
    U = np.clip(U, 1e-12, 1 - 1e-12)
    out = {k: np.full(n, v) for k, v in vals.items()}
    for j, k in enumerate(keys):
        out[k] = _ppf(dists[k], vals[k], U[:, j])
    return out


def mc_table(vals, dists, n, seed, method="mt", reporting=True):
    """Per portfolio (quoted capex <= budget): E[NPV], P(target), P(actual capex <= budget), with the target fixed at the
    reporting baseline and reductions counted with fixed (reporting) factors."""
    s = sample(vals, dists, n, seed, method)
    if reporting:
        for k in ("ef_grid", "ef_gas", "ef_diesel", "ef_freight", "ef_steel_incumbent", "ef_steel_alt"):
            s[k] = np.full(n, vals[k])
    target = inventory(vals)["target"]
    budget = vals["budget"]
    out = {}
    for c in PORTS:
        quoted = portfolio(c, vals)["capex"]
        if quoted > budget + 1e-6:
            continue
        m = portfolio(c, s)
        cap = np.broadcast_to(m["capex"], (n,))
        out["+".join(c) or "(none)"] = dict(e_npv=float(np.mean(m["npv"])), sd_npv=float(np.std(m["npv"])),
                                           p_target=float(np.mean(np.broadcast_to(m["red12"], (n,)) >= target)),
                                           p_budget=float(np.mean(cap <= budget + 1e-6)), quoted=quoted,
                                           npv=np.broadcast_to(m["npv"], (n,)), red=np.broadcast_to(m["red12"], (n,)), cap=cap)
    return out, s, target


def alpha_saa(alpha, n, z=1.6448536):
    return min(1.0, alpha + z * math.sqrt(alpha * (1 - alpha) / n))


def decide(tab, n, alpha, beta=None):
    """D2/D3/D4 from an mc_table: maximise E[NPV] subject to P(target) >= tightened alpha (and budget prob)."""
    a = alpha_saa(alpha, n) if alpha else None
    b = alpha_saa(beta, n) if beta else None
    ok = [k for k, r in tab.items() if (a is None or r["p_target"] >= a - 1e-12) and (b is None or r["p_budget"] >= b - 1e-12)]
    return max(ok, key=lambda k: tab[k]["e_npv"]) if ok else None


