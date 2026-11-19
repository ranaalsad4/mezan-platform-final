"""AI capability D - decision explanation grounded in calculation-engine outputs.

facts()      builds a structured fact sheet from mezan_platform.analysis results (every number is copied from the
             engine's output; nothing is estimated here).
narrative()  deterministic, rule-based narrative generator (always available). Each section lists the engine outputs
             it rests on.
explain()    optional language-model rewrite of the same fact sheet (mezan_ai.llm). The output is accepted only if
             verify_numbers() finds no number that is absent from the fact sheet; otherwise the deterministic narrative
             is returned with the reason. The label on every explanation says which path produced it.
"""
from __future__ import annotations

import re

from mezan_platform import labels as LB
from . import llm

PCT_TOL = 0.006


def _sar(x):
    if x is None:
        return "n/a"
    return f"SAR {x / 1e6:,.2f} million" if abs(x) >= 1e6 else f"SAR {x:,.0f}"


def _pct(x, d=1):
    return f"{100 * x:.{d}f}%"


def facts(result, voi=None, switching=None, discount=None, tornado_rows=None, data_status=None):
    s = result["settings"]
    rec = result["recommended"]
    F = dict(n=s["n"], seed=s["seed"], budget=s["budget"], target_t=result["target_t"], target_share=s["target_share"],
             alpha=s["alpha"], beta=s["beta"], alpha_eff=result["a_eff"], beta_eff=result["b_eff"],
             scope12=result["totals"]["Scope 1+2"], basis=result["basis_label"], activity_basis=result["activity_basis"])
    if rec:
        st = result["stats_recommended"]
        passing = [r for r in result["table"] if r["within_budget_quote"] and r["passes_carbon"] and r["passes_budget"]
                   and r["portfolio"] != "(none)"]
        passing.sort(key=lambda r: -r["e_npv"])
        runner = passing[1] if len(passing) > 1 else None
        higher_failing = [r for r in result["table"] if r["within_budget_quote"] and r["e_npv"] > rec["e_npv"]
                          and not (r["passes_carbon"] and r["passes_budget"])]
        F.update(portfolio=rec["portfolio"], portfolio_names=LB.portfolio_names(rec["portfolio"]), e_npv=rec["e_npv"],
                 npv_base=rec["npv_base_inputs"], quoted_capex=rec["quoted_capex"], p_target=rec["p_target"], p_budget=rec["p_budget"],
                 p5_npv=rec["p5_npv"], p_loss=rec["p_loss"], p90_capex=rec["p90_capex"], e_t12=rec["e_t12"],
                 margin_target_se=rec["margin_target_se"], margin_budget_se=rec["margin_budget_se"], n_passing=len(passing),
                 runner_up=runner["portfolio"] if runner else None, runner_up_e_npv=runner["e_npv"] if runner else None,
                 higher_failing=[dict(portfolio=r["portfolio"], e_npv=r["e_npv"], fails=("carbon" if not r["passes_carbon"] else "")
                                      + (" and " if not r["passes_carbon"] and not r["passes_budget"] else "")
                                      + ("budget" if not r["passes_budget"] else "")) for r in higher_failing][:2])
        if st:
            F["e_capex"] = st["e_capex"]
    else:
        F.update(portfolio=None, min_budget=(result["min_budget"] or {}).get("budget"),
                 min_budget_portfolio=(result["min_budget"] or {}).get("portfolio"))
    if switching:
        sw = []
        for x in switching:
            for c in x["changes"]:
                sw.append(dict(parameter=x["parameter"], label=LB.label(x["parameter"]), threshold=c["threshold"], base=x["base"],
                               below=c["below"], above=c["above"], rel_distance=abs(c["threshold"] - x["base"]) / abs(x["base"])))
        sw.sort(key=lambda d: d["rel_distance"])
        F["switch_points"] = sw
        F["robust_parameters"] = [dict(parameter=x["parameter"], label=LB.label(x["parameter"]), range=x["range"])
                                  for x in switching if x["robust"]]
    if tornado_rows:
        t = tornado_rows[0]
        F["top_driver"] = dict(parameter=t["parameter"], label=LB.label(t["parameter"]), swing=t["swing"], low=t["low"], high=t["high"],
                               percentiles=(5, 95))
    if discount:
        F["discount_switch_D4"] = discount["changes_D4"][0]["threshold"] if discount["changes_D4"] else None
        F["discount_switch_D4_to"] = discount["changes_D4"][0]["above"] if discount["changes_D4"] else None
        F["discount_switch_D1"] = discount.get("changes_D1", [{}])[0].get("threshold") if discount.get("changes_D1") else None
    if voi:
        top = voi["ranking"][0]
        F.update(voi_rule=voi["rule"], evpi=voi["evpi"], voi_top=top["information"], voi_top_value=top["evppi_sar"],
                 voi_top_cost=top["collection_cost_sar"], voi_top_changes=top["decision_changes"],
                 voi_worth=[r["information"] for r in voi["ranking"] if r["net_value_sar"] is not None and r["net_value_sar"] > 0],
                 evsi=voi["evsi_audit"]["evsi"], evsi_cost=voi["evsi_audit"]["cost"], evsi_measurement=voi["evsi_audit"]["measurement"])
    if data_status:
        F["data_status"] = data_status
    return F


