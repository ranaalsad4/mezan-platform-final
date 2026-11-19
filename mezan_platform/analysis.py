"""Analysis service: runs the unchanged model v1.3 engines for one set of scenario settings.

Everything numerical comes from carbon_iq (engine, optimize, uncertainty, decisions, voi, sensitivity, timing,
dataquality.integrate, mrc). This module only:
  * assembles parameters from the user's scenario settings (same rules as the v2.1 app: discount rate fixed, tariff
    shifted, gas price scaled around the register's distributions);
  * applies the decision rules D1-D4 exactly as decisions.choose() does in the saved run;
  * refines existing switch-point sweeps by bisection (sensitivity.switch_points uses a 41-point grid; the grid result
    is kept and the bisection only narrows the bracket);
  * sweeps the discount rate for the primary rule D4 (the rate is a fixed input with no distribution).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace

import numpy as np

from carbon_iq import decisions as D
from carbon_iq import engine as E
from carbon_iq import optimize as O
from carbon_iq import sensitivity as S
from carbon_iq import timing as TM
from carbon_iq import uncertainty as U
from carbon_iq import voi as V
from carbon_iq.assumptions import MODEL_VERSION, P, PROJECTS, base_values
from carbon_iq.dataquality import integrate as DI

BASE = base_values()
SEED = 20261024
BASIS_LABELS = {
    "reporting": "Fixed reporting baseline (primary rule)",
    "physical": "Sampled emission factors (sensitivity)",
    "baseline": "Uncertain baseline (sensitivity)",
}
RULE_TEXT = {
    "D1": "Deterministic optimum: highest NPV at most-likely inputs, quoted capex within budget, reduction meets target",
    "D2": "Highest expected NPV, quoted capex within budget (no reliability requirement)",
    "D3": "Highest expected NPV with P(carbon target met) at or above the required level",
    "D4": "Highest expected NPV with P(carbon target met) and P(actual capex within budget) each at or above the required level",
}


@dataclass(frozen=True)
class Settings:
    """Scenario settings. Defaults reproduce the saved model v1.3 run (outputs/results.json)."""
    budget: float = float(BASE["budget"])
    target_share: float = float(BASE["target_share"])
    alpha: float = float(BASE["chance_level"])            # required P(carbon target met)
    beta: float = float(BASE["budget_chance_level"])      # required P(actual capex <= budget)
    discount_rate: float = float(BASE["discount_rate"])
    tariff: float = float(BASE["tariff"])
    gas_price_usd: float = float(BASE["gas_price_usd"])
    n: int = 20000
    basis: str = "reporting"
    seed: int = SEED

    def changed_from_defaults(self):
        d = Settings()
        return {k: (getattr(d, k), v) for k, v in asdict(self).items() if v != getattr(d, k)}

    def key(self):
        return tuple(sorted(asdict(self).items()))


DEFAULTS = Settings()

SETTING_META = {      # label, unit, help, (min, max)
    "budget": ("Capital budget", "SAR", "Maximum quoted capital cost of the portfolio. Also the limit for the budget probability rule.",
               (500_000, 20_000_000)),
    "target_share": ("Carbon-reduction target", "% of Scope 1+2", "Required yearly Scope 1+2 reduction as a share of the "
                     "baseline.", (0.0, 0.30)),
    "alpha": ("Required probability: carbon target", "probability", "A portfolio must meet the carbon target in at least this "
              "share of simulated futures (tightened for sampling error).", (0.50, 0.99)),
    "beta": ("Required probability: within budget", "probability", "A portfolio's uncertain actual capex must stay within the "
             "budget in at least this share of simulated futures (tightened for sampling error). Separate from the carbon test.",
             (0.50, 0.99)),
    "discount_rate": ("Discount rate", "real, per year", "Real discount rate used for every NPV.", (0.02, 0.14)),
    "tariff": ("Electricity tariff today", "SAR/kWh", "Shifts the centre of the tariff distribution.", (0.10, 0.35)),
    "gas_price_usd": ("Natural-gas price today", "USD/MMBtu", "Scales the gas-price distribution.", (1.0, 8.0)),
    "n": ("Monte Carlo scenarios", "futures", "20,000 reproduces the saved report run (seed 20261024).", (2000, 20000)),
    "basis": ("Carbon-target baseline convention", "", "How reductions are counted against the target.", None),
    "seed": ("Scenario seed", "integer", "Random seed of the scenario sample; the same seed gives identical results.", (1, 2**31 - 1)),
}


def validate(s: Settings):
    """Return a list of human-readable problems with the settings (empty = valid)."""
    out = []
    for k, (label, unit, _, rng) in SETTING_META.items():
        val = getattr(s, k)
        if rng is not None and not (rng[0] <= val <= rng[1]):
            out.append(f"{label} must be between {rng[0]:,} and {rng[1]:,} ({unit}).")
    if s.basis not in BASIS_LABELS:
        out.append("Unknown carbon-target baseline convention.")
    if int(s.n) != s.n:
        out.append("Monte Carlo scenarios must be a whole number.")
    return out


# ------------------------------------------------------------------ parameters
def deterministic_params(s: Settings, activity=None):
    p = dict(BASE)
    p.update(budget=s.budget, target_share=s.target_share, chance_level=s.alpha, budget_chance_level=s.beta,
             discount_rate=s.discount_rate, tariff=s.tariff, gas_price_usd=s.gas_price_usd)
    for k, (val, _) in (activity or {}).items():
        p[k] = val
    return p


def _shift_prices(prm, s: Settings):
    n = len(next(iter(prm.values())))
    prm = dict(prm)
    prm["discount_rate"] = np.full(n, s.discount_rate)
    prm["tariff"] = prm["tariff"] + (s.tariff - BASE["tariff"])
    prm["gas_price_usd"] = prm["gas_price_usd"] * s.gas_price_usd / BASE["gas_price_usd"]
    return prm


def scenario_params(s: Settings, activity=None):
    """Monte Carlo parameters and per-scenario target offsets. Without `activity` this is the v2.1 app's sample; with
    approved plant data it is dataquality.integrate's construction (estimation error included)."""
    if activity is None:
        return _shift_prices(U.sample(s.n, s.seed), s), 0.0
    _, prm0, z = DI.params_for(activity, n=s.n, seed=s.seed)
    base_for_share = dict(BASE, target_share=s.target_share)
    prm, dT = DI._apply(activity, prm0, z, base_for_share)
    return _shift_prices(prm, s), dT


