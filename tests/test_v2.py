"""v2: MRC real-data case study, unit conversions, learning content vs code, and both interface modes / datasets."""
import ast
import importlib
import json
import re
from pathlib import Path

import pytest

from carbon_iq import engine as E
from carbon_iq import learning as LC
from carbon_iq import mrc as M
from carbon_iq.assumptions import P, base_values, gas_price_sar_per_gj

ROOT = Path(__file__).resolve().parents[1]
R = json.load(open(ROOT / "outputs" / "results.json"))


# ------------------------------------------------------------------ MRC import and unit conversions
def test_mrc_reported_values_match_the_data_book():
    """Values verified against the Ma'aden Sustainability Data Book 2025, PDF page 5 (ASI 5.1, MRC column)."""
    expect = dict(electricity_gj=1_040_392, natural_gas_gj=1_104_220, diesel_heating_gj=26_749, gasoline_gj=1_568,
                  scope1_t=63_961, scope2_t=96_671, scope12_t=160_632, energy_total_gj=2_172_929)
    for k, val in expect.items():
        assert M.REPORTED[k].value == val, k
        assert M.REPORTED[k].kind == "reported" and M.REPORTED[k].page == "PDF page 5"
    assert M.v("scope1_t") + M.v("scope2_t") == M.v("scope12_t")
    assert M.energy_check()["difference"] == 0


def test_unit_conversions():
    assert M.gj_to_mwh(3.6) == pytest.approx(1.0)
    assert M.gj_to_mwh(1_040_392) == pytest.approx(288_997.78, abs=0.01)
    assert gas_price_sar_per_gj(2.15) == pytest.approx(2.15 * 3.75 / 1.055056)
    # IPCC factor arithmetic: (CO2 + CH4 x 28 + N2O x 265) kg/TJ -> t/GJ; natural gas equals the register value
    assert M.fuel_factor_t_per_gj("natural_gas_gj") == pytest.approx(P["ef_gas"].value, rel=1e-12)
    assert M.fuel_factor_t_per_gj("diesel_heating_gj") == pytest.approx((74_100 + 3 * 28 + 0.6 * 265) / 1e6)


def test_mrc_scope1_recalculation_and_implied_grid_factor():
    s = M.scope1_recalc()
    assert abs(s["diff_pct"]) < 0.5                          # 64,105 vs 63,961 t
    assert s["total_t"] == pytest.approx(sum(r["activity_gj"] * r["ef_t_per_gj"] for r in s["rows"]))
    g = M.implied_grid_factor()
    assert g["implied_t_per_mwh"] == pytest.approx(96_671 / (1_040_392 / 3.6))
    assert g["implied_t_per_mwh"] < g["national_t_per_mwh"]


def test_no_hypothetical_value_is_labelled_reported():
    for i in M.scenario_defaults():
        assert i.kind in ("hypothetical", "calculated"), i.key
    reg = M.source_register()
    kinds = {r["kind"] for r in reg}
    assert kinds <= {"reported", "calculated", "benchmark", "hypothetical"}
    for r in reg:
        if r["kind"] == "reported":
            assert r["page"].startswith("PDF page") and "Ma'aden" in r["source"], r
        else:
            assert "PDF page 5" not in r["page"] or r["kind"] == "calculated", r


def test_mrc_scenario_uses_the_unchanged_engine():
    # the synthetic model is untouched: project NPVs equal the saved v1.3 run
    prj, _ = E.projects(base_values())
    for p in R["projects"]:
        assert float(prj[p["id"]]["npv"]) == pytest.approx(p["npv"], rel=1e-12)
    p = M.params()
    assert p["elec_mwh"] == pytest.approx(M.gj_to_mwh(M.v("electricity_gj")))
    best, rows = M.portfolios(p)
    assert len(rows) == 16 and best is not None and best["feasible"]
    assert best["npv"] == max(r["npv"] for r in rows if r["feasible"])


def test_mrc_monte_carlo_choice_respects_both_confidence_rules():
    p = M.params()
    mc = M.monte_carlo(p, n=4000)
    for r in mc["rows"]:
        assert 0 <= r["p_target"] <= 1 and 0 <= r["p_budget"] <= 1
    ch = mc["choice"]
    if ch is not None:
        assert ch["p_target"] >= mc["alpha_eff"] and ch["p_budget"] >= mc["beta_eff"] and ch["quoted_capex"] <= p["budget"]


# ------------------------------------------------------------------ learning content matches the code
PART_D = {"ghg", "factors", "dataquality", "montecarlo", "voi", "evpi", "npv", "roi", "irr", "mac", "multicriteria", "portfolio",
          "ptarget", "sensitivity", "timing", "risk", "ranking", "stability", "reconcile", "budget"}


def _exists(path, name):
    f = ROOT / path
    assert f.exists(), path
    if path.startswith("carbon_iq/"):
        mod = importlib.import_module(path[:-3].replace("/", "."))
        obj = mod
        for part in name.split("."):
            obj = getattr(obj, part)
        return True
    tree = ast.parse(f.read_text(encoding="utf-8"))
    return any(isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name for n in ast.walk(tree))


def test_learning_covers_every_part_d_method_with_seven_elements():
    keys = {m["key"] for m in LC.METHODS}
    assert PART_D <= keys
    for m in LC.METHODS:
        for f in ("what", "origin", "why", "how", "example", "code", "judges", "status", "status_note"):
            assert m[f], (m["key"], f)
        assert m["status"] in (LC.STATUS_FULL, LC.STATUS_PART, LC.STATUS_NONE)
        assert all(r in LC.R for r in m["refs"])


