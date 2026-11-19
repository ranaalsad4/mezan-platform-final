"""Mezan_A6_Independent_Calculations.xlsx - an independent recalculation in spreadsheet formulas.

Inputs are typed values copied from outputs/assumptions.csv. Every result is a live formula written for this workbook
(not copied from Mezan_Data_Model.xlsx): year-by-year cash flows, Excel's own IRR(), explicit discounting,
a shared B+C activity ledger, all 64 portfolios, the deterministic optimum, the normal closed form for budget
compliance, the reform decision tree and the GBM trigger. The Check sheet compares each result with the Python model
(values typed from outputs/results.json, labelled as such). Recalculated with LibreOffice; python tools/build_a6_workbook.py
"""
import itertools
import json
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as CL

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
OUT = HERE / "outputs" / "a6" / "Mezan_A6_Independent_Calculations.xlsx"
REG = pd.read_csv(HERE / "outputs" / "assumptions.csv")
RES = json.load(open(HERE / "outputs" / "results.json"))
VAL = {r.key: float(r.value) for r in REG.itertuples()}
HDR = PatternFill("solid", fgColor="1F4E46"); INP = PatternFill("solid", fgColor="FFF2CC"); PY = PatternFill("solid", fgColor="DDEBF7")
B = Font(bold=True)

wb = Workbook()
# ------------------------------------------------------------------ Inputs
ws = wb.active; ws.title = "Inputs"
ws["A1"] = "Inputs typed from outputs/assumptions.csv (register v%s). Yellow = typed input; everything else in this workbook is a formula." % RES["meta"]["model_version"]
ws["A1"].font = B
N = {}
for i, r in enumerate(REG.itertuples(), start=3):
    ws.cell(i, 1, r.key); c = ws.cell(i, 2, float(r.value)); c.fill = INP; ws.cell(i, 3, r.unit); ws.cell(i, 4, r.evidence)
    N[r.key] = f"Inputs!$B${i}"
extra = [("sar_per_usd", 3.75, "SAR/USD (peg)"), ("gj_per_mmbtu", 1.055056, "GJ/MMBtu")]
for j, (k, v_, u) in enumerate(extra, start=i + 2):
    ws.cell(j, 1, k); c = ws.cell(j, 2, v_); c.fill = INP; ws.cell(j, 3, u); N[k] = f"Inputs!$B${j}"
ws.column_dimensions["A"].width = 24; ws.column_dimensions["C"].width = 30
n = N

# ------------------------------------------------------------------ Emissions (with factor derivations)
ws = wb.create_sheet("Emissions")
ws["A1"] = "Inventory: activity x factor (units checked: factor denominator = activity unit)"; ws["A1"].font = B
rows = [("Scope 1", "Natural gas (GJ x t/GJ)", "gas_gj", "ef_gas"), ("Scope 1", "Diesel forklifts (L x t/L)", "diesel_forklift_l", "ef_diesel"),
        ("Scope 1", "Diesel generators (L x t/L)", "diesel_genset_l", "ef_diesel"), ("Scope 2", "Grid electricity (MWh x t/MWh)", "elec_mwh", "ef_grid"),
        ("Scope 3", "Steel Cat 1 (t x t/t)", "steel_t", "ef_steel_incumbent"), ("Scope 3", "Freight Cat 4 (t-km x t/t-km)", "freight_tkm", "ef_freight")]
for i, (s, nm, a, f) in enumerate(rows, start=3):
    ws.cell(i, 1, s); ws.cell(i, 2, nm); ws.cell(i, 3, f"={n[a]}*{n[f]}")
E = {}
for i, s in enumerate(("Scope 1", "Scope 2", "Scope 3"), start=10):
    ws.cell(i, 2, s); ws.cell(i, 3, f'=SUMIF($A$3:$A$8,"{s}",$C$3:$C$8)'); E[s] = f"Emissions!$C${i}"
