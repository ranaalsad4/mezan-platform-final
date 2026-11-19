"""Phase B3 impact scorecard: Mezan_Phase_B_Impact_Scorecard.xlsx + outputs/phase_b/scorecard_metrics.json.

No new calculation: every metric is read from the validated run outputs (outputs/results.json, outputs/a4, outputs/a6) by an
explicit path, re-read for the trace check, and labelled with unit, basis, evidence type and limitation. Ratios that are
shown (e.g. reduction as % of the baseline) are spreadsheet formulas on those values.
    python tools/build_phase_b.py
"""
import json
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as CL

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
O = HERE / "outputs"
OUT = O / "phase_b"
OUT.mkdir(exist_ok=True)
SRC = {"results.json": json.load(open(O / "results.json")), "a6_results.json": json.load(open(O / "a6" / "a6_results.json")),
       "a4_results.json": json.load(open(O / "a4" / "a4_results.json"))}
A4V = pd.read_csv(O / "a4" / "information_value.csv")
CASES = pd.read_csv(O / "a4" / "decision_comparison.csv").set_index("case")


def get(src, path):
    """Follow a path through nested JSON; a dict step {key: value} selects the list item with item[key] == value."""
    x = SRC[src]
    for step in path:
        if isinstance(step, dict):
            (k, v), = step.items()
            x = next(i for i in x if i.get(k) == v)
        else:
            x = x[step]
    return x


def ptxt(src, path):
    return src + ":" + "/".join(f"[{list(s)[0]}={list(s.values())[0]}]" if isinstance(s, dict) else str(s) for s in path)


