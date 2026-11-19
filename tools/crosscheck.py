"""Three-way comparison of Python results, the Excel workbook and the Word report (read-only).

    python tools/crosscheck.py . outputs/crosscheck.csv

The workbook must carry cached formula values (run_all.py recalculates it with LibreOffice when available).
Word figures are searched as printed text, so a figure printed in another format is reported as 'not found'."""
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import openpyxl

PKG = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2])
sys.path.insert(0, str(PKG))
from carbon_iq import engine as E, optimize as O, timing as TM  # noqa: E402
from carbon_iq.assumptions import v  # noqa: E402

R = json.loads((PKG / "outputs/results.json").read_text())
wb = openpyxl.load_workbook(PKG / "Mezan_Data_Model.xlsx", data_only=True)
text = subprocess.run(["pandoc", "-t", "plain", "--wrap=none", str(PKG / "Mezan_Complete_Project.docx")],
                      capture_output=True, text=True).stdout
text_n = text.replace("−", "-").replace(" ", " ")
rows = []


def add(item, py, xl=None, word=None, tol=1e-6, note=""):
    def ok(a, b):
        if a is None or b is None:
            return None
        if isinstance(a, str) or isinstance(b, str):
            return str(a) == str(b)
        return abs(a - b) <= tol * max(1.0, abs(a))
    rows.append({"item": item, "python": py, "excel": xl, "excel_match": ok(py, xl),
                 "word_text": word[0] if word else None, "word_found": word[1] if word else None, "note": note})


def S_(x):
    return ("-" if x < 0 else "") + "SAR " + f"{abs(round(x)):,}"


def find(s):
    return (s, s in text_n)


def cell(sheet, ref):
    return wb[sheet][ref].value


def find_row(sheet, col_label_idx, label, val_idx):
    for r in wb[sheet].iter_rows(values_only=True):
        if r[col_label_idx] == label:
            return r[val_idx]
    return None


st = R["scope_totals"]
add("Scope 1 (t)", st["Scope 1"], cell("Baseline Emissions", "G12"), find(f"Scope 1 {round(st['Scope 1']):,}"))
add("Scope 2 (t)", st["Scope 2"], cell("Baseline Emissions", "G13"), find(f"Scope 2 {round(st['Scope 2']):,}"))
add("Scope 3 (t)", st["Scope 3"], cell("Baseline Emissions", "G14"), find(f"Scope 3 {round(st['Scope 3']):,}"))
add("Total (t)", st["Total"], cell("Baseline Emissions", "G16"), find(f"{round(st['Total']):,} tCO"))
add("Target (t/yr)", R["target_t"], cell("Baseline Emissions", "G17"), find(f"{round(R['target_t']):,} t/yr"))
ut = R["uncertainty_totals"]
add("U Scope 1+2 (±%)", ut["Scope 1+2"]["u95_pct"], cell("Data Quality", "F15"), find(f"±{ut['Scope 1+2']['u95_pct']:.1f}%"), tol=1e-4,
    note="Excel inputs rounded to 4 dp")
add("U Total (±%)", ut["Total"]["u95_pct"], cell("Data Quality", "F16"), find(f"±{ut['Total']['u95_pct']:.1f}%"), tol=1e-4)
for i, r in enumerate(R["uncertainty"], start=5):
    add(f"U source {r['source_id']} (±%)", r["u_combined_pct"], cell("Data Quality", f"F{i}"), tol=1e-4)
add("MC check U Scope 1+2 (±%)", R["mc_baseline_scope12"]["u95_pct"], cell("Data Quality", "F18"),
    find(f"±{R['mc_baseline_scope12']['u95_pct']:.1f}%"), tol=1e-4)
fin = {}
for row in wb["Financials & Cash Flows"].iter_rows(values_only=True):
    if isinstance(row[0], str) and len(row[0]) > 2 and row[0][1] == " " and row[0][0] in "ABCDEF":
        fin[row[0][0]] = row
cfn = {}
for row in wb["Financials & Cash Flows"].iter_rows(values_only=True):
    if row[0] in tuple("ABCDEF") and len(row) > 27 and isinstance(row[27], (int, float)):
        cfn[row[0]] = row[27]