# ------------------------------------------------------------------ main run
def run(s: Settings = DEFAULTS, activity=None, activity_label=None):
    """Full portfolio evaluation for one set of settings.

    activity: None = reference activity data from the assumption register (model v1.3); otherwise the approved plant
    data as {register key: (annual total, sd of the estimated part)} from dataquality.integrate.activity_from_annual."""
    problems = validate(s)
    if problems:
        raise ValueError("; ".join(problems))
    p = deterministic_params(s, activity)
    rows_b = E.baseline(p)
    tot = E.scope_totals(rows_b)
    unc_rows, unc_tot = E.uncertainty_table(rows_b)
    T = E.target_t(p)
    prj, inter = E.projects(p)
    det_best, det_rows = O.enumerate_best(prj, inter, s.budget, T)
    prm, dT = scenario_params(s, activity)
    sc = U.Scenarios(params=prm, basis=s.basis)
    Ts = T + dT
    pr = D.portfolio_probs(sc, s.budget, Ts)
    a_eff, b_eff = U.alpha_saa(s.alpha, s.n), U.alpha_saa(s.beta, s.n)
    choice = {"D1": sc.index(det_best["ids"]) if det_best else None, "D2": D.choose(pr, s.budget),
              "D3": D.choose(pr, s.budget, a_eff), "D4": D.choose(pr, s.budget, a_eff, b_eff)}
    det_by_name = {r["portfolio"]: r for r in det_rows}
    table = []
    for k in range(len(sc.ports)):
        name = sc.name(k)
        v = sc.PNPV[k]
        q5 = float(np.percentile(v, 5))
        se_t = math.sqrt(max(pr["p_target"][k] * (1 - pr["p_target"][k]), 1e-12) / s.n)
        se_b = math.sqrt(max(pr["p_budget"][k] * (1 - pr["p_budget"][k]), 1e-12) / s.n)
        table.append(dict(
            k=k, portfolio=name, ids=sc.ports[k], quoted_capex=float(sc.capex[k]),
            within_budget_quote=bool(sc.capex[k] <= s.budget + 1e-6),
            npv_base_inputs=float(det_by_name[name]["npv"]), scope12_base_inputs=float(det_by_name[name]["scope12_t"]),
            e_npv=float(pr["e_npv"][k]), p5_npv=q5, cvar5_npv=float(v[v <= q5].mean()), p_loss=float((v < 0).mean()),
            e_t12=float(sc.PT12[k].mean()), p_target=float(pr["p_target"][k]), p_budget=float(pr["p_budget"][k]),
            p_both=float(pr["p_both"][k]), p90_capex=float(pr["p90_capex"][k]),
            margin_target_se=float((pr["p_target"][k] - a_eff) / se_t), margin_budget_se=float((pr["p_budget"][k] - b_eff) / se_b),
            passes_carbon=bool(pr["p_target"][k] >= a_eff - 1e-12), passes_budget=bool(pr["p_budget"][k] >= b_eff - 1e-12)))
    rec_k = choice["D4"]
    min_budget = None
    if rec_k is None:
        need = []
        for r in table:
            if r["passes_carbon"] and r["portfolio"] != "(none)":
                need.append((max(float(np.quantile(sc.PCAP[r["k"]], b_eff, method="higher")), r["quoted_capex"]), r["portfolio"]))
        need.sort()
        min_budget = dict(budget=need[0][0], portfolio=need[0][1]) if need else None
    return dict(
        settings=asdict(s), model_version=MODEL_VERSION, basis_label=BASIS_LABELS[s.basis],
        activity_basis="approved plant data" if activity is not None else "reference activity data (assumption register)",
        activity_label=activity_label, activity=activity,
        p=p, baseline_rows=rows_b, uncertainty_rows=unc_rows, uncertainty_totals=unc_tot, totals=tot, target_t=T,
        target_sd=float(np.std(dT)) if np.ndim(dT) else 0.0,
        prj=prj, inter=inter, det_best=det_best, det_rows=det_rows, sc=sc, pr=pr, a_eff=a_eff, b_eff=b_eff,
        choice=choice, choice_names={r: (sc.name(k) if k is not None else None) for r, k in choice.items()},
        table=table, recommended=(table[rec_k] if rec_k is not None else None), min_budget=min_budget,
        stats_recommended=(sc.stats(rec_k, T, budget=s.budget) if rec_k is not None else None))


