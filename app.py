"""MEZAN | ميزان - AI-Assisted Industrial Investment Platform (app v3.1, model v1.3).   Run:  streamlit run app.py

One professional application with six workspaces. Every number shown is computed by the unchanged calculation engine
(carbon_iq, model v1.3) through mezan_platform; the AI layer (mezan_ai) classifies records, flags anomalies, offers gated
ML estimate challengers and words explanations, and never produces a quantitative result itself. Research prototype.
"""
from pathlib import Path

import streamlit as st
from PIL import Image

from mezan_platform import APP_VERSION
from mezan_platform import datasets as DSet
from mezan_ui import settings_panel as SP
from mezan_ui import state as S
from mezan_ui import theme as TH

_icon = Path(TH.FAVICON)
st.set_page_config(page_title="MEZAN | ميزان — AI-Assisted Industrial Investment Platform",
                   page_icon=Image.open(_icon) if _icon.exists() else None, layout="wide", initial_sidebar_state="auto")
TH.inject(st)
S.init()
ss = st.session_state


def _status_of(fac_key, pc):
    if fac_key == "MRC":
        return "Reported annual data · hypothetical investments", "warn"
    return f"Plant data: {pc.get('status', '—')}", TH.status_tone(pc.get("status"))


pc = S.plant_context(ss["plant_src"]) if ss.get("facility", "SYN") != "MRC" else {}

with st.sidebar:
    st.markdown(TH.sidebar_brand_html(), unsafe_allow_html=True)
    fac_key = st.selectbox("Facility", S.FAC_KEYS, key="facility", format_func=lambda k: DSet.FACILITIES[k]["short"])
    fac = DSet.FACILITIES[fac_key]
    if fac_key == "SYN" and not pc:
        pc = S.plant_context(ss["plant_src"])
    stxt, tone = _status_of(fac_key, pc)
    fg, bg, _ = TH.TONES[tone]
    st.markdown(f'<div class="mz-fac"><div class="n">{fac["name"]}</div><div class="m">Reporting year {fac["year"]} · '
                f'{fac["location"]}</div><span class="s" style="color:{fg};background:{bg}">{stxt}</span></div>',
                unsafe_allow_html=True)
    st.markdown('<div class="mz-sb-label">Workspace</div>', unsafe_allow_html=True)
    for p in S.PAGES:
        st.button(p, key=f"nav_{S.PAGE_KEYS[p]}", icon=S.PAGE_ICONS[p], type="primary" if ss["nav"] == p else "secondary",
                  on_click=S.go_to, args=(p,), use_container_width=True, help=p)
    st.markdown(f'<div class="mz-sb-foot">App v{APP_VERSION} · model v1.3<br>Research prototype · not investment advice · '
                "not externally validated</div>", unsafe_allow_html=True)

page = ss["nav"]

if fac_key == "MRC":
    from mezan_ui.pages import mrc
    head = st.columns([4, 1.45], vertical_alignment="center")
    with head[1]:
        mrc.config_popover()
    with head[0]:
        st.markdown(TH.topbar_html(fac["short"], "Reported company data", "Hypothetical investment scenario"), unsafe_allow_html=True)
    mrc.render(page, fac)
    st.stop()

head = st.columns([4, 1.45], vertical_alignment="center")
with head[1]:
    ran = SP.drawer(pc)
with head[0]:
    s_ = S.settings()
    basis = "Approved operational data" if ss["applied_activity_basis"] == "plant" else "Reference data"
    st.markdown(TH.topbar_html(fac["short"], basis, f"{s_.n:,} futures · seed {s_.seed}", stale=S.settings_changed()),
                unsafe_allow_html=True)
ran = SP.changed_banner() or ran
if ran or ss.pop("_run_requested", False):
    with st.status("Running investment analysis…", expanded=True) as status:
        ctx_ = S.analysis_context(S.plant_context(ss["plant_src"]))
        st.write(f"Simulating {S.settings().n:,} futures and evaluating every portfolio of the candidate projects…")
        S.result(ctx_)
        st.write("Switching thresholds, discount-rate sweep, sensitivity and value of information…")
        S.switching(ctx_); S.discount(ctx_); S.voi(ctx_); S.tornado(ctx_)
        st.write("Evidence-grounded explanation…")
        S.explanation(ctx_)
        status.update(label="Analysis complete — all pages now reflect the applied settings", state="complete", expanded=False)
ctx = S.analysis_context(pc)
if ctx.get("fallback"):
    st.info(ctx["basis_note"])

from importlib import import_module  # noqa: E402

PG = import_module(f"mezan_ui.pages.{ {'Executive Overview': 'overview', 'Plant Data': 'plant_data', 'Carbon & Emissions': 'emissions', 'Investment Planner': 'planner', 'Decision Intelligence': 'decision', 'Reports & Evidence': 'reports'}[page]}")
PG.render(fac, pc, ctx)