ws.cell(13, 2, "Scope 1+2"); ws.cell(13, 3, "=C10+C11"); E["Scope 1+2"] = "Emissions!$C$13"
ws.cell(14, 2, "Total"); ws.cell(14, 3, "=C13+C12"); E["Total"] = "Emissions!$C$14"
ws.cell(15, 2, "Target (share x Scope 1+2)"); ws.cell(15, 3, f"={n['target_share']}*C13"); E["target"] = "Emissions!$C$15"
ws.cell(17, 1, "Factor derivations from primary figures").font = B
ws.cell(18, 2, "Gas: (56,100 + 1x28 + 0.1x265) kg/TJ / 1e6 (IPCC 2006, AR5 GWP)"); ws.cell(18, 3, "=(56100+1*28+0.1*265)/1000000")
ws.cell(19, 2, "Diesel IPCC: (74,100 + 3x28 + 0.6x265)/1e6 x 43.0 x 0.84/1000"); ws.cell(19, 3, "=(74100+3*28+0.6*265)/1000000*43*0.84/1000")
ws.cell(20, 2, "Grid: 205,579 Gg / 358,640 GWh (BTR1 2021 / GASTAT 2021)"); ws.cell(20, 3, "=205579/358640")
ws.cell(21, 2, "Grid per MWh consumed: 205,579 / 301,600 (includes T&D losses)"); ws.cell(21, 3, "=205579/301600")
ws.column_dimensions["B"].width = 62; ws.column_dimensions["C"].width = 16

# ------------------------------------------------------------------ Cash flows (year by year)
ws = wb.create_sheet("Cash Flows")
ws["A1"] = "Year-by-year net cash flows (SAR), end of year; capex at t = 0. B+C column = shared activity ledger (B's compressor saving acts on the load left after C)"
ws["A1"].font = B
heads = ["Year", "DF 1/(1+r)^t", "A", "B", "C", "D", "E", "F", "B+C together", "A tonnes", "B tonnes", "C tonnes", "D tonnes", "E tonnes"]
for j, h in enumerate(heads, start=1):
    c = ws.cell(3, j, h); c.font = Font(bold=True, color="FFFFFF"); c.fill = HDR
comp = f"({n['elec_mwh']}*{n['compressed_air_share']})"
motor = f"({n['elec_mwh']}*{n['motor_share']})"
tar = f"({n['tariff']}*1000)"
gas = f"({n['gas_price_usd']}*{n['sar_per_usd']}/{n['gj_per_mmbtu']})"
r0 = 4
for t in range(0, 26):
    i = r0 + t
    ws.cell(i, 1, t)
    ws.cell(i, 2, f"=1/(1+{n['discount_rate']})^A{i}")
    if t == 0:
        ws.cell(i, 3, f"=-{n['pv_kwp']}*{n['pv_capex_kw']}"); ws.cell(i, 4, f"=-{n['b_capex']}"); ws.cell(i, 5, f"=-{n['c_capex']}")
        ws.cell(i, 6, f"=-{n['d_capex']}"); ws.cell(i, 7, f"=-{n['e_capex']}"); ws.cell(i, 8, f"=-{n['f_onboard']}")
        ws.cell(i, 9, f"=-{n['b_capex']}-{n['c_capex']}")
        for j in range(10, 15):
            ws.cell(i, j, 0)
        continue
    on = lambda life: f"(A{i}<={n[life]})"  # noqa: E731
    ws.cell(i, 3, f"={on('pv_life')}*({n['pv_kwp']}*{n['pv_yield']}/1000*(1-{n['pv_degradation']})^(A{i}-1)*{tar}-{n['pv_om_frac']}*{n['pv_kwp']}*{n['pv_capex_kw']})")
    ws.cell(i, 4, f"={on('b_life')}*({motor}*{n['b_saving_frac']}+{comp}*{n['b_comp_frac']})*{tar}")
    ws.cell(i, 5, f"={on('c_life')}*({comp}*{n['c_saving_frac']}*{tar}-{n['c_om']})")
    ws.cell(i, 6, f"={on('d_life')}*({n['gas_gj']}*{n['d_saving_frac']}*{gas}-{n['d_om']})")
    ws.cell(i, 7, f"={on('e_life')}*({n['diesel_forklift_l']}*{n['diesel_price']}-{n['diesel_forklift_l']}*{n['e_kwh_per_l']}/1000*{tar}+{n['e_maint_saving']})")
    ws.cell(i, 8, f"=-{on('f_life')}*{n['f_steel_t']}*{n['f_premium']}")
    ws.cell(i, 9, f"={on('c_life')}*({comp}*{n['c_saving_frac']}*{tar}-{n['c_om']})+{on('b_life')}*({motor}*{n['b_saving_frac']}"
                  f"+IF({on('c_life')},{comp}*(1-{n['c_saving_frac']}),{comp})*{n['b_comp_frac']})*{tar}")
    ws.cell(i, 10, f"={on('pv_life')}*{n['pv_kwp']}*{n['pv_yield']}/1000*(1-{n['pv_degradation']})^(A{i}-1)*{n['ef_grid']}")
    ws.cell(i, 11, f"={on('b_life')}*({motor}*{n['b_saving_frac']}+{comp}*{n['b_comp_frac']})*{n['ef_grid']}")
    ws.cell(i, 12, f"={on('c_life')}*{comp}*{n['c_saving_frac']}*{n['ef_grid']}")
    ws.cell(i, 13, f"={on('d_life')}*{n['gas_gj']}*{n['d_saving_frac']}*{n['ef_gas']}")
    ws.cell(i, 14, f"={on('e_life')}*({n['diesel_forklift_l']}*{n['ef_diesel']}-{n['diesel_forklift_l']}*{n['e_kwh_per_l']}/1000*{n['ef_grid']})")