def alternatives(result, top=6):
    """Recommended portfolio first, then the next best by expected NPV among portfolios whose quoted capex fits."""
    rows = [r for r in result["table"] if r["within_budget_quote"] and r["portfolio"] != "(none)"]
    rows.sort(key=lambda r: -r["e_npv"])
    rec = result["recommended"]
    out = ([rec] if rec else []) + [r for r in rows if not rec or r["portfolio"] != rec["portfolio"]]
    return out[:top]


def project_table(result):
    p, prj = result["p"], result["prj"]
    out = []
    for i, d in prj.items():
        r_ = E.project_irr(d, p.get("pv_degradation", 0.0)) if i == "A" else E.irr(float(d["capex"]), float(d["annual_cf"]), int(d["life"]))
        cf = float(d["annual_cf"])
        out.append(dict(id=i, name=PROJECTS[i], capex=float(d["capex"]), annual_cf=cf, life=int(d["life"]), npv=float(d["npv"]),
                        irr=r_, payback=(E.simple_payback(float(d["capex"]), cf) if cf > 0 else None),
                        scope12_t=float(d["scope12_t"]), scope3_t=float(d["scope3_t"]), mac=float(E.mac(d))))
    return out


# ------------------------------------------------------------------ decision intelligence
def tornado(result, ids=None, top=8):
    """One-way sensitivity of the NPV of `ids` around the CURRENT settings (sensitivity.tornado uses the register)."""
    ids = tuple(ids or (result["recommended"] or result["det_best"] or {"ids": ("A", "B")})["ids"])
    base = result["p"]

    def npv_t(q):
        prj, inter = E.projects(q)
        t = E.portfolio(ids, prj, inter)
        return float(t["npv"]), float(t["scope12_t"])
    b_npv, b_t = npv_t(base)
    rows = []
    for k in P:
        lv = S.pct_values(k)
        if lv is None:
            continue
        res = []
        for val in lv:
            q = dict(base); q[k] = val
            res.append(npv_t(q))
        rows.append(dict(parameter=k, label=P[k].label if hasattr(P[k], "label") else k, low=lv[0], high=lv[1],
                         npv_low=res[0][0], npv_high=res[1][0], swing=abs(res[1][0] - res[0][0]), base_npv=b_npv))
    rows.sort(key=lambda r: -r["swing"])
    return ids, rows[:top]


def _det_choice(base, budget, T, key, val):
    q = dict(base); q[key] = float(val)
    prj, inter = E.projects(q)
    best, _ = O.enumerate_best(prj, inter, budget, T)
    return best["portfolio"] if best else "infeasible"


def _range(key):
    d = P[key].dist
    if d is None:
        return None
    if d[0] == "uniform":
        return d[1], d[2]
    if d[0] == "triangular":
        return d[1], d[3]
    if d[0] == "normal_rel":
        return P[key].value * (1 - 2.33 * d[1]), P[key].value * (1 + 2.33 * d[1])
    return P[key].value * math.exp(-2.33 * d[1]), P[key].value * math.exp(2.33 * d[1])


