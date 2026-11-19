"""Ma'aden Rolling Company (MRC) facility: the six workspaces built from the unchanged MRC calculations (carbon_iq/mrc.py)
and display blocks (carbon_iq/ui/mrc_view.py). Reported values are Ma'aden's; every investment number is a hypothetical
Mezan scenario, not a Ma'aden value, plan or endorsement."""
import plotly.graph_objects as go
import streamlit as st

from carbon_iq import mrc as M
from carbon_iq.ui import mrc_view as MV
from mezan_ai.insights import Insight
from mezan_platform import report as R
from .. import components as CP
from .. import theme as TH

N = MV.MC_N
GRID = ["Implied by MRC's report (0.335)", "Saudi national average (0.573)"]


def _items():
    return MV.overrides_from_state()


def config_popover():
    """Hypothetical MRC scenario settings in the global configuration panel (same session keys as mrc_view)."""
    d = {i.key: i.value for i in M.scenario_defaults()}
    ss = st.session_state
    defaults = dict(mrc_pv=int(d["pv_kwp"]), mrc_budget=int(d["budget"] / 1e6), mrc_target=int(round(d["target_share"] * 100)),
                    mrc_grid=GRID[0], mrc_tariff=0.18)
    for k, v in defaults.items():
        ss.setdefault(k, v)
    with st.popover("Investment & Scenario Configuration", icon=":material/tune:", use_container_width=True, key="cfg_pop"):
        st.markdown("#### Investment & Scenario Configuration · MRC")
        st.caption("Hypothetical scenario on MRC's reported energy profile. Ma'aden publishes no project costs, roof areas, budgets or "
                   "MRC-level targets: all five settings are Mezan assumptions. Results update immediately.")
        st.markdown("**Investment objectives**")
        c = st.columns(2)
        c[0].number_input("Capital budget (SAR million)", 10, 200, step=5, key="mrc_budget", help="Hypothetical budget.")
        c[1].number_input("Carbon reduction target (% of reported Scope 1+2)", 1, 20, step=1, key="mrc_target", help="Hypothetical target.")
        st.markdown("**Financial and energy assumptions**")
        c = st.columns(3)
        c[0].number_input("Solar size (kWp)", 1_000, 50_000, step=1_000, key="mrc_pv", help="Hypothetical rooftop size.")
        c[1].selectbox("Grid factor for electricity savings", GRID, key="mrc_grid",
                       help="MRC's report implies 0.335 tCO₂e/MWh; the national average is 0.573. The method is not stated in the report.")
        c[2].number_input("Electricity tariff (SAR per kWh)", 0.10, 0.40, step=0.01, key="mrc_tariff", format="%.2f")
        st.caption(f"Risk requirements: carbon and budget tests at 90% each, on {N:,} simulated futures (fixed for this case study).")
        if st.button("Reset to defaults", key="mrc_reset", icon=":material/restart_alt:"):
            for k, v in defaults.items():
                ss[k] = v
            st.rerun()


def banner():
    st.markdown(TH.label("reported", "Reported 2025 (Ma'aden)") + TH.label("hypothetical", "Investment scenario: hypothetical")
                + '<span class="mz-note">Energy and emissions are Ma\'aden\'s published figures; every investment number is a '
                  "hypothetical Mezan scenario, not a Ma'aden value, plan or endorsement.</span>", unsafe_allow_html=True)


def insights(items):
    f = MV._feas(items, N)
    ch = f["cc_choice"]
    g = M.implied_grid_factor()
    r = M.scope1_reconciliation()
    out = [Insight(f"Recalculated Scope 1 differs from the reported value by {r['diff_pct']:+.2f}%, {r['diff_share_of_u95']:.0%} of the "
                   "recalculation's own uncertainty: consistent.", "info", "Calculation engine", "mrc.scope1_reconciliation", "Emissions"),
           Insight(f"Scope 2 implies a grid factor of {g['implied_t_per_mwh']:.3f} tCO₂e/MWh vs the national {g['national_t_per_mwh']:.3f}; "
                   "the method is not stated in the report. Verify with MRC before relying on electricity savings in tonnes.",
                   "action", "Rule-based check", "mrc.implied_grid_factor", "Emissions"),
           Insight("Monthly records are not published: missing-data estimation, ML anomaly detection and record classification are "
                   "not applicable to this facility (no values are invented).", "info", "Rule-based check", "mrc.MISSING", "Plant Data")]
    if ch:
        out.append(Insight(f"Hypothetical scenario: the confidence rule selects {ch['portfolio']} (expected NPV {TH.sar(ch['e_npv'])}, "
                           f"target met in {ch['p_target']:.1%}, budget kept in {ch['p_budget']:.1%} of {N:,} futures).", "info",
                           "Calculation engine", "mrc.monte_carlo", "Investment Planner"))
    if f.get("knife_edge"):
        out.append(Insight(f"The selected plan passes the 90% budget rule by only {ch['budget_margin_se']:.1f} Monte Carlo standard errors: "
                           "treat the choice as unsettled.", "warning", "Calculation engine", "mrc.budget_feasibility", "Investment Planner"))
    return out


