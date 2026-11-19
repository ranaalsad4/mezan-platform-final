"""App v3.1 interface behaviour: navigation, configuration panel (percentage inputs, stale-results guard), the eight
Decision Intelligence question cards (answers generated from the current run), report exports (HTML/PDF) matching the
active run, brand assets, unavailable-data and no-language-model operation. Uses Streamlit's AppTest (no browser)."""
import json
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from mezan_platform import analysis as A
from mezan_platform import datasets as DSet
from mezan_platform import report as R

ROOT = Path(__file__).resolve().parents[1]
RES = json.load(open(ROOT / "outputs" / "results.json"))
D4 = {d["id"]: d for d in RES["decision_scenarios"]}["D4"]
QUESTIONS = ["invest", "why", "change", "risk", "info", "timing", "ai", "trust"]


def app(page="Executive Overview", facility="SYN", **state):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=600)
    at.session_state["nav"] = page
    at.session_state["facility"] = facility
    for k, v in state.items():
        at.session_state[k] = v
    return at.run()


def text(at):
    parts = [m.value for m in at.markdown] + [x.value for x in at.success] + [x.value for x in at.warning]
    parts += [x.value for x in at.error] + [x.value for x in at.info] + [x.value for x in at.caption]
    return "\n".join(parts)


def test_sidebar_navigation_buttons_switch_pages():
    at = app()
    assert not at.exception
    labels = [b.label for b in at.button if b.key and b.key.startswith("nav_")]
    assert labels == ["Executive Overview", "Plant Data", "Carbon & Emissions", "Investment Planner", "Decision Intelligence",
                      "Reports & Evidence"]
    at.button(key="nav_planner").click().run()
    assert not at.exception and at.session_state["nav"] == "Investment Planner"
    assert "Portfolio opportunity map" in text(at)
    at.button(key="nav_decision").click().run()
    assert at.session_state["nav"] == "Decision Intelligence" and "Mezan Decision Intelligence" in text(at)


def test_overview_names_projects_in_full_from_the_run():
    t = text(app())
    assert f"Fund {D4['portfolio']}" in t
    for name in ("Solar PV", "Efficient motors + VSDs", "Compressed-air repairs"):
        assert name in t
    assert "separately" in t and "not guarantees" in t


@pytest.mark.parametrize("q", QUESTIONS)
def test_every_decision_question_card_answers(q):
    at = app("Decision Intelligence", di_q=q)
    assert not at.exception, [e.value for e in at.exception]
    t = text(at)
    assert "mz-ans" in t and "Method:" in t
    if q == "ai":
        assert "Layer 1" in t and "Layer 2" in t and "Layer 3" in t
    btn = at.button(key=f"dq_{q}")
    assert btn.proto.type == "primary"                                     # selected state is visible


def test_question_selection_persists_across_reruns_and_navigation():
    at = app("Decision Intelligence")
    at.button(key="dq_info").click().run()
    assert at.session_state["di_q"] == "info" and "EVPI" in text(at)
    at.button(key="nav_overview").click().run()
    at.button(key="nav_decision").click().run()
    assert at.session_state["di_q"] == "info" and "EVPI" in text(at)


def test_decision_answers_follow_the_current_run():
    """Change the budget, run, and the answer must name the new D4 choice computed by the engine (not a stored example)."""
    at = app("Decision Intelligence", di_q="invest")
    at.number_input(key="set_budget_m").set_value(4.2).run()
    at.button(key="run_analysis").click().run()
    assert not at.exception
    exp = A.run(A.Settings(budget=4_200_000.0)).get("recommended")
    t = text(at)
    if exp:
        assert f"Fund {exp['portfolio']}" in t and f"SAR {exp['e_npv'] / 1e6:.2f} M" in t
    else:
        assert "Nothing yet" in t


def test_percentage_settings_propagate_and_stale_results_are_flagged():
    at = app("Carbon & Emissions")
    assert at.slider(key="set_target_pct").value == 15
    at.slider(key="set_target_pct").set_value(20).run()
    t = text(at)
    assert "Assumptions changed" in t and "Results out of date" in t and f"{RES['target_t']:,.0f}" in t   # old run still shown
    at.button(key="run_analysis_banner").click().run()
    assert not at.exception
    tt = A.run(A.Settings(target_share=0.20))["target_t"]
    t = text(at)
    assert f"{tt:,.0f}" in t and "Assumptions changed" not in t and "Results out of date" not in t
    at.button(key="reset_settings").click().run()
    assert at.slider(key="set_target_pct").value == 15 and at.number_input(key="set_discount_pct").value == 6.0


def test_unavailable_data_case_runs_every_page():
    for page in ("Plant Data", "Executive Overview", "Carbon & Emissions", "Reports & Evidence"):
        at = app(page, plant_src="upload")
        assert not at.exception, page
    assert "Upload a CSV" in text(app("Plant Data", plant_src="upload"))


def test_runs_without_a_language_model(monkeypatch):
    for k in list(os.environ):
        if k.startswith("MEZAN_LLM"):
            monkeypatch.delenv(k)
    from mezan_ai import llm
    assert not llm.config()["enabled"]
    at = app("Decision Intelligence", di_q="ai")
    assert not at.exception and "not configured" in text(at)


def test_report_exports_match_the_active_run():
    from mezan_ai import explain as X
    res = A.run(A.Settings(budget=4_200_000.0, n=5000))
    ex = X.explain(res, use_llm=False)
    m = R.report_model(res, DSet.FACILITIES["SYN"], ex)
    kp = {k[0]: k[1] for sec in m["sections"] for k in sec.get("kpis", [])}
    rec = res["recommended"]
    if rec:
        assert kp["Expected NPV"] == R._sar(rec["e_npv"]) and kp["Carbon target met"] == f"{rec['p_target']:.2%}"
    pdf = R.executive_pdf(res, DSet.FACILITIES["SYN"], ex)
    assert pdf[:5] == b"%PDF-" and pdf.count(b"/Type /Page") - pdf.count(b"/Type /Pages") >= 3   # multi-page
    html = R.executive_html(res, DSet.FACILITIES["SYN"], ex)
    assert "data:image/png;base64," in html and "Executive Decision Report" in html
    assert R.settings_hash(res["settings"]) != R.settings_hash(A.DEFAULTS.__dict__)


def test_brand_assets_present_and_used():
    for f in ("mezan_icon_512.png", "mezan_icon_256.png", "mezan_icon_128.png", "favicon.png", "favicon.ico"):
        assert (ROOT / "assets" / f).exists(), f
    from PIL import Image
    im = Image.open(ROOT / "assets" / "mezan_icon_256.png")
    assert im.mode == "RGBA" and im.getpixel((0, 0))[3] == 0 and im.getpixel((128, 128))[3] == 255   # transparent corners
    t = text(app())
    assert "data:image/png;base64," in t and "MEZAN" in t and "AI-Assisted Industrial Investment Platform" in t


def test_mrc_configuration_and_no_synthetic_controls():
    at = app("Investment Planner", "MRC")
    assert not at.exception
    keys = {w.key for w in at.number_input}
    assert {"mrc_budget", "mrc_target", "mrc_pv", "mrc_tariff"} <= keys and "set_budget_m" not in keys
    assert "not a Ma'aden value" in text(at)


def test_no_unsupported_claims_in_interface_text():
    t = "\n".join(text(app(p)) for p in ("Executive Overview", "Decision Intelligence", "Reports & Evidence")).lower()
    for bad in ("guaranteed to", "validated by ma'aden", "externally validated model", "generative ai explanation",
                "trained on real plant data", "joint probability of"):
        assert bad not in t, bad