R = SRC["results.json"]
D4 = get("results.json", ["decision_scenarios", {"id": "D4"}])
PORT = D4["portfolio"]
MCP = ["mc_portfolios", {"portfolio": PORT}]
MOD, SYN = "modelled (synthetic facility)", "modelled (synthetic facility); probability from 200,000 validation scenarios"
M = [  # id, group, metric, unit, source, path, evidence, basis/limitation
    ("S1", "Baseline", "Scope 1+2 baseline emissions", "tCO2e/yr", "results.json", ["scope_totals", "Scope 1+2"], MOD,
     "Synthetic activity data x Saudi grid factor 0.573 (BTR1/GASTAT 2021), IPCC fuel factors. Not a verified inventory"),
    ("S2", "Baseline", "Reduction target (15% of Scope 1+2)", "tCO2e/yr", "results.json", ["target_t"], "case definition (hypothetical)",
     "Management target assumed for the case"),
    ("S3", "Baseline", "Capital budget", "SAR", "results.json", ["meta", "budget"], "case definition (hypothetical)", "—"),
    ("R1", "Recommendation", "Recommended portfolio (primary rule D4)", "—", "results.json", ["decision_scenarios", {"id": "D4"}, "portfolio"], MOD,
     "Maximise expected NPV with P(target) >= 90% and P(actual capex <= budget) >= 90% (sampling-tightened, validated)"),
    ("I1", "Carbon", "Annual Scope 1+2 reduction, year 1, base inputs", "tCO2e/yr", "results.json", ["optimal", "scope12_t"], MOD,
     "Deterministic, overlap between B and C removed once; PV output declines 0.5%/yr after year 1. Same portfolio as D4 (checked)"),
    ("I2", "Carbon", "Expected Scope 1+2 reduction (Monte Carlo mean)", "tCO2e/yr", "results.json", MCP + ["e_t12"], MOD,
     "Mean over 20,000 scenarios, reporting factors; above I1 because B's savings range is skewed above its base value"),
    ("I3", "Carbon", "5th-percentile Scope 1+2 reduction", "tCO2e/yr", "results.json", MCP + ["p5_t12"], MOD, "95% of scenarios reduce at least this much"),
    ("P1", "Risk", "Probability of meeting the carbon target", "probability", "results.json", MCP + ["p_target_val"], SYN, "Fixed reporting factors and baseline (A1-02)"),
    ("P2", "Risk", "Probability that actual capex stays within the budget", "probability", "results.json", MCP + ["p_budget_val"], SYN,
     "Each project's capex normal, s.d. 15% of the quote, independent (no correlated overruns)"),
    ("C1", "Investment", "Quoted capital investment", "SAR", "results.json", ["decision_scenarios", {"id": "D4"}, "capex_quote"], MOD,
     "Solar from a Riyadh benchmark (SAR 2.5/W); B and C hypothetical; no supplier quotations"),
    ("C2", "Investment", "90th-percentile actual capex", "SAR", "results.json", MCP + ["p90_capex"], MOD, "Contingency view"),
    ("F1", "Financial", "NPV at base inputs (real, 6%)", "SAR", "results.json", ["decision_scenarios", {"id": "D4"}, "npv_base_inputs"], MOD,
     "Most-likely inputs; tariff 0.18 SAR/kWh; no tax, inflation or financing"),
    ("F2", "Financial", "Expected NPV (Monte Carlo)", "SAR", "results.json", ["decision_scenarios", {"id": "D4"}, "e_npv"], MOD,
     "Mean over scenarios; higher than F1 because the tariff range is skewed upwards (A1-24). F1 and F2 are two views of the same "
     "benefit: never add them"),
    ("F3", "Financial", "5th-percentile NPV", "SAR", "results.json", MCP + ["p5_npv"], MOD, "Downside"),
    ("F4", "Financial", "Probability of a negative NPV", "probability", "results.json", MCP + ["p_loss"], MOD, "In-sample, 20,000 scenarios"),
    ("F5", "Financial", "IRR of solar PV (A)", "per year", "results.json", ["projects", {"id": "A"}, "irr"], MOD, "With 0.5%/yr degradation (A6 fix)"),
    ("F6", "Financial", "IRR of motors + VSDs (B)", "per year", "results.json", ["projects", {"id": "B"}, "irr"], MOD, "—"),
    ("F7", "Financial", "IRR of compressed-air repair (C)", "per year", "results.json", ["projects", {"id": "C"}, "irr"], MOD, "Marginal project (A5-10)"),
    ("F8", "Financial", "Abatement cost of A (negative = saves money)", "SAR/tCO2e", "results.json", ["projects", {"id": "A"}, "mac_sar_per_t"], MOD, "—"),
    ("F9", "Financial", "Abatement cost of B", "SAR/tCO2e", "results.json", ["projects", {"id": "B"}, "mac_sar_per_t"], MOD, "—"),
    ("F10", "Financial", "Abatement cost of C", "SAR/tCO2e", "results.json", ["projects", {"id": "C"}, "mac_sar_per_t"], MOD, "—"),
    ("V1", "Information", "Value of perfect information on all inputs (EVPI)", "SAR", "results.json", ["evpi"], MOD,
     "Upper limit of what any study is worth; A6: lower bound under a chance-constrained reading (alternative below)"),
    ("V2", "Information", "EVPI keeping the 90% carbon requirement (A6 alternative)", "SAR", "a6_results.json", ["voi", "evpi_chance_constraint_kept"], MOD, "—"),
    ("V3", "Information", "Value of compressed-air sub-metering (EVPPI)", "SAR", "results.json", ["voi", {"parameter": "c_saving_frac"}, "evppi_sar"], MOD,
     "Only measurement that can change the portfolio (A+B+C vs A+B)"),
    ("V4", "Information", "Assumed cost of compressed-air sub-metering", "SAR", "results.json", ["voi", {"parameter": "c_saving_frac"}, "collection_cost_sar"],
     "hypothetical", "Assumption, not a quotation"),
    ("V5", "Information", "Value of the motor-system audit (EVSI)", "SAR", "results.json", ["evsi_audit", "evsi"], MOD, "Cannot change the decision"),
    ("V6", "Information", "Value of collecting the missing monthly records (best measurement, any rule)", "SAR", "a4", None, MOD,
     "Pre-posterior value, A4 demo; zero: no missing record can change the decision"),
    ("Q1", "Data quality", "Scope 1+2 if missing months were counted as zero", "tCO2e/yr", "a4c", "C3", MOD, "Common practice that Mezan refuses"),
    ("Q2", "Data quality", "Scope 1+2 with complete records (synthetic truth)", "tCO2e/yr", "a4c", "C0", MOD, "—"),
]
rows = []
for mid, grp, name, unit, src, path, ev, basis in M:
    if src == "a4":
        val = float(A4V.value_npv.max()); tr = float(pd.read_csv(O / "a4" / "information_value.csv").value_npv.max()); where = "a4/information_value.csv:max(value_npv)"
    elif src == "a4c":
        val = float(CASES.loc[path, "scope12"]); tr = float(pd.read_csv(O / "a4" / "decision_comparison.csv").set_index("case").loc[path, "scope12"])
        where = f"a4/decision_comparison.csv:[case={path}]/scope12"
    else:
        val = get(src, path); tr = get(src, path); where = ptxt(src, path)
    rows.append(dict(id=mid, group=grp, metric=name, value=val, unit=unit, evidence=ev, basis_limitation=basis, source=where,
                     traced_value=tr))
