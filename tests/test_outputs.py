"""Workbook agreement with the Python engine, reproducibility and the Streamlit app."""
import json
import shutil
from pathlib import Path

import openpyxl
import pytest

from carbon_iq import engine as E
from carbon_iq import optimize as O
from carbon_iq import timing as TM
from carbon_iq.assumptions import v
from carbon_iq.recalc import recalc

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "Mezan_Data_Model.xlsx"


@pytest.fixture(scope="module")
def wb(tmp_path_factory):
    if not XLSX.exists():
        pytest.skip("run run_all.py first")
    out = tmp_path_factory.mktemp("x") / "m.xlsx"
    shutil.copy(XLSX, out)
    res = recalc(out)                      # portable LibreOffice recalculation (carbon_iq/recalc.py)
    if res["status"] == "skipped":
        pytest.skip("LibreOffice not installed, so the live Excel formulas cannot be evaluated here. In Colab run "
                    "'!apt-get install -y -qq libreoffice-calc' first; locally install LibreOffice or open the file in Excel")
    assert res["status"] == "success" and res["total_errors"] == 0, res
    return openpyxl.load_workbook(out, data_only=True)


def test_workbook_sheets(wb):
    for s in ("README", "Facility Profile", "Production & Operations", "Electricity & Fuel", "Suppliers & Logistics",
              "Emission Factors", "Baseline Emissions", "Data Quality", "Investment Alternatives", "Financials & Cash Flows",
              "Optimization", "Monte Carlo", "Decision Objectives", "Value of Information", "Sensitivity", "Investment Timing", "Dashboard"):
        assert s in wb.sheetnames


def test_excel_matches_python(wb):
    t = E.scope_totals(E.baseline())
    b = wb["Baseline Emissions"]
    assert b["G15"].value == pytest.approx(t["Scope 1+2"]) and b["G16"].value == pytest.approx(t["Total"])
    assert b["G17"].value == pytest.approx(E.target_t())
    _, tot = E.uncertainty_table()
    assert wb["Data Quality"]["F15"].value == pytest.approx(tot["Scope 1+2"][1], rel=1e-4)   # inputs rounded to 4 dp
    prj, inter = E.projects()
    best, _ = O.enumerate_best(prj, inter, v("budget"), E.target_t())
    o = wb["Optimization"]
    assert o["H4"].value == best["portfolio"] and o["H5"].value == pytest.approx(best["npv"])
    f = wb["Financials & Cash Flows"]
    npvs = {r[0].value[0]: r[3].value for r in f.iter_rows(min_row=1, max_row=40)
            if isinstance(r[0].value, str) and len(r[0].value) > 2 and r[0].value[1] == " " and r[0].value[0] in "ABCDEF"}
    for k, d in prj.items():
        assert npvs[k] == pytest.approx(float(d["npv"]))
    cf_npv = {r[0].value: r[27].value for r in f.iter_rows(min_row=1, max_row=60) if r[0].value in tuple("ABCDEF") and r[27].value is not None}
    for k, d in prj.items():
        assert cf_npv[k] == pytest.approx(float(d["npv"]), abs=1e-3)    # Excel NPV() on yearly cash flows
    d = wb["Dashboard"]
    vals = {r[0].value: r[1].value for r in d.iter_rows(min_row=4, max_row=25)}
    tr = TM.decision_tree()
    assert vals["Decision tree"] == tr["decision"]
    assert vals["Static break-even gas price (USD/MMBtu)"] == pytest.approx(tr["static_breakeven_usd"])
    assert vals["GBM trigger (USD/MMBtu)"] == pytest.approx(TM.gbm_trigger()["trigger_usd"])
    obj = wb["Decision Objectives"]
    assert obj["A6"].value == "D1" and obj["D6"].value == best["portfolio"] and obj["F6"].value == pytest.approx(best["npv"])
    for r in range(6, 13):
        if obj[f"D{r}"].value != "none feasible":
            assert obj[f"E{r}"].value <= v("budget")
        else:
            assert obj[f"E{r}"].value == "n/a"
    voi = wb["Value of Information"]
    rows = [r for r in range(1, voi.max_row + 1) if str(voi.cell(r, 1).value or "").startswith("Motor-system savings")]
    assert rows and voi.cell(rows[0], 3).value == pytest.approx(v("cost_motor_audit"))


def test_outputs_reproducible(tmp_path):
    from carbon_iq import pipeline
    a, _ = pipeline.run(n=3000, timing_detail=False)
    b, _ = pipeline.run(n=3000, timing_detail=False)
    ka = json.dumps({k: a[k] for k in ("mc_portfolios", "voi", "evpi", "optimal")}, default=str, sort_keys=True)
    kb = json.dumps({k: b[k] for k in ("mc_portfolios", "voi", "evpi", "optimal")}, default=str, sort_keys=True)
    assert ka == kb


def test_streamlit_app_runs():
    """v3: one application, six workspaces; the scenario settings drawer reruns only on 'Run analysis'."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=240)
    at.session_state["nav"] = "Investment Planner"
    at.run()
    assert not at.exception
    at.number_input(key="set_budget_m").set_value(4.0).run()
    at.button(key="run_analysis").click().run()
    assert not at.exception
    for basis in ("physical", "baseline"):                           # sensitivity bases
        at.selectbox(key="set_basis").set_value(basis).run()
        at.button(key="run_analysis").click().run()
        assert not at.exception
    at.session_state["nav"] = "Reports & Evidence"
    at.run()
    assert not at.exception
    cols = [c for d in at.dataframe for c in d.value.columns]
    assert "Evidence" in cols and "Source / rationale" in cols