last = r0 + 25
for j in range(1, 15):
    ws.column_dimensions[CL(j)].width = 13

# ------------------------------------------------------------------ Projects
ws = wb.create_sheet("Projects")
heads = ["Project", "Capex", "NPV (explicit discounting)", "NPV via NPV()", "IRR (Excel IRR)", "Simple payback (yr)", "Year-1 Scope 1+2 t",
         "Discounted tonnes", "MAC SAR/t", "Scope 3 t"]
for j, h in enumerate(heads, start=1):
    c = ws.cell(1, j, h); c.font = Font(bold=True, color="FFFFFF"); c.fill = HDR
PR = {}
col = {"A": "C", "B": "D", "C": "E", "D": "F", "E": "G", "F": "H"}
tcol = {"A": "J", "B": "K", "C": "L", "D": "M", "E": "N"}
for i, k in enumerate("ABCDEF", start=2):
    cc = col[k]
    rng = f"'Cash Flows'!{cc}{r0 + 1}:{cc}{last}"
    ws.cell(i, 1, k)
    ws.cell(i, 2, f"=-'Cash Flows'!{cc}{r0}")
    ws.cell(i, 3, f"=SUMPRODUCT('Cash Flows'!{cc}{r0}:{cc}{last},'Cash Flows'!B{r0}:B{last})")
    ws.cell(i, 4, f"=NPV({n['discount_rate']},{rng})+'Cash Flows'!{cc}{r0}")
    ws.cell(i, 5, f"=IFERROR(IRR('Cash Flows'!{cc}{r0}:{cc}{last}),\"n/a\")")
    ws.cell(i, 6, f"=IF('Cash Flows'!{cc}{r0 + 1}>0,B{i}/'Cash Flows'!{cc}{r0 + 1},\"n/a\")")
    if k in tcol:
        tc = tcol[k]
        ws.cell(i, 7, f"='Cash Flows'!{tc}{r0 + 1}")
        ws.cell(i, 8, f"=SUMPRODUCT('Cash Flows'!{tc}{r0 + 1}:{tc}{last},'Cash Flows'!B{r0 + 1}:B{last})")
        ws.cell(i, 9, f"=-C{i}/H{i}")
        ws.cell(i, 10, 0)
    else:
        ws.cell(i, 7, 0)
        ws.cell(i, 10, f"={n['f_steel_t']}*({n['ef_steel_incumbent']}-{n['ef_steel_alt']})")
        ws.cell(i, 8, f"=J{i}*SUMPRODUCT(('Cash Flows'!A{r0 + 1}:A{last}<={n['f_life']})*'Cash Flows'!B{r0 + 1}:B{last})")
        ws.cell(i, 9, f"=-C{i}/H{i}")
    PR[k] = i