SWITCH_KEYS = ("c_saving_frac", "b_saving_frac", "tariff", "pv_capex_kw", "pv_yield", "gas_price_usd", "c_capex", "b_capex")


def switching(result, keys=SWITCH_KEYS, n_grid=41, tol=1e-6):
    """Switch points of the deterministic optimum (rule D1) for each input across its plausible range, at the current
    settings. Grid as sensitivity.switch_points, each change bracket then narrowed by bisection."""
    base, budget, T = result["p"], result["settings"]["budget"], result["target_t"]
    out = []
    for key in keys:
        rng = _range(key)
        if rng is None:
            continue
        grid = np.linspace(rng[0], rng[1], n_grid)
        seq = [(float(g), _det_choice(base, budget, T, key, g)) for g in grid]
        changes = []
        for i in range(1, len(seq)):
            (x0, a), (x1, b) = seq[i - 1], seq[i]
            if a == b:
                continue
            lo, hi = x0, x1
            while hi - lo > tol * max(1.0, abs(hi)):
                mid = (lo + hi) / 2
                if _det_choice(base, budget, T, key, mid) == a:
                    lo = mid
                else:
                    hi = mid
            changes.append(dict(threshold=(lo + hi) / 2, below=a, above=b, bracket=(lo, hi)))
        b0 = float(base.get(key, P[key].value))
        nearest = min(changes, key=lambda c: abs(c["threshold"] - b0)) if changes else None
        out.append(dict(parameter=key, base=b0, unit=P[key].unit, range=(float(rng[0]), float(rng[1])), changes=changes,
                        robust=not changes, current=_det_choice(base, budget, T, key, b0),
                        nearest_rel_distance=(abs(nearest["threshold"] - b0) / abs(b0) if nearest and b0 else None)))
    return out


def discount_switch(s: Settings, rates=(0.02, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10, 0.12, 0.14), activity=None, tol=1e-4):
    """Primary rule D4 and deterministic rule D1 across discount rates; each change refined by bisection on D4."""
    def d4(rate):
        r = run(replace(s, discount_rate=float(rate)), activity)
        return r["choice_names"]["D4"] or "none feasible", r["choice_names"]["D1"] or "infeasible"
    seq = [(r_, *d4(r_)) for r_ in rates]

    def refine(j):
        changes = []
        for i in range(1, len(seq)):
            x0, a, x1, b = seq[i - 1][0], seq[i - 1][j], seq[i][0], seq[i][j]
            if a == b:
                continue
            lo, hi = x0, x1
            while hi - lo > tol:
                mid = (lo + hi) / 2
                if d4(mid)[j - 1] == a:
                    lo = mid
                else:
                    hi = mid
            changes.append(dict(threshold=(lo + hi) / 2, below=a, above=b))
        return changes
    return dict(sequence=[dict(rate=r_, D4=a, D1=b) for r_, a, b in seq], changes_D4=refine(1), changes_D1=refine(2))


def value_of_information(result):
    """EVPI, EVPPI ranking, noise floor and the motor-audit EVSI under rule D3 (carbon chance constraint), exactly as
    carbon_iq.voi computes them on this run's scenarios (scalar target)."""
    sc, budget, T, a = result["sc"], result["settings"]["budget"], result["target_t"], result["a_eff"]
    ranking, noise = V.ranking(sc, budget, T, a)
    evsi, choices, _ = V.evsi_audit(sc, budget, T, a)
    return dict(rule="D3", evpi=V.evpi(sc, budget, T, a), ranking=ranking, noise_floor=noise,
                evsi_audit=dict(evsi=evsi, cost=float(P["cost_motor_audit"].value), error_sd=float(P["audit_error_sd"].value),
                                choices=sorted(set(choices)), measurement="Motor-system audit (project B savings)"))


def timing(result, p_reform=None, g_reform=None):
    """Invest-now-or-wait for project D only (partially implemented extension)."""
    t = TM.decision_tree(p_reform=float(BASE["tree_p_reform"]) if p_reform is None else p_reform,
                         g_reform=float(BASE["tree_g_reform"]) if g_reform is None else g_reform,
                         g_now=result["settings"]["gas_price_usd"])
    g = TM.gbm_trigger()
    return dict(tree=t, gbm=g, scope="Project D (furnace waste-heat recovery) and the gas price only; decision tree and GBM "
                                      "trigger in the app, log-OU least-squares Monte Carlo in run_all.py outputs.")


def data_from_ledger(ledger):
    """(activity or None, problem text, annual table) from a reviewed dataquality Ledger. Unresolved gaps block."""
    ann = ledger.annual()
    try:
        return DI.activity_from_annual(ann), None, ann
    except DI.IncompleteData as e:
        return None, str(e), ann