chk = get("results.json", ["optimal", "portfolio"]) == PORT
json.dump([r for r in rows if isinstance(r["value"], (int, float))], open(OUT / "scorecard_metrics.json", "w"), indent=1)

# ------------------------------------------------------------------ comparison with traditional selection
mc = {m["portfolio"]: m for m in R["mc_portfolios"]}
comp = []
for b in R["baselines"]:
    m = mc[b["portfolio"]]
    comp.append(dict(method=b["method"], rule="Fund projects one by one in this order while the quoted budget allows (no uncertainty)",
                     portfolio=b["portfolio"], quoted_capex=b["capex"], npv_base=b["npv"], reduction_t=b["scope12_t"], meets_target_base=b["meets_target"],
                     e_npv=m["e_npv"], p_target=m["p_target_val"], p_budget=m["p_budget_val"], p_loss=m["p_loss"]))
comp.append(dict(method="Mezan primary rule D4", rule="Max expected NPV s.t. P(target) >= 90% and P(actual capex <= budget) >= 90%",
                 portfolio=PORT, quoted_capex=D4["capex_quote"], npv_base=D4["npv_base_inputs"], reduction_t=R["optimal"]["scope12_t"] if chk else None,
                 meets_target_base=D4["meets_target_base_inputs"], e_npv=D4["e_npv"], p_target=D4["p_target_val"], p_budget=D4["p_budget_val"],
                 p_loss=mc[PORT]["p_loss"]))
comp = pd.DataFrame(comp)

# ------------------------------------------------------------------ sensitivity
sens = []
for key, col, lab in (("tariff_scenarios", "tariff", "Industrial tariff (SAR/kWh)"), ("pv_capex_scenarios", "pv_capex_kw", "Rooftop PV cost (SAR/kWp)"),
                      ("gas_scenarios", "gas_price_usd", "Methane price (USD/MMBtu)"), ("ef_scenarios", "ef_grid", "Grid factor (tCO2e/MWh)")):
    for s in R[key]:
        sens.append(dict(input=lab, scenario=f"{s['id']} {s['label']}", value=s[col], D1=s["deterministic"], D1_npv=s["det_npv"],
                         D4=s["joint"], D4_e_npv=s.get("joint_e_npv"), min_budget_D4=s.get("joint_min_budget")))
for d in R["discount_robustness"]:
    sens.append(dict(input="Real discount rate", scenario=f"{d['rate']:.0%}", value=d["rate"], D1=d["with_target"], D1_npv=d["npv_with_target"],
                     D4=None, D4_e_npv=None, min_budget_D4=None))
sens = pd.DataFrame(sens)
sw = pd.DataFrame([dict(input=k, tested_range=f"{v['range'][0]:.4g} – {v['range'][1]:.4g}", robust=v["robust"],
                        changes="; ".join(f"at {a:.4g}: {b} -> {c}" for a, b, c in v["changes"]) or "none") for k, v in R["switch_points"].items()])
gs = pd.read_csv(O / "a6" / "a6_gsa_sobol.csv")
gs = gs.sort_values(["output", "ST"], ascending=[True, False]).groupby("output").head(5)