def render(page, fac):
    items = _items()
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    if page == "Executive Overview":
        TH.page_header(st, "What does the reported data say, and what would a hypothetical investment plan look like?",
                       "Executive Overview", f"{fac['name']} · {fac['location']} · reporting year {fac['year']}. {fac['status']}.")
        banner()
        TH.cards(st, [("Scope 1 (reported)", f"{M.v('scope1_t'):,.0f} t", "tCO₂e/yr · Ma'aden 2025", "neutral"),
                      ("Scope 2 (reported)", f"{M.v('scope2_t'):,.0f} t", "tCO₂e/yr · method not stated", "neutral"),
                      ("Scope 1+2 (reported)", f"{M.v('scope12_t'):,.0f} t", "tCO₂e/yr", "brand"),
                      ("Energy use (reported)", f"{M.v('energy_total_gj') / 1e6:,.2f} million GJ", "2025", "neutral")])
        left, right = st.columns([1.3, 1], gap="large")
        with left:
            CP.intelligence(insights(items), limit_per_group=3)
        with right:
            CP.chart(MV.energy_chart(go), "Reported energy by carrier.", key="mrc_en")
        MV.render_recommendation(items, N)
        CP.next_action("See how Mezan reconciles the reported emissions.", "Carbon & Emissions")
    elif page == "Plant Data":
        TH.page_header(st, "Can I trust my operational data?", "Plant Data Intelligence", "Reported annual data and what is missing.")
        banner()
        MV.block_reported()
        TH.section(st, "What the report does not provide")
        MV.block_missing()
        st.info("Monthly operating records are not published for MRC, so the record classification, ML anomaly detection and "
                "missing-data workflow cannot run here. They are demonstrated on the synthetic plant.")
    elif page == "Carbon & Emissions":
        TH.page_header(st, "Where are my emissions coming from, and how reliable is my carbon baseline?", "Carbon & Emissions",
                       "Scope 1 recalculation and Scope 2 factor check against Ma'aden's reported values.")
        banner()
        MV.block_scope1(go)
        TH.section(st, "Scope 2 factor check")
        MV.block_scope2(go)
    elif page == "Investment Planner":
        TH.page_header(st, "Which decarbonisation projects should I fund with my available capital?", "Investment Planner",
                       "Hypothetical investment scenario on MRC's reported energy profile; settings in the configuration panel.")
        banner()
        t1, t2, t3 = st.tabs(["Projects", "Portfolios", "Monte Carlo and confidence"])
        with t1:
            MV.block_projects(go, items)
        with t2:
            MV.block_portfolio(go, items)
        with t3:
            MV.block_mc(go, items, N)
    elif page == "Decision Intelligence":
        TH.page_header(st, "What moves the value of the hypothetical MRC plan?", "Mezan Decision Intelligence",
                       "Sensitivity of the hypothetical plan; value of information and timing were not run for MRC.")
        banner()
        CP.intelligence(insights(items), groups=["Investment recommendation", "Financial and analytical findings"])
        MV.block_sensitivity(go, items)
        st.caption("Value of information and investment timing were not run for MRC (annual data only; hypothetical costs).")
    else:
        TH.page_header(st, "Can I explain, verify and defend this investment recommendation?", "Reports & Evidence",
                       "Sources, register and limitations for the MRC case study.")
        banner()
        MV.render_recommendation(items, N)
        TH.section(st, "Source-to-variable register")
        MV.block_register()
        TH.section(st, "Limitations")
        for x in R.LIMITATIONS:
            st.markdown(f"- {x}")
