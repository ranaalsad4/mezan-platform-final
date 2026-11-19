# Mezan — Phase B1 demonstration script (2–3 minutes)

Synthetic Saudi manufacturing facility · all numbers from the reproducible run (model v1.3, 20,000 scenarios, seed 20261024).
Modelled results only — no real deployment or verified savings.

## Pre-flight
- pip install -r requirements.txt; python run_all.py; python tools/run_a4.py --fast (or full); python tools/run_a6.py emissions finance optimization
- python -m pytest -q tests/test_b.py (checks that the demo shows the validated numbers)
- streamlit run app.py → open http://localhost:8501 → tab '▶ Guided demo' → step 1; browser zoom 90%; close other tabs
- Keep Mezan_Phase_B_Demo_Guide.pdf open in a second window as the fallback

## Script
| Time | Step | Screen | Say | Point to make |
|---|---|---|---|---|
| 0:00–0:20 | 1 · Factory | Guided demo → step 1 | This is a synthetic but realistic Saudi plant: a metal-fabrication factory near Riyadh emitting 9,054 tonnes of CO₂ a year from electricity, gas and diesel. Management has SAR 5 million and must cut 1,358 tonnes — 15%. | Problem framing: a real Saudi industrial decision, with numbers anchored to official Saudi sources. |
| 0:20–0:40 | 2 · Incomplete data | Step 2 | Real records are messy. Here three electricity months are missing or recorded as zero, gas has a blank, a typing error and a conflicting second record, a steel delivery and a diesel month are gone, and production has a negative entry. Mezan flags every problem and refuses to treat a missing month as zero. | Data-quality engine: never zero by default; decision blocked until gaps are resolved. |
| 0:40–1:00 | 3 · Estimates & warnings | Step 3 | Each gap gets a statistical estimate with a 95% interval, checked against history. Had the gaps been counted as zero, emissions would be understated by 25% and the plan would change. One estimate triggered an operational-change warning that a reviewer had to resolve explicitly. | Uncertainty-aware estimation with human review — not a black box. |
| 1:00–1:15 | 4 · Baseline & options | Step 4 | Six investment options: solar, efficient motors, compressed-air repair, heat recovery, electric forklifts and a lower-carbon steel supplier — each with cost, NPV, tonnes saved and cost per tonne. | Transparent project economics; costs other than solar are hypothetical. |
| 1:15–1:40 | 5 · Ranking vs Mezan | Step 5 | A common approach funds the cheapest tonnes first. That picks A+B+C+D+F: expected NPV only SAR 0.32 M, the budget holds in 76% of scenarios and there is a 40% chance of losing money. Mezan chooses A+B+C. Ranking by NPV happens to agree here — what Mezan adds is how sure we can be. | Honest baseline comparison: different from MAC ranking, same as NPV ranking in this case. |
| 1:40–2:00 | 6 · Probabilities | Step 6 | Across 20,000 simulated futures, checked on 200,000 more, A+B+C meets the target in >99.99% and stays within budget in 98.8% of cases, with expected NPV SAR 2.56 M. | Chance-constrained optimisation: carbon and budget risk in one decision (no competitor advertises this — A3). |
| 2:00–2:20 | 7 · Value of information | Step 7 | Before spending, what is worth measuring? Only compressed-air savings could change the decision — worth about SAR 35,954 against an assumed SAR 40,000 to meter. The missing bills from step 2 would not change the decision. | Tells management which data to collect first — and which not to bother with. |
| 2:20–2:50 | 8 · Recommendation | Step 8 | Recommendation: fund A+B+C for SAR 4.05 M, about 1,755 tonnes a year. Before signing: sub-meter compressed air, and get a supplier quote for solar — the result depends on that cost. Everything here is modelled on a synthetic plant; the next step is a pilot with real records. | Actionable decision with explicit trade-offs and limits. |

## Backup if the live dashboard fails
- If the app does not start: open Mezan_Phase_B_Demo_Guide.pdf and present the eight screenshots in order with the same script.
- If the app is slow: tick 'Show all steps on one page' and scroll (no recalculation is needed; the demo reads saved outputs).
- If a judge asks a what-if (budget, tariff, discount rate): use the sidebar and the Portfolio / Uncertainty tabs; if unavailable, answer from the Sensitivity sheet of Mezan_Phase_B_Impact_Scorecard.xlsx.
- If no screen is available: use the one-page scorecard numbers (step 6 and 8) verbally.

## Google Colab
```python
!unzip -q -o /content/Mezan_Phase_B.zip -d /content
%cd /content/Mezan
!pip install -q -r requirements.txt
!python run_all.py && python tools/run_a4.py --fast
!nohup streamlit run app.py --server.port 8501 --server.headless true > st.log 2>&1 &
from google.colab.output import eval_js; print(eval_js("google.colab.kernel.proxyPort(8501)"))   # open the printed link
```

Note: Not yet confirmed on real Google Colab (A1-01): rehearse once on Colab before the competition.

Screenshots: docs/phase_b/screenshots/demo_step1.png … demo_step8.png (captured from the live app).