"""5 · Mezan Decision Intelligence - why is this the best decision, what could change it, and should I collect more
information before investing? Eight question cards; each answer is generated from the current engine outputs
(analysis.run, switching, discount_switch, tornado, value_of_information, timing) - never from stored example numbers."""
import inspect
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from mezan_ai import llm
from mezan_platform import analysis as A
from mezan_platform import labels as LB
from mezan_platform import report as R
from .. import components as CP
from .. import state as S
from .. import theme as TH

QUESTIONS = [
    ("invest", "What should I invest in?", ":material/savings:"),
    ("why", "Why is this the best investment?", ":material/workspace_premium:"),
    ("change", "What could change my decision?", ":material/alt_route:"),
    ("risk", "What is my biggest financial risk?", ":material/trending_down:"),
    ("info", "Is better information worth buying?", ":material/query_stats:"),
    ("timing", "Should I invest now or wait?", ":material/schedule:"),
    ("ai", "How does Mezan use AI?", ":material/hub:"),
    ("trust", "Can I trust this recommendation?", ":material/verified_user:"),
]
QTEXT = {k: q for k, q, _ in QUESTIONS}
WRAP = {"wrap": True} if "wrap" in inspect.signature(st.button).parameters else {}   # multi-line card labels (Streamlit ≥ 1.50)


def _pick(k):
    st.session_state["di_q"] = k


def answer(q, direct, number=None, action=None, method=None):
    st.markdown(f'<div class="mz-ans"><div class="q">{QTEXT[q]}</div><div class="a">{direct}</div>'
                + (f'<div class="n">{number}</div>' if number else "")
                + (f'<div class="act"><b>Recommended management action:</b> {action}</div>' if action else "")
                + (f'<div class="m">Method: {method}</div>' if method else "") + "</div>", unsafe_allow_html=True)


# ------------------------------------------------------------------ 1
def q_invest(res, ctx):
    rec, s = res["recommended"], res["settings"]
    if not rec:
        mb = res["min_budget"]
        answer("invest", f"Nothing yet: no portfolio meets both risk requirements within {TH.sar(s['budget'])}.",
               f"Minimum feasible budget ≈ {TH.sar(mb['budget'])} ({mb['portfolio']})" if mb else None,
               "Revisit the budget, the carbon target or the required confidence levels — Mezan does not relax them on its own.",
               "Primary rule D4 on the current run")
        return
    answer("invest", f"Fund {rec['portfolio']}: {LB.portfolio_names(rec['portfolio'])}.",
           f"Expected NPV {TH.sar(rec['e_npv'])} · capital {TH.sar(rec['quoted_capex'])} of {TH.sar(s['budget'])}",
           "Request firm supplier quotations for these projects and confirm the inputs closest to a switching point "
           "(see 'What could change my decision?').",
           f"Primary rule D4: highest expected NPV with carbon success ≥ {res['a_eff']:.4f} and budget success ≥ {res['b_eff']:.4f}, "
           f"tested separately on {s['n']:,} simulated futures")
    TH.cards(st, [("Carbon target met", TH.pct(rec["p_target"], 2), f"required {s['alpha']:.0%}", "ok"),
                  ("Capex within budget", TH.pct(rec["p_budget"], 2), f"required {s['beta']:.0%}", "ok"),
                  ("Expected reduction", f"{rec['e_t12']:,.0f} t/yr", f"target {res['target_t']:,.0f} t/yr", "neutral"),
                  ("NPV at base inputs", TH.sar(rec["npv_base_inputs"]), "deterministic", "neutral")])
    CP.chart(CP.probability_chart(res, top=5, height=360), "Modelled probabilities, not guarantees.", key="di_inv")


