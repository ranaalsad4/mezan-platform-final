"""3 · Carbon & Emissions - where are my emissions coming from, and how reliable is my carbon baseline?
Scope 1/2 breakdown, energy use, model-based uncertainty, the cost of zero-filled data, emission factors and sources.
All values from the calculation engine (GHG Protocol accounting, IPCC 2006 Approach 1 uncertainty)."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from carbon_iq import engine as E
from carbon_iq.assumptions import EF_GRID_SCENARIOS, P, base_values
from carbon_iq.dataquality import integrate as DI
from .. import components as CP
from .. import state as S
from .. import theme as TH

EF_KEY = {"S1-GAS": "ef_gas", "S1-DSL-FL": "ef_diesel", "S1-DSL-GEN": "ef_diesel", "S2-ELEC": "ef_grid",
          "S3-C1-STEEL": "ef_steel_incumbent", "S3-C4-FRT": "ef_freight"}
ACT_KEY = {"S1-GAS": "gas_gj", "S1-DSL-FL": "diesel_forklift_l", "S1-DSL-GEN": "diesel_genset_l", "S2-ELEC": "elec_mwh",
           "S3-C1-STEEL": "steel_t", "S3-C4-FRT": "freight_tkm"}
EVIDENCE_TEXT = {"external": "External published source", "derived": "Derived from cited values", "hypothetical": "Hypothetical assumption"}
GJ_PER_MWH = 3.6   # exact unit identity (1 MWh = 3.6 GJ)


def _s12(activity):
    p = dict(base_values())
    for k, (v, _) in activity.items():
        p[k] = v
    return E.scope_totals(E.baseline(p)), p


def render(fac, pc, ctx):
    res = S.result(ctx)
    tot, s = res["totals"], res["settings"]
    unc_rows, ut = res["uncertainty_rows"], res["uncertainty_totals"]
    TH.page_header(st, "Where are my emissions coming from, and how reliable is my carbon baseline?", "Carbon & Emissions",
                   "Understand your emissions footprint, identify major emission sources and establish a defensible reduction baseline.")
    CP.basis_note(ctx)
    u12 = ut["Scope 1+2"][1]
    TH.cards(st, [("Scope 1 · direct", f"{tot['Scope 1']:,.0f}", "tCO₂e/year · fuel combustion", "neutral"),
                  ("Scope 2 · electricity", f"{tot['Scope 2']:,.0f}", "tCO₂e/year · location-based", "neutral"),
                  ("Scope 1 + 2 baseline", f"{tot['Scope 1+2']:,.0f}", "tCO₂e/year · basis of the target", "brand"),
                  ("Model-based uncertainty", f"±{u12:.1f}%",
                   f"{tot['Scope 1+2'] * (1 - u12 / 100):,.0f} – {tot['Scope 1+2'] * (1 + u12 / 100):,.0f} tCO₂e/year", "neutral"),
                  ("Required reduction", f"{res['target_t']:,.0f}", f"tCO₂e/year · {s['target_share']:.0%} of Scope 1+2", "gold"),
                  ("Scope 3 · reported separately", f"{tot['Scope 3']:,.0f}", "tCO₂e/year · purchased steel and freight; not in the target",
                   "neutral")])

    # breakdown
    TH.section(st, "Emissions breakdown", "Which sources make up the Scope 1 and 2 baseline that investments must reduce.")
    rows = sorted([r for r in res["baseline_rows"] if r["scope"] in ("Scope 1", "Scope 2")], key=lambda r: r["emissions_t"])
    total12 = sum(r["emissions_t"] for r in rows)
    top = rows[-1]
    c = st.columns([1.5, 1], gap="large")
    with c[0]:
        fig = go.Figure(go.Bar(y=[r["source"] for r in rows], x=[r["emissions_t"] for r in rows], orientation="h",
                               marker_color=[TH.PURPLE if r["scope"] == "Scope 2" else TH.GOLD for r in rows],
                               text=[f"{r['emissions_t']:,.0f} t · {r['emissions_t'] / total12:.0%}" for r in rows], textposition="outside",
                               customdata=[r["scope"] for r in rows],
                               hovertemplate="%{y}<br>%{customdata}<br>%{x:,.0f} tCO₂e/year<extra></extra>"))
        fig.update_xaxes(title="tCO₂e per year", range=[0, top["emissions_t"] * 1.32])
        CP.chart(TH.style_fig(fig, 300, "Scope 1 and 2 emissions by source", legend=None),
                 "Purple = Scope 2 (purchased electricity); gold = Scope 1 (fuel burned on site). Labels show tonnes and share of Scope 1+2.",
                 key="em_src")
    with c[1]:
        st.markdown(TH.cards_html([("Largest source", top["source"], f"{top['emissions_t']:,.0f} tCO₂e/year · {top['emissions_t'] / total12:.0%} "
                                                                     f"of Scope 1+2", "gold")]), unsafe_allow_html=True)
        st.markdown(f"**Why it matters for investment.** {top['source']} is {top['emissions_t'] / total12:.0%} of the Scope 1+2 baseline, "
                    f"so projects that cut {'electricity use or replace grid power' if top['scope'] == 'Scope 2' else 'this fuel'} "
                    f"carry most of the reduction needed for the {res['target_t']:,.0f} t target. Its tonnes depend directly on the grid "
                    "emission factor, which is the main source of baseline uncertainty below." if top["scope"] == "Scope 2" else
                    f"**Why it matters for investment.** {top['source']} is {top['emissions_t'] / total12:.0%} of the Scope 1+2 baseline.")
        st.markdown(TH.cards_html([("Scope split", f"{tot['Scope 1'] / total12:.0%} / {tot['Scope 2'] / total12:.0%}",
                                    "Scope 1 / Scope 2 share of the baseline", "neutral")]), unsafe_allow_html=True)

    # energy
    TH.section(st, "Energy consumption", "Electricity, natural gas and diesel used by the plant, in their original units.")
    p = res["p"]
    c = st.columns([1.3, 1], gap="large")
    with c[0]:
        e_gj, g_gj = p["elec_mwh"] * GJ_PER_MWH, p["gas_gj"]
        fig = go.Figure(go.Bar(y=["Natural gas", "Grid electricity"], x=[g_gj, e_gj], orientation="h", marker_color=[TH.GOLD, TH.PURPLE],
                               text=[f"{g_gj:,.0f} GJ", f"{e_gj:,.0f} GJ"],
                               textposition="outside", hovertemplate="%{y}: %{x:,.0f} GJ<extra></extra>"))
        fig.update_xaxes(title="GJ per year (common energy scale)", range=[0, max(e_gj, g_gj) * 1.3])
        CP.chart(TH.style_fig(fig, 220, "Electricity and gas on a common energy scale", legend=None),
                 "Electricity is converted with the exact identity 1 MWh = 3.6 GJ; gas is already in GJ (net calorific value).", key="em_en")
    with c[1]:
        st.dataframe(pd.DataFrame([
            {"Energy source": "Grid electricity", "Original amount": f"{p['elec_mwh']:,.0f} MWh", "Common scale": f"{e_gj:,.0f} GJ"},
            {"Energy source": "Natural gas", "Original amount": f"{p['gas_gj']:,.0f} GJ", "Common scale": f"{g_gj:,.0f} GJ"},
            {"Energy source": "Diesel, forklifts", "Original amount": f"{p['diesel_forklift_l']:,.0f} L", "Common scale": "not converted"},
            {"Energy source": "Diesel, backup generators", "Original amount": f"{p['diesel_genset_l']:,.0f} L", "Common scale": "not converted"}]),
            hide_index=True, width="stretch")
        st.caption("Diesel stays in litres: the register holds no diesel calorific value, so no conversion is made.")

    # uncertainty
    TH.section(st, "Baseline uncertainty",
               "Uncertainty represents how much the emissions estimate could vary under the assumed activity-data and "
               "emission-factor uncertainties.")
    c = st.columns([1, 1], gap="large")
    with c[0]:
        names = ["Scope 1", "Scope 2", "Scope 1+2"]
        vals = [ut[n][0] for n in names]
        half = [ut[n][0] * ut[n][1] / 100 for n in names]
        fig = go.Figure(go.Bar(x=names, y=vals, marker_color=[TH.GOLD, TH.PURPLE, TH.INK],
                               error_y=dict(type="data", array=half, color=TH.BAD, thickness=2, width=10),
                               text=[f"{v:,.0f} ± {h:,.0f}" for v, h in zip(vals, half)], textposition="inside", insidetextanchor="end",
                               textfont=dict(color="white"), hovertemplate="%{x}: %{y:,.0f} tCO₂e/yr<extra></extra>"))
        fig.update_yaxes(title="tCO₂e per year", range=[0, (vals[2] + half[2]) * 1.12])
        CP.chart(TH.style_fig(fig, 320, "Central estimate and model-based range", legend=None),
                 "Bars are the central estimate; red whiskers show the ±range from the assumed input uncertainties.", key="em_unc")
    with c[1]:
        s12 = [r for r in unc_rows if r["scope"] in ("Scope 1", "Scope 2")]
        var = [(r["source"], (r["emissions_t"] * r["u_combined_pct"] / 100) ** 2, r) for r in s12]
        tv = sum(v for _, v, _ in var) or 1
        var.sort(key=lambda x: x[1])
        fig = go.Figure(go.Bar(y=[n for n, _, _ in var], x=[v / tv for _, v, _ in var], orientation="h", marker_color=TH.PURPLE_LT,
                               text=[f"{v / tv:.0%}" for _, v, _ in var], textposition="outside",
                               customdata=[[r["u_activity_pct"], r["u_ef_pct"]] for _, _, r in var],
                               hovertemplate="%{y}<br>share of variance %{x:.1%}<br>activity ±%{customdata[0]:.1f}% · factor ±%{customdata[1]:.1f}%<extra></extra>"))
        fig.update_xaxes(tickformat=".0%", range=[0, 1.15], title="share of Scope 1+2 variance")
        CP.chart(TH.style_fig(fig, 320, "Main sources of uncertainty", legend=None),
                 "Each source's share of the combined Scope 1+2 variance (activity and emission-factor uncertainty combined).", key="em_var")
    st.markdown(TH.label("calculated", "Model-based") + '<span class="mz-note">The range combines the assumed uncertainty of each activity '
                "and factor (U = √(Ua² + Uef²) per source, IPCC 2006 Approach 1). It is not an externally validated confidence interval, "
                "and every synthetic-plant input is an assumption rather than a measured observation.</span>", unsafe_allow_html=True)

    # data quality matters
    TH.section(st, "Why data quality matters",
               "Missing data can hide emissions and lead manufacturers to underestimate the investment required to meet their carbon target.")
    if pc.get("ledger") is not None:
        zero = dict(DI.register_activity())
        zero.update(DI.naive_zero_activity(pc["ledger"]))
        zt, _ = _s12(zero)
        ref = tot["Scope 1+2"]
        gap = ref - zt["Scope 1+2"]
        c = st.columns([1.3, 1], gap="large")
        with c[0]:
            bars = [("Reference baseline (complete records)", ref, TH.PURPLE),
                    (f"Same plant, {pc['name']} gaps counted as zero", zt["Scope 1+2"], TH.BAD)]
            if pc.get("activity"):
                full = dict(DI.register_activity()); full.update(pc["activity"])
                at, _ = _s12(full)
                bars.append((f"Approved estimates ({pc['status'].lower()})", at["Scope 1+2"], TH.GOLD))
            fig = go.Figure(go.Bar(y=[b[0] for b in bars][::-1], x=[b[1] for b in bars][::-1], orientation="h",
                                   marker_color=[b[2] for b in bars][::-1], text=[f"{b[1]:,.0f} t" for b in bars][::-1],
                                   textposition="outside", hovertemplate="%{y}<br>%{x:,.0f} tCO₂e/yr<extra></extra>"))
            fig.update_xaxes(title="Scope 1+2, tCO₂e per year", range=[0, ref * 1.25])
            CP.chart(TH.style_fig(fig, 250, "Zero-filled gaps understate the baseline", legend=None),
                     "Zero-filling is shown only to illustrate the error; it is not an acceptable accounting method.", key="em_zero")
        with c[1]:
            TH.cards(st, [("Hidden emissions", f"{gap:,.0f} t/yr", f"{gap / ref:.0%} of the baseline disappears", "bad"),
                          ("Target understated by", f"{gap * s['target_share']:,.0f} t/yr",
                           f"a {s['target_share']:.0%} target computed on the zero-filled baseline", "warn")])
            st.caption("Mezan never fills a gap with zero: gaps stay open until an estimate is approved or real data arrive.")
    else:
        st.info("Load plant data in Plant Data to see how missing records would distort the baseline.")

    with st.expander("Emission-factor sensitivity: alternative grid factors (separate from the data-quality comparison)"):
        sc = []
        for e in EF_GRID_SCENARIOS:
            q = dict(res["p"]); q["ef_grid"] = e["value"]
            sc.append({"Grid factor scenario": e["label"], "Factor (tCO₂e/MWh)": e["value"],
                       "Scope 1+2 (tCO₂e/yr)": round(E.scope_totals(E.baseline(q))["Scope 1+2"])})
        st.dataframe(pd.DataFrame(sc), hide_index=True, width="stretch",
                     column_config={"Scope 1+2 (tCO₂e/yr)": st.column_config.NumberColumn(format="localized")})
        st.caption("Same activity data with alternative published grid factors; shows how much the baseline depends on the factor choice.")

    # factors and evidence
    TH.section(st, "Emission factors and evidence", "Every activity, factor and source behind the baseline.")
    plant = res["activity"] or {}
    tab = []
    for r in unc_rows:
        ak, ek = ACT_KEY[r["source_id"]], EF_KEY[r["source_id"]]
        if ak in plant and pc.get("annual") is not None:
            ann = pc["annual"]
            row = ann[ann.register == ak]
            status = (f"Measured ({int(row.n_measured.iloc[0])} mo) + approved estimates ({int(row.n_estimated.iloc[0])} mo)"
                      if len(row) else "Operational data")
        else:
            status = "Hypothetical (synthetic register)"
        tab.append({"Activity source": r["source"], "Amount": f"{r['activity']:,.0f} {r['unit']}", "Scope": r["scope"],
                    "Emission factor": f"{r['ef_t_per_unit']:.4g} tCO₂e/{r['unit']}", "Factor origin": EVIDENCE_TEXT.get(P[ek].evidence, P[ek].evidence),
                    "Source reference": P[ek].url or str(P[ek].source)[:80], "Data status": status,
                    "Emissions (tCO₂e/yr)": round(r["emissions_t"]), "Range (±)": f"{r['u_combined_pct']:.1f}%"})
    st.dataframe(pd.DataFrame(tab), hide_index=True, width="stretch",
                 column_config={"Source reference": st.column_config.LinkColumn("Source reference", display_text="open source"),
                                "Emissions (tCO₂e/yr)": st.column_config.NumberColumn(format="localized")})
    st.markdown(TH.label("hypothetical") + TH.label("external") + TH.label("calculated") + TH.label("estimated")
                + '<span class="mz-note">Data status distinguishes hypothetical, externally sourced, calculated and approved-estimate values. '
                  "No synthetic-plant input is a measured factory observation.</span>", unsafe_allow_html=True)
    with st.expander("Methodology and references", icon=":material/menu_book:"):
        st.markdown("- **Accounting:** activity × emission factor, summed by scope — [GHG Protocol Corporate Standard](https://ghgprotocol.org/corporate-standard); "
                    "Scope 2 location-based ([GHG Protocol Scope 2 Guidance](https://ghgprotocol.org/scope-2-guidance)).\n"
                    "- **Uncertainty:** first-order propagation, [IPCC 2006 Guidelines Vol. 1 Ch. 3](https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/1_Volume1/V1_3_Ch3_Uncertainties.pdf) (Approach 1).\n"
                    "- **Target:** Scope 1+2 only; Scope 3 (purchased steel, inbound freight) is reported separately.")
        for k in sorted({EF_KEY[r["source_id"]] for r in unc_rows}):
            x = P[k]
            st.markdown(f"- **{k}** = {x.value} {x.unit} · {EVIDENCE_TEXT.get(x.evidence, x.evidence)} · {x.status}. {x.source}"
                        + (f" [link]({x.url})" if x.url else ""))
    if pc.get("ledger") is not None and pc["status"] != "Approved":
        st.warning(f"Plant-data baseline status: **{pc['status']}**. " + (pc.get("problem") or "Review the remaining items in Plant Data."))
    CP.next_action("With the baseline and target set, compare which projects deliver the reduction at the best value.", "Investment Planner")