ws.cell(9, 1, "B+C ledger"); ws.cell(9, 3, f"=SUMPRODUCT('Cash Flows'!I{r0}:I{last},'Cash Flows'!B{r0}:B{last})")
ws.cell(10, 1, "Overlap NPV = NPV(B) + NPV(C) - NPV(B+C ledger)"); ws.cell(10, 3, "=C3+C4-C9")
ws.cell(11, 1, "Overlap year-1 tonnes"); ws.cell(11, 7, f"={comp}*{n['b_comp_frac']}*{n['c_saving_frac']}*{n['ef_grid']}")
ws.column_dimensions["A"].width = 44
for j in range(2, 11):
    ws.column_dimensions[CL(j)].width = 17

# ------------------------------------------------------------------ Portfolios (64) and the deterministic optimum
ws = wb.create_sheet("Portfolios")
ws["A1"] = "All 64 portfolios. Budget and target from Inputs/Emissions. Best = highest NPV among feasible portfolios."; ws["A1"].font = B
heads = ["Portfolio", "A", "B", "C", "D", "E", "F", "Capex", "NPV", "Scope 1+2 reduction", "Within budget", "Meets target", "Feasible", "NPV if feasible"]
for j, h in enumerate(heads, start=1):
    c = ws.cell(3, j, h); c.font = Font(bold=True, color="FFFFFF"); c.fill = HDR
ports = [c for r in range(7) for c in itertools.combinations("ABCDEF", r)]
for i, c in enumerate(ports, start=4):
    ws.cell(i, 1, "+".join(c) or "(none)")
    for j, k in enumerate("ABCDEF", start=2):
        ws.cell(i, j, 1 if k in c else 0)
    lin = lambda colp: "+".join(f"{CL(2 + j)}{i}*Projects!${colp}${2 + j}" for j in range(6))  # noqa: E731
    ws.cell(i, 8, f"={lin('B')}")
    ws.cell(i, 9, f"={lin('C')}-C{i}*D{i}*Projects!$C$10")
    ws.cell(i, 10, f"={lin('G')}-C{i}*D{i}*Projects!$G$11")
    ws.cell(i, 11, f"=H{i}<={n['budget']}+0.000001")
    ws.cell(i, 12, f"=J{i}>={E['target']}-0.000000001")
    ws.cell(i, 13, f"=AND(K{i},L{i})")
    ws.cell(i, 14, f"=IF(M{i},I{i},-1E+30)")
lastp = 3 + len(ports)
ws.cell(lastp + 2, 1, "Deterministic optimum").font = B
ws.cell(lastp + 2, 9, f"=MAX(N4:N{lastp})")
ws.cell(lastp + 2, 2, f"=INDEX(A4:A{lastp},MATCH(I{lastp + 2},N4:N{lastp},0))")
OPT_NAME, OPT_NPV = f"Portfolios!$B${lastp + 2}", f"Portfolios!$I${lastp + 2}"
ws.column_dimensions["A"].width = 16
for j in range(8, 15):
    ws.column_dimensions[CL(j)].width = 15

# ------------------------------------------------------------------ Chance constraint (budget) closed form, decision tree, GBM
ws = wb.create_sheet("Risk & Timing")
ws["A1"] = "Closed forms written independently of the Python model"; ws["A1"].font = B
ws["A3"] = "P(actual capex <= budget) for A+B+C: normal sum, s.d. 15% of each quoted capex"; ws["A3"].font = B
ws["A4"] = "Mean (quoted)"; ws["B4"] = "=Projects!B2+Projects!B3+Projects!B4"
ws["A5"] = "s.d."; ws["B5"] = "=SQRT((0.15*Projects!B2)^2+(0.15*Projects!B3)^2+(0.15*Projects!B4)^2)"
ws["A6"] = "P(<= budget)"; ws["B6"] = f"=NORMDIST({n['budget']},B4,B5,TRUE)"
ws["A7"] = "Tightened SAA level for 90%, n = 20,000 (one-sided 95%)"; ws["B7"] = "=0.9+NORMSINV(0.95)*SQRT(0.9*0.1/20000)"
ws["A9"] = "Heat-recovery decision tree (one reform step)"; ws["A9"].font = B
ws["A10"] = "SAR saved per USD/MMBtu per year"; ws["B10"] = f"={n['gas_gj']}*{n['d_saving_frac']}*{n['sar_per_usd']}/{n['gj_per_mmbtu']}"
ws["A11"] = "Expected price after the decision"; ws["B11"] = f"={n['tree_p_reform']}*{n['tree_g_reform']}+(1-{n['tree_p_reform']})*{n['gas_price_usd']}"
ws["A12"] = "Annuity factor (life)"; ws["B12"] = f"=(1-(1+{n['discount_rate']})^-{n['d_life']})/{n['discount_rate']}"
ws["A13"] = "NPV invest now"; ws["B13"] = (f"=-{n['d_capex']}+(B10*{n['gas_price_usd']}-{n['d_om']})/(1+{n['discount_rate']})"
                                           f"+(B10*B11-{n['d_om']})*(B12-1/(1+{n['discount_rate']}))")