# ------------------------------------------------------------------ 2
def q_why(res, ctx):
    from .planner import why_it_wins
    rec = res["recommended"]
    lines = why_it_wins(res)
    if not rec:
        answer("why", "No portfolio is recommended, so there is no winner to explain.", method="Primary rule D4")
        return
    feas = [r for r in res["table"] if r["within_budget_quote"] and r["passes_carbon"] and r["passes_budget"] and r["portfolio"] != "(none)"]
    answer("why", f"{rec['portfolio']} is the most valuable of the {len(feas)} portfolios that fit the budget and pass both risk tests.",
           f"{len(res['table'])} portfolios compared on the same {res['settings']['n']:,} futures",
           "Use the comparison below in the investment memo: it shows what was given up and why.",
           "Expected NPV ranking within the feasible set (rule D4); explanation generated from engine outputs")
    for line in lines:
        st.markdown(f"- {line}")
    afford = sorted([r for r in res["table"] if r["within_budget_quote"] and r["portfolio"] != "(none)"], key=lambda r: -r["e_npv"])[:8]
    col = [TH.GOLD if r["portfolio"] == rec["portfolio"] else (TH.PURPLE if r["passes_carbon"] and r["passes_budget"] else TH.GREY)
           for r in afford]
    fig = go.Figure(go.Bar(y=[r["portfolio"] for r in afford][::-1], x=[r["e_npv"] / 1e6 for r in afford][::-1], orientation="h",
                           marker_color=col[::-1], text=[f"{TH.sar(r['e_npv'])} · {CP.status_of(res, r)}" for r in afford][::-1],
                           textposition="outside", hovertemplate="%{y}: SAR %{x:.2f} M<extra></extra>"))
    fig.update_xaxes(title="Expected NPV, SAR million", range=[0, max(r["e_npv"] for r in afford) / 1e6 * 1.6])
    CP.chart(TH.style_fig(fig, 330, "Most valuable affordable portfolios", legend=None),
             "Gold = recommended; purple = passes both tests; grey = fails a test despite a higher value.", key="di_why")
    ex = S.explanation(ctx)
    with st.expander("Full explanation and its status", expanded=False):
        st.markdown(TH.label("ai" if ex["source"] == "llm" else "rule", "AI-generated · language model" if ex["source"] == "llm"
                             else "Rule-based narrative") + f'<span class="mz-note">{ex["label"]}. Language model: {llm.describe()}.</span>',
                    unsafe_allow_html=True)
        if ex["source"] == "llm":
            st.markdown(ex["llm_text"])
        else:
            for sec in ex["sections"]:
                st.markdown(f"**{sec['title']}.** {sec['text']}  \n<span class='mz-note'>Source: {sec['evidence']}</span>",
                            unsafe_allow_html=True)
        if ex.get("rejected"):
            st.info(ex["rejected"])


# ------------------------------------------------------------------ 3
def _threshold_card(title, rule, base, thr, lo, hi, below, above, fmt, implication):
    span = (hi - lo) or 1
    pb, pt = (base - lo) / span * 100, (thr - lo) / span * 100
    ftxt, btxt = fmt.pair(thr, base) if hasattr(fmt, "pair") else (fmt(thr), fmt(base))

    def pos(x):   # keep labels inside the card near the edges
        return (f"left:{x:.1f}%;transform:none" if x < 12 else f"left:{x:.1f}%;transform:translateX(-100%)" if x > 88
                else f"left:{x:.1f}%")
    rel = abs(thr - base) / abs(base) if base else 0
    near = rel <= 0.05
    cur_port = above if base >= thr else below
    alt = below if base >= thr else above
    seg = (f'<div class="seg" style="left:0;width:{pt:.1f}%;background:{TH.LAV2}"></div>'
           f'<div class="seg" style="left:{pt:.1f}%;width:{100 - pt:.1f}%;background:#E8DDF8"></div>')
    st.markdown(
        f'<div class="mz-thr"><div class="h"><span>{title}</span><span>{TH.tone_chip(rule, "brand" if "D4" in rule else "neutral")} '
        f'{TH.tone_chip(f"{rel:.1%} from threshold", "warn" if near else "ok")}</span></div>'
        f'<div class="track">{seg}<div class="mk" style="left:{pt:.1f}%;background:{TH.BAD}"></div>'
        f'<div class="mk" style="left:{pb:.1f}%;background:{TH.INK}"></div>'
        f'<div class="ml" style="{pos(pb)};top:-22px;color:{TH.INK}">current {btxt}</div>'
        f'<div class="ml" style="{pos(pt)};top:16px;color:{TH.BAD}">switch at {ftxt}</div></div>'
        f'<div class="row"><span>Below: <b>{below}</b></span><span>Above: <b>{above}</b></span>'
        f'<span>Tested range {fmt(lo)} – {fmt(hi)}</span></div>'
        f'<div class="mz-note" style="margin-top:6px"><b>Implication:</b> {implication.format(cur=cur_port, alt=alt)}</div></div>',
        unsafe_allow_html=True)


