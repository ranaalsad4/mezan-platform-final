"""Phase A6 - independent mathematical and integrated validation. Writes outputs/a6/*.csv, a6_results.json and charts.

    python tools/run_a6.py                 # all sections (~25 min on 2 cores)
    python tools/run_a6.py emissions finance optimization   # selected sections

Sections compare the model (carbon_iq) with the separately written re-implementation in independent/indep.py, with
published benchmarks, or with closed forms. Each row states which kind of check it is:
  independent  - recomputed by code that does not import carbon_iq (same input values)
  benchmark    - compared with a published numerical result or a closed form
  internal     - the model checked against itself (e.g. different seeds or sample sizes); NOT independent
All data are the synthetic case: nothing here is real-world validation.
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from independent import indep as I  # noqa: E402

OUT = HERE / "outputs" / "a6"
OUT.mkdir(parents=True, exist_ok=True)
RES = json.load(open(HERE / "outputs" / "results.json"))
VALS, DISTS = I.load_register(HERE / "outputs" / "assumptions.csv")
SUMMARY = {}


def rel(a, b):
    return abs(a - b) / max(1.0, abs(b))


def save(name, df):
    df.to_csv(OUT / name, index=False)
    return df


# ------------------------------------------------------------------ 1. emissions
def emissions():
    inv = I.inventory(VALS)
    df_ = I.derived_factors()
    rows = []
    for k in ("Scope 1", "Scope 2", "Scope 3", "Scope 1+2", "Total"):
        rows.append(dict(item=k, model=RES["scope_totals"][k], independent=inv[k], kind="independent"))
    rows.append(dict(item="Target (15% of Scope 1+2)", model=RES["target_t"], independent=inv["target"], kind="independent"))
    for (name, val, key, tol) in (("Natural gas factor re-derived from IPCC 2006 + AR5 GWP (t/GJ)", df_["ef_gas"], "ef_gas", 1e-9),
                                  ("Diesel factor, IPCC 2006 defaults incl. CH4/N2O, density 0.84 (t/L)", df_["ef_diesel_ipcc"], "ef_diesel", 0.02),
                                  ("Grid factor re-derived: BTR1 205,579 Gg / GASTAT 358,640 GWh (t/MWh)", df_["ef_grid"], "ef_grid", 0.001)):
        rows.append(dict(item=name, model=VALS[key], independent=val, kind="benchmark (primary data)", tolerance=tol))
    d = pd.DataFrame(rows)
    d["rel_diff"] = [rel(a, b) for a, b in zip(d.independent, d.model)]
    d["tolerance"] = d.get("tolerance", pd.Series([1e-9] * len(d))).fillna(1e-9)
    d["pass"] = d.rel_diff <= d.tolerance
    SUMMARY["emissions"] = dict(n=len(d), passed=int(d["pass"].sum()),
                                grid_consumption_factor=df_["ef_grid_consumption"],
                                note="Diesel: register uses DESNZ 2.66155 kg/L; IPCC default with CH4/N2O gives "
                                     f"{df_['ef_diesel_ipcc']*1000:.4f} kg/L ({(df_['ef_diesel_ipcc']/VALS['ef_diesel']-1):+.1%}), inside the 2% tolerance")
    return save("a6_emissions.csv", d)


# ------------------------------------------------------------------ 2. finance
def finance():
    rows = []
    prj = {p["id"]: p for p in RES["projects"]}
    for k in I.IDS:
        m = I.project_metrics(k, VALS)
        q = prj[k]
        for metric, a, b in (("capex", m["capex"], q["capex"]), ("NPV", m["npv"], q["npv"]), ("payback (yr)", m["payback"], q["payback_y"]),
                             ("IRR", m["irr"], q["irr"]), ("MAC (SAR/t)", m["mac"], q["mac_sar_per_t"]),
                             ("Scope 1+2 reduction (t)", m["red12"], q["scope12_t"]), ("Scope 3 reduction (t)", m["red3"], q["scope3_t"])):
            if a is None or b is None or (isinstance(a, float) and math.isinf(a)):
                ok = (a is None or (isinstance(a, float) and math.isinf(a))) and b is None
                rows.append(dict(level="project", item=k, metric=metric, model=b, independent=a, rel_diff=0.0 if ok else None, pass_=ok))
                continue
            rows.append(dict(level="project", item=k, metric=metric, model=b, independent=a, rel_diff=rel(a, b), pass_=rel(a, b) < 1e-7))
    # all 64 portfolios: ledger cash flows vs model sum-minus-overlap
    sys.path.insert(0, str(HERE))
    from carbon_iq import engine as E
    from carbon_iq.assumptions import base_values
    p = base_values()
    mp, inter = E.projects(p)
    for c in I.PORTS:
        a = I.portfolio(c, VALS)
        b = E.portfolio(c, mp, inter)
        nm = "+".join(c) or "(none)"
        rows.append(dict(level="portfolio", item=nm, metric="NPV", model=float(b["npv"]), independent=a["npv"], rel_diff=rel(a["npv"], float(b["npv"])),
                         pass_=rel(a["npv"], float(b["npv"])) < 1e-7))
        rows.append(dict(level="portfolio", item=nm, metric="Scope 1+2 reduction (t)", model=float(b["scope12_t"]), independent=a["red12"],
                         rel_diff=rel(a["red12"], float(b["scope12_t"])), pass_=rel(a["red12"], float(b["scope12_t"])) < 1e-7))
    d = pd.DataFrame(rows).rename(columns={"pass_": "pass"})
    fails = d[~d["pass"].astype(bool)]
    SUMMARY["finance"] = dict(n=len(d), passed=int(d["pass"].astype(bool).sum()), failures=fails[["item", "metric", "model", "independent"]].to_dict("records"))
    return save("a6_finance.csv", d)


# ------------------------------------------------------------------ 3. optimisation
def optimization():
    from carbon_iq import engine as E
    from carbon_iq import optimize as O
    from carbon_iq.assumptions import base_values
    p = base_values()
    prj, inter = E.projects(p)
    rows = []
    budgets = np.arange(0, 8.01e6, 0.25e6)
    targets = np.arange(0, 3201, 100)
    for excl in ((), (("A", "E"),), (("B", "C"),)):
        for b in budgets:
            for t in targets:
                m = O.solve_milp(prj, inter, b, t, excl)
                e, _ = O.enumerate_best(prj, inter, b, t, excl)
                i = I.enumerate_best(VALS, b, t, excl)
                mp = m["portfolio"] or "(none)" if m else None
                ep = e["portfolio"] if e else None
                ip = i[0] if i else None
                mn = m["npv"] if m else None
                inn = i[1] if i else None
                same_choice = (mp == ep == ip)
                # equal-NPV ties are accepted when the NPVs agree
                same_value = (mn is None and inn is None) or (mn is not None and inn is not None and abs(mn - inn) < 1e-3)
                rows.append(dict(exclusive=";".join("+".join(x) for x in excl) or "none", budget=b, target=t, milp=mp, enumeration=ep,
                                 independent=ip, milp_npv=mn, independent_npv=inn, same_choice=same_choice, same_value=same_value))
    d = pd.DataFrame(rows)
    SUMMARY["optimization"] = dict(cases=len(d), identical_choice=int(d.same_choice.sum()), identical_value=int(d.same_value.sum()),
                                   infeasible_cases=int(d.milp.isna().sum()),
                                   distinct_optima=int(d.milp.dropna().nunique()))
    return save("a6_optimization.csv", d)


# ------------------------------------------------------------------ 4/5. Monte Carlo and chance constraints
def montecarlo():
    from carbon_iq import uncertainty as U
    from carbon_iq.assumptions import base_values
    from carbon_iq.engine import target_t
    B = VALS["budget"]
    model = {r["portfolio"]: r for r in RES["mc_portfolios"]}
    n_m = RES["meta"]["scenarios"]
    rows = []
    t0 = time.time()
    tabs = {}
    for method, n, seed in (("mt", 200_000, 101), ("sobol", 2 ** 17, 202)):
        tab, _, _ = I.mc_table(VALS, DISTS, n, seed, method)
        tabs[method] = (tab, n)
        for k, r in tab.items():
            m = model[k]
            for metric, a, b in (("E[NPV]", r["e_npv"], m["e_npv"]), ("P(target)", r["p_target"], m["p_target"]),
                                 ("P(capex<=budget)", r["p_budget"], m["p_budget"])):
                if metric == "E[NPV]":
                    se = math.sqrt(r["sd_npv"] ** 2 / n + m["sd_npv"] ** 2 / n_m)
                else:
                    pp = (a + b) / 2
                    se = math.sqrt(max(pp * (1 - pp), 1e-12) * (1 / n + 1 / n_m))
                z = (a - b) / se if se > 0 else 0.0
                rows.append(dict(sampler=f"independent {method} n={n}", portfolio=k, metric=metric, model_20k=b, independent=a, se=se, z=z))
    d = save("a6_mc_independent.csv", pd.DataFrame(rows))
    # decisions from the independent samples
    dec = {}
    for method, (tab, n) in tabs.items():
        dec[method] = dict(D2=I.decide(tab, n, None), D3=I.decide(tab, n, 0.9), D4=I.decide(tab, n, 0.9, 0.9))
    SUMMARY["mc_independent"] = dict(rows=len(d), max_abs_z=float(d.z.abs().max()), share_abs_z_gt_3=float((d.z.abs() > 3).mean()),
                                     share_abs_z_gt_2=float((d.z.abs() > 2).mean()), decisions=dec,
                                     model_decisions={x["id"]: x["portfolio"] for x in RES["decision_scenarios"] if x["id"] in ("D2", "D3", "D4")})
    # analytic check of P(actual capex <= budget): sum of independent normals (truncation at 5% negligible)
    an = []
    from scipy.stats import norm
    sds = {"A": VALS["pv_kwp"] * VALS["pv_capex_kw"] * 0.15, "B": VALS["b_capex"] * 0.15, "C": VALS["c_capex"] * 0.15,
           "D": VALS["d_capex"] * 0.15, "E": VALS["e_capex"] * 0.15, "F": 0.0}
    for k, r in tabs["mt"][0].items():
        ids = [] if k == "(none)" else k.split("+")
        mu = r["quoted"]
        sd = math.sqrt(sum(sds[i] ** 2 for i in ids))
        pa = 1.0 if sd == 0 else float(norm.cdf((B - mu) / sd))
        an.append(dict(portfolio=k, quoted=mu, sd_actual=sd, p_budget_analytic=pa, p_budget_model=model[k]["p_budget"],
                       p_budget_model_validation=model[k]["p_budget_val"], p_budget_independent=r["p_budget"]))
    an = save("a6_chance_budget_analytic.csv", pd.DataFrame(an))
    SUMMARY["chance_budget"] = dict(max_abs_diff_model_vs_analytic=float((an.p_budget_model - an.p_budget_analytic).abs().max()),
                                    max_abs_diff_validation_vs_analytic=float((an.p_budget_model_validation - an.p_budget_analytic).abs().max()),
                                    alpha_saa_20000=I.alpha_saa(0.9, 20000))
    # convergence: model sampler, several sizes and seeds (internal check)
    conv = []
    T = target_t()
    for n in (1000, 2000, 5000, 10000, 20000, 50000, 100000):
        for s in range(10):
            sc = U.Scenarios(params=U.sample(n, 7000 + s), basis="reporting")
            kb = sc.best_expected(B)
            kc, _, _, okc = sc.decide(B, T, U.alpha_saa(0.9, n))
            kj, _, _, okj = sc.decide(B, T, U.alpha_saa(0.9, n), budget_reliability=U.alpha_saa(0.9, n))
            iabc, iab = sc.index(("A", "B", "C")), sc.index(("A", "B"))
            conv.append(dict(n=n, seed=7000 + s, e_npv_ABC=float(sc.PNPV[iabc].mean()), p_target_AB=float((sc.PT12[iab] >= T).mean()),
                             p_target_ABC=float((sc.PT12[iabc] >= T).mean()), p_budget_ABC=sc.p_within_budget(iabc, B),
                             D2=sc.name(kb), D3=sc.name(kc) if okc else "none feasible", D4=sc.name(kj) if (kj is not None and okj) else "none feasible"))
    c = save("a6_mc_convergence.csv", pd.DataFrame(conv))
    g = c.groupby("n").agg(e_npv_mean=("e_npv_ABC", "mean"), e_npv_sd=("e_npv_ABC", "std"), p_ab_mean=("p_target_AB", "mean"),
                           p_ab_sd=("p_target_AB", "std"), p_bud_mean=("p_budget_ABC", "mean"), p_bud_sd=("p_budget_ABC", "std"),
                           D2_ABC=("D2", lambda x: (x == "A+B+C").mean()), D3_ABC=("D3", lambda x: (x == "A+B+C").mean()),
                           D4_ABC=("D4", lambda x: (x == "A+B+C").mean())).reset_index()
    sd_npv = model["A+B+C"]["sd_npv"]
    g["e_npv_sd_theory"] = sd_npv / np.sqrt(g.n)
    g["p_bud_sd_theory"] = np.sqrt(model["A+B+C"]["p_budget"] * (1 - model["A+B+C"]["p_budget"]) / g.n)
    save("a6_mc_convergence_summary.csv", g)
    SUMMARY["mc_convergence"] = g.to_dict("records")
    SUMMARY["mc_time_s"] = time.time() - t0


# ------------------------------------------------------------------ 6. value of information
def voi():
    from carbon_iq import uncertainty as U
    from carbon_iq import voi as V
    from carbon_iq.engine import target_t
    B, T = VALS["budget"], target_t()
    n = 20000
    a = U.alpha_saa(0.9, n)
    sc = U.Scenarios(params=U.sample(n, 20261024), basis="reporting")
    k0, e0, p0, _ = sc.decide(B, T, a)
    cand = sc.candidates(B)
    NP, TT = sc.PNPV[cand], sc.PT12[cand]
    # (a) model EVPI re-done independently with explicit loops over scenarios (same definition)
    best = np.full(n, -np.inf)
    for j in range(len(cand)):
        best = np.where((TT[j] >= T) & (NP[j] > best), NP[j], best)
    fb = NP[np.argmax(TT, axis=0), np.arange(n)]
    evpi_same = float(np.where(np.isfinite(best), best, fb).mean() - e0)
    # (b) EVPI with the chance constraint kept under perfect information: the policy may miss the target in up to 10%
    #     of scenarios, chosen where giving up the target gains most (exact on the sample: fractional knapsack in s)
    unc = NP.max(axis=0)
    con = np.where(np.isfinite(best), best, -np.inf)
    gain = unc - np.where(np.isfinite(con), con, -1e18)
    must_miss = ~np.isfinite(con)
    allow = int(math.floor((1 - a) * n)) - int(must_miss.sum())
    val = np.where(np.isfinite(con), con, unc)
    if allow > 0:
        order = np.argsort(-np.where(must_miss, -np.inf, gain))[:allow]
        val[order] = unc[order]
    evpi_cc = float(val.mean() - e0)
    # (c) EVPPI by nested Monte Carlo on a fine grid (no binning): fix the parameter at 40 quantiles, 20,000 inner
    rows = []
    from carbon_iq.assumptions import P
    for key in ("c_saving_frac", "b_saving_frac", "tariff", "pv_yield", "ef_grid", "pv_capex_kw"):
        qs = (np.arange(40) + 0.5) / 40
        xs = np.quantile(sc.p[key], qs)
        vals_, choices = [], []
        for x in xs:
            s2 = U.Scenarios(params=U.sample(n, 31337, fixed={key: x}), basis="reporting")
            k, e, _, ok = s2.decide(B, T, a)
            # value of the chosen portfolio is measured on the conditional sample; compare with the prior choice there
            vals_.append(e - float(s2.PNPV[s2.index(sc.ports[k0])].mean()))
            choices.append(s2.name(k))
        binned, ch_b = V.evppi(sc, sc.p[key], B, T, a)
        rows.append(dict(parameter=key, evppi_nested=float(np.mean(vals_)), evppi_binned_model=binned,
                         posterior_choices_nested=";".join(sorted(set(choices))), share_grid_changing_choice=float(np.mean([c != sc.name(k0) for c in choices])),
                         model_reported=next((r["evppi_sar"] for r in RES["voi"] if r["parameter"] == key), None)))
    ev = save("a6_voi_evppi.csv", pd.DataFrame(rows))
    # (d) EVSI of the motor audit by likelihood weighting (exact Bayesian posterior on the sample, no binning)
    sd = VALS["audit_error_sd"]
    b = sc.p["b_saving_frac"]
    sig_grid = np.quantile(b + np.random.default_rng(5).normal(0, sd, n), (np.arange(40) + 0.5) / 40)
    alt = []
    for sgl in sig_grid:
        w = np.exp(-0.5 * ((sgl - b) / sd) ** 2); w /= w.sum()
        en = NP @ w
        pt = (TT >= T).astype(float) @ w
        ok = np.where(pt >= a - 1e-12)[0]
        j = ok[np.argmax(en[ok])] if len(ok) else int(np.argmax(pt))
        j0 = cand.index(k0)
        alt.append((en[j] - en[j0], sc.name(cand[j])))
    evsi_w = float(np.mean([x for x, _ in alt]))
    SUMMARY["voi"] = dict(prior_choice=sc.name(k0), evpi_model=RES["evpi"], evpi_recomputed_same_definition=evpi_same,
                          evpi_chance_constraint_kept=evpi_cc, evsi_model=RES["evsi_audit"]["evsi"], evsi_likelihood_weighting=evsi_w,
                          evsi_posterior_choices=sorted(set(c for _, c in alt)), evppi=ev.to_dict("records"))


# ------------------------------------------------------------------ 7. real options
def realoptions():
    from carbon_iq import timing as TM
    from carbon_iq.assumptions import v
    out = {}
    # (a) decision tree by hand
    t = TM.decision_tree()
    d = TM.project_d()
    r = v("discount_rate")
    unit = d["q_gj"] * 3.75 / 1.055056
    eg = v("tree_p_reform") * v("tree_g_reform") + (1 - v("tree_p_reform")) * v("gas_price_usd")
    now = -d["capex"] + (unit * v("gas_price_usd") - d["om"]) / (1 + r) + sum((unit * eg - d["om"]) / (1 + r) ** k for k in range(2, d["life"] + 1))
    af = sum(1 / (1 + r) ** k for k in range(1, d["life"] + 1))
    hi = -d["capex"] + (unit * v("tree_g_reform") - d["om"]) * af
    lo = -d["capex"] + (unit * v("gas_price_usd") - d["om"]) * af
    wait = (v("tree_p_reform") * max(hi, 0) + (1 - v("tree_p_reform")) * max(lo, 0)) / (1 + r)
    out["tree"] = dict(model_now=t["npv_invest_now"], hand_now=now, model_wait=t["value_wait_one_year"], hand_wait=wait,
                       model_decision=t["decision"], hand_decision="invest now" if now >= wait else "wait for the price decision")
    # (b) log-OU expected price: closed form used in exercise_value vs simulated mean of the exact discretisation
    G, dt = TM.simulate_logou(200000, 10, g0=v("gas_price_usd"), seed=99)
    sig, kap, gbar = v("ro_sigma"), v("ro_kappa"), v("gas_price_usd")
    alpha = math.log(gbar) - sig ** 2 / (4 * kap)
    x0 = math.log(gbar)
    rows = []
    for k in (1, 5, 10):
        cf = math.exp(alpha + (x0 - alpha) * math.exp(-kap * k) + sig ** 2 / (2 * kap) * (1 - math.exp(-2 * kap * k)) / 2)
        sim = float(G[:, int(k / dt)].mean())
        rows.append(dict(year=k, closed_form=cf, simulated=sim, se=float(G[:, int(k / dt)].std() / math.sqrt(len(G)))))
    out["logou_mean"] = rows
    out["logou_long_run_mean_equals_gbar"] = math.exp(alpha + sig ** 2 / (4 * kap))
    # (c) LSMC engine on the published Longstaff-Schwartz (2001) American put benchmark: S0=36, K=40, r=6%, sigma=20%, T=1,
    #     50 exercise dates per year. Published LSM value 4.472 (finite difference 4.478).
    rng = np.random.default_rng(11)
    vals = []
    for rep in range(5):
        def gbm(seed):
            g = np.random.default_rng(seed)
            n, m = 100000, 50
            z = g.standard_normal((n // 2, m)); z = np.vstack([z, -z])
            dtt = 1 / m
            x = np.cumsum((0.06 - 0.02) * dtt + 0.2 * math.sqrt(dtt) * z, axis=1)
            return np.hstack([np.full((n, 1), 36.0), 36 * np.exp(x)])
        Gf, Ge = gbm(1000 + rep), gbm(2000 + rep)
        disc = math.exp(-0.06 / 50)
        evf, eve = np.maximum(40 - Gf, 0), np.maximum(40 - Ge, 0)
        betas = TM._fit_policy(Gf, evf, disc)
        v_, _ = TM._apply_policy(Ge, eve, disc, betas)
        vals.append(float(v_.mean()))
    out["lsmc_put_benchmark"] = dict(model_lsmc_mean=float(np.mean(vals)), sd_across_reps=float(np.std(vals)), published_lsm=4.472,
                                     published_fd=4.478, european_bs=float(_bs_put(36, 40, 0.06, 0.2, 1)))
    del rng
    # (d) GBM trigger: lambda is the positive root of 0.5 s^2 L(L-1) + mu L - r = 0; trigger maximises the value of a
    #     threshold policy (checked by direct numerical maximisation of the closed-form threshold value)
    g = TM.gbm_trigger()
    mu, s, rc = g["mu"], g["sigma"], g["r_continuous"]
    lam = g["lambda"]
    resid = 0.5 * s ** 2 * lam * (lam - 1) + mu * lam - rc
    be = g["breakeven_usd"]
    G0 = v("gas_price_usd")
    th = np.linspace(be * 1.0001, be * 8, 20000)
    # value today of investing when G first hits th (G0 < th): (G0/th)^lam * (A*unit*th - I)  (Dixit-Pindyck)
    T_ = d["life"]
    A_ = (1 - math.exp(-(rc - mu) * T_)) / (rc - mu)
    I_ = d["capex"] + d["om"] * (1 - math.exp(-rc * T_)) / rc
    valth = (G0 / th) ** lam * (A_ * unit * th - I_)
    out["gbm"] = dict(lambda_=lam, quadratic_residual=resid, trigger_model=g["trigger_usd"], trigger_numeric=float(th[np.argmax(valth)]),
                      breakeven=be)
    out["notes"] = ("Decision tree = prototype for an administered price (one reform step), not a published method. LSMC = Longstaff-Schwartz "
                    "(2001) on a log-OU process as in KAPSARC DP49; GBM trigger = Dixit-Pindyck closed form as in DP49 Eq. C.7/C.13. "
                    "The DP49 calibration (kappa 0.5, sigma 0.522 from Henry Hub) is borrowed; Saudi administered prices do not follow it.")
    SUMMARY["realoptions"] = out


def _bs_put(S, K, r, s, T):
    from scipy.stats import norm
    d1 = (math.log(S / K) + (r + s * s / 2) * T) / (s * math.sqrt(T)); d2 = d1 - s * math.sqrt(T)
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


# ------------------------------------------------------------------ 8. missing data (A4 engine; synthetic data only)
def missingdata():
    from scipy.stats import norm
    cells = pd.read_csv(HERE / "outputs" / "a4" / "validation_cells.csv")
    est = cells[cells.estimated == True].copy()  # noqa: E712
    z95 = norm.ppf(0.975)
    # the study stores the UNCALIBRATED sd (calibration is applied when coverage is evaluated); production estimates use
    # sd x CAL_MONTHLY. Recompute both and compare with the reported held-out coverage.
    from carbon_iq.dataquality import estimate as EST
    cal = EST.CAL_MONTHLY
    est["covered_raw"] = (est["true"] - est["estimate"]).abs() <= z95 * est["sd"]
    est["covered_recomputed"] = (est["true"] - est["estimate"]).abs() <= z95 * cal * est["sd"]
    agree = float((est["covered_raw"] == est["covered"].astype(bool)).mean())
    rep = pd.read_csv(HERE / "outputs" / "a4" / "calibration_coverage.csv")
    rep_after = rep[(rep.dataset.str.startswith("base")) & (rep.setting.str.startswith("after")) & (rep.scenario == "all")].iloc[0]
    rows = []
    for (var,), g in est.groupby(["variant"]):
        k, n = int(g.covered_recomputed.sum()), len(g)
        lo, hi = _wilson(k, n)
        rows.append(dict(dataset=var, gaps=n, coverage=k / n, ci_low=lo, ci_high=hi, mape=float(g.rel_err.abs().mean()),
                         mape_mean_of_measured=float(g.err_mean.abs().mean()), bias=float(g.rel_err.mean())))
    cov = save("a6_missing_coverage.csv", pd.DataFrame(rows))
    # propagation into the decision: the target sd in the A4 case C2 must equal share x sqrt(sum (ef_i sd_i)^2)
    dec = pd.read_csv(HERE / "outputs" / "a4" / "decision_comparison.csv")
    c2 = dec[dec.case == "C2"].iloc[0]
    import re
    sds = dict((k, float(x)) for k, x in re.findall(r"(\w+) ([\d.]+)", c2.detail.split("estimated sd:")[1]))
    sd_t = VALS["target_share"] * math.sqrt((VALS["ef_grid"] * sds.get("elec_mwh", 0)) ** 2 + (VALS["ef_gas"] * sds.get("gas_gj", 0)) ** 2
                                            + (VALS["ef_diesel"] * sds.get("diesel_forklift_l", 0)) ** 2)
    # operational-change test: the model's detect_change vs a separately written permutation max-|t| test on simple
    # series NOT produced by the A4 generator (iid log-normal noise, with or without one step)
    rng = np.random.default_rng(321)
    ch = []
    for shift in (0.0, 0.05, 0.10, 0.20, 0.30):
        for sd in (0.03, 0.06):
            hits, hits_i, split_ok, n_rep = 0, 0, 0, 200
            for rep_ in range(n_rep):
                x = rng.normal(0, sd, 24)
                x[14:] += math.log(1 + shift)
                ser = {f"2025-{m+1:02d}" if m < 12 else f"2026-{m-11:02d}": float(v_) for m, v_ in enumerate(x)}
                r_ = EST.detect_change(ser, key=f"a6-{shift}-{sd}-{rep_}")
                ri = _indep_change(x, rng)
                hits += r_ is not None; hits_i += ri is not None
                if r_ is not None and shift > 0:
                    split_ok += abs(sorted(ser).index(r_["split"]) - 14) <= 1
            ch.append(dict(true_shift=shift, noise_sd=sd, detect_rate_model=hits / n_rep, detect_rate_independent=hits_i / n_rep,
                           split_within_1_month=(split_ok / hits) if hits and shift > 0 else None))
    chd = save("a6_change_detection_independent.csv", pd.DataFrame(ch))
    SUMMARY["missing"] = dict(coverage_flag_agreement=agree, by_dataset=cov.to_dict("records"),
                              calibration_factor=cal, coverage_reported_after=float(rep_after.monthly_coverage),
                              change_detection=chd.to_dict("records"),
                              target_sd_model=float(c2.target_sd), target_sd_independent=sd_t,
                              note="sds in the detail string are rounded to 0.1, so agreement is to about 0.1%")


def _indep_change(x, rng, alpha=0.01, min_shift=0.10, n_perm=499):
    """Separately written single mean-shift test: max |Welch t| over splits (>= 3 before, >= 2 after), permutation p."""
    def stat(y):
        best, at = 0.0, -1
        for s_ in range(3, len(y) - 1):
            a, b = y[:s_], y[s_:]
            se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
            t = abs(b.mean() - a.mean()) / se if se > 0 else 0.0
            if t > best:
                best, at = t, s_
        return best, at
    t0, s0 = stat(x)
    if s0 < 0 or abs(math.exp(x[s0:].mean() - x[:s0].mean()) - 1) < min_shift:
        return None
    cnt = sum(stat(rng.permutation(x))[0] >= t0 - 1e-12 for _ in range(n_perm))
    p = (cnt + 1) / (n_perm + 1)
    return (s0, p) if p < alpha else None


def _wilson(k, n, z=1.959964):
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - h, c + h


# ------------------------------------------------------------------ 9. global sensitivity (Sobol, Saltelli/Jansen estimators)
def gsa(N=2 ** 13):
    from scipy.stats import qmc
    from carbon_iq import engine as E
    from carbon_iq.assumptions import base_values
    keys = sorted(DISTS)
    k = len(keys)
    U2 = qmc.Sobol(2 * k, scramble=True, seed=8).random(N)
    UA, UB = np.clip(U2[:, :k], 1e-12, 1 - 1e-12), np.clip(U2[:, k:], 1e-12, 1 - 1e-12)
    base = base_values()
    T = E.target_t(base)
    budget = base["budget"]
    efk = ("ef_grid", "ef_gas", "ef_diesel", "ef_freight", "ef_steel_incumbent", "ef_steel_alt")

    def model(U):
        p = {kk: np.full(N, vv) for kk, vv in base.items()}
        for j, kk in enumerate(keys):
            p[kk] = I._ppf(DISTS[kk], VALS[kk], U[:, j])
        prj, inter = E.projects(p)
        pe = dict(p); pe.update({kk: np.full(N, base[kk]) for kk in efk})
        prj_e, inter_e = E.projects(pe)
        res = {}
        npv = {c: E.portfolio(c, prj, inter)["npv"] for c in I.PORTS}
        red = {c: E.portfolio(c, prj_e, inter_e)["scope12_t"] for c in I.PORTS}
        quoted = {c: float(E.portfolio(c, *E.projects(base))["capex"]) for c in I.PORTS}
        res["NPV(A+B+C)"] = npv[("A", "B", "C")]
        res["NPV(A+B+C) - NPV(A+B)"] = npv[("A", "B", "C")] - npv[("A", "B")]
        res["Reduction(A+B+C) - target"] = red[("A", "B", "C")] - T
        cands = [c for c in I.PORTS if quoted[c] <= budget + 1e-6]
        V = np.vstack([np.where(np.broadcast_to(red[c], (N,)) >= T, np.broadcast_to(npv[c], (N,)), -np.inf) for c in cands])
        bestc = np.argmax(V, axis=0)
        res["1[scenario-best portfolio = A+B+C]"] = np.array([cands[j] == ("A", "B", "C") for j in bestc], float)
        return res

    yA, yB = model(UA), model(UB)
    rows = []
    for j, kk in enumerate(keys):
        UAB = UA.copy(); UAB[:, j] = UB[:, j]
        yAB = model(UAB)
        for out in yA:
            fa, fb, fab = yA[out], yB[out], yAB[out]
            var = np.var(np.concatenate([fa, fb]))
            if var <= 0:
                s1 = st = 0.0
            else:
                s1 = float(np.mean(fb * (fab - fa)) / var)              # Saltelli 2010
                st = float(0.5 * np.mean((fa - fab) ** 2) / var)        # Jansen 1999
            rows.append(dict(output=out, parameter=kk, S1=s1, ST=st))
    d = save("a6_gsa_sobol.csv", pd.DataFrame(rows))
    top = {}
    for out, g in d.groupby("output"):
        g = g.sort_values("ST", ascending=False)
        top[out] = g.head(6)[["parameter", "S1", "ST"]].to_dict("records")
    SUMMARY["gsa"] = dict(N=N, evaluations=N * (len(keys) + 2), top=top)


def _clean(o):
    """NaN/inf -> None so the JSON is standard (readable by the report builders)."""
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, float) and not math.isfinite(o):
        return None
    if hasattr(o, "item") and not isinstance(o, (list, dict)):
        return _clean(o.item())
    return o


SECTIONS = dict(emissions=emissions, finance=finance, optimization=optimization, montecarlo=montecarlo, voi=voi,
                realoptions=realoptions, missingdata=missingdata, gsa=gsa)

if __name__ == "__main__":
    sel = sys.argv[1:] or list(SECTIONS)
    prev = json.load(open(OUT / "a6_results.json")) if (OUT / "a6_results.json").exists() else {}
    for s in sel:
        t0 = time.time()
        SECTIONS[s]()
        print(f"{s}: {time.time() - t0:.0f}s", flush=True)
    prev.update(SUMMARY)
    prev["model_version"] = RES["meta"]["model_version"]
    json.dump(_clean(prev), open(OUT / "a6_results.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(json.dumps({k: SUMMARY[k] for k in SUMMARY if k not in ("mc_convergence", "gsa", "voi")}, indent=1, default=str)[:4000])