ws["A14"] = "NPV if reform (decided at t = 1)"; ws["B14"] = f"=-{n['d_capex']}+(B10*{n['tree_g_reform']}-{n['d_om']})*B12"
ws["A15"] = "NPV if no reform"; ws["B15"] = f"=-{n['d_capex']}+(B10*{n['gas_price_usd']}-{n['d_om']})*B12"
ws["A16"] = "Value of waiting one year"; ws["B16"] = f"=({n['tree_p_reform']}*MAX(B14,0)+(1-{n['tree_p_reform']})*MAX(B15,0))/(1+{n['discount_rate']})"
ws["A18"] = "GBM trigger (Dixit-Pindyck, DP49 Eq. C.7/C.13)"; ws["A18"].font = B
ws["A19"] = "r continuous"; ws["B19"] = f"=LN(1+{n['discount_rate']})"
ws["A20"] = "b = mu - s^2/2"; ws["B20"] = f"={n['ro_mu_gbm']}-{n['ro_sigma']}^2/2"
ws["A21"] = "lambda"; ws["B21"] = f"=(-B20+SQRT(B20^2+2*B19*{n['ro_sigma']}^2))/{n['ro_sigma']}^2"
ws["A22"] = "A = (1-exp(-(r-mu)T))/(r-mu)"; ws["B22"] = f"=(1-EXP(-(B19-{n['ro_mu_gbm']})*{n['d_life']}))/(B19-{n['ro_mu_gbm']})"
ws["A23"] = "Break-even USD/MMBtu"; ws["B23"] = f"=({n['d_capex']}+{n['d_om']}*(1-EXP(-B19*{n['d_life']}))/B19)/(B22*B10)"
ws["A24"] = "Trigger USD/MMBtu = lambda/(lambda-1) x break-even"; ws["B24"] = "=B21/(B21-1)*B23"
ws.column_dimensions["A"].width = 64; ws.column_dimensions["B"].width = 18

# ------------------------------------------------------------------ Check
ws = wb.create_sheet("Check", 0)
ws["A1"] = "Independent spreadsheet vs Python model (blue = Python value typed from outputs/results.json)"; ws["A1"].font = Font(bold=True, size=12)
ws["A2"] = "Synthetic case; this checks the arithmetic and formulas, not the real-world validity of the inputs."
for j, h in enumerate(["Quantity", "Spreadsheet (formula)", "Python model", "Abs. difference", "Tolerance", "Pass"], start=1):
    c = ws.cell(4, j, h); c.font = Font(bold=True, color="FFFFFF"); c.fill = HDR
prj = {p["id"]: p for p in RES["projects"]}
dt = RES["timing_tree"]
ds = {d["id"]: d for d in RES["decision_scenarios"]}
abc = next(r for r in RES["mc_portfolios"] if r["portfolio"] == "A+B+C")
checks = [(f"{s}", E[s], RES["scope_totals"][s], 1e-6) for s in ("Scope 1", "Scope 2", "Scope 3", "Scope 1+2", "Total")]
checks += [("Target", E["target"], RES["target_t"], 1e-6), ("Gas factor derivation", "Emissions!C18", VAL["ef_gas"], 1e-9),
           ("Grid factor derivation (rounded to 0.573)", "Emissions!C20", VAL["ef_grid"], 0.0005)]
