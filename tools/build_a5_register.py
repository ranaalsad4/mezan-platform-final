"""A5 deliverables built from the live register and pipeline outputs (no numbers typed by hand):
  outputs/a5/Mezan_A5_Source_Register.xlsx  - source and assumption register with v1.2 -> v1.3 changes, scenarios,
                                                  GHG boundary review, financial-formula checks and evidence gaps
  outputs/a5/Mezan_A5_Before_After.xlsx     - before/after numerical comparison (projects, portfolios, decisions,
                                                  attribution, scenarios)
  outputs/a5/a5_summary.json                    - the same numbers for the report
Run after run_all.py:  python tools/build_a5_register.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from carbon_iq import assumptions as A  # noqa: E402
from carbon_iq import engine as E  # noqa: E402

OUT = HERE / "outputs"
A5 = OUT / "a5"
A5.mkdir(exist_ok=True)

# ------------------------------------------------------------------ 1. register with v1.2 comparison
with A.use_profile("v1.2"):
    P12 = dict(A.P)
rows = []
for k, p in A.P.items():
    o = P12[k]
    changed = (o.value != p.value) or (o.dist != p.dist) or (o.status != p.status)
    rows.append(dict(key=k, group=p.group, value_v13=p.value, unit=p.unit, value_v12=o.value,
                     changed_in_A5="yes" if changed else "", change=A.A5_CHANGE_LABELS.get(k, ""),
                     evidence_class=p.evidence, quality_status=p.status, status_v12=o.status,
                     uncertainty_v13=str(p.dist) if p.dist else "fixed (scenario or sensitivity only)",
                     uncertainty_v12=str(o.dist) if o.dist else "fixed",
                     source=p.source, note=p.note, published=p.published, effective=p.effective, geography=p.geography, url=p.url))
reg = pd.DataFrame(rows)

# ------------------------------------------------------------------ 2. scenarios
scen = []
for s in A.TARIFF_SCENARIOS:
    scen.append(dict(input="Industrial electricity tariff (SAR/kWh)", id=s["id"], value=s["value"], label=s["label"],
                     status=s["status"], effective=s.get("effective", ""), url=s.get("url", "")))
for s in A.GAS_SCENARIOS:
    scen.append(dict(input="Industrial methane price (USD/MMBtu)", id=s["id"], value=s["value"], label=s["label"],
                     status=s["status"], effective=s["effective"], url=s["url"]))
for s in A.PV_CAPEX_SCENARIOS:
    scen.append(dict(input="Rooftop PV capital cost (SAR/kWp)", id=s["id"], value=s["value"], label=s["label"],
                     status="benchmark" if s["id"] == "P0" else "v1.2 assumption", effective="", url=s["url"]))
for s in A.EF_GRID_SCENARIOS:
    scen.append(dict(input="Grid emission factor (tCO2e/MWh)", id=s["id"], value=s["value"], label=s["label"],
                     status=s.get("status", ""), effective=s.get("effective", ""), url=s.get("url", "")))
scen = pd.DataFrame(scen)
gev = pd.DataFrame(A.EF_GRID_EVIDENCE)

# ------------------------------------------------------------------ 3. GHG boundary review (GHG Protocol Corporate Standard,
# Scope 2 Guidance 2015, Scope 3 Standard 2011). Statements describe this model; "gap" rows are not in the inventory.
p = A.base_values()
base = E.baseline(p)
t_and_d_proxy = (0.682 - p["ef_grid"]) * p["elec_mwh"]
BOUND = [
    ("Scope 1", "Stationary combustion: natural gas (furnaces, process heat)", "Included", "S1-GAS",
     "IPCC 2006 default CO2/CH4/N2O factors on net calorific value, AR5 GWP (consistent with the KSA BTR1 inventory)"),
    ("Scope 1", "Stationary combustion: diesel backup generators", "Included", "S1-DSL-GEN", "Same diesel factor as forklifts"),
    ("Scope 1", "Mobile combustion: diesel forklifts (company-owned)", "Included", "S1-DSL-FL",
     "Owned/operated equipment is Scope 1 under the operational-control approach"),
    ("Scope 1", "Fugitive: refrigerants (HFCs in air-conditioning and chillers)", "GAP - not inventoried", "",
     "Usually material in Riyadh because of air-conditioning load; needs refrigerant top-up records (A5-05)"),
    ("Scope 1", "Process emissions (non-combustion)", "Not applicable to the case", "",
     "Metal fabrication and assembly with no smelting or chemical process (case definition); re-check for a real plant"),
    ("Scope 2", "Purchased grid electricity, location-based", "Included", "S2-ELEC",
     "Generation-based national average 0.573 tCO2e/MWh (BTR1 2021 / GASTAT 2021). GHG Protocol Scope 2 Guidance: location-based "
     "uses grid-average generation factors; T&D losses of the consumer belong to Scope 3 Cat 3"),
    ("Scope 2", "Purchased grid electricity, market-based", "Reported equal to location-based",
     "", "No contractual instruments (I-RECs, PPAs, supplier-specific factors) held by the case plant and no published Saudi residual "
     "mix; the Scope 2 Guidance then allows the grid-average factor. A Saudi I-REC issuer exists; no redemption assumed"),
    ("Scope 2", "On-site rooftop PV (project A)", "Reduces purchased electricity", "",
     "Self-consumed on-site generation is not purchased, so it lowers Scope 2 directly; no certificates are claimed. "
     "Self-consumption vs. load profile not yet checked (A1-19)"),
    ("Scope 3 Cat 1", "Purchased steel (cradle-to-gate)", "Included (crude-steel proxy)", "S3-C1-STEEL",
     "worldsteel crude-steel intensity excludes rolling/finishing; a product-level EPD factor would be higher (A5-07)"),
    ("Scope 3 Cat 3", "Fuel- and energy-related activities: grid T&D losses and upstream fuel", "GAP - not inventoried", "",
     f"Indicative size of the T&D/own-use part only: (0.682 - 0.573) x {p['elec_mwh']:,.0f} MWh = {t_and_d_proxy:,.0f} tCO2e "
     "(derived from the same BTR1/GASTAT data; upper bound because own use of power plants is included). Not added to totals"),
    ("Scope 3 Cat 4", "Upstream transport (inbound road freight)", "Included (UK proxy factor)", "S3-C4-FRT",
     "DESNZ 2025 HGV average-laden factor; Saudi fleet load factor unknown (A1-20)"),
    ("Target", "Scope 1+2 reduction target", "Scope 1+2 only", "",
     "Project F (Scope 3) is excluded from the target count; Scope 3 changes are reported separately"),
    ("Year", "Base year and reduction year", "Year-1 reductions", "",
     "Reductions are year-1 values; PV output declines 0.5%/yr after year 1 (v1.3), so later-year reductions are lower"),
]
bound = pd.DataFrame(BOUND, columns=["scope", "source category", "treatment", "inventory row", "basis / comment"])

# ------------------------------------------------------------------ 4. financial-formula checks (independent recomputation)
prj, inter = E.projects(p)
r = p["discount_rate"]
chk = []


def explicit_npv(capex, flows):
    return -capex + sum(cf / (1 + r) ** t for t, cf in enumerate(flows, start=1))


# A: year-by-year with degradation
a_mwh = p["pv_kwp"] * p["pv_yield"] / 1000
a_flows = [a_mwh * (1 - p["pv_degradation"]) ** (t - 1) * p["tariff"] * 1000 - p["pv_om_frac"] * prj["A"]["capex"]
           for t in range(1, int(p["pv_life"]) + 1)]
chk.append(("A NPV, explicit year-by-year with 0.5%/yr degradation", explicit_npv(prj["A"]["capex"], a_flows), prj["A"]["npv"]))
for k in "BCDEF":
    flows = [prj[k]["annual_cf"]] * int(prj[k]["life"])
    chk.append((f"{k} NPV, explicit discounting", explicit_npv(prj[k]["capex"], flows), prj[k]["npv"]))
# MAC = -NPV / discounted tonnes
a_t = [prj["A"]["scope12_t"] * (1 - p["pv_degradation"]) ** (t - 1) / (1 + r) ** t for t in range(1, int(p["pv_life"]) + 1)]
chk.append(("A MAC = -NPV / discounted lifetime tonnes", -prj["A"]["npv"] / sum(a_t), E.mac(prj["A"])))
for k in "BCDE":
    eac = -prj[k]["npv"] / prj[k]["af"]
    chk.append((f"{k} MAC = equivalent annual cost / annual tonnes", eac / prj[k]["scope12_t"], E.mac(prj[k])))
# B-C overlap: ledger vs portfolio
for sel in (("B", "C"), ("A", "B", "C"), ("A", "B", "C", "D", "E")):
    led = E.ledger(sel, p)["scope12_t"]
    s12 = E.scope_totals(base)["Scope 1+2"]
    chk.append((f"Reduction {'+'.join(sel)}: ledger (activities recomputed) vs portfolio (overlap removed)", s12 - led,
                E.portfolio(sel, prj, inter)["scope12_t"]))
# overlap NPV: B and C together = explicit cash flows on the shared ledger
tariff_mwh = p["tariff"] * 1000
comp = p["elec_mwh"] * p["compressed_air_share"]
motor = p["elec_mwh"] * p["motor_share"]
bc = []
for t in range(1, int(max(p["b_life"], p["c_life"])) + 1):
    c_on = t <= p["c_life"]
    b_on = t <= p["b_life"]
    comp_after = comp * (1 - p["c_saving_frac"]) if c_on else comp
    sav = (comp * p["c_saving_frac"] if c_on else 0) + ((motor * p["b_saving_frac"] + comp_after * p["b_comp_frac"]) if b_on else 0)
    bc.append(sav * tariff_mwh - (p["c_om"] if c_on else 0))
chk.append(("B+C NPV, explicit shared-ledger cash flows", explicit_npv(p["b_capex"] + p["c_capex"], bc),
            E.portfolio(("B", "C"), prj, inter)["npv"]))
# annuity factor identities
chk.append(("Degraded annuity factor, closed form vs sum (r=6%, n=25, d=0.5%)",
            sum(((1 - 0.005) ** (t - 1)) / 1.06 ** t for t in range(1, 26)), E.degraded_annuity_factor(0.06, 25, 0.005)))
chk.append(("Annuity factor, closed form vs sum (r=6%, n=15)", sum(1 / 1.06 ** t for t in range(1, 16)), float(E.annuity_factor(0.06, 15))))
fin = pd.DataFrame(chk, columns=["check", "independent", "model"])
fin["abs_diff"] = (fin.independent - fin.model).abs()
fin["pass"] = fin.abs_diff < 1e-6 * np.maximum(1, fin.model.abs())

FIN_NOTES = [
    ("Discounting", "Real 6% rate with constant real prices (tariff, gas, diesel held flat in real terms): consistent. End-of-year "
     "cash flows, capex at t=0. No tax, inflation, financing or salvage value (prototype simplification)"),
    ("Different lives", "Projects with different lives are compared by NPV (additive) without replacement; MAC uses each project's own "
     "discounted tonnes. Portfolio NPVs therefore assume no reinvestment after a measure ends"),
    ("PV degradation (new)", "v1.2 had none, overstating PV NPV by SAR 186,860 at v1.2 inputs (338k -> 151k). Fixed O&M is not degraded"),
    ("PV inverter replacement", "Not modelled: inverters typically need replacement once in a 25-year life; no Saudi cost source "
     "found, so not added (A5-11); this omission flatters A"),
    ("B-C overlap", "B's compressor-motor saving applies only to the load left after C; removed once in portfolio() and checked "
     "against the activity ledger and explicit cash flows (rows above)"),
    ("PV vs. load", "PV 1,850 MWh + B 864 + C 360 = 3,074 MWh < 12,000 MWh annual load, so savings cannot exceed purchases on an annual "
     "basis; hourly self-consumption not checked (A1-19)"),
    ("Compressed-air O&M (new)", "Leak savings persist only with an ongoing leak programme; SAR 15,000/yr is an assumption. Without it "
     "C's NPV would be overstated"),
    ("MAC", "Since v1.3 MAC divides by discounted tonnes (equivalent-annual-cost convention); identical to v1.2 for constant-output "
     "projects"),
]
fnotes = pd.DataFrame(FIN_NOTES, columns=["item", "finding"])

# ------------------------------------------------------------------ 5. benchmark checks (public cost evidence; never quotations)
BENCH = [
    ("pv_capex_kw", "SAR 2,500/kWp", "Knight Frank 2025: typical Riyadh rooftop SAR 2.5/W", "Used (single benchmark; A5-04)",
     A.URL["knightfrank_2025"]),
    ("b_capex", "SAR 1,200,000",
     "Clemson University IAC example recommendation (undated, US): AFD equipment for 15-60 hp units + 15% installation = USD 276-478 "
     "per hp installed (about SAR 1,390-2,400/kW at 3.75 SAR/USD)",
     "Not used to replace the value: motor kW of the case plant is not defined, IE4 motor cost not covered, US prices. Order-of-magnitude "
     "only: SAR 1.2M would buy roughly 500-860 kW of drives at these rates",
     "https://cecas.clemson.edu/iac/wp-content/uploads/2020/07/Use-Adjustable-Frequency-Drive-or-Multiple-Speed-Motors-on-Existing-System.pdf"),
    ("c_capex / c_om", "SAR 350,000 / SAR 15,000 per yr", "No public Saudi or international cost benchmark of adequate quality found",
     "Kept hypothetical (+/-15%)", ""),
    ("d_capex", "SAR 600,000", "No public cost benchmark of adequate quality found for furnace recuperators of unspecified size",
     "Kept hypothetical (+/-15%)", ""),
    ("e_capex", "SAR 900,000 (12 units)", "Search found only vendor marketing and blog pages (no dated, sourced price data)",
     "Kept hypothetical (+/-15%)", ""),
    ("f_premium", "SAR 80/t", "No public Saudi low-carbon steel premium found", "Kept hypothetical, uniform 50-120", ""),
]
bench = pd.DataFrame(BENCH, columns=["parameter", "model value", "public evidence found", "use", "url"])

# ------------------------------------------------------------------ 6. evidence gaps
GAPS = [
    ("A1-01 (carried)", "Critical", "Project not yet run on real Google Colab (simulated Colab environment only)", "Run once on Colab before submission"),
    ("A4-01 (carried)", "High", "No real industrial validation: the facility, its activity data and all A4 validation are synthetic",
     "Pilot with real bills and fuel records"),
    ("A5-01", "High", "Official 2027 industrial tariff schedule (SPA 25 Oct 2026 confirms an adjustment; rates in an attachment not "
     "retrieved; 23 halalas from secondary sources)", "T0-T3 scenarios; 0.18 kept as reference"),
    ("A5-02", "Medium", "2026 regulated methane price (reported +10-20%, no official figure); gas availability for a Riyadh plant unverified",
     "G0-G2 scenarios; no decision change across them"),
    ("A5-03", "High", "No supplier quotation for any project; all capex except PV remain hypothetical", "+/-15% capex uncertainty, "
     "budget chance constraint"),
    ("A5-04", "High", "PV capex rests on one consultancy benchmark; the recommendation change (A+B -> A+B+C, D4 feasible) depends on it",
     "P1 scenario reported: with SAR 3,750/kWp D1 = A+B and D4 infeasible"),
    ("A5-05", "Medium", "Scope 1 refrigerant (fugitive) emissions not inventoried", "Documented boundary gap"),
    ("A5-06", "Medium", f"Scope 3 Cat 3 (T&D losses, upstream fuel) not inventoried; T&D/own-use part indicatively {t_and_d_proxy:,.0f} t",
     "Documented boundary gap"),
    ("A5-07", "Low", "Steel factor is crude-steel (excludes rolling/finishing); supplier EPDs not obtained", "Uniform range 1.47-2.34"),
    ("A5-08", "Low", "Freight (DESNZ UK) and diesel (IPCC default) factors are transferred, not Saudi-specific", "+/-15% on freight"),
    ("A5-09", "Low", "Forklift kWh per litre displaced (3.5) has no source", "Uniform 3.0-4.0"),
    ("A5-10", "Medium", "Project C is marginal (NPV SAR 16.5k; switch point at the base savings value 0.20) - its inclusion in the "
     "recommendation is not robust", "Reported as a knife-edge in stability analysis"),
    ("A5-11", "Low", "PV inverter replacement and hourly self-consumption not modelled", "Documented"),
    ("A5-12", "Medium", "Discount rate 6% is a utility/energy-sector study WACC transferred to a private manufacturer; at 8-12% the "
     "deterministic choice is A+B", "Discount-rate robustness table"),
    ("A5-13", "Medium", "Grid factor derived from 2021 inventory data (latest official); 2024 generation mix with more renewables "
     "would lower it; SEC-specific factor not publicly retrieved", "E0-E2 scenarios; normal 5% uncertainty"),
    ("A5-14", "Low", "PV yield is simulated (utility-scale PVsyst), not measured rooftop output", "Triangular 1,650-2,010"),
]
gaps = pd.DataFrame(GAPS, columns=["id", "priority", "gap", "how handled now"])

# ------------------------------------------------------------------ 7. before/after
with A.use_profile("v1.2"):
    p12 = A.base_values()
    prj12, inter12 = E.projects(p12)
    base12 = E.scope_totals(E.baseline(p12))
    tgt12 = E.target_t(p12)
base13 = E.scope_totals(base)
tgt13 = E.target_t(p)
pr = []
for k in "ABCDEF":
    a, b = prj12[k], prj[k]
    pr.append(dict(project=k, name=b["name"], capex_v12=a["capex"], capex_v13=b["capex"], npv_v12=a["npv"], npv_v13=b["npv"],
                   d_npv=b["npv"] - a["npv"], t_v12=a["scope12_t"] + a["scope3_t"], t_v13=b["scope12_t"] + b["scope3_t"],
                   mac_v12=E.mac(a), mac_v13=E.mac(b)))
pr = pd.DataFrame(pr)
inv = pd.DataFrame([dict(item=s, v12=base12[s], v13=base13[s]) for s in base13] +
                   [dict(item="Target (15% of Scope 1+2), t", v12=tgt12, v13=tgt13)])
inv["change"] = inv.v13 - inv.v12
att = pd.read_csv(OUT / "a5_attribution.csv")
first, last = att.iloc[0], att.iloc[-1]
pf = []
for port in ("A+B", "A+C+D", "A+B+C"):
    sel = tuple(port.split("+"))
    with A.use_profile("v1.2"):
        c12 = E.portfolio(sel, *E.projects(A.base_values()))
    c13 = E.portfolio(sel, prj, inter)
    pf.append(dict(portfolio=port, capex_v12=c12["capex"], capex_v13=c13["capex"], npv_v12=first[f"npv[{port}]"], npv_v13=last[f"npv[{port}]"],
                   e_npv_v12=first[f"e_npv[{port}]"], e_npv_v13=last[f"e_npv[{port}]"], t12_v12=first[f"t12[{port}]"],
                   t12_v13=last[f"t12[{port}]"], p_target_v12=first[f"p_target[{port}]"], p_target_v13=last[f"p_target[{port}]"],
                   p_budget_v12=first[f"p_budget[{port}]"], p_budget_v13=last[f"p_budget[{port}]"]))
pf = pd.DataFrame(pf)
_mb = json.load(open(OUT / "results.json"))["budget_analysis"]["min_budget_by_portfolio"]
dec = pd.DataFrame([
    dict(rule="D1 deterministic NPV optimum", v12=first.deterministic, v13=last.deterministic,
         value_v12=first.det_npv, value_v13=last.det_npv, metric="NPV at base inputs, SAR"),
    dict(rule="D2 maximum expected NPV", v12=first.best_expected, v13=last.best_expected,
         value_v12=first.best_expected_e_npv, value_v13=last.best_expected_e_npv, metric="E[NPV], SAR"),
    dict(rule="D3 carbon target with 90% probability", v12=first.chance_constrained, v13=last.chance_constrained,
         value_v12=first.cc_p_target, value_v13=last.cc_p_target, metric="P(target)"),
    dict(rule="D4 carbon 90% + budget 90% (primary rule)", v12=first.joint, v13=last.joint,
         value_v12=first.joint_min_budget, value_v13=last.joint_min_budget, metric=f"Smallest budget at which any portfolio satisfies D4, SAR (v1.3: {_mb[0]['portfolio']}; {last.joint} needs "
                f"{next(m['budget_needed'] for m in _mb if m['portfolio'] == last.joint):,.0f})"),
])

scen_res = []
for f, col in (("tariff_scenarios.csv", "tariff"), ("gas_price_scenarios.csv", "gas_price_usd"),
               ("grid_factor_scenarios.csv", "ef_grid"), ("pv_capex_scenarios.csv", "pv_capex_kw")):
    d = pd.read_csv(OUT / f)
    for _, s in d.iterrows():
        scen_res.append(dict(input=col, id=s.id, value=s[col], label=s.label, D1=s.deterministic, D1_npv=s.det_npv, D2=s.best_expected, D2_e_npv=s.best_expected_e_npv,
                             D3=s.chance_constrained, D4=s.joint, D4_min_budget=s.joint_min_budget))
scen_res = pd.DataFrame(scen_res)
dr = pd.read_csv(OUT / "discount_rate_robustness.csv")

# ------------------------------------------------------------------ write workbooks
from openpyxl import load_workbook  # noqa: E402
from openpyxl.styles import Alignment, Font, PatternFill  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402

HDR = PatternFill("solid", fgColor="1F4E46")
CHG = PatternFill("solid", fgColor="FFF2CC")
BAD = PatternFill("solid", fgColor="F8CBAD")


def style(path, widths=None, changed_col=None):
    wb = load_workbook(path)
    for ws in wb.worksheets:
        if ws.title == "README":
            ws.column_dimensions["A"].width = 130
            for row in ws.iter_rows():
                for c in row:
                    c.alignment = Alignment(wrap_text=True, vertical="top")
            ws["A1"].font = Font(bold=True, size=13)
            continue
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = HDR
            c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "B2"
        for i, col in enumerate(ws.iter_cols(min_row=1, max_row=ws.max_row), start=1):
            n = max(len(str(c.value)) if c.value is not None else 0 for c in col)
            ws.column_dimensions[get_column_letter(i)].width = min(max(10, n + 2), 60)
            for c in col[1:]:
                c.alignment = Alignment(wrap_text=True, vertical="top")
                if isinstance(c.value, float):
                    c.number_format = "#,##0.00" if abs(c.value) >= 100 else "0.0000"
        heads = [c.value for c in ws[1]]
        if "changed_in_A5" in heads:
            j = heads.index("changed_in_A5") + 1
            for row in ws.iter_rows(min_row=2):
                if row[j - 1].value == "yes":
                    for c in row:
                        c.fill = CHG
        if "pass" in heads:
            j = heads.index("pass") + 1
            for row in ws.iter_rows(min_row=2):
                if row[j - 1].value is False:
                    row[j - 1].fill = BAD
        ws.auto_filter.ref = ws.dimensions
    wb.save(path)


README1 = [
    f"Mezan v{A.MODEL_VERSION} - A5 source and assumption register (generated by tools/build_a5_register.py from the live register)",
    "The case facility is HYPOTHETICAL (a synthetic Riyadh metal-fabrication plant). No value is a real factory observation, and no "
    "cost is a supplier quotation.",
    "Evidence class: measured (none - no real facility data) | external (cited source) | derived (computed from cited values) | "
    "hypothetical (illustrative case assumption) | estimated (filled at run time by the A4 missing-data engine; never stored here).",
    "Quality status: verified | derived | transferred (source from another context) | provisional (partial/secondary evidence) | hypothetical.",
    "Rows shaded yellow changed between v1.2 and v1.3 (value, distribution or status). The v1.2 register is reproducible with "
    "carbon_iq.assumptions.use_profile('v1.2').",
    "Sheets: Register | Scenarios | Grid factor evidence | GHG boundary | Financial checks | Financial notes | Cost benchmarks | Evidence gaps",
    "Sources accessed 25-26 October 2026. URLs are in each row.",
]
p1 = A5 / "Mezan_A5_Source_Register.xlsx"
with pd.ExcelWriter(p1, engine="openpyxl") as w:
    pd.DataFrame({"Mezan": README1}).to_excel(w, sheet_name="README", index=False, header=False)
    reg.to_excel(w, sheet_name="Register", index=False)
    scen.to_excel(w, sheet_name="Scenarios", index=False)
    gev.to_excel(w, sheet_name="Grid factor evidence", index=False)
    bound.to_excel(w, sheet_name="GHG boundary", index=False)
    fin.to_excel(w, sheet_name="Financial checks", index=False)
    fnotes.to_excel(w, sheet_name="Financial notes", index=False)
    bench.to_excel(w, sheet_name="Cost benchmarks", index=False)
    gaps.to_excel(w, sheet_name="Evidence gaps", index=False)
style(p1)

README2 = [
    f"Mezan - before (v1.2 register) and after (v{A.MODEL_VERSION} register) comparison",
    "Same model code, same random seed (20261024) and 20,000 Monte Carlo scenarios; only register inputs differ. New random inputs use a "
    "separate stream so v1.2 draws are unchanged.",
    "Attribution: each A5 change applied alone to the v1.2 register (one change at a time). Effects are not additive.",
    "Inventory and projects: deterministic base values. Portfolios: P(target) and P(capex <= budget) from the Monte Carlo.",
    "Scenario sheets run the full v1.3 analysis with one input fixed at the scenario value.",
]
p2 = A5 / "Mezan_A5_Before_After.xlsx"
with pd.ExcelWriter(p2, engine="openpyxl") as w:
    pd.DataFrame({"Mezan": README2}).to_excel(w, sheet_name="README", index=False, header=False)
    dec.to_excel(w, sheet_name="Decisions", index=False)
    inv.to_excel(w, sheet_name="Inventory", index=False)
    pr.to_excel(w, sheet_name="Projects", index=False)
    pf.to_excel(w, sheet_name="Portfolios", index=False)
    att.to_excel(w, sheet_name="Attribution", index=False)
    scen_res.to_excel(w, sheet_name="Scenarios", index=False)
    dr.to_excel(w, sheet_name="Discount rate", index=False)
style(p2)

_rec = lambda df: json.loads(df.to_json(orient="records", double_precision=15))  # noqa: E731  (NaN -> null)
summary = dict(model_version=A.MODEL_VERSION, register=_rec(reg), scenarios=_rec(scen),
               boundary=_rec(bound), fin_checks=_rec(fin), fin_notes=_rec(fnotes),
               bench=_rec(bench), gaps=_rec(gaps), decisions=_rec(dec),
               inventory=_rec(inv), projects=_rec(pr), portfolios=_rec(pf),
               attribution=_rec(att), scenario_results=_rec(scen_res), discount=_rec(dr),
               t_and_d_proxy=t_and_d_proxy, n_changed=int((reg.changed_in_A5 == "yes").sum()),
               evidence_counts=reg.evidence_class.value_counts().to_dict(), status_counts=reg.quality_status.value_counts().to_dict(),
               fin_all_pass=bool(fin["pass"].all()))
json.dump(summary, open(A5 / "a5_summary.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print("register rows", len(reg), "changed", summary["n_changed"], "fin checks pass", summary["fin_all_pass"], len(fin))
print(fin[["check", "abs_diff", "pass"]].to_string())
print(dec.to_string())

# ------------------------------------------------------------------ charts
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

CH = A5 / "charts"
CH.mkdir(exist_ok=True)
C12, C13 = "#9AA5B1", "#1F6F5C"
fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
x = np.arange(len(pr))
ax[0].bar(x - 0.2, pr.npv_v12 / 1e6, 0.4, color=C12, label="v1.2 register")
ax[0].bar(x + 0.2, pr.npv_v13 / 1e6, 0.4, color=C13, label="v1.3 register")
ax[0].axhline(0, color="#333", lw=0.8)
ax[0].set_xticks(x, pr.project)
ax[0].set_ylabel("NPV at base inputs (SAR million)")
ax[0].set_title("Project NPV", fontsize=10, loc="left")
ax[0].legend(frameon=False, fontsize=8)
lab = ["v1.2"] + [c.replace("only: ", "").replace(" + tree_g_reform", "").replace(" + c_om", " + c_om") for c in att.case[1:-1]] + ["v1.3"]
y = np.arange(len(att))
ax[1].barh(y, att.det_npv / 1e6, color=[C12] + ["#C9D3DB"] * (len(att) - 2) + [C13])
for yy, (v_, d_) in enumerate(zip(att.det_npv, att.deterministic)):
    ax[1].text(v_ / 1e6 + 0.03, yy, d_, va="center", fontsize=8)
ax[1].set_yticks(y, lab, fontsize=8)
ax[1].invert_yaxis()
ax[1].set_xlabel("D1 NPV (SAR million)")
ax[1].set_title("Each A5 change alone (D1 choice labelled)", fontsize=10, loc="left")
for a_ in ax:
    a_.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(CH / "a5_1_npv.png", dpi=170)
plt.close(fig)

fig, ax = plt.subplots(1, 2, figsize=(10, 3.2), sharey=True)
x = np.arange(len(pf))
for i, (col, title, thr) in enumerate((("p_target", "P(meet 15% target)", 0.9), ("p_budget", "P(actual capex ≤ SAR 5M)", 0.9))):
    ax[i].bar(x - 0.2, pf[col + "_v12"], 0.4, color=C12, label="v1.2 register")
    ax[i].bar(x + 0.2, pf[col + "_v13"], 0.4, color=C13, label="v1.3 register")
    ax[i].axhline(thr, color="#B03A2E", lw=1, ls="--")
    ax[i].set_xticks(x, pf.portfolio)
    ax[i].set_ylim(0, 1.05)
    ax[i].set_title(title, fontsize=10, loc="left")
    ax[i].spines[["top", "right"]].set_visible(False)
ax[0].legend(frameon=False, fontsize=8, loc="lower left")
fig.tight_layout()
fig.savefig(CH / "a5_2_probabilities.png", dpi=170)
plt.close(fig)
print("charts", sorted(p_.name for p_ in CH.iterdir()))
