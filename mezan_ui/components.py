"""Shared interface components (presentation only; every value comes from the current analysis run)."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from mezan_platform import labels as LB
from . import state as S
from . import theme as TH

GROUPS = [   # Mezan Intelligence groups: (title, label kind, predicate on Insight)
    ("Investment recommendation", "engine", lambda i: i.kind == "Calculation engine" and i.page == "Investment Planner"),
    ("Machine-learning findings", "ml", lambda i: i.kind in ("ML flag", "ML classification")),
    ("Data-quality warnings", "rule", lambda i: i.kind in ("Rule-based check", "Statistical estimate")),
    ("Financial and analytical findings", "engine", lambda i: i.kind == "Calculation engine" and i.page != "Investment Planner"),
]


def chart(fig, explain=None, key=None):
    """Render a chart with its one-sentence explanation underneath."""
    st.plotly_chart(fig, width="stretch", key=key, config={"displaylogo": False, "responsive": True})
    if explain:
        st.markdown(f'<div class="mz-explain">{explain}</div>', unsafe_allow_html=True)


def next_action(text, page=None, key=None, label=None):
    c = st.columns([5, 1.4], vertical_alignment="center")
    c[0].markdown(f'<div class="mz-next"><b>Next action</b>&nbsp;·&nbsp;{text}</div>', unsafe_allow_html=True)
    if page:
        c[1].button(label or f"Go to {page}", key=key or f"next_{S.PAGE_KEYS.get(page, page)}", on_click=S.go_to, args=(page,),
                    icon=":material/arrow_forward:", use_container_width=True)


def project_list(portfolio):
    return [f"{i} · {LB.SHORT[i]}" for i in portfolio.split("+")] if portfolio and portfolio != "(none)" else []


def intelligence(insights, title="Mezan Intelligence", groups=None, limit_per_group=3, expand_first=False):
    """Prioritised findings grouped by what produced them; evidence behind each in an expander."""
    with st.container(border=True):
        st.markdown(f'<div class="mz-grp" style="font-size:1.06rem;margin-top:0">{title}</div>', unsafe_allow_html=True)
        st.caption("Selected and worded by rules from the current run, ledger and ML results; each finding names the component it "
                   "comes from. No finding computes a number itself.")
        shown = 0
        for gtitle, kind, pred in GROUPS:
            if groups and gtitle not in groups:
                continue
            sel = [i for i in insights if pred(i)][:limit_per_group]
            if not sel:
                continue
            st.markdown(f'<div class="mz-grp">{TH.label(kind, gtitle)}</div>', unsafe_allow_html=True)
            for i in sel:
                st.markdown(TH.insight_html(i), unsafe_allow_html=True)
                with st.expander("Evidence", expanded=expand_first and shown == 0):
                    st.markdown(f"**Source:** `{i.evidence}`  \n**Produced by:** {i.kind}  \n**Where to act:** {S.page_name(i.page)}")
                shown += 1
        if not shown:
            st.markdown('<div class="mz-ins"><div class="txt">No open findings for this workspace.</div></div>', unsafe_allow_html=True)


def basis_note(ctx):
    if ctx.get("activity_used"):
        st.markdown(TH.label("estimated", "Approved operational data") + f'<span class="mz-note">{ctx["basis_note"]}</span>',
                    unsafe_allow_html=True)
    else:
        st.markdown(TH.label("synthetic", "Reference data · synthetic register") + TH.label("hypothetical", "Hypothetical inputs")
                    + f'<span class="mz-note">{ctx["basis_note"]}</span>', unsafe_allow_html=True)


def workflow_steps(pc, ctx, res):
    """The eight-stage decision journey with its ACTUAL completion state."""
    ss = st.session_state
    led = pc.get("ledger")
    pending = int((led.table.decision == "pending").sum()) if led is not None else None
    approved = pc.get("status") == "Approved"
    used = bool(ctx.get("activity_used"))
    an = pc.get("anomalies") or {}
    rec = res["recommended"]
    return [
        ("Operational records", pc.get("raw") is not None, pc.get("name") or "no data loaded"),
        ("Issues identified", led is not None,
         (f"rules + {'Isolation Forest' if an.get('applied') else 'rules only (ML not applied)'}") if led is not None
         else pc.get("status", "—")),
        ("Baseline reviewed", approved, "approved" if approved else (f"{pending} record(s) pending" if pending else pc.get("status", "—"))),
        ("Emissions baseline", True, f"{res['totals']['Scope 1+2']:,.0f} tCO₂e/yr · {'operational data' if used else 'reference data'}"),
        ("Objectives and risk set", True, f"{TH.sar(res['settings']['budget'])} · {res['settings']['target_share']:.0%} cut"),
        ("Futures evaluated", True, f"{len(res['table'])} portfolios × {res['settings']['n']:,}"),
        ("Portfolio recommended", rec is not None, rec["portfolio"] if rec else "none feasible"),
        ("Report exported", ss.get("report_downloaded", False), "Reports & Evidence"),
    ]


def workflow(pc, ctx, res):
    steps = workflow_steps(pc, ctx, res)
    html = []
    for i, (name, done, note) in enumerate(steps, 1):
        col = (TH.OK, "#E2F1EA") if done else (TH.GOLD_DK, "#FBF1DA")
        html.append(f'<div class="st {"done" if done else ""}"><div class="dot" style="color:{col[0]};background:{col[1]};'
                    f'border:2px solid {col[0]}">{"✓" if done else i}</div><div class="n">{name}</div><div class="m">{note}</div></div>')
    with st.container(border=True):
        st.markdown('<div class="mz-grp" style="margin-top:0">Decision workflow</div>', unsafe_allow_html=True)
        st.markdown('<div class="mz-flow">' + "".join(html) + "</div>", unsafe_allow_html=True)
        if not ctx.get("activity_used"):
            st.caption("This run uses the reference (synthetic) activity data. An approved operational-data baseline is used only "
                       "after Plant Data review and selecting it in the configuration panel.")


def probability_chart(res, top=6, height=360):
    """Carbon and budget success shown separately, each with its own required level."""
    rows = [r for r in res["table"] if r["within_budget_quote"] and r["portfolio"] != "(none)"]
    rows.sort(key=lambda r: -r["e_npv"])
    rows = rows[:top]
    rec = res["recommended"]["portfolio"] if res["recommended"] else None
    names = [r["portfolio"] + (" ★" if r["portfolio"] == rec else "") for r in rows]
    s = res["settings"]
    fig = go.Figure()
    fig.add_bar(x=names, y=[r["p_target"] for r in rows], name="Carbon target met", marker_color=TH.PURPLE,
                hovertemplate="%{x}<br>Carbon target met in %{y:.2%} of futures<extra></extra>")
    fig.add_bar(x=names, y=[r["p_budget"] for r in rows], name="Capex within budget", marker_color=TH.GOLD,
                hovertemplate="%{x}<br>Actual capex within budget in %{y:.2%} of futures<extra></extra>")
    same = abs(s["alpha"] - s["beta"]) < 1e-9
    fig.add_hline(y=s["alpha"], line_dash="dash", line_color=TH.PURPLE, line_width=1.5,
                  annotation_text=(f"required {s['alpha']:.0%} (both tests)" if same else f"carbon required {s['alpha']:.0%}"),
                  annotation_position="top left", annotation_font=dict(size=11, color=TH.PURPLE), annotation_bgcolor="rgba(255,255,255,0.9)")
    if not same:
        fig.add_hline(y=s["beta"], line_dash="dot", line_color=TH.GOLD_DK, line_width=1.5,
                      annotation_text=f"budget required {s['beta']:.0%}", annotation_position="bottom right", annotation_bgcolor="rgba(255,255,255,0.9)",
                      annotation_font=dict(size=11, color=TH.GOLD_DK))
    lo = max(0.0, min([r["p_target"] for r in rows] + [r["p_budget"] for r in rows] + [s["alpha"], s["beta"]]) - 0.15)
    fig.update_layout(barmode="group", bargap=0.28)
    fig.update_yaxes(tickformat=".0%", range=[lo, 1.08], title="share of simulated futures")
    return TH.style_fig(fig, height, "Carbon and budget success, tested separately")


def decision_rules_table(res):
    rows = []
    for rule, role in (("D1", "Comparison"), ("D2", "Comparison"), ("D3", "Carbon test only"), ("D4", "PRIMARY")):
        k = res["choice"][rule]
        if k is None:
            rows.append({"Rule": rule, "Role": role, "Portfolio": "none feasible", "Expected NPV": "—", "NPV at base inputs": "—",
                         "Carbon success": "—", "Budget success": "—", "Definition": S.A.RULE_TEXT[rule]})
            continue
        r = res["table"][k]
        rows.append({"Rule": rule, "Role": role, "Portfolio": r["portfolio"], "Expected NPV": TH.sar(r["e_npv"]),
                     "NPV at base inputs": TH.sar(r["npv_base_inputs"]), "Carbon success": TH.pct(r["p_target"], 2),
                     "Budget success": TH.pct(r["p_budget"], 2), "Definition": S.A.RULE_TEXT[rule]})
    return pd.DataFrame(rows)


def status_of(res, r):
    rec = res["recommended"]["portfolio"] if res["recommended"] else None
    if r["portfolio"] == rec:
        return "Recommended"
    if not r["within_budget_quote"]:
        return "Quote over budget"
    if r["passes_carbon"] and r["passes_budget"]:
        return "Passes both tests"
    if not r["passes_carbon"] and not r["passes_budget"]:
        return "Fails both tests"
    return "Fails carbon test" if not r["passes_carbon"] else "Fails budget test"


def alternatives_table(res, top=10):
    rows = [r for r in res["table"] if r["portfolio"] != "(none)"]
    rows.sort(key=lambda r: (-(r["within_budget_quote"] and r["passes_carbon"] and r["passes_budget"]), -r["e_npv"]))
    rec = res["recommended"]
    if rec:
        rows = [rec] + [r for r in rows if r["portfolio"] != rec["portfolio"]]
    out = []
    for r in rows[:top]:
        out.append({"Portfolio": r["portfolio"], "Projects": LB.portfolio_names(r["portfolio"]), "Status": status_of(res, r),
                    "Expected NPV (SAR M)": round(r["e_npv"] / 1e6, 3), "NPV at base inputs (SAR M)": round(r["npv_base_inputs"] / 1e6, 3),
                    "Quoted capex (SAR M)": round(r["quoted_capex"] / 1e6, 3), "Downside NPV, 5th pct (SAR M)": round(r["p5_npv"] / 1e6, 3),
                    "Carbon success": r["p_target"], "Budget success": r["p_budget"], "P(NPV < 0)": r["p_loss"],
                    "Expected cut (tCO₂e/yr)": round(r["e_t12"])})
    return pd.DataFrame(out)


PCT_COLS = ("Carbon success", "Budget success", "P(NPV < 0)")


def portfolio_column_config():
    cfg = {c: st.column_config.ProgressColumn(c, min_value=0.0, max_value=1.0, format="percent") for c in PCT_COLS[:2]}
    cfg["P(NPV < 0)"] = st.column_config.NumberColumn("P(NPV < 0)", format="percent")
    for c in ("Expected NPV (SAR M)", "NPV at base inputs (SAR M)", "Quoted capex (SAR M)", "Downside NPV, 5th pct (SAR M)"):
        cfg[c] = st.column_config.NumberColumn(c, format="%.2f")
    cfg["Expected cut (tCO₂e/yr)"] = st.column_config.NumberColumn("Expected cut (tCO₂e/yr)", format="localized")
    return cfg


def highlight_status(df, col="Status"):
    """Pandas Styler: recommended rows gold, failing rows faint red, unresolved rows amber."""
    def row_style(r):
        v = str(r.get(col, ""))
        if v.startswith("Recommended") or v.startswith("Approved"):
            bg = "#FBF3DD"
        elif v.startswith("Fails") or v.startswith("Quote over") or v.startswith("Blocked") or v.startswith("Refused"):
            bg = "#FBEDEB"
        elif v.startswith("Pending") or v.startswith("Needs") or v.startswith("Awaiting"):
            bg = "#FCF5E8"
        else:
            bg = ""
        return [f"background-color:{bg}" if bg else "" for _ in r]
    return df.style.apply(row_style, axis=1)