for k in "ABCDEF":
    i = PR[k]
    checks.append((f"{k} NPV (explicit)", f"Projects!C{i}", prj[k]["npv"], 1e-3))
    checks.append((f"{k} NPV via NPV()", f"Projects!D{i}", prj[k]["npv"], 1e-3))
    checks.append((f"{k} MAC", f"Projects!I{i}", prj[k]["mac_sar_per_t"], 1e-6))
    if prj[k]["irr"] is not None:
        checks.append((f"{k} IRR (Excel IRR)", f"Projects!E{i}", prj[k]["irr"], 1e-6))
    if prj[k]["payback_y"] is not None:
        checks.append((f"{k} payback", f"Projects!F{i}", prj[k]["payback_y"], 1e-9))
    checks.append((f"{k} year-1 reduction", f"Projects!G{i}" if k != "F" else f"Projects!J{i}", prj[k]["scope12_t"] if k != "F" else prj[k]["scope3_t"], 1e-6))
checks.append(("B-C overlap NPV", "Projects!C10", RES["interaction"]["BC"]["npv"], 1e-3))
checks.append(("Deterministic optimum NPV", OPT_NPV, ds["D1"]["npv_base_inputs"], 1e-3))
checks.append(("P(capex <= budget) A+B+C: closed form vs 20,000-scenario estimate", "'Risk & Timing'!B6", abc["p_budget"], 0.003))
checks.append(("P(capex <= budget) A+B+C: closed form vs 200,000 validation", "'Risk & Timing'!B6", abc["p_budget_val"], 0.002))
checks.append(("Tightened SAA level", "'Risk & Timing'!B7", RES["mc_chance_constrained"]["alpha_saa"], 1e-6))
checks.append(("Decision tree: NPV invest now", "'Risk & Timing'!B13", dt["npv_invest_now"], 1e-3))
checks.append(("Decision tree: value of waiting", "'Risk & Timing'!B16", dt["value_wait_one_year"], 1e-3))
checks.append(("GBM lambda", "'Risk & Timing'!B21", RES["timing_gbm"]["lambda"], 1e-9))
checks.append(("GBM trigger USD/MMBtu", "'Risk & Timing'!B24", RES["timing_gbm"]["trigger_usd"], 1e-6))
for i, (q, f, pyv, tol) in enumerate(checks, start=5):
    ws.cell(i, 1, q); ws.cell(i, 2, f"={f}"); c = ws.cell(i, 3, float(pyv)); c.fill = PY
    ws.cell(i, 4, f"=ABS(B{i}-C{i})"); ws.cell(i, 5, tol); ws.cell(i, 6, f"=D{i}<=E{i}*MAX(1,ABS(C{i}))")
i += 1
ws.cell(i, 1, "Deterministic optimum portfolio"); ws.cell(i, 2, f"={OPT_NAME}"); c = ws.cell(i, 3, ds["D1"]["portfolio"]); c.fill = PY
ws.cell(i, 6, f"=B{i}=C{i}")
i += 2
ws.cell(i, 1, "All checks pass").font = B; ws.cell(i, 6, f"=AND(F5:F{i - 2})")
ALL_CELL = f"F{i}"
ws.column_dimensions["A"].width = 62
for j in range(2, 7):
    ws.column_dimensions[CL(j)].width = 18
for w in wb.worksheets:
    for row in w.iter_rows():
        for c in row:
            if c.alignment.wrap_text is None:
                c.alignment = Alignment(vertical="top")
wb.save(OUT)

from carbon_iq.recalc import recalc  # noqa: E402
info = recalc(OUT)
import openpyxl  # noqa: E402
wv = openpyxl.load_workbook(OUT, data_only=True)["Check"]
rows = [(wv.cell(r, 1).value, wv.cell(r, 2).value, wv.cell(r, 3).value, wv.cell(r, 6).value) for r in range(5, wv.max_row + 1) if wv.cell(r, 1).value]
summary = dict(recalc=info, checks=len(rows) - 1, all_pass=wv[ALL_CELL].value,
               failures=[r for r in rows if r[3] is False])
json.dump(summary, open(HERE / "outputs" / "a6" / "a6_workbook_check.json", "w"), indent=1, default=str)
print(json.dumps(summary, indent=1, default=str))
