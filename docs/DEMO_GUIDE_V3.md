# Mezan | ميزان — live demonstration (app v3.1, 4–5 minutes)

Start: `python -m streamlit run app.py`. Keep the default settings (20,000 futures, seed 20261024). Every number on screen is
computed live by the model; nothing is scripted. Figures below are what the default run produces (checked 19 Nov 2026).

| # | Where | Do | Say |
|---|---|---|---|
| 1 | Executive Overview | Point at the recommendation card | "Mezan answers one committee question: which decarbonisation projects to fund, and how sure can we be. For this synthetic Saudi metal-fabrication plant it recommends solar PV, efficient motors and drives, and compressed-air repairs: expected NPV SAR 2.56 million for SAR 4.05 million of capital." |
| 2 | Overview → Decision workflow, Mezan Intelligence | Point at step 3 (amber) and the first two findings | "The workflow shows what is really done. Nine monthly records still need review, and machine learning flagged one unusual month — so this run uses reference data, and the screen says so." |
| 3 | Plant Data → dataset "Unlabelled utility/ERP export" | Show the classification cards, then **Confirm stream assignments** | "Real exports arrive without our labels. Rules and a small text classifier assign 188 of 190 records correctly; two diesel purchases are genuinely ambiguous, so Mezan asks a person instead of guessing." |
| 4 | Plant Data → "Monthly records with gaps and errors" | Scroll to anomaly detection, then **Approve all eligible estimates** | "The Isolation Forest flags May 2026: gas per tonne is 68 robust deviations high — the rules caught it too. Scores rank months; they are not probabilities. Missing months get estimates with ranges, and nothing counts until a reviewer approves it." |
| 5 | Carbon & Emissions → Why data quality matters | Point at the two bars | "If those gaps were simply counted as zero, 2,231 tonnes — a quarter of the baseline — would disappear, and the target would be understated by 335 tonnes." |
| 6 | Header → Investment & Scenario Configuration | Set the budget to 4.20, press **Run investment analysis** | "Management sets the budget, the target and two separate risk requirements." |
| 7 | Investment Planner | Recommendation panel and opportunity map | "At SAR 4.2 million the original plan still meets the carbon target in 99.99% of futures, but keeps within budget in only 64%. The primary rule therefore switches to A+C+D. Simulation creates the futures; optimisation picks the most valuable plan that passes both tests." |
| 8 | Configuration → **Reset to defaults**, **Run investment analysis**; Decision Intelligence | Click *What could change my decision?* | "The deterministic choice sits close to two thresholds: compressed-air savings of 19.90% against 20.00% assumed, and a compressed-air cost of SAR 352,224 against 350,000. The primary rule itself holds up to a 10.02% discount rate." |
| 9 | Decision Intelligence | Click *Is better information worth buying?* then *How does Mezan use AI?* | "Perfect sub-metering data would be worth at most SAR 35,954 — less than its SAR 40,000 cost. Machine learning supports the data; the engines calculate the numbers; decision science selects the investment." |
| 10 | Reports & Evidence | Download **Executive Decision Report (PDF)**; open the AI capability tab | "One report carries the recommendation, risks, conditions, limitations and the evidence for every AI capability." |

**Backup.** No network or API key is needed. If a step is slow, the Executive Overview already shows every headline number.

**Facts to keep straight.** AI classifies records, flags anomalies, offers gated ML estimates and (only if configured) words
the explanation; it never calculates emissions, NPV or probabilities. Probabilities are modelled, not guaranteed. All data are
synthetic or published; the model is not externally validated.
