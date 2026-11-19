"""Phase B text content in one place (demo script, backup sequence, Colab steps), with every number read from the run
outputs. Writes docs/phase_b/demo_script.json (used by the Word package and the PDF guide) and docs/phase_b/DEMO_SCRIPT.md.
    python tools/phase_b_content.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
R = json.load(open(HERE / "outputs" / "results.json"))
A6 = json.load(open(HERE / "outputs" / "a6" / "a6_results.json"))
SC = {r["id"]: r for r in json.load(open(HERE / "outputs" / "phase_b" / "scorecard_metrics.json"))}
CMP = json.load(open(HERE / "outputs" / "phase_b" / "scorecard_check.json"))["comparison"]
D4 = next(d for d in R["decision_scenarios"] if d["id"] == "D4")
mac = next(c for c in CMP if c["method"].startswith("Rank by abatement"))
c_voi = next(v for v in R["voi"] if v["parameter"] == "c_saving_frac")
zero = SC["Q1"]["value"] / SC["Q2"]["value"] - 1


def pct(p, d=1):
    return f">{1 - 10 ** -(d + 2):.{d}%}" if 1 - 0.5 * 10 ** -(d + 2) <= p < 1 else f"{p:.{d}%}"


STEPS = [
    dict(step="1 · Factory", time="0:00–0:20", screen="Guided demo → step 1",
         say=f"This is a synthetic but realistic Saudi plant: a metal-fabrication factory near Riyadh emitting {SC['S1']['value']:,.0f} tonnes "
             f"of CO₂ a year from electricity, gas and diesel. Management has SAR 5 million and must cut {SC['S2']['value']:,.0f} tonnes — 15%.",
         point="Problem framing: a real Saudi industrial decision, with numbers anchored to official Saudi sources."),
    dict(step="2 · Incomplete data", time="0:20–0:40", screen="Step 2",
         say="Real records are messy. Here three electricity months are missing or recorded as zero, gas has a blank, a typing error and a "
             "conflicting second record, a steel delivery and a "
             "diesel month are gone, and production has a negative entry. Mezan flags every problem and refuses to treat a missing "
             "month as zero.",
         point="Data-quality engine: never zero by default; decision blocked until gaps are resolved."),
    dict(step="3 · Estimates & warnings", time="0:40–1:00", screen="Step 3",
         say=f"Each gap gets a statistical estimate with a 95% interval, checked against history. Had the gaps been counted as zero, "
             f"emissions would be understated by {abs(zero):.0%} and the plan would change. One estimate triggered an operational-change "
             f"warning that a reviewer had to resolve explicitly.",
         point="Uncertainty-aware estimation with human review — not a black box."),
    dict(step="4 · Baseline & options", time="1:00–1:15", screen="Step 4",
         say="Six investment options: solar, efficient motors, compressed-air repair, heat recovery, electric forklifts and a lower-carbon "
             "steel supplier — each with cost, NPV, tonnes saved and cost per tonne.",
         point="Transparent project economics; costs other than solar are hypothetical."),
    dict(step="5 · Ranking vs Mezan", time="1:15–1:40", screen="Step 5",
         say=f"A common approach funds the cheapest tonnes first. That picks {mac['portfolio']}: expected NPV only SAR {mac['e_npv'] / 1e6:.2f} M, "
             f"the budget holds in {mac['p_budget']:.0%} of scenarios and there is a {mac['p_loss']:.0%} chance of losing money. Mezan "
             f"chooses {D4['portfolio']}. Ranking by NPV happens to agree here — what Mezan adds is how sure we can be.",
         point="Honest baseline comparison: different from MAC ranking, same as NPV ranking in this case."),
    dict(step="6 · Probabilities", time="1:40–2:00", screen="Step 6",
         say=f"Across 20,000 simulated futures, checked on 200,000 more, {D4['portfolio']} meets the target in {pct(D4['p_target_val'], 2)} "
             f"and stays within budget in {D4['p_budget_val']:.1%} of cases, with expected NPV SAR {D4['e_npv'] / 1e6:.2f} M.",
         point="Chance-constrained optimisation: carbon and budget risk in one decision (no competitor advertises this — A3)."),
    dict(step="7 · Value of information", time="2:00–2:20", screen="Step 7",
         say=f"Before spending, what is worth measuring? Only compressed-air savings could change the decision — worth about "
             f"SAR {c_voi['evppi_sar']:,.0f} against an assumed SAR {c_voi['collection_cost_sar']:,.0f} to meter. The missing bills from step 2 "
             f"would not change the decision.",
         point="Tells management which data to collect first — and which not to bother with."),
    dict(step="8 · Recommendation", time="2:20–2:50", screen="Step 8",
         say=f"Recommendation: fund {D4['portfolio']} for SAR {D4['capex_quote'] / 1e6:.2f} M, about {SC['I1']['value']:,.0f} tonnes a year. "
             f"Before signing: sub-meter compressed air, and get a supplier quote for solar — the result depends on that cost. "
             f"Everything here is modelled on a synthetic plant; the next step is a pilot with real records.",
         point="Actionable decision with explicit trade-offs and limits."),
]
BACKUP = [
    "If the app does not start: open Mezan_Phase_B_Demo_Guide.pdf and present the eight screenshots in order with the same script.",
    "If the app is slow: tick 'Show all steps on one page' and scroll (no recalculation is needed; the demo reads saved outputs).",
    "If a judge asks a what-if (budget, tariff, discount rate): use the sidebar and the Portfolio / Uncertainty tabs; if unavailable, "
    "answer from the Sensitivity sheet of Mezan_Phase_B_Impact_Scorecard.xlsx.",
    "If no screen is available: use the one-page scorecard numbers (step 6 and 8) verbally.",
]
PREFLIGHT = [
    "pip install -r requirements.txt; python run_all.py; python tools/run_a4.py --fast (or full); python tools/run_a6.py emissions finance optimization",
    "python -m pytest -q tests/test_b.py (checks that the demo shows the validated numbers)",
    "streamlit run app.py → open http://localhost:8501 → tab '▶ Guided demo' → step 1; browser zoom 90%; close other tabs",
    "Keep Mezan_Phase_B_Demo_Guide.pdf open in a second window as the fallback",
]
COLAB = [
    "Upload Mezan_Phase_B.zip to the Colab file panel (or open Mezan_Colab.ipynb from the package).",
    "!unzip -q -o /content/Mezan_Phase_B.zip -d /content",
    "%cd /content/Mezan",
    "!pip install -q -r requirements.txt",
    "!python run_all.py && python tools/run_a4.py --fast",
    "!nohup streamlit run app.py --server.port 8501 --server.headless true > st.log 2>&1 &",
    "from google.colab.output import eval_js; print(eval_js(\"google.colab.kernel.proxyPort(8501)\"))   # open the printed link",
    "Not yet confirmed on real Google Colab (A1-01): rehearse once on Colab before the competition.",
]
out = dict(steps=STEPS, backup=BACKUP, preflight=PREFLIGHT, colab=COLAB, portfolio=D4["portfolio"])
(HERE / "docs" / "phase_b").mkdir(parents=True, exist_ok=True)
json.dump(out, open(HERE / "docs" / "phase_b" / "demo_script.json", "w"), indent=1, ensure_ascii=False)
md = ["# Mezan — Phase B1 demonstration script (2–3 minutes)", "",
      "Synthetic Saudi manufacturing facility · all numbers from the reproducible run (model v1.3, 20,000 scenarios, seed 20261024).",
      "Modelled results only — no real deployment or verified savings.", "", "## Pre-flight", *[f"- {x}" for x in PREFLIGHT], "",
      "## Script", "| Time | Step | Screen | Say | Point to make |", "|---|---|---|---|---|",
      *[f"| {s['time']} | {s['step']} | {s['screen']} | {s['say']} | {s['point']} |" for s in STEPS], "",
      "## Backup if the live dashboard fails", *[f"- {x}" for x in BACKUP], "", "## Google Colab", "```python", *COLAB[1:-1], "```",
      "", f"Note: {COLAB[-1]}", "", "Screenshots: docs/phase_b/screenshots/demo_step1.png … demo_step8.png (captured from the live app)."]
(HERE / "docs" / "phase_b" / "DEMO_SCRIPT.md").write_text("\n".join(md), encoding="utf-8")
print("ok", len(STEPS))
