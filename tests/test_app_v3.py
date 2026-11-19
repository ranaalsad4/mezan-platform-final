"""App v3 interface: six workspaces for both facilities, scenario settings drawer, plant-data approval workflow, AI
classification flow, exports. Uses Streamlit's AppTest (no browser)."""
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
RES = json.load(open(ROOT / "outputs" / "results.json"))
D4 = {d["id"]: d for d in RES["decision_scenarios"]}["D4"]
PAGES = ["Executive Overview", "Plant Data", "Carbon & Emissions", "Investment Planner", "Decision Intelligence", "Reports & Evidence"]


def app(page="Executive Overview", facility="SYN", **state):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=600)
    at.session_state["nav"] = page
    at.session_state["facility"] = facility
    for k, v in state.items():
        at.session_state[k] = v
    return at.run()


def text(at):
    parts = [m.value for m in at.markdown] + [f"{m.label} {m.value} {m.delta}" for m in at.metric] + [x.value for x in at.success]
    parts += [x.value for x in at.warning] + [x.value for x in at.error] + [x.value for x in at.info] + [x.value for x in at.caption]
    return "\n".join(parts)


@pytest.mark.parametrize("facility", ["SYN", "MRC"])
@pytest.mark.parametrize("page", PAGES)
def test_every_workspace_runs(facility, page):
    at = app(page, facility)
    assert not at.exception, [e.value for e in at.exception]


def test_no_learning_mode_or_guided_demo():
    at = app()
    labels = [r.label for r in at.radio] + [str(o) for r in at.radio for o in r.options]
    assert not any("Learning" in x or "Presentation Mode" in x or "Guided demo" in x for x in labels)
    assert not any("Learn how this works" in e.label for e in at.expander)


def test_overview_shows_the_model_outputs():
    t = text(app())
    for s in (D4["portfolio"], f"SAR {D4['e_npv'] / 1e6:.2f} M", f"{100 * D4['p_target']:.2f}%", f"{100 * D4['p_budget']:.2f}%",
              f"{RES['scope_totals']['Scope 1+2']:,.0f}", f"{RES['target_t']:,.0f}"):
        assert s in t, s
    assert "Mezan Intelligence" in t and "Decision workflow" in t


def test_settings_change_needs_run_and_infeasible_budget_is_not_raised():
    at = app("Investment Planner")
    at.number_input(key="set_budget_m").set_value(1.0).run()
    assert not at.exception and "Assumptions changed" in text(at)
    assert f"Fund {D4['portfolio']}" in text(at)                                  # still the last run
    at.button(key="run_analysis").click().run()
    assert not at.exception
    t = text(at)
    assert "No portfolio passes both tests" in t and "budget is not raised" in t and "Assumptions changed" not in t
    assert at.number_input(key="set_budget_m").value == 1.0
    at.button(key="reset_settings").click().run()
    at.button(key="run_analysis").click().run()
    assert f"Fund {D4['portfolio']}" in text(at)


def test_plant_data_approval_workflow_blocks_until_reviewed():
    at = app("Plant Data")
    assert not at.exception and "Baseline blocked" in text(at)
    at.button(key="bulk_approve").click().run()
    assert any("natural_gas (1 month(s))" in e.value for e in at.error)          # outlier still needs a decision
    at.button(key="bulk_outliers").click().run()
    assert any("diesel_forklift (1 month(s))" in e.value for e in at.error)      # operational-change refusal
    assert any("OPERATIONAL_CHANGE" in w.value for w in at.warning)
    at.button(key="bulk_override").click().run()
    t = text(at)
    assert "Baseline blocked" not in t and "Isolation Forest flag" in t          # gaps resolved; ML flag review pending
    at.session_state["anom_review"] = {"demo": {"2026-05": "confirmed"}}
    at.run()
    assert "Plant-data baseline approved" in text(at)
    # use the approved plant data in the analysis
    at.session_state["set_activity_basis"] = "plant"
    at.button(key="run_analysis").click().run()
    at.session_state["nav"] = "Carbon & Emissions"
    at.run()
    assert not at.exception and "Approved operational data" in text(at)


def test_severe_gap_is_refused():
    at = app("Plant Data", plant_src="severe")
    assert not at.exception and any("electricity (6 month(s))" in e.value for e in at.error)


def test_unlabelled_export_needs_confirmed_classification():
    at = app("Plant Data", plant_src="unlabelled")
    t = text(at)
    assert "Stream classification" in t and "188 of 190" in t and "Confirm the stream assignments" in t
    at.button(key="cls_confirm").click().run()
    assert not at.exception
    t = text(at)
    assert "set aside" in t and "Data quality assessment" in t


def test_reports_offer_exports():
    at = app("Reports & Evidence")
    assert not at.exception
    t = text(at)
    labels = " ".join(b.label for b in at.get("download_button"))
    for x in ("Executive Decision Report (HTML)", "Executive Decision Report (PDF)", "Analysis results (JSON)", "Portfolio comparison (CSV)",
              "Assumptions register (CSV)", "Data lineage and audit records (CSV)"):
        assert x in labels, x


def test_mrc_labels_reported_and_hypothetical_values():
    t = text(app("Carbon & Emissions", "MRC")) + text(app("Executive Overview", "MRC"))
    assert "not a Ma'aden value" in t and "Reported" in t
    assert "63,961" in t and "64,105" in t and "160,632" in t
    assert "Recommendation for the hypothetical MRC scenario" in t and "Limitations" in t


def test_datasets_stay_separate():
    syn = text(app("Executive Overview")) + text(app("Investment Planner"))
    assert "Ma'aden" not in syn and "160,632" not in syn
    mrc = text(app("Executive Overview", "MRC")) + text(app("Investment Planner", "MRC"))
    assert "9,054" not in mrc and "1,358" not in mrc
    at = app()
    before = text(at)
    at.selectbox(key="facility").set_value("MRC").run()
    at.selectbox(key="facility").set_value("SYN").run()
    assert not at.exception and text(at) == before