def narrative(F):
    """Deterministic explanation: list of dict(title, text, evidence)."""
    out = []
    if F.get("portfolio"):
        out.append(dict(title="Recommendation", evidence="analysis.run → decisions.choose (rule D4)", text=(
            f"Fund portfolio {F['portfolio']} ({F['portfolio_names']}). Its expected NPV across {F['n']:,} simulated futures is "
            f"{_sar(F['e_npv'])}; at most-likely inputs (deterministic) it is {_sar(F['npv_base'])}. The quoted capital cost is "
            f"{_sar(F['quoted_capex'])} against a budget of {_sar(F['budget'])}.")))
        why = (f"Of the {F['n_passing']} portfolios whose quoted cost fits the budget and that pass both probability tests, "
               f"{F['portfolio']} has the highest expected NPV.")
        if F.get("runner_up"):
            why += f" The next best, {F['runner_up']}, is expected to be worth {_sar(F['runner_up_e_npv'])}."
        for h in F.get("higher_failing", []):
            why += f" {h['portfolio']} would be worth more ({_sar(h['e_npv'])}) but fails the {h['fails']} test."
        out.append(dict(title="Why it wins", evidence="analysis.run → portfolio table (64 portfolios)", text=why))
        out.append(dict(title="Constraints", evidence="decisions.portfolio_probs; uncertainty.alpha_saa", text=(
            f"Two separate tests, both passed. Carbon target ({F['target_t']:,.0f} tCO2e/yr): met in {_pct(F['p_target'], 2)} of "
            f"simulated futures (required {_pct(F['alpha'], 0)}, applied as {_pct(F['alpha_eff'], 2)} to allow for sampling error). "
            f"Budget: actual capital cost within {_sar(F['budget'])} in {_pct(F['p_budget'], 2)} of futures (required "
            f"{_pct(F['beta'], 0)}, applied as {_pct(F['beta_eff'], 2)}). These are modelled probabilities under assumed input "
            "ranges, not guarantees.")))
        risk = (f"In the worst 5% of futures the NPV falls to {_sar(F['p5_npv'])} or less; a negative NPV occurs in "
                f"{_pct(F['p_loss'], 2)} of futures. The 90th-percentile actual capital cost is {_sar(F['p90_capex'])}.")
        if min(F["margin_target_se"], F["margin_budget_se"]) < 2:
            risk += (" One test is passed by less than two Monte Carlo standard errors: treat the choice as close to a "
                     "threshold.")
        out.append(dict(title="Main risks", evidence="uncertainty.Scenarios.stats", text=risk))
    else:
        mb = F.get("min_budget")
        out.append(dict(title="Recommendation", evidence="analysis.run → decisions.choose (rule D4)", text=(
            "No portfolio passes both probability tests within the budget, so none is recommended (none is forced). "
            + (f"The smallest budget that would make the rule feasible is about {_sar(mb)} ({F.get('min_budget_portfolio')})."
               if mb else "No portfolio meets the carbon requirement at any budget."))))
    ch = []
    for sp in F.get("switch_points", [])[:3]:
        ch.append(f"if {sp['label'][0].lower() + sp['label'][1:]} moves from {LB.fmt_value(sp['parameter'], sp['base'])} past "
                  f"{LB.fmt_value(sp['parameter'], sp['threshold'])}, the deterministic optimum changes from {sp['below']} to "
                  f"{sp['above']}" if sp["threshold"] > sp["base"] else
                  f"if {sp['label'][0].lower() + sp['label'][1:]} falls from {LB.fmt_value(sp['parameter'], sp['base'])} below "
                  f"{LB.fmt_value(sp['parameter'], sp['threshold'])}, the deterministic optimum changes from {sp['above']} to "
                  f"{sp['below']}")
    if ch or F.get("top_driver") or F.get("discount_switch_D4"):
        txt = ("Switching analysis: " + "; ".join(ch) + ".") if ch else ""
        td = F.get("top_driver")
        if td:
            robust = any(r["parameter"] == td["parameter"] for r in F.get("robust_parameters", []))
            txt += (f" Sensitivity analysis: {td['label'][0].lower() + td['label'][1:]} moves the portfolio's NPV most (swing {_sar(td['swing'])} between "
                    f"its 5th and 95th percentiles)" + (", yet it does not change the choice anywhere in its range." if robust else "."))
        if F.get("discount_switch_D4"):
            txt += (f" The primary rule switches to {F['discount_switch_D4_to']} only above a discount rate of "
                    f"{_pct(F['discount_switch_D4'], 1)}.")
        out.append(dict(title="What could change the decision", evidence="analysis.switching; analysis.tornado; analysis.discount_switch",
                        text=txt.strip()))
    if F.get("voi_top"):
        txt = (f"Under rule {F['voi_rule']}, resolving all uncertainty before investing would be worth at most {_sar(F['evpi'])} (EVPI). "
               f"The most valuable single item is {F['voi_top']}: perfect information on it is worth at most "
               f"{_sar(F['voi_top_value'])} (EVPPI, an upper bound)")
        if F.get("voi_top_cost") is not None:
            worth = F["voi_top_value"] > F["voi_top_cost"]
            txt += (f", {'above' if worth else 'below'} its assumed collection cost of {_sar(F['voi_top_cost'])}, so collecting it "
                    f"{'can be' if worth else 'is not'} economically justified at that price.")
        else:
            txt += "."
        txt += (f" A realistic, imperfect measurement ({F['evsi_measurement']}) is worth {_sar(F['evsi'])} (EVSI) against a cost of "
                f"{_sar(F['evsi_cost'])}. EVSI is calculated for this one measurement only.")
        out.append(dict(title="Is better information worth collecting?", evidence="voi.evpi; voi.ranking (EVPPI); voi.evsi_audit", text=txt))
    ds = F.get("data_status")
    if ds:
        out.append(dict(title="Data basis", evidence="dataquality ledger", text=ds))
    return out