def _fmt(k):
    f = lambda v: LB.fmt_value(k, v)  # noqa: E731
    f.pair = lambda a, b: LB.fmt_pair(k, a, b)
    return f


def q_change(res, ctx):
    sw, disc, s = S.switching(ctx), S.discount(ctx), res["settings"]
    items = []
    for x in sw:
        for c in x["changes"]:
            items.append((abs(c["threshold"] - x["base"]) / abs(x["base"]), x, c))
    items.sort(key=lambda t: t[0])
    d4c, d1c = disc.get("changes_D4", []), disc.get("changes_D1", [])
    if items:
        rel, x, c = items[0]
        ft, fb = LB.fmt_pair(x["parameter"], c["threshold"], x["base"])
        direct = (f"The deterministic choice (rule D1) is closest to switching on {LB.label(x['parameter']).lower()}: "
                  f"{ft} vs the current {fb}.")
    else:
        direct = "No tested input changes the deterministic choice within its range."
    robust = [LB.label(x["parameter"]) for x in sw if x["robust"]]
    answer("change", direct, (f"Primary rule D4 holds up to a {d4c[0]['threshold']:.2%} discount rate (current {s['discount_rate']:.1%})"
                              if d4c else "Primary rule D4 does not change within the tested discount rates"),
           "Verify the inputs nearest their threshold (sub-metering, quotations) before committing capital; inputs marked robust "
           "need no further work for this decision.",
           "Switch points: 41-point sweep refined by bisection (D1, deterministic); discount-rate sweep re-runs D4 and D1")
    st.caption("A D1 threshold shows where the deterministic optimum changes. It is a warning sign, not a confirmed change in the "
               "risk-constrained recommendation (D4); only the discount-rate sweep below re-runs D4 itself.")
    for rel, x, c in items[:4]:
        k = x["parameter"]
        _threshold_card(LB.label(k), "Rule D1 · deterministic", x["base"], c["threshold"], x["range"][0], x["range"][1], c["below"],
                        c["above"], _fmt(k),
                        "the deterministic choice is {cur} today; crossing the threshold would make it {alt}. "
                        + ("Close to the current value — confirm this input." if rel <= 0.05 else "Comfortable margin."))
    rates = [r["rate"] for r in disc["sequence"]]
    for lab, ch in (("Rule D4 · primary", d4c), ("Rule D1 · deterministic", d1c)):
        for c in ch[:1]:
            _threshold_card("Real discount rate", lab, s["discount_rate"], c["threshold"], min(rates), max(rates), c["below"], c["above"],
                            lambda v: f"{v:.2%}", "at the current rate the choice is {cur}; a higher cost of capital would favour {alt}.")
    if robust:
        st.markdown(TH.label("calculated", "Robust") + '<span class="mz-note">No switch anywhere in the tested range: '
                    + ", ".join(robust) + "</span>", unsafe_allow_html=True)
    with st.expander("Evidence: all switching thresholds and the discount-rate sweep"):
        rows = []
        for x in sw:
            for c in (x["changes"] or [None]):
                rows.append({"Input": LB.label(x["parameter"]), "Rule": "D1", "Current": LB.fmt_value(x["parameter"], x["base"]),
                             "Switch point": LB.fmt_value(x["parameter"], c["threshold"]) if c else "none in range",
                             "Distance": f"{abs(c['threshold'] - x['base']) / abs(x['base']):.1%}" if c else "—",
                             "Below → above": f"{c['below']} → {c['above']}" if c else f"{x['current']} throughout",
                             "Tested range": f"{LB.fmt_value(x['parameter'], x['range'][0])} – {LB.fmt_value(x['parameter'], x['range'][1])}"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        seq = pd.DataFrame(disc["sequence"])
        st.dataframe(seq.assign(rate=seq.rate.map(lambda r: f"{r:.1%}")).rename(columns={"rate": "Discount rate", "D4": "D4 (primary)",
                                                                                          "D1": "D1 (deterministic)"}),
                     hide_index=True, width="stretch")


# ------------------------------------------------------------------ 4
def q_risk(res, ctx):
    ids, tor = S.tornado(ctx)
    sw = {x["parameter"]: x for x in S.switching(ctx)}
    top = tor[0]
    st_ = res["stats_recommended"]
    robust = sw.get(top["parameter"], {}).get("robust")
    answer("risk", f"{LB.label(top['parameter'])} moves the value of {'+'.join(ids)} the most: about {TH.sar(top['swing'])} between "
                   f"its 5th and 95th percentile.",
           (f"Downside NPV (5th pct) {TH.sar(st_['p5_npv'])} · P(NPV < 0) {st_['p_loss']:.2%}" if st_ else None),
           ("It changes value but not the choice: no switch in its tested range. " if robust else
            "It can also change the choice — see 'What could change my decision?'. ")
           + "Consider hedging or contracting this exposure rather than delaying the investment.",
           "One-way sensitivity (tornado) at the current settings; downside statistics from the Monte Carlo run")
    fig = go.Figure()
    names = [LB.label(r["parameter"]) for r in tor][::-1]
    fig.add_bar(y=names, x=[(r["npv_low"] - r["base_npv"]) / 1e6 for r in tor][::-1], orientation="h", name="input at 5th percentile",
                marker_color=TH.GOLD, hovertemplate="%{y}<br>input low: %{x:+.2f} M<extra></extra>")
    fig.add_bar(y=names, x=[(r["npv_high"] - r["base_npv"]) / 1e6 for r in tor][::-1], orientation="h", name="input at 95th percentile",
                marker_color=TH.PURPLE, hovertemplate="%{y}<br>input high: %{x:+.2f} M<extra></extra>")
    fig.update_layout(barmode="overlay", bargap=0.35)
    fig.add_vline(x=0, line_color=TH.INK, line_width=1)
    fig.update_xaxes(title=f"Change in NPV of {'+'.join(ids)} at base inputs, SAR million")
    CP.chart(TH.style_fig(fig, 420, "Which assumptions move investment value most"),
             "Each bar moves one input from its 5th (gold) to its 95th (purple) percentile with all others fixed. Value changes are not "
             "choice changes: switching is tested separately.", key="di_tor")
    tbl = pd.DataFrame([{"Assumption": LB.label(r["parameter"]), "NPV swing (SAR)": round(r["swing"]),
                         "Changes the choice?": ("no (robust)" if sw.get(r["parameter"], {}).get("robust") else
                                                 "yes, within range" if r["parameter"] in sw else "not tested")} for r in tor])
    with st.expander("Evidence: sensitivity table"):
        st.dataframe(tbl, hide_index=True, width="stretch", column_config={"NPV swing (SAR)": st.column_config.NumberColumn(format="localized")})


# ------------------------------------------------------------------ 5
def q_info(res, ctx):
    v, s = S.voi(ctx), res["settings"]
    rk = v["ranking"]
    top = rk[0]
    worth = [r for r in rk if r["net_value_sar"] is not None and r["net_value_sar"] > 0]
    if worth:
        direct = (f"Yes, for {worth[0]['information']}: even its upper-bound value ({TH.sar(worth[0]['evppi_sar'])}) exceeds the "
                  f"assumed cost ({TH.sar(worth[0]['collection_cost_sar'])}).")
        act = "Commission that measurement before the final investment decision."
    else:
        direct = (f"Not for the measurements assessed: the most valuable, {top['information']}, is worth at most "
                  f"{TH.sar(top['evppi_sar'])} with perfect information"
                  + (f" — below its {TH.sar(top['collection_cost_sar'])} cost." if top["collection_cost_sar"] else "."))
        act = ("Proceed without these measurements. This applies only to the items assessed under the stated costs; it does not mean "
               "that no other data collection is useful (for example, firm supplier quotations).")
    answer("info", direct, f"EVPI (all uncertainty resolved) {TH.sar(v['evpi'])} — the most any information could be worth",
           act, f"Value of information under rule {v['rule']} (carbon chance constraint), on this run's {s['n']:,} futures. It does not "
                "exactly evaluate the primary rule D4.")
    TH.cards(st, [("EVPI", TH.sar(v["evpi"]), "maximum value of resolving all modelled uncertainty · upper bound", "neutral"),
                  ("EVPPI · highest", TH.sar(top["evppi_sar"]), f"perfectly resolving: {top['information']} · upper bound", "gold"),
                  ("EVSI · motor-system audit", TH.sar(v["evsi_audit"]["evsi"]),
                   f"realistic value of an imperfect audit (±{100 * v['evsi_audit']['error_sd']:.0f} pp) · cost "
                   f"{TH.sar(v['evsi_audit']['cost'])}", "neutral")])
    items = [r for r in rk if r["collection_cost_sar"]]
    fig = go.Figure()
    fig.add_bar(y=[r["information"] for r in items][::-1], x=[r["evppi_sar"] for r in items][::-1], orientation="h",
                name="Value with perfect information (EVPPI, upper bound)", marker_color=TH.PURPLE,
                text=[TH.sar(r["evppi_sar"]) for r in items][::-1], textposition="outside",
                hovertemplate="%{y}<br>EVPPI SAR %{x:,.0f}<extra></extra>")
    fig.add_bar(y=[r["information"] for r in items][::-1], x=[r["collection_cost_sar"] for r in items][::-1], orientation="h",
                name="Assumed collection cost", marker_color=TH.GOLD, text=[TH.sar(r["collection_cost_sar"]) for r in items][::-1],
                textposition="outside", hovertemplate="%{y}<br>cost SAR %{x:,.0f}<extra></extra>")
    fig.update_layout(barmode="group", bargap=0.3)
    fig.update_xaxes(title="SAR", range=[0, max([r["evppi_sar"] for r in items] + [r["collection_cost_sar"] for r in items]) * 1.25])
    CP.chart(TH.style_fig(fig, 340, "Information value against its cost"),
             "A measurement can only pay if its purple bar is longer than its gold bar — and real measurements are worth less than EVPPI.",
             key="di_voi")
    st.caption(f"EVSI is implemented for one measurement only (the motor-system audit). Estimator noise floor (an irrelevant input): "
               f"SAR {v['noise_floor']:,.0f}. Collection costs are hypothetical.")
    with st.expander("Evidence: value-of-information table"):
        st.dataframe(pd.DataFrame([{"Information": r["information"], "EVPPI, perfect information (SAR)": f"{r['evppi_sar']:,.0f}",
                                    "Assumed collection cost (SAR)": (f"{r['collection_cost_sar']:,.0f}" if r["collection_cost_sar"]
                                                                      else "not collectable / no cost available"),
                                    "Upper-bound net value (EVPPI − cost, SAR)": (f"{r['net_value_sar']:,.0f}" if r["net_value_sar"] is not None else "—"),
                                    "Could change the decision": "yes" if r["decision_changes"] else "no"} for r in rk]),
                     hide_index=True, width="stretch")


# ------------------------------------------------------------------ 6
def q_timing(res, ctx):
    st.markdown(TH.label("partial") + '<span class="mz-note">Partially implemented: one project (D, furnace waste-heat recovery) and '
                "one uncertainty (the natural-gas price). Not available for the other projects.</span>", unsafe_allow_html=True)
    c = st.columns(2)
    pr = c[0].slider("Probability of a gas-price reform within one year", 0, 100, int(round(100 * float(A.BASE["tree_p_reform"]))), 5,
                     key="preform_pct", format="%d%%")
    gr = c[1].slider("Gas price after reform (USD per MMBtu)", 2.0, 9.0, float(A.BASE["tree_g_reform"]), 0.025, key="greform",
                     format="%.2f")
    t = A.timing(res, pr / 100, gr)
    tr = t["tree"]
    now, wait = tr["npv_invest_now"], tr["value_wait_one_year"]
    best = "Invest now" if now > wait else "Wait one year"
    answer("timing", f"{best} for waste-heat recovery under these assumptions ({tr['decision']}).",
           f"Difference in expected value {TH.sar(abs(now - wait))} in favour of {'investing now' if now > wait else 'waiting'}",
           "Revisit when the gas-price decision is announced." if now <= wait else "Proceed; waiting does not add value here.",
           f"One-year decision tree for project D with today's gas price {res['settings']['gas_price_usd']:.2f} USD/MMBtu; "
           "GBM real-options trigger as a cross-check")
    k = st.columns(2, gap="medium")
    k[0].markdown(TH.cards_html([("Invest now", TH.sar(now), "expected NPV today", "ok" if now >= wait else "neutral")]), unsafe_allow_html=True)
    k[1].markdown(TH.cards_html([("Wait one year", TH.sar(wait), f"expected value after learning the price ({pr}% reform chance, "
                                                              f"{gr:.2f} USD/MMBtu if reformed)", "ok" if wait > now else "neutral")]),
                  unsafe_allow_html=True)
    st.caption(f"Static break-even gas price {tr['static_breakeven_usd']:.2f} USD/MMBtu · GBM investment trigger "
               f"{t['gbm']['trigger_usd']:.2f} USD/MMBtu (option multiplier {t['gbm']['multiplier']:.2f}). {t['scope']}")


# ------------------------------------------------------------------ 7
def q_ai(res, ctx, pc):
    ss = st.session_state
    an = pc.get("anomalies") or {}
    cl = pc.get("classification")
    ml_run = bool(ss["ml_eval"].get(pc.get("src")))
    cfg = llm.config()
    answer("ai", "Machine learning supports data intelligence. Analytical engines calculate the numbers. Decision science selects and "
                 "evaluates investments. AI-assisted communication explains the evidence where configured.",
           f"Language model: {llm.describe()} · every number shown comes from the calculation engine",
           "Judge the recommendation on the engine evidence; treat ML outputs as flags and proposals that a reviewer accepts or rejects.",
           "Capability register with evaluation evidence: Reports & Evidence")
    lay = [
        ("Layer 1", "AI and machine learning", TH.GOLD_DK,
         [f"Record classification — rules + TF-IDF/logistic regression: {'executed on ' + pc['name'] if cl is not None else 'available (current data already labelled)'}",
          f"Isolation Forest anomaly detection: {'executed, ' + str(an.get('n_flagged', 0)) + ' month(s) flagged' if an.get('applied') else 'not applied — ' + (an.get('reason', 'no data')[:70])}",
          f"Ridge regression and random forest estimate challengers: {'back-tested on this dataset' if ml_run else 'available on request (Plant Data)'}",
          f"Language-model explanation: {'configured (' + cfg['provider'] + ')' if cfg['enabled'] else 'not configured — rule-based narrative used'}"],
         "Flags and proposals; a reviewer decides."),
        ("Layer 2", "Auditable analytical engines", TH.PURPLE,
         ["Data-quality rules and statistical estimation (refusal rules, reviewer approval)",
          f"Scope 1 and 2 carbon accounting: {res['totals']['Scope 1+2']:,.0f} tCO₂e/yr",
          f"Uncertainty propagation: ±{res['uncertainty_totals']['Scope 1+2'][1]:.1f}% (model-based)",
          "Financial assessment: NPV, IRR, payback, abatement cost"], "Deterministic, documented, tested."),
        ("Layer 3", "Decision science", TH.INK,
         [f"Monte Carlo simulation: {res['settings']['n']:,} futures", f"Portfolio optimisation: {len(res['table'])} portfolios",
          "Separate carbon and budget risk tests (D4)", "Sensitivity and switching analysis", "Value of information (EVPI, EVPPI, one EVSI)",
          "Investment timing (partial: one project)"], "Selects and stress-tests the investment."),
    ]
    html = "".join(f'<div class="mz-layer" style="border-top:4px solid {col}"><div class="k" style="color:{col}">{k}</div>'
                   f'<div class="t">{t}</div><ul>{"".join(f"<li>{i}</li>" for i in items)}</ul><div class="r">{r}</div></div>'
                   for k, t, col, items, r in lay)
    st.markdown(f'<div class="mz-arch">{html}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="mz-flow">' + "".join(
        f'<div class="st"><div class="dot" style="background:{TH.LAV};color:{TH.INK};border:2px solid {TH.PURPLE}">{i}</div>'
        f'<div class="n">{n}</div></div>' for i, n in enumerate(["Raw operational records", "ML flags & proposals", "Reviewer approval",
                                                                 "Emissions baseline", "Simulated futures", "Risk-tested portfolio",
                                                                 "Explained recommendation"], 1)) + "</div>", unsafe_allow_html=True)
    rows = [("Machine-learning models available and executed", "ml",
             f"Classifier {'ran' if cl is not None else 'idle'}; Isolation Forest {'ran' if an.get('applied') else 'not applied'}; "
             f"ML challengers {'ran' if ml_run else 'idle'}"),
            ("Rule-based analytical explanations", "rule", "Always on: narrative and Mezan Intelligence findings are selected and worded by rules"),
            ("Optional language-model assistance", "optional", "Rewrites the verified fact sheet only; any number not in the engine outputs "
                                                               "rejects the whole text"),
            ("Current language-model configuration", "ai" if cfg["enabled"] else "rule",
             f"{llm.describe()} (MEZAN_LLM_PROVIDER / MEZAN_LLM_API_KEY / MEZAN_LLM_MODEL); no paid service is required")]
    for t, k, d in rows:
        st.markdown(TH.label(k, t) + f'<span class="mz-note">{d}</span>', unsafe_allow_html=True)


# ------------------------------------------------------------------ 8
def q_trust(res, ctx, pc):
    rec, s = res["recommended"], res["settings"]
    saved = json.loads((TH.ROOT / "outputs" / "results.json").read_text())
    d4 = {d["id"]: d for d in saved["decision_scenarios"]}["D4"]
    is_saved = (s == {**s, **A.asdict(A.DEFAULTS)}) and not ctx.get("activity_used")
    if rec:
        m = min(rec["margin_target_se"], rec["margin_budget_se"])
        tight = "carbon" if rec["margin_target_se"] <= rec["margin_budget_se"] else "budget"
        direct = ("Within its stated limits, yes: the tighter of the two tests (" + tight + ") is cleared by "
                  + R.fmt_margin(m, rec["p_target"] if tight == "carbon" else rec["p_budget"]).replace("SE", "Monte Carlo standard errors")
                  + (" — comfortably." if m >= 2 else " — narrowly; rerun with more futures or another seed."))
    else:
        direct = "There is no recommendation to trust: no portfolio passes both tests."
    answer("trust", direct, (f"Independent 200,000-future validation of the saved run: carbon {d4['p_target_val']:.4%}, budget "
                             f"{d4['p_budget_val']:.4%}" if is_saved else "Independent validation exists for the default settings only"),
           "Treat the result as decision support: confirm the near-threshold inputs, obtain quotations and replace synthetic data with "
           "measured plant records before committing capital.",
           "Sampling-error margins, out-of-sample validation (run_all.py), regression tests, documented limitations")
    TH.cards(st, [("Data basis", "Approved operational" if ctx.get("activity_used") else "Reference (synthetic)",
                   pc.get("status", "—") if pc else "—", "ok" if ctx.get("activity_used") else "warn"),
                  ("Carbon test margin", R.fmt_margin(rec["margin_target_se"], rec["p_target"]) if rec else "—", "standard errors above the tightened level", "neutral"),
                  ("Budget test margin", R.fmt_margin(rec["margin_budget_se"], rec["p_budget"]) if rec else "—", "standard errors above the tightened level", "neutral"),
                  ("Model status", "Research prototype", "not externally validated", "warn")])
    st.markdown("**What supports it:** calculation engine checked by an independent re-implementation (phase A6), Python/Excel/Word "
                "agreement checks, fault-injection tests and out-of-sample validation of the reported choices.  \n"
                "**What limits it:**")
    for x in R.LIMITATIONS:
        st.markdown(f"- {x}")


def render(fac, pc, ctx):
    res = S.result(ctx)
    TH.page_header(st, "Why is this the best decision, what could change it, and should I collect more information before investing?",
                   "Mezan Decision Intelligence",
                   "Choose a question. Every answer is generated from the current analysis run and names the method behind it.")
    CP.basis_note(ctx)
    with st.spinner("Sensitivity, switching and information value…"):
        S.switching(ctx); S.discount(ctx); S.voi(ctx); S.tornado(ctx)
    cur = st.session_state.get("di_q", "invest")
    for row in (QUESTIONS[:4], QUESTIONS[4:]):
        cols = st.columns(4, gap="small")
        for c, (k, q, icon) in zip(cols, row):
            c.button(q, key=f"dq_{k}", icon=icon, type="primary" if cur == k else "secondary", on_click=_pick, args=(k,),
                     use_container_width=True, **WRAP)
    fn = {"invest": q_invest, "why": q_why, "change": q_change, "risk": q_risk, "info": q_info, "timing": q_timing}
    if cur in fn:
        fn[cur](res, ctx)
    elif cur == "ai":
        q_ai(res, ctx, pc)
    else:
        q_trust(res, ctx, pc)
    CP.next_action("Export the executive decision report with the evidence behind this answer.", "Reports & Evidence")
