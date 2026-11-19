"""Mezan Intelligence findings (rule-based) - short, ranked statements generated from the CURRENT model results (never hard-coded text).

Each insight carries:
  kind      what produced the underlying finding: "Calculation engine", "Rule-based check", "ML flag",
            "Statistical estimate", "ML classification"
  severity  "action" (blocks or needs a decision), "warning" (close to a threshold), "info"
  evidence  the function and values the statement rests on
  page      where to act in the interface
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from mezan_platform import labels as LB


@dataclass
class Insight:
    text: str
    severity: str
    kind: str
    evidence: str
    page: str

    def as_dict(self):
        return asdict(self)


ORDER = {"action": 0, "warning": 1, "info": 2}


def data_insights(ledger=None, anomalies=None, classification=None, blocked=None):
    out = []
    if classification is not None and len(classification):
        unres = int((classification.method == "unresolved").sum())
        auto = int((classification.method.isin(["rule", "ml"])).sum())
        if unres:
            out.append(Insight(f"{unres} record(s) could not be assigned to an energy stream automatically and need a reviewer "
                               "decision before they can enter the baseline.", "action", "ML classification",
                               f"classifier.classify: {unres} unresolved of {len(classification)}", "Plant Data"))
        if auto:
            n_ml = int((classification.method == "ml").sum())
            out.append(Insight(f"{auto} unlabelled record(s) were assigned to a stream ({auto - n_ml} by rules, {n_ml} by the text "
                               "classifier); confirm them in the review table.", "info", "ML classification",
                               "classifier.classify", "Plant Data"))
    if ledger is not None:
        t = ledger.table
        pend = t[t.decision == "pending"]
        if len(pend):
            by = pend.groupby("stream").size().sort_values(ascending=False)
            lead = ", ".join(f"{n} {s.replace('_', ' ')}" for s, n in by.items())
            out.append(Insight(f"{len(pend)} monthly record(s) require review before the plant-data baseline can be approved "
                               f"({lead}).", "action", "Rule-based check", f"dataquality ledger: {len(pend)} pending decisions",
                               "Plant Data"))
        ref = t[(t.decision == "pending") & (t.refusal != "")]
        if len(ref):
            codes = sorted({r.split(":")[0] for r in ref.refusal})
            out.append(Insight(f"Estimation was refused for {len(ref)} record(s) ({', '.join(codes)}); these gaps stay open "
                               "until real data are obtained or a reviewer documents an override.", "action", "Statistical estimate",
                               "estimate.propose refusal rules", "Plant Data"))
    if blocked:
        out.append(Insight(f"Plant-data baseline blocked: {blocked}. Missing data are never counted as zero.", "action",
                           "Rule-based check", "integrate.activity_from_annual", "Emissions"))
    if anomalies is not None:
        if anomalies.get("applied"):
            n = anomalies.get("n_flagged", 0)
            if n:
                months = ", ".join(anomalies["flags"].period.tolist()[:4])
                out.append(Insight(f"Isolation Forest flagged {n} month(s) in the reporting year as unusual combinations of "
                                   f"energy intensities ({months}); confirm or dismiss each before approving the baseline.",
                                   "warning", "ML flag", f"anomaly.detect: score ≥ {anomalies['threshold']:.2f}", "Plant Data"))
        else:
            out.append(Insight("ML anomaly detection was not applied: " + anomalies.get("reason", ""), "info", "ML flag",
                               "anomaly.detect", "Plant Data"))
    return out


def decision_insights(result, voi=None, switching=None, discount=None, tornado_rows=None):
    out = []
    rec = result["recommended"]
    s = result["settings"]
    if rec:
        out.append(Insight(f"Recommended portfolio {rec['portfolio']} ({LB.portfolio_names(rec['portfolio'])}): expected NPV "
                           f"SAR {rec['e_npv'] / 1e6:,.2f} million, carbon target met in {rec['p_target']:.2%} and budget held in "
                           f"{rec['p_budget']:.2%} of {s['n']:,} simulated futures.", "info", "Calculation engine",
                           "analysis.run → decisions.choose (D4)", "Investment Planner"))
        tight = min(rec["margin_target_se"], rec["margin_budget_se"])
        if tight < 2:
            which = "carbon" if rec["margin_target_se"] <= rec["margin_budget_se"] else "budget"
            out.append(Insight(f"The {which} test is passed by only {tight:.1f} Monte Carlo standard errors: a different random "
                               "sample could change the recommendation. Rerun with 20,000 scenarios or another seed.", "warning",
                               "Calculation engine", "probability margin vs tightened level", "Investment Planner"))
    else:
        mb = result["min_budget"]
        out.append(Insight("No portfolio passes both probability tests within the budget; none is recommended."
                           + (f" About SAR {mb['budget'] / 1e6:,.2f} million ({mb['portfolio']}) would be needed." if mb else ""),
                           "action", "Calculation engine", "analysis.run → decisions.choose (D4)", "Investment Planner"))
    if switching:
        near = []
        for x in switching:
            for c in x["changes"]:
                rel = abs(c["threshold"] - x["base"]) / abs(x["base"])
                near.append((rel, x, c))
        near.sort(key=lambda t: t[0])
        for rel, x, c in near[:2]:
            if rel <= 0.05:
                out.append(Insight(f"The deterministic choice is sensitive to {LB.label(x['parameter']).lower()}: it switches "
                                   f"between {c['below']} and {c['above']} at {LB.fmt_value(x['parameter'], c['threshold'])}, "
                                   f"{rel:.1%} from the current {LB.fmt_value(x['parameter'], x['base'])}.", "warning",
                                   "Calculation engine", "analysis.switching (bisection of sensitivity sweep)", "Decision Intelligence"))
    if tornado_rows and switching:
        t = tornado_rows[0]
        if any(x["parameter"] == t["parameter"] and x["robust"] for x in switching):
            out.append(Insight(f"{LB.label(t['parameter'])} moves NPV the most (swing SAR {t['swing'] / 1e6:,.2f} million) but does "
                               "not change the recommended portfolio anywhere in its tested range.", "info", "Calculation engine",
                               "analysis.tornado + analysis.switching", "Decision Intelligence"))
    if discount and discount.get("changes_D4"):
        c = discount["changes_D4"][0]
        if abs(c["threshold"] - s["discount_rate"]) <= 0.02:
            out.append(Insight(f"The primary recommendation switches to {c['above']} above a discount rate of {c['threshold']:.1%} "
                               f"(current {s['discount_rate']:.1%}).", "warning", "Calculation engine", "analysis.discount_switch",
                               "Decision Intelligence"))
    if voi:
        worth = [r for r in voi["ranking"] if r["net_value_sar"] is not None and r["net_value_sar"] > 0]
        if worth:
            r = worth[0]
            out.append(Insight(f"Collecting better data on {r['information']} is economically justified: its value (EVPPI SAR "
                               f"{r['evppi_sar']:,.0f}) exceeds the assumed cost (SAR {r['collection_cost_sar']:,.0f}).", "action",
                               "Calculation engine", "voi.ranking", "Decision Intelligence"))
        else:
            top = voi["ranking"][0]
            out.append(Insight("Additional measurement is not economically justified under the current assumptions: the most "
                               f"valuable item ({top['information']}) is worth at most SAR {top['evppi_sar']:,.0f} with perfect "
                               "information" + (f", below its SAR {top['collection_cost_sar']:,.0f} cost." if top["collection_cost_sar"]
                                                else "."), "info", "Calculation engine", "voi.ranking (EVPPI, upper bound)",
                               "Decision Intelligence"))
    return out


def rank(insights):
    return sorted(insights, key=lambda i: ORDER.get(i.severity, 3))
