"""1 · Executive Overview - what is the recommended investment decision? (synthetic plant). All values from the current run."""
import plotly.graph_objects as go
import streamlit as st

from mezan_platform import labels as LB
from .. import components as CP
from .. import state as S
from .. import theme as TH


def hero(res):
    s, rec = res["settings"], res["recommended"]
    n = f"{s['n']:,}"
    if not rec:
        mb = res["min_budget"]
        st.markdown(
            f'<div class="mz-hero" style="border-left-color:{TH.BAD}"><div class="k">Recommended investment strategy · primary rule D4</div>'
            f'<div class="p">No portfolio passes both risk requirements within {TH.sar(s["budget"])}</div>'
            f'<div class="foot">Mezan does not force a recommendation or raise the budget.'
            + (f" The smallest budget that would make the primary rule feasible is about {TH.sar(mb['budget'])} ({mb['portfolio']})."
               if mb else " No portfolio meets the carbon requirement at any budget.") + "</div></div>", unsafe_allow_html=True)
        return
    pills = "".join(f'<span class="pill"><b>{i}</b>{LB.SHORT[i]}</span>' for i in rec["portfolio"].split("+"))
    cut = rec["e_t12"]
    grid = [("Expected NPV", TH.sar(rec["e_npv"]), f"mean of {n} futures · base inputs {TH.sar(rec['npv_base_inputs'])}"),
            ("Capital required", TH.sar(rec["quoted_capex"]), f"quoted · budget {TH.sar(s['budget'])}"),
            ("Carbon target met", TH.pct(rec["p_target"], 2), f"of futures · required {s['alpha']:.0%}"),
            ("Capex within budget", TH.pct(rec["p_budget"], 2), f"of futures · required {s['beta']:.0%}"),
            ("Expected reduction", f"{cut:,.0f} t/yr", f"target {res['target_t']:,.0f} tCO₂e/yr")]
    g = "".join(f'<div><div class="a">{a}</div><div class="b">{b}</div><div class="c">{c}</div></div>' for a, b, c in grid)
    st.markdown(f'<div class="mz-hero"><div class="k">Recommended investment strategy · primary rule D4</div>'
                f'<div class="p">Fund {rec["portfolio"]}: {LB.portfolio_names(rec["portfolio"])}</div><div class="pills">{pills}</div>'
                f'<div class="grid">{g}</div><div class="foot">Highest expected NPV among portfolios that fit the budget and pass the '
                f"carbon and budget requirements separately. Probabilities are modelled across {n} simulated futures — not "
                "guarantees.</div></div>", unsafe_allow_html=True)