def test_every_code_reference_exists():
    for m in LC.METHODS:
        for path, fn, _, _ in m["code"]:
            assert _exists(path, fn), (m["key"], path, fn)


def test_status_claims_match_the_code():
    assert LC.BY_KEY["roi"]["status"] == LC.STATUS_NONE
    # v2.1: single-criterion sorting is not MCDA; no weighted score and no risk register exist in the code
    assert LC.BY_KEY["multicriteria"]["status"] == LC.STATUS_NONE and LC.BY_KEY["ranking"]["status"] == LC.STATUS_FULL
    assert "not MCDA" in LC.BY_KEY["multicriteria"]["status_note"] or "not multi-criteria" in LC.BY_KEY["ranking"]["status_note"]
    assert LC.BY_KEY["risk"]["status"] == LC.STATUS_NONE and LC.BY_KEY["stability"]["status"] == LC.STATUS_FULL
    src = "\n".join(f.read_text(encoding="utf-8") for f in (ROOT / "carbon_iq").glob("*.py") if f.name not in ("learning.py",))
    assert not re.search(r"def\s+\w*roi\w*\s*\(", src, re.I)          # no ROI function exists
    assert not re.search(r"def\s+\w*(weight|mcda|ahp|topsis|risk_register)\w*\s*\(", src, re.I)   # no MCDA / risk register code
    assert LC.BY_KEY["timing"]["status"] == LC.STATUS_PART and "one project" in LC.BY_KEY["timing"]["status_note"]
    assert hasattr(importlib.import_module("carbon_iq.engine"), "irr")


def test_learning_sections_are_concise():
    from carbon_iq.ui.learn_ui import method_markdown
    for m in LC.METHODS:
        txt = " ".join(method_markdown(m)[i] for i in (0, 2, 3, 4, 6))      # what, why, how, example, judges
        assert len(txt.split()) <= 300, (m["key"], len(txt.split()))


def test_references_are_well_formed():
    for k, (text, url) in LC.R.items():
        assert len(text) > 20
        assert url == "" or re.match(r"https://[\w.-]+/\S+$", url), (k, url)
        if url == "":
            assert "no free link" in text or "supplied by the user" in text, k


# ------------------------------------------------------------------ interface: v3 tests are in tests/test_app_v3.py
DSETS = ["Synthetic Saudi metal-fabrication plant", "Ma'aden Rolling Company (MRC) – 2025 reported data"]


def _run(mode, ds, page):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=600)
    at.session_state["mode"] = mode
    at.session_state["dataset"] = ds
    at.session_state["nav"] = page
    return at.run()


def _text(at):
    parts = [m.value for m in at.markdown] + [f"{m.value} {m.delta}" for m in at.metric] + [x.value for x in at.success]
    parts += [x.value for x in at.warning] + [x.value for x in at.error] + [x.value for x in at.caption]
    return "\n".join(parts)


def test_every_method_has_example_code_reference_and_20_second_script():
    from carbon_iq.ui.learn_ui import code_of
    for m in LC.METHODS:
        assert m["example"] and m["refs"] and m["code"], m["key"]
        assert 40 <= len(m["judges"].split()) <= 75, (m["key"], len(m["judges"].split()))   # about 20 seconds at ~150 words/min
        src = code_of(m["code"][0][0], m["code"][0][1])
        assert ("def " in src or "class " in src) and m["code"][0][1].split(".")[-1] in src, m["key"]


def test_scope1_reconciliation_explains_the_gap():
    r = M.scope1_reconciliation()
    assert r["co2_only"] + r["non_co2"] == pytest.approx(r["recalculated"])
    assert r["diff_t"] == pytest.approx(r["recalculated"] - 63_961) and 140 < r["diff_t"] < 150
    assert r["diff_share_of_u95"] < 0.1                                   # well inside the uncertainty
    assert abs(r["ar4"] - r["recalculated"]) < 5 and abs(r["ar6"] - r["recalculated"]) < 5   # GWP choice is not the cause
    assert 54_300 < r["gas_factor_to_close"] < 58_300                      # closing factor inside the IPCC range
    assert r["co2_range"][0] < 63_961 < r["co2_range"][1]
    assert r["if_gross_cv"] < 0.95 * 63_961                               # gross-CV reading would not match


def test_implied_grid_factor_is_labelled_derived_not_verified():
    rows = M.grid_factor_comparison()
    implied, national, verified = rows
    assert implied["kind"] == "calculated" and implied["verified"].startswith("No")
    assert "Not a utility" in national["verified"]
    assert verified["value"] is None and "Not available" in verified["verified"]


def test_budget_is_never_raised_and_infeasibility_is_explained():
    p = M.params({"budget": 40e6})
    mc = M.monte_carlo(p, n=5000)
    f = M.budget_feasibility(p, mc)
    assert p["budget"] == 40e6 and mc["budget"] == 40e6 and f["budget"] == 40e6        # unchanged
    assert f["det_best"] is None and f["det_min_budget"] > 40e6
    assert mc["choice"] is None and mc["min_budget"]["budget_needed"] > 40e6
    q = M.params({"target_share": 0.20})
    g = M.budget_feasibility(q, M.monte_carlo(q, n=2000))
    assert g["det_min_budget"] is None and g["det_max_cut"] < M.target_t(q) and g["cc_min_budget"] is None


def test_knife_edge_is_flagged_for_the_default_mrc_scenario():
    p = M.params()
    f = M.budget_feasibility(p, M.monte_carlo(p, n=20000))
    ch = f["cc_choice"]
    assert ch is not None and ch["budget_needed"] <= p["budget"]
    assert f["knife_edge"] == (abs(ch["budget_margin_se"]) < 2)