_NUM = re.compile(r"(?<![A-Za-z])(\d[\d,]*\.?\d*)")


def _numbers(text):
    vals = []
    for m in _NUM.findall(text):
        s = m.rstrip(".").replace(",", "")
        try:
            vals.append(float(s))
        except ValueError:
            pass
    return vals


def allowed_numbers(F, narrative_sections):
    vals = set()
    for sec in narrative_sections:
        vals.update(_numbers(sec["text"]))

    def add(v):
        if isinstance(v, bool) or v is None:
            return
        if isinstance(v, (int, float)):
            for x in (v, v * 100, v / 1e6, v / 1e3):
                vals.add(round(float(x), 6))
        elif isinstance(v, dict):
            for x in v.values():
                add(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                add(x)
    for v in F.values():
        add(v)
    return vals


def verify_numbers(text, allowed):
    """Numbers in `text` that do not match an allowed value (within PCT_TOL relative, or small counts 0-12)."""
    bad = []
    for x in _numbers(text):
        if x <= 12 and float(x).is_integer():
            continue
        if not any(abs(x - a) <= PCT_TOL * max(abs(a), 1e-9) for a in allowed):
            bad.append(x)
    return bad


def fact_sheet(F, sections):
    return "\n".join(f"- {s['title']}: {s['text']}" for s in sections)


def explain(result, voi=None, switching=None, discount=None, tornado_rows=None, data_status=None, use_llm=True, post=None):
    """dict(sections, label, source, llm_text, rejected). source = 'deterministic' or 'llm'."""
    F = facts(result, voi, switching, discount, tornado_rows, data_status)
    secs = narrative(F)
    base = dict(sections=secs, facts=F, source="deterministic", llm_text=None, rejected=None,
                label="Rule-based narrative from calculation-engine outputs (no language model)")
    cfg = llm.config()
    if not (use_llm and (cfg["enabled"] or post is not None)):
        return base
    try:
        text = llm.complete(fact_sheet(F, secs), cfg if cfg["enabled"] else dict(cfg, enabled=True, model="test", _key="test"), post=post)
    except Exception as e:  # noqa: BLE001 - any failure falls back to the deterministic narrative
        return dict(base, rejected=f"language model unavailable ({type(e).__name__})")
    bad = verify_numbers(text, allowed_numbers(F, secs))
    if bad:
        return dict(base, rejected=f"language-model text contained numbers not in the engine outputs ({', '.join(f'{b:g}' for b in bad[:5])}); "
                                   "deterministic explanation shown instead")
    return dict(base, source="llm", llm_text=text,
                label=f"AI-generated explanation ({llm.describe()}); every number checked against calculation-engine outputs")