# ------------------------------------------------------------------ key assumptions
reg = pd.read_csv(O / "assumptions.csv")
keys = ["tariff", "gas_price_usd", "diesel_price", "discount_rate", "ef_grid", "ef_gas", "ef_diesel", "pv_capex_kw", "pv_yield", "pv_degradation",
        "b_capex", "b_saving_frac", "c_capex", "c_saving_frac", "c_om", "elec_mwh", "gas_gj", "budget", "target_share", "chance_level"]
assum = reg.set_index("key").loc[keys, ["value", "unit", "evidence", "status", "dist", "published", "url"]].reset_index()

LIM = [
    "The facility is hypothetical: activity data are synthetic; no factory has used Mezan (no deployment, customers or verified savings).",
    "All impacts are modelled. NPV and expected NPV are two views of the same benefit and must not be added; project NPVs must not be added "
    "to the portfolio NPV (the B-C overlap is removed only at portfolio level).",
    "Costs other than solar are hypothetical (no supplier quotations); the solar cost is one public benchmark (A5-04).",
    "The 2027 industrial tariff rates were not retrieved (A5-01); the 2026 methane price is unconfirmed (A5-02).",
    "Validation is mathematical (Phase A6) and on synthetic data; there is no validation on real industrial records (A4-01).",
    "Inputs are sampled independently; correlated risks (price reforms, cost overruns) are not represented (A6-07).",
    "Scope 1 refrigerants and Scope 3 Category 3 are not inventoried (A5-05, A5-06).",
    "The package has not been run on real Google Colab (A1-01).",
]

# ------------------------------------------------------------------ workbook
HDR = PatternFill("solid", fgColor="1F4E46"); NOTE = Font(italic=True, color="555555")
wb = Workbook()
ws = wb.active; ws.title = "README"
txt = [f"Mezan Phase B3 impact scorecard (model v{R['meta']['model_version']}; 20,000 scenarios, seed {R['meta']['seed']}; validation 200,000)",
       "SYNTHETIC CASE: a hypothetical Riyadh metal-fabrication plant. All impacts are MODELLED, not verified savings.",
       "Every value is read from the validated run outputs; the 'source' column gives the file and path; the trace check re-reads it.",
       "Sheets: Scorecard | Comparison (traditional ranking vs Mezan) | Sensitivity | Switch points | Sobol (A6) | Key assumptions | Limitations",
       "Do not add metrics that measure the same benefit (NPV and expected NPV; project and portfolio NPVs; deterministic and expected reductions).",
       "Regenerate: python run_all.py && python tools/run_a6.py && python tools/build_phase_b.py"]
for i, t in enumerate(txt, start=1):
    ws.cell(i, 1, t).font = Font(bold=(i <= 2))
ws.column_dimensions["A"].width = 140


def sheet(name, df, widths=None, note=None):
    w = wb.create_sheet(name)
    r0 = 1
    if note:
        w.cell(1, 1, note).font = NOTE; r0 = 3
    for j, c in enumerate(df.columns, start=1):
        cell = w.cell(r0, j, c); cell.font = Font(bold=True, color="FFFFFF"); cell.fill = HDR; cell.alignment = Alignment(wrap_text=True)
    for i, row in enumerate(df.itertuples(index=False), start=r0 + 1):
        for j, v in enumerate(row, start=1):
            v = None if (isinstance(v, float) and pd.isna(v)) else v
            c = w.cell(i, j, v); c.alignment = Alignment(wrap_text=True, vertical="top")
            if isinstance(v, float):
                c.number_format = "0.000%" if df.columns[j - 1] in ("p_target", "p_budget", "p_loss") else "#,##0.00"
    for j in range(1, len(df.columns) + 1):
        w.column_dimensions[CL(j)].width = (widths or {}).get(j, 18)
    w.freeze_panes = w.cell(r0 + 1, 1)
    return w, r0


sc_df = pd.DataFrame(rows)[["id", "group", "metric", "value", "unit", "evidence", "basis_limitation", "source", "traced_value"]]
w, r0 = sheet("Scorecard", sc_df, {1: 6, 2: 13, 3: 48, 4: 16, 5: 12, 6: 30, 7: 60, 8: 52, 9: 14},
              note="Green formulas below the table derive ratios from the listed values. Trace check: column I re-reads the source path.")
