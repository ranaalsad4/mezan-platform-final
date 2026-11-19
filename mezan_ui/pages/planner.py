"""4 · Investment Planner - which decarbonisation projects should I fund with my available capital?
Recommended strategy, project catalogue, portfolio comparison, opportunity map, investment uncertainty and the decision
methodology (D1-D4, D4 primary). All values from the current analysis run."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from carbon_iq import decisions as D
from carbon_iq.assumptions import GAS_SCENARIOS, P, PV_CAPEX_SCENARIOS, TARIFF_SCENARIOS
from mezan_platform import analysis as A
from mezan_platform import labels as LB
from .. import components as CP
from .. import state as S
from .. import theme as TH

PROJECT_KEYS = {"A": ["pv_kwp", "pv_yield", "pv_capex_kw", "pv_om_frac", "pv_life", "pv_degradation"],
                "B": ["b_capex", "b_saving_frac", "b_comp_frac", "b_life"], "C": ["c_capex", "c_saving_frac", "c_om", "c_life"],
                "D": ["d_capex", "d_saving_frac", "d_om", "d_life"], "E": ["e_capex", "e_kwh_per_l", "e_maint_saving", "e_life"],
                "F": ["f_steel_t", "f_premium", "f_onboard", "f_life"]}


@st.cache_data(show_spinner=False)
def _scen_tables(n, budget, alpha, beta):
    return (D.tariff_scenarios(n, 20261024, budget, alpha, beta), D.gas_scenarios(n, 20261024, budget, alpha, beta),
            D.pv_capex_scenarios(n, 20261024, budget, alpha, beta))


def recommendation_panel(res):
    s, rec = res["settings"], res["recommended"]
    if not rec:
        mb = res["min_budget"]
        st.error(f"No portfolio passes both tests within {TH.sar(s['budget'])}. No recommendation is forced and the budget is not raised. "
                 + (f"The smallest budget that would make the rule feasible is about {TH.sar(mb['budget'])} ({mb['portfolio']})." if mb
                    else "No portfolio meets the carbon requirement at any budget."))
        return
    st_ = res["stats_recommended"]
    pills = "".join(f'<span class="pill"><b>{i}</b>{LB.SHORT[i]}</span>' for i in rec["portfolio"].split("+"))
    st.markdown(f'<div class="mz-hero"><div class="k">Recommended investment strategy · primary rule D4</div>'
                f'<div class="p">Fund {rec["portfolio"]}</div><div class="pills">{pills}</div>'
                f'<div class="foot" style="margin-top:0">Selected from {len(res["table"])} portfolios evaluated on the same '
                f'{s["n"]:,} simulated futures (seed {s["seed"]}).</div></div>', unsafe_allow_html=True)
    c = st.columns(2, gap="medium")
    with c[0]:
        st.markdown('<div class="mz-grp">Financial value</div>', unsafe_allow_html=True)
        TH.cards(st, [("Expected NPV", TH.sar(rec["e_npv"]), f"average over {s['n']:,} futures", "ok" if rec["e_npv"] > 0 else "bad"),
                      ("NPV at base inputs", TH.sar(rec["npv_base_inputs"]), "deterministic, most-likely inputs", "neutral"),
                      ("Quoted capital", TH.sar(rec["quoted_capex"]), f"available budget {TH.sar(s['budget'])}", "neutral")])
    with c[1]:
        st.markdown('<div class="mz-grp">Risk</div>', unsafe_allow_html=True)
        TH.cards(st, [("Carbon success", TH.pct(rec["p_target"], 2), f"modelled · required {s['alpha']:.0%}",
                       "ok" if rec["passes_carbon"] else "bad"),
                      ("Budget success", TH.pct(rec["p_budget"], 2), f"modelled · required {s['beta']:.0%}",
                       "ok" if rec["passes_budget"] else "bad"),
                      ("Downside NPV (5th pct)", TH.sar(st_["p5_npv"]), f"P(NPV < 0) = {st_['p_loss']:.2%}",
                       "warn" if st_["p_loss"] > 0.05 else "neutral")])
    st.caption(f"Expected NPV averages the {s['n']:,} simulated futures; NPV at base inputs uses the most-likely value of every input. "
               "They differ because some ranges are skewed (for example the electricity tariff is more likely to rise than fall). "
               "Carbon and budget success are two separate modelled probabilities, not guarantees and not one joint probability.")


def catalogue(res):
    pt = A.project_table(res)
    rec_ids = set(res["recommended"]["portfolio"].split("+")) if res["recommended"] else set()
    cols = st.columns(3, gap="medium")
    for j, r in enumerate(pt):
        inrec = r["id"] in rec_ids
        badge = TH.tone_chip("In recommended portfolio", "gold") if inrec else TH.tone_chip("Not selected", "neutral")
        rows = [("Investment cost", TH.sar(r["capex"])), ("Net saving per year", TH.sar(r["annual_cf"])),
                ("Scope 1+2 reduction", f"{r['scope12_t']:,.0f} t/yr"), ("NPV (base inputs)", TH.sar(r["npv"])),
                ("IRR", f"{r['irr']:.1%}" if r["irr"] is not None else "n/a"),
                ("Payback", f"{r['payback']:.1f} yr" if r["payback"] else "never"), ("Life", f"{r['life']} yr"),
                ("Abatement cost (MAC)", f"SAR {r['mac']:,.0f}/t")]
        if r["scope3_t"]:
            rows.insert(3, ("Scope 3 reduction", f"{r['scope3_t']:,.0f} t/yr"))
        tbl = "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in rows)
        with cols[j % 3]:
            st.markdown(f'<div class="mz-proj {"inrec" if inrec else ""}"><div class="h"><div class="nm">{r["id"]} · {r["name"]}</div></div>'
                        f'<div style="margin-top:6px">{badge}</div><table>{tbl}</table></div>', unsafe_allow_html=True)
            with st.expander("Assumptions"):
                st.markdown("\n".join(f"- {LB.label(k)}: **{P[k].value:g} {P[k].unit}** · {P[k].evidence}" for k in PROJECT_KEYS[r["id"]] if k in P))
    st.caption("Costs other than solar PV are hypothetical placeholders; the solar cost is one public benchmark, not a quotation. "
               "MAC = cost per tonne abated (negative = saves money). Only metrics the engine calculates are shown.")
    pts = sorted([r for r in pt if r["scope12_t"] > 0], key=lambda r: r["mac"])
    x0, xs, ws = 0.0, [], []
    for r in pts:
        xs.append(x0 + r["scope12_t"] / 2); ws.append(r["scope12_t"]); x0 += r["scope12_t"]
    fig = go.Figure(go.Bar(x=xs, y=[r["mac"] for r in pts], width=ws, text=[f"{r['id']} {LB.SHORT[r['id']]}" for r in pts],
                           textposition="outside", marker_color=[TH.OK if r["mac"] < 0 else TH.GOLD for r in pts],
                           marker_line=dict(color="white", width=1.5),
                           hovertemplate="%{text}<br>MAC SAR %{y:,.0f}/t<extra></extra>"))
    fig.add_vline(x=res["target_t"], line_dash="dash", line_color=TH.BAD, annotation_text=f"target {res['target_t']:,.0f} t",
                  annotation_position="top", annotation_font=dict(size=11, color=TH.BAD))
    lo, hi = min(r["mac"] for r in pts), max(r["mac"] for r in pts)
    fig.update_yaxes(title="SAR per tCO₂e", range=[min(lo * 1.25, -50), max(hi * 1.35, 50)])
    fig.update_xaxes(title="Cumulative Scope 1+2 reduction, tCO₂e per year")
    CP.chart(TH.style_fig(fig, 360, "Marginal abatement cost curve", legend=None),
             "Bar width = tonnes cut per year; height = cost per tonne. Green bars save money while cutting emissions.", key="pl_mac")


def why_it_wins(res):
    rec = res["recommended"]
    if not rec:
        return []
    afford = sorted([r for r in res["table"] if r["within_budget_quote"] and r["portfolio"] != "(none)"], key=lambda r: -r["e_npv"])
    out = []
    higher = [r for r in afford if r["e_npv"] > rec["e_npv"] + 1e-6]
    for r in higher[:3]:
        why = []
        if not r["passes_carbon"]:
            why.append(f"meets the carbon target in only {r['p_target']:.1%} of futures")
        if not r["passes_budget"]:
            why.append(f"stays within budget in only {r['p_budget']:.1%} of futures")
        out.append(f"**{r['portfolio']}** has a higher expected NPV ({TH.sar(r['e_npv'])}) but " + " and ".join(why) + ".")
    over = [r for r in res["table"] if not r["within_budget_quote"] and r["e_npv"] > rec["e_npv"]]
    if over:
        out.append(f"{len(over)} portfolio(s) with higher expected NPV cost more than the {TH.sar(res['settings']['budget'])} budget as quoted.")
    feas = [r for r in afford if r["passes_carbon"] and r["passes_budget"] and r["portfolio"] != rec["portfolio"]]
    if feas:
        r = feas[0]
        out.append(f"The best other portfolio that passes both tests, **{r['portfolio']}**, is worth {TH.sar(rec['e_npv'] - r['e_npv'])} "
                   "less in expected NPV.")
    return out


def opportunity_map(res):
    rec = res["recommended"]
    rows = [r for r in res["table"] if r["portfolio"] != "(none)"]
    groups = [("Recommended", lambda r: rec and r["portfolio"] == rec["portfolio"], "star", TH.GOLD, 22),
              ("Passes both requirements", lambda r: r["within_budget_quote"] and r["passes_carbon"] and r["passes_budget"]
               and not (rec and r["portfolio"] == rec["portfolio"]), "circle", TH.PURPLE, 11),
              ("Fails one or more requirements", lambda r: not (r["within_budget_quote"] and r["passes_carbon"] and r["passes_budget"]),
               "x-thin-open", TH.GREY, 9)]
    fig = go.Figure()
    for name, pred, sym, col, size in groups:
        g = [r for r in rows if pred(r)]
        if not g:
            continue
        fig.add_scatter(x=[r["quoted_capex"] / 1e6 for r in g], y=[r["e_npv"] / 1e6 for r in g], mode="markers", name=name,
                        marker=dict(symbol=sym, size=size, color=col, line=dict(width=1.5 if sym != "star" else 1, color=col if sym == "x-thin-open" else TH.INK)),
                        customdata=[[r["portfolio"], r["p_target"], r["p_budget"], CP.status_of(res, r)] for r in g],
                        hovertemplate="<b>%{customdata[0]}</b><br>Expected NPV SAR %{y:.2f} M<br>Quoted capex SAR %{x:.2f} M<br>"
                                      "Carbon success %{customdata[1]:.1%}<br>Budget success %{customdata[2]:.1%}<br>%{customdata[3]}<extra></extra>")
    fig.add_vline(x=res["settings"]["budget"] / 1e6, line_dash="dash", line_color=TH.BAD, annotation_text="budget",
                  annotation_position="top right", annotation_font=dict(size=11, color=TH.BAD))
    if rec:
        fig.add_annotation(x=rec["quoted_capex"] / 1e6, y=rec["e_npv"] / 1e6, text=f"<b>{rec['portfolio']}</b>", showarrow=True,
                           arrowhead=0, ax=-48, ay=-34, font=dict(size=12, color=TH.INK), bgcolor="rgba(255,255,255,0.9)")
    fig.update_xaxes(title="Quoted capital cost, SAR million")
    fig.update_yaxes(title="Expected NPV, SAR million")
    return TH.style_fig(fig, 430, "Portfolio opportunity map")


def render(fac, pc, ctx):
    res = S.result(ctx)
    s, rec = res["settings"], res["recommended"]
    TH.page_header(st, "Which decarbonisation projects should I fund with my available capital?", "Investment Planner",
                   "Compare investment alternatives across thousands of possible futures and identify the most valuable portfolio that "
                   "satisfies your carbon and budget requirements.")
    CP.basis_note(ctx)
    st.markdown(TH.cards_html([("Alternatives evaluated", f"{len(res['table'])}", "every combination of six projects", "neutral"),
                               ("Simulated futures", f"{s['n']:,}", f"same sample for every portfolio · seed {s['seed']}", "neutral"),
                               ("Capital budget", TH.sar(s["budget"]), "limit for the quoted cost and the budget test", "neutral"),
                               ("Carbon target", f"{res['target_t']:,.0f} t/yr", f"{s['target_share']:.0%} of Scope 1+2", "gold")]),
                unsafe_allow_html=True)
    recommendation_panel(res)

    TH.section(st, "Project catalogue", "The six candidate projects and what each contributes on its own (base inputs).")
    catalogue(res)

    TH.section(st, "Portfolio comparison", "The recommended portfolio against the strongest alternatives.")
    for line in why_it_wins(res):
        st.markdown(f"- {line}")
    df = CP.alternatives_table(res, top=6)
    st.dataframe(CP.highlight_status(df), hide_index=True, width="stretch", column_config=CP.portfolio_column_config())
    with st.expander(f"All {len(res['table'])} evaluated portfolios"):
        full = CP.alternatives_table(res, top=len(res["table"]))
        flt = st.multiselect("Show status", sorted(full.Status.unique()), key="pl_flt", placeholder="All statuses")
        if flt:
            full = full[full.Status.isin(flt)]
        st.dataframe(CP.highlight_status(full), hide_index=True, width="stretch", height=420, column_config=CP.portfolio_column_config())

    TH.section(st, "Portfolio opportunity map", "Value against capital for every portfolio, with its status under the primary rule.")
    c = st.columns([1.35, 1], gap="large")
    with c[0]:
        CP.chart(opportunity_map(res), "Hover over a point for both probabilities. Gold star = recommended; purple = passes both "
                                       "requirements; grey cross = fails at least one (or is over budget as quoted).", key="pl_map")
    with c[1]:
        CP.chart(CP.probability_chart(res, top=5, height=430),
                 "The most valuable affordable portfolios, with carbon and budget success tested separately.", key="pl_prob")

    TH.section(st, "Investment uncertainty", "How the value, cost and carbon reduction of the recommendation vary across simulated futures.")
    if rec:
        sc, rk, st_ = res["sc"], res["choice"]["D4"], res["stats_recommended"]
        TH.cards(st, [("Downside NPV (5th pct)", TH.sar(st_["p5_npv"]), "1 in 20 futures is worse", "neutral"),
                      ("Average of worst 5%", TH.sar(st_["cvar5_npv"]), "CVaR(5%)", "neutral"),
                      ("Probability of negative NPV", f"{st_['p_loss']:.2%}", "share of futures losing value", "warn" if st_["p_loss"] > 0.05 else "ok"),
                      ("90th-percentile capex", TH.sar(st_["p90_capex"]), f"quoted {TH.sar(rec['quoted_capex'])}", "neutral")])
        c = st.columns(3, gap="medium")
        with c[0]:
            fig = go.Figure(go.Histogram(x=sc.PNPV[rk] / 1e6, nbinsx=50, marker_color=TH.PURPLE, opacity=0.85,
                                         hovertemplate="NPV %{x} M<br>%{y} futures<extra></extra>"))
            fig.add_vline(x=st_["p5_npv"] / 1e6, line_dash="dot", line_color=TH.WARN, annotation_text="5th pct",
                          annotation_font=dict(size=11, color=TH.WARN))
            fig.add_vline(x=0, line_color=TH.BAD, line_width=1.5)
            fig.update_xaxes(title="NPV, SAR million"); fig.update_yaxes(title="futures")
            CP.chart(TH.style_fig(fig, 300, "NPV distribution", legend=None), "Most futures create value; the red line marks zero NPV.", key="pl_npv")
        with c[1]:
            fig = go.Figure(go.Histogram(x=sc.PCAP[rk] / 1e6, nbinsx=50, marker_color=TH.GOLD, opacity=0.9,
                                         hovertemplate="capex %{x} M<br>%{y} futures<extra></extra>"))
            fig.add_vline(x=s["budget"] / 1e6, line_dash="dash", line_color=TH.BAD, annotation_text="budget",
                          annotation_font=dict(size=11, color=TH.BAD))
            fig.add_vline(x=rec["quoted_capex"] / 1e6, line_dash="dot", line_color=TH.INK, annotation_text="quote",
                          annotation_position="top left", annotation_font=dict(size=11, color=TH.INK))
            fig.update_xaxes(title="Actual capital cost, SAR million"); fig.update_yaxes(title="futures")
            CP.chart(TH.style_fig(fig, 300, "Capital cost uncertainty", legend=None),
                     "Quotes can overrun: futures right of the red line break the budget.", key="pl_cap")
        with c[2]:
            fig = go.Figure(go.Histogram(x=sc.PT12[rk], nbinsx=50, marker_color=TH.PURPLE_LT, opacity=0.95,
                                         hovertemplate="%{x} t/yr<br>%{y} futures<extra></extra>"))
            fig.add_vline(x=res["target_t"], line_dash="dash", line_color=TH.BAD, annotation_text="target",
                          annotation_font=dict(size=11, color=TH.BAD))
            fig.update_xaxes(title="Scope 1+2 reduction, tCO₂e/yr"); fig.update_yaxes(title="futures")
            CP.chart(TH.style_fig(fig, 300, "Carbon reduction uncertainty", legend=None),
                     "Futures right of the target line meet it (target shown at base inputs).", key="pl_t12")
        st.caption("Quoted capital cost is checked against the budget (deterministic feasibility); budget success uses the uncertain "
                   "actual cost (probabilistic feasibility).")

    with st.expander("Decision methodology: rules D1–D4 and sampling-error adjustment", icon=":material/rule:"):
        st.markdown(f"**Primary rule D4** — select the highest expected-value portfolio that satisfies the quoted capital budget and the "
                    f"separate carbon and budget probability requirements. Carbon success must be at least **{res['a_eff']:.4f}** and budget "
                    f"success at least **{res['b_eff']:.4f}**: the required {s['alpha']:.0%} and {s['beta']:.0%} tightened for sampling "
                    f"error on {s['n']:,} futures (sample-average approximation). The two tests are applied separately, not as one joint "
                    "probability. D1–D3 are shown for comparison.")
        st.dataframe(CP.decision_rules_table(res), hide_index=True, width="stretch")
        st.caption("run_all.py also validates the reported choices on an independent 200,000-scenario sample (Reports & Evidence).")
        if st.toggle("Recompute the four rules under published price and cost scenarios (≤ 5,000 futures)", key="scen_tables"):
            with st.spinner("Running scenario tables…"):
                tt, gs, ps = _scen_tables(min(s["n"], 5000), s["budget"], s["alpha"], s["beta"])
            for title, rows, col, unit, ev in (("Industrial electricity tariff", tt, "tariff", "SAR/kWh", TARIFF_SCENARIOS),
                                               ("Industrial natural-gas price", gs, "gas_price_usd", "USD/MMBtu", GAS_SCENARIOS),
                                               ("Rooftop PV cost", ps, "pv_capex_kw", "SAR/kWp", PV_CAPEX_SCENARIOS)):
                evd = {e["id"]: e for e in ev}
                st.markdown(f"**{title}**")
                st.dataframe(pd.DataFrame([{"Scenario": f"{r['id']} {r['label']}", unit: r[col], "D1": r["deterministic"],
                                            "D2": r["best_expected"], "D3": r["chance_constrained"], "D4 (primary)": r["joint"],
                                            "Evidence": evd[r["id"]].get("status", evd[r["id"]].get("url", ""))} for r in rows]),
                             hide_index=True, width="stretch")
    CP.next_action("Find out why this portfolio wins, what could change the decision and whether better information is worth buying.",
                   "Decision Intelligence")
