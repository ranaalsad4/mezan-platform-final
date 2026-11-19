"""Investment & Scenario Configuration: four groups (investment objectives, risk requirements, financial and energy
assumptions, advanced simulation settings) with units, defaults, tooltips, validation, reset, a change indicator and
Run investment analysis. Editing a setting never reruns the simulation; results stay tied to the applied settings."""
from dataclasses import asdict

import streamlit as st

from carbon_iq import engine as E
from mezan_platform import analysis as A
from . import state as S
from . import theme as TH

DEF = asdict(A.DEFAULTS)
M = A.SETTING_META
PANEL_TITLE = "Investment & Scenario Configuration"


def _reset():
    ss = st.session_state
    for k, v in DEF.items():
        ss[f"set_{k}"] = v
    ss["set_budget_m"] = DEF["budget"] / 1e6
    for k, w in S.PCT_KEYS.items():
        ss[w] = round(100 * DEF[k], 2)
    ss["set_activity_basis"] = "reference"


def _default_text(k):
    d = DEF[k]
    if k == "budget":
        return f"SAR {d / 1e6:.2f} million"
    if k in S.PCT_KEYS:
        return f"{100 * d:g}%"
    if k in ("n", "seed"):
        return f"{d:,}"
    if k == "basis":
        return A.BASIS_LABELS[d]
    return f"{d:g} {M[k][1]}"


def _help(k, extra=""):
    return f"{M[k][2]} Default: {_default_text(k)}.{(' ' + extra) if extra else ''}"


def apply():
    """Make the pending settings the applied settings (the next render runs or reuses the cached analysis)."""
    ss = st.session_state
    pend = S.pending_settings()
    if A.validate(pend):
        return False
    ss["applied"] = asdict(pend)
    ss["applied_activity_basis"] = ss["set_activity_basis"]
    ss["runs"] += 1
    ss["_run_requested"] = True
    return True


def _target_tonnes(pend, pc):
    act = pc.get("activity") if (st.session_state["set_activity_basis"] == "plant" and pc.get("status") == "Approved") else None
    try:
        return float(E.target_t(A.deterministic_params(pend, act)))
    except Exception:  # noqa: BLE001
        return None


def drawer(pc):
    """Render the configuration panel. Run buttons apply the settings in their click callback, i.e. before any part of
    the page is drawn, so no element of a run can describe stale settings."""
    ss = st.session_state
    stale = S.settings_changed()
    lab = PANEL_TITLE + ("  ·  changed" if stale else "")
    with st.popover(lab, icon=":material/tune:", use_container_width=True, key="cfg_pop"):
        st.markdown(f"#### {PANEL_TITLE}")
        st.caption("Set what management wants to achieve and how sure the plan must be. Changes take effect when you press "
                   "**Run investment analysis**; until then every page shows the last run.")
        pend = S.pending_settings()

        st.markdown("**1 · Investment objectives**")
        c = st.columns(3)
        c[0].number_input("Capital budget (SAR million)", 0.5, 20.0, step=0.25, key="set_budget_m", format="%.2f",
                          help=_help("budget", "Checked against the quoted capital cost of a portfolio."))
        c[1].slider("Carbon reduction target (% of Scope 1+2)", 0, 30, step=1, key="set_target_pct", format="%d%%",
                    help=_help("target_share"))
        tt = _target_tonnes(pend, pc)
        c[2].markdown(TH.cards_html([("Target in tonnes", f"{tt:,.0f} tCO₂e/yr" if tt is not None else "—",
                                      f"{pend.target_share:.0%} of the Scope 1+2 baseline", "gold")]), unsafe_allow_html=True)

        st.markdown("**2 · Risk requirements** — two separate tests, not one joint probability")
        c = st.columns(2)
        c[0].slider("Required probability of meeting the carbon target", 50, 99, step=1, key="set_alpha_pct", format="%d%%",
                    help=_help("alpha", "Tested on its own."))
        c[1].slider("Required probability of staying within the capital budget", 50, 99, step=1, key="set_beta_pct", format="%d%%",
                    help=_help("beta", "Tested separately from the carbon requirement."))
        st.caption("A portfolio must pass **both** tests. Each required level is tightened slightly for sampling error on the "
                   "simulated futures. Modelled probabilities are not guarantees.")

        st.markdown("**3 · Financial and energy assumptions**")
        c = st.columns(3)
        c[0].number_input("Real discount rate (% per year)", 2.0, 14.0, step=0.5, key="set_discount_pct", format="%.1f",
                          help=_help("discount_rate"))
        c[1].number_input("Electricity tariff (SAR per kWh)", 0.10, 0.35, step=0.005, key="set_tariff", format="%.3f",
                          help=_help("tariff"))
        c[2].number_input("Natural gas price (USD per MMBtu)", 1.0, 8.0, step=0.05, key="set_gas_price_usd", format="%.2f",
                          help=_help("gas_price_usd"))

        with st.expander("4 · Advanced simulation settings", icon=":material/settings:"):
            c = st.columns(3)
            c[0].selectbox("Monte Carlo scenarios (simulated futures)", [2000, 5000, 10000, 20000], key="set_n",
                           help=_help("n", "Fewer scenarios run faster but carry more sampling error."),
                           format_func=lambda v: f"{v:,}")
            c[1].number_input("Scenario seed", 1, 2**31 - 1, step=1, key="set_seed", help=_help("seed"))
            c[2].selectbox("Carbon-target baseline convention", list(A.BASIS_LABELS), key="set_basis",
                           format_func=lambda b: A.BASIS_LABELS[b], help=_help("basis"))
            st.radio("Activity data used by the analysis", ["reference", "plant"], key="set_activity_basis", horizontal=True,
                     format_func=lambda v: "Reference register (model v1.3)" if v == "reference" else "Approved operational data",
                     help="Approved operational data are used only when the Plant Data baseline is approved; unresolved gaps "
                          "or unreviewed ML flags keep the reference data in use.")
            if ss["set_activity_basis"] == "plant" and pc.get("status") != "Approved":
                st.caption(f"Plant-data baseline is '{pc.get('status')}': the run will use reference data until it is approved.")

        pend = S.pending_settings()
        problems = A.validate(pend)
        changed = pend.changed_from_defaults()
        if changed:
            st.markdown(TH.label("partial", "Changed from defaults") + '<span class="mz-note">'
                        + ", ".join(M[k][0] for k in changed) + "</span>", unsafe_allow_html=True)
        for p in problems:
            st.error(p)
        if S.settings_changed():
            st.markdown('<div class="mz-stale">Settings differ from the last run. Results on every page still describe the last run.</div>',
                        unsafe_allow_html=True)
        b = st.columns([1.4, 1])
        b[0].button("Run investment analysis", type="primary", key="run_analysis", disabled=bool(problems),
                    icon=":material/play_arrow:", use_container_width=True, on_click=apply)
        b[1].button("Reset to defaults", key="reset_settings", on_click=_reset, icon=":material/restart_alt:", use_container_width=True)
    return False


def changed_banner():
    """Stale-results guard shown on every page while edited settings have not been run."""
    if not S.settings_changed():
        return False
    c = st.columns([5, 1.3])
    c[0].markdown('<div class="mz-stale"><b>Assumptions changed — results below are from the last run.</b>&nbsp;They do not yet '
                  "reflect your edited settings. Run the analysis to update every page.</div>", unsafe_allow_html=True)
    c[1].button("Run analysis now", key="run_analysis_banner", type="primary", icon=":material/play_arrow:",
                use_container_width=True, disabled=bool(A.validate(S.pending_settings())), on_click=apply)
    return False