last = r0 + len(sc_df)
idx = {r["id"]: r0 + 1 + i for i, r in enumerate(rows)}
f = last + 2
w.cell(f, 3, "Derived (spreadsheet formulas)").font = Font(bold=True)
der = [("Reduction as % of Scope 1+2 baseline", f"=D{idx['I1']}/D{idx['S1']}", "0.0%"),
       ("Reduction vs target (ratio)", f"=D{idx['I1']}/D{idx['S2']}", "0.00"),
       ("Budget headroom at quoted capex (SAR)", f"=D{idx['S3']}-D{idx['C1']}", "#,##0"),
       ("Net value of sub-metering (EVPPI - assumed cost, SAR)", f"=D{idx['V3']}-D{idx['V4']}", "#,##0"),
       ("Error in Scope 1+2 if missing months were counted as zero", f"=D{idx['Q1']}/D{idx['Q2']}-1", "0.0%"),
       ("All trace checks pass", f"=AND(J{r0 + 1}:J{last})", "General")]
w.cell(r0, 10, "trace ok").font = Font(bold=True, color="FFFFFF"); w.cell(r0, 10).fill = HDR
for i in range(r0 + 1, last + 1):
    w.cell(i, 10, f"=IF(ISNUMBER(D{i}),ABS(D{i}-I{i})<=1E-9*MAX(1,ABS(I{i})),D{i}=I{i})")
for i, (lab, form, fmt) in enumerate(der, start=f + 1):
    w.cell(i, 3, lab); c = w.cell(i, 4, form); c.number_format = fmt; c.font = Font(color="1F7A3A", bold=True)
for rid, rr in idx.items():
    unit = rows[list(idx).index(rid)]["unit"]
    for col in (4, 9):
        cell = w.cell(rr, col)
        if isinstance(cell.value, (int, float)):
            cell.number_format = ("0.000%" if unit == "probability" else "0.00%") if unit in ("probability", "per year") else "#,##0.0"
sheet("Comparison", comp, {1: 34, 2: 44, 3: 14, 4: 14, 5: 14, 6: 12, 7: 12, 8: 14, 9: 11, 10: 11, 11: 11},
      note=("Traditional baseline = fund projects one at a time in a ranking order while the quoted budget allows (no uncertainty). "
            "Probabilities from 200,000 validation scenarios. Ranking by NPV gives the same portfolio as Mezan in this case."))
sheet("Sensitivity", sens, {1: 28, 2: 46, 3: 10, 4: 12, 5: 14, 6: 14, 7: 14, 8: 14},
      note="Each scenario reruns the full analysis with one input fixed. D4 = primary rule; 'none feasible' = no portfolio meets both 90% requirements.")
sheet("Switch points", sw, {1: 18, 2: 22, 3: 9, 4: 60}, note="Deterministic optimum, one input varied over its uncertainty range.")
sheet("Sobol (A6)", gs, {1: 36, 2: 20, 3: 10, 4: 10}, note="Variance-based indices (A6): S1 first order, ST total effect; top five inputs per output.")
sheet("Key assumptions", assum, {1: 18, 2: 12, 3: 18, 4: 12, 5: 12, 6: 28, 7: 26, 8: 50}, note="Full register: outputs/a5/Mezan_A5_Source_Register.xlsx")
sheet("Limitations", pd.DataFrame({"limitation": LIM}), {1: 140})
p = OUT / "Mezan_Phase_B_Impact_Scorecard.xlsx"
wb.save(p)
from carbon_iq.recalc import recalc  # noqa: E402
info = recalc(p)
import openpyxl  # noqa: E402
v = openpyxl.load_workbook(p, data_only=True)["Scorecard"]
derived = {v.cell(i, 3).value: v.cell(i, 4).value for i in range(f + 1, f + 1 + len(der))}
json.dump(dict(recalc=info, derived=derived, portfolio=PORT, optimal_equals_d4=chk, comparison=comp.to_dict("records")),
          open(OUT / "scorecard_check.json", "w"), indent=1, default=str)
print(json.dumps(dict(recalc=info["status"], formulas=info["total_formulas"], errors=info["total_errors"], derived=derived), indent=1, default=str))