for p in R["projects"]:
    k = p["id"]
    add(f"{k} NPV (SAR)", p["npv"], fin[k][3], find(f"SAR {abs(round(p['npv'])):,}"), tol=1e-9)
    add(f"{k} NPV via Excel NPV() cash flows", p["npv"], cfn.get(k), tol=1e-6)
    add(f"{k} annual cash flow", p["annual_cf"], fin[k][1])
    add(f"{k} Scope 1+2 t/yr", p["scope12_t"], fin[k][4])
    add(f"{k} Scope 3 t/yr", p["scope3_t"], fin[k][5])
    if k != "F":
        add(f"{k} MAC SAR/t", p["mac_sar_per_t"], fin[k][6], tol=1e-6)
o = R["optimal"]
add("Optimal portfolio", o["portfolio"], cell("Optimization", "H4"), find(f"chooses {o['portfolio']}"))
add("Optimal NPV", o["npv"], cell("Optimization", "H5"), find(f"SAR {o['npv']/1e6:.2f}M"))
add("Optimal Scope 1+2 t", o["scope12_t"], cell("Optimization", "H6"), find(f"{round(o['scope12_t']):,} t/yr"))
add("MILP agrees with enumeration", True, R["milp"]["agrees_with_enumeration"])
pd_ = {r["portfolio"]: r for r in R.get("portfolios", [])} if R.get("portfolios") else None
det = {}
with open(PKG / "outputs/portfolios_deterministic.csv") as fh:
    for r in csv.DictReader(fh):
        det[r["portfolio"]] = r
nmis = 0
for r in wb["Optimization"].iter_rows(min_row=8, max_row=71, values_only=True):
    name = r[0]
    if name in det:
        if abs(float(det[name]["npv"]) - r[8]) > 1e-6 * max(1, abs(r[8])) or abs(float(det[name]["scope12_t"]) - r[9]) > 1e-6:
            nmis += 1
add("64 portfolios: Excel vs Python mismatches", 0, nmis)
cc, be = R["mc_chance_constrained"], R["mc_best_expected"]
add("Chance-constrained portfolio", cc["portfolio"], word=find(f"validated choice is {cc['portfolio']}"))
add("Chance-constrained E[NPV]", cc["e_npv"], word=find(f"SAR {cc['e_npv']/1e6:.2f}M"))
add("Chance-constrained P(target)", cc["p_target"], word=find(f"target {cc['p_target']*100:.1f}%"))
add("Best-expected E[NPV]", be["e_npv"], word=find(f"SAR {be['e_npv']/1e6:.2f}M"))
add("Best-expected P(target)", be["p_target"], word=find(f"target {be['p_target']*100:.1f}%"))
for r in wb["Monte Carlo"].iter_rows(min_row=5, max_row=30, values_only=True):
    if r[0] == cc["portfolio"]:
        add("Excel MC table E[NPV] (chance-constrained portfolio)", round(cc["e_npv"], 4), r[2], tol=1e-6)
        break
add("EVPI (rounded to SAR 1 as written in Excel)", round(R["evpi"]), cell("Value of Information", "B4"), find(f"SAR {R['evpi']/1e6:.2f}M"), tol=1e-9)
add("EVSI motor audit", R["evsi_audit"]["evsi"], None, find(f"SAR {R['evsi_audit']['evsi']/1e6:.2f}M"))
for r in R["voi"]:
    xl = find_row("Value of Information", 0, r["information"], 1)
    add(f"EVPPI {r['parameter']}", round(r["evppi_sar"], 0), xl, tol=1e-9)
t = R["timing_tree"]
dash = {r[0]: r[1] for r in wb["Dashboard"].iter_rows(min_row=4, max_row=25, values_only=True)}
add("Tree decision", t["decision"], dash.get("Decision tree"), find(t["decision"]))
add("Tree option premium", t["option_premium"], None, find(f"SAR {round(t['option_premium']/1e3):,}k"))
add("Static break-even gas (USD)", t["static_breakeven_usd"], dash.get("Static break-even gas price (USD/MMBtu)"),
    find(f"${t['static_breakeven_usd']:.2f}/MMBtu"))