def render(fac, pc, ctx):
    res = S.result(ctx)
    s, tot, rec = res["settings"], res["totals"], res["recommended"]
    u12 = res["uncertainty_totals"]["Scope 1+2"][1]
    TH.page_header(st, "What is the recommended investment decision?", "Executive Overview",
                   f"{fac['name']} · reporting year {fac['year']}. Mezan turns incomplete plant records into a reviewed carbon "
                   "baseline and tests every combination of decarbonisation projects across thousands of possible futures.")
    CP.basis_note(ctx)
    hero(res)

    led = pc.get("ledger")
    if pc.get("base") is not None:
        measured = pc["base"].cells.status.isin(["measured", "converted"]).mean()
        pending = int((led.table.decision == "pending").sum())
        ready = (f"{measured:.0%} measured", f"{pc['status']}" + (f" · {pending} pending review" if pending else ""),
                 TH.status_tone(pc["status"]))
    else:
        ready = ("—", pc.get("status", "no data"), "warn")
    TH.cards(st, [("Scope 1 + 2 baseline", f"{tot['Scope 1+2']:,.0f} t", f"tCO₂e/yr · ±{u12:.1f}% model-based range", "neutral"),
                  ("Scope 1 · direct", f"{tot['Scope 1']:,.0f} t", "fuel combustion, tCO₂e/yr", "neutral"),
                  ("Scope 2 · electricity", f"{tot['Scope 2']:,.0f} t", "location-based, tCO₂e/yr", "neutral"),
                  ("Carbon target", f"{res['target_t']:,.0f} t/yr", f"{s['target_share']:.0%} of Scope 1+2", "gold"),
                  ("Data readiness", ready[0], ready[1], ready[2])])

    st.markdown(TH.cards_html([
        ("Data intelligence", "Rules + ML", "Rule checks, statistical estimates and Isolation Forest flags; a reviewer approves "
                                            "every change", "neutral"),
        ("Carbon accounting", "GHG Protocol", "Scope 1 and 2 with model-based uncertainty; Scope 3 kept outside the target", "neutral"),
        ("Decision science", f"{len(res['table'])} × {s['n']:,}", "every project combination tested across simulated futures with two "
                                                                     "separate risk tests", "neutral"),
        ("Decision intelligence", "Why · what if", "sensitivity, switching points, value of information and timing", "neutral")]),
        unsafe_allow_html=True)
    st.caption("Unlike a carbon calculator, Mezan does not stop at a footprint: it reviews the data behind it, prices the "
               "uncertainty and selects the portfolio that is worth most while meeting the carbon and budget requirements.")

    CP.workflow(pc, ctx, res)
    left, right = st.columns([1.25, 1], gap="large")
    with left:
        CP.intelligence(S.all_insights(pc, ctx), limit_per_group=2)
    with right:
        CP.chart(CP.probability_chart(res, top=5, height=380),
                 "Each portfolio is tested twice: carbon success and budget success must each clear the required level (★ = recommended).",
                 key="ov_prob")
        rows = sorted([r for r in res["baseline_rows"] if r["scope"] in ("Scope 1", "Scope 2")], key=lambda r: r["emissions_t"])
        fig = go.Figure(go.Bar(y=[r["source"] for r in rows], x=[r["emissions_t"] for r in rows], orientation="h",
                               marker_color=[TH.PURPLE if r["scope"] == "Scope 2" else TH.GOLD for r in rows],
                               text=[f"{r['emissions_t']:,.0f} t" for r in rows], textposition="outside",
                               customdata=[r["scope"] for r in rows],
                               hovertemplate="%{y}<br>%{customdata}: %{x:,.0f} tCO₂e/yr<extra></extra>"))
        fig.update_xaxes(title="tCO₂e per year", range=[0, max(r["emissions_t"] for r in rows) * 1.25])
        CP.chart(TH.style_fig(fig, 300, "Where the emissions come from", legend=None),
                 "Purple = Scope 2 (purchased electricity), gold = Scope 1 (fuel burned on site).", key="ov_src")

    with st.expander("How this recommendation is produced", icon=":material/science:"):
        st.markdown(f"- **Activity data** × **emission factors** (GHG Protocol) give the Scope 1 and 2 baseline; model-based range ±{u12:.1f}%.\n"
                    f"- Six candidate projects form {len(res['table'])} portfolios, each simulated on the same {s['n']:,} futures (seed {s['seed']}).\n"
                    f"- **Primary rule D4**: highest expected NPV among portfolios whose quoted cost fits the budget, whose carbon success is at "
                    f"least {res['a_eff']:.4f} and whose budget success is at least {res['b_eff']:.4f} (required levels tightened for sampling error).\n"
                    "- Expected NPV averages all simulated futures; NPV at base inputs uses the most-likely value of every input.\n"
                    "- Synthetic plant: every input is hypothetical or transferred from public sources; outputs are model estimates, not "
                    "verified factory outcomes.")
    pend = int((led.table.decision == "pending").sum()) if led is not None else 0
    if led is not None and pc["status"] != "Approved":
        CP.next_action(f"{pend} record(s) and the anomaly review stand between the reference analysis and an approved operational baseline."
                       if pend else "Review the remaining anomaly flags to approve the operational baseline.", "Plant Data")
    else:
        CP.next_action("See why this portfolio wins, what could change the decision and whether better information is worth buying.",
                       "Decision Intelligence")