add("GBM trigger (USD)", R["timing_gbm"]["trigger_usd"], dash.get("GBM trigger (USD/MMBtu)"), find(f"${R['timing_gbm']['trigger_usd']:.2f}/MMBtu"))
add("LSMC trigger (USD)", R["timing_scan"]["trigger_usd"], None, find(f"${R['timing_scan']['trigger_usd']:.2f}/MMBtu"))
ts = json.loads((PKG / "outputs/test_summary.json").read_text())
add("Tests reported in Word", ts["total"], None, find(f"{ts['total']} automated tests"))
add("Excel formulas reported in Word", ts["excel_formulas"], None, find(f"{ts['excel_formulas']} Excel formulas"))
# ---- v1.1/v1.2 additions
obj = wb["Decision Objectives"]
for i, ob in enumerate(R["decision_scenarios"], start=6):
    add(f"Rule {ob['id']} id", ob["id"], obj[f"A{i}"].value)
    add(f"Rule {ob['id']} portfolio", ob["portfolio"], obj[f"D{i}"].value)
    if ob["portfolio"] != "none feasible":
        add(f"Rule {ob['id']} NPV at base inputs (live Excel)", ob["npv_base_inputs"], obj[f"F{i}"].value)
        add(f"Rule {ob['id']} quoted capex (live Excel)", ob["capex_quote"], obj[f"E{i}"].value)
        add(f"Rule {ob['id']} P(capex <= budget)", round(ob["p_budget"], 4), obj[f"J{i}"].value, tol=1e-9)
        add(f"Rule {ob['id']} P(target) validation", round(ob["p_target_val"], 4), obj[f"I{i}"].value, tol=1e-9)
        add(f"Rule {ob['id']} E[NPV] in Word", ob["e_npv"], word=find(S_(ob["e_npv"])))
mb = R["budget_analysis"]["min_budget_by_portfolio"][0]
add("Minimum budget in Word", mb["budget_needed"], None, find(S_(mb["budget_needed"])))
ke = R["knife_edge"]
add("Knife-edge validation probability in Word", ke["p_validation"], None, find(f"{ke['p_validation']*100:.2f}%"))
if R["mc_joint"]["feasible"]:
    add("Primary rule portfolio reported in Word", R["mc_joint"]["portfolio"], None, find(f"{R['mc_joint']['portfolio']} qualifies"))
else:
    add("Primary rule infeasible reported in Word", R["mc_joint"]["feasible"], None, find("no portfolio qualifies"))
mc = {r[0]: r for r in wb["Monte Carlo"].iter_rows(min_row=5, max_row=40, values_only=True) if r[0]}
for r in R["mc_portfolios"][:6]:
    add(f"MC {r['portfolio']} P(capex <= budget)", round(r["p_budget"], 4), mc[r["portfolio"]][9], tol=1e-9)
    add(f"MC {r['portfolio']} P(target) validation", round(r["p_target_val"], 4), mc[r["portfolio"]][11], tol=1e-9)
for tsn in R["tariff_scenarios"]:
    add(f"Tariff {tsn['id']} deterministic NPV in Word", tsn["det_npv"], word=find(S_(tsn["det_npv"])))
voi_ws = wb["Value of Information"]
_mrow = next((r for r in range(1, voi_ws.max_row + 1) if str(voi_ws.cell(r, 1).value or "").startswith("Motor-system savings")), None)
add("VOI motor-audit cost linked (Excel)", float(R["evsi_audit"]["audit_cost"]), voi_ws.cell(_mrow, 3).value if _mrow else None)
_fi = json.loads((PKG / 'outputs/fault_injection.json').read_text())
add("Fault injection reported in Word", _fi['faults'], None, find(f"{_fi['detected']} of {_fi['faults']} deliberately injected faults"))
# recompute deterministic results with the package code to make sure stored results are current
prj, inter = E.projects()
best, _ = O.enumerate_best(prj, inter, v("budget"), E.target_t())
add("Recomputed optimum NPV (live code)", best["npv"], o["npv"])
add("Recomputed tree premium (live code)", TM.decision_tree()["option_premium"], t["option_premium"])

with open(OUT, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
xl_checked = [r for r in rows if r["excel_match"] is not None]
wd_checked = [r for r in rows if r["word_found"] is not None]
print(f"checks: {len(rows)} | excel compared {len(xl_checked)}, mismatches {sum(1 for r in xl_checked if not r['excel_match'])} | "
      f"word compared {len(wd_checked)}, not found {sum(1 for r in wd_checked if not r['word_found'])}")
for r in rows:
    if r["excel_match"] is False or r["word_found"] is False:
        print("  ISSUE:", r["item"], "| py", r["python"], "| xl", r["excel"], "| word", r["word_text"], r["word_found"])
