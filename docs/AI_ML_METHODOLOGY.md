# Mezan | ميزان — AI and machine-learning methodology (app v3)

**Scope.** This document describes every AI or machine-learning component in the platform, the exact technique, how it is
evaluated, and what it is not allowed to do. All quantitative results — emissions, NPV, IRR, payback, MAC, Monte Carlo
probabilities, portfolio selection, sensitivity, switching, value of information and investment timing — are produced by the
calculation engine (`carbon_iq`, model v1.3) and are **never** produced, changed or validated by an AI component.

All evaluation data are **synthetic** (known truth). None of the results below says anything about real plants until the
evaluation is repeated on real records. Reproduce with `python tools/evaluate_ai.py` (≈2 minutes) →
`outputs/ai/ai_evaluation.json` and two case-level CSVs.

## Labels used in the interface

| Label | Meaning |
|---|---|
| Calculation engine | Output of `carbon_iq` (deterministic, statistical, simulation or optimisation code) |
| Rule-based check / Rule-based classification | Deterministic, documented rules (no learning) |
| Statistical estimate | The existing missing-data estimator (production intensity, seasonal history or mean; leave-one-out back-test) |
| ML classification | Proposal from the TF-IDF + logistic-regression text model |
| ML flag | Isolation Forest anomaly flag (advisory) |
| ML estimate (adopted by reviewer) | ML challenger estimate that passed the evidence gate and was chosen by a reviewer |
| Rule-based narrative | Deterministic explanation generated from engine outputs |
| AI-generated explanation | Language-model text (optional), accepted only after every number was verified against engine outputs |

## A · Record classification (`mezan_ai/classifier.py`) — Implemented

**Problem.** Utility, fuel-card and ERP exports arrive with free-text descriptions instead of Mezan's stream codes.

**Technique (hybrid, in order).**
1. *Provided label*: a valid schema stream is kept.
2. *Semantic rules*: an English/Arabic keyword lexicon, restricted to streams whose canonical unit matches the record's
   unit (`quality.UNITS`); a unique best keyword match, or a unit that admits only one stream, decides.
3. *ML text model*: TF-IDF character n-grams (2–5, word boundaries) + multinomial logistic regression (scikit-learn),
   trained on `mezan_ai/data/record_descriptions.csv` (576 curated synthetic descriptions, 96 templates, 8 streams;
   `tools/build_classifier_corpus.py`). Used only when the rules cannot decide. Probabilities are restricted to
   unit-compatible streams and renormalised; a proposal requires ≥ 0.60, otherwise the record goes to the reviewer.

**Safeguards.** A record can never be assigned to a stream with an incompatible unit. Every proposal needs reviewer
confirmation. Unassigned records are set aside — their months then count as *missing* in the ledger, never as zero. The
original upload is not modified.

**Evaluation (synthetic).**

| Measure | Result |
|---|---|
| Rules: share of corpus decided / accuracy when decided | 82.1% / 100% (lexicon and corpus written together: optimistic) |
| ML alone, grouped 5-fold CV (whole templates held out) | 81.4% |
| Hybrid (rules, then ML), grouped CV | 96.7% |
| Demo export (190 records, wording not in the training corpus) | 188 correct, 2 left for the reviewer, 0 wrong |

**Limits.** Synthetic corpus; real exports will contain wording, languages and abbreviations not seen here. Retrain on
labelled real exports before relying on the ML stage.

## B · Anomaly detection (`mezan_ai/anomaly.py`) — Implemented (advisory)

**Technique.** Isolation Forest (Liu, Ting & Zhou 2008; scikit-learn, 300 trees, seed 20261024) on **month-level** feature
vectors: log electricity, natural-gas and forklift-diesel intensity per tonne of output, log operating hours per tonne,
log output, and month-of-year (sin/cos) so a recurring summer peak is not flagged. It complements the existing per-stream
robust z-score rule (|z| > 3.5) by looking at unusual *combinations* of intensities.

**Data requirement.** At least 18 months with complete features (one missing energy feature per month is allowed and
scored at that feature's median, disclosed per row). Otherwise ML is **not applied** and the interface says so; only the
rule-based checks run.

**Threshold.** A month is flagged when its isolation score is ≥ 0.55. Chosen on synthetic data (60 random facilities,
40 with one injected anomaly ×0.6, ×1.3, ×1.5 or ×2.0 in an energy stream-month, 20 clean):

| Detector | Detection rate | False alarms per plant-year |
|---|---|---|
| Robust z-score rule (existing) | 80.0% | 0.65 |
| Isolation Forest, threshold 0.50 | 95.0% | 4.13 |
| **Isolation Forest, threshold 0.55 (used)** | **77.5%** | **1.10** |
| Isolation Forest, threshold 0.60 | 17.5% | 0.15 |
| Rule ∪ Isolation Forest (0.55) | 87.5% | — |

**Explanation of a flag.** The isolation score plus the two features furthest from their median (robust standard
deviations), e.g. "natural gas per tonne (+68.4 robust sd)". Scores are relative isolation scores, **not probabilities**.

**Safeguards.** Flags never change a value. The reviewer confirms or dismisses each flag; decisions go to the audit trail.
The plant-data baseline is "Approved" only when every gap is resolved **and** every flag has been reviewed.

## C · Missing-data assistance (`mezan_ai/imputation.py`) — Implemented (gated, reviewer opt-in)

**Default.** The existing statistical estimator is unchanged and remains the default.

**Challengers.** Ridge regression and random-forest regression (scikit-learn, 120 trees, min 2 samples per leaf) on output,
operating hours, month (sin/cos) and a year indicator, trained on the stream's usable months of both years and back-tested
with the **same** leave-one-out protocol on the reporting year's measured months.

**Evidence gate.** An ML estimate can be adopted for a cell only if (1) the statistical estimator produced a proposal —
ML never bypasses a refusal rule (too few months, gap too long, operational change, unreliable estimate); (2) ≥ 15 usable
months; (3) the ML back-test error is below 90% of the statistical method's; and (4) a reviewer explicitly chooses it.
Adopted estimates get prediction intervals from the same formula as statistical ones, are labelled `estimated (ml_ridge)`
or `estimated (ml_forest)`, and are written to the audit trail.

**Evaluation (synthetic, 30 facilities, 2 months removed from each of electricity, natural gas and forklift diesel; error
against the known truth).**

| Policy | Mean absolute % error |
|---|---|
| Statistical estimator only (current default) | 5.46% |
| Best ML challenger always | 4.68% |
| **Gated policy** (ML only where the gate passes; 37% of gaps) | **4.81%** |
| Where the gate passed (64 gaps): statistical vs ML | 6.50% vs 4.73% |

Per model (added in v3.1): mean leave-one-out back-test error — statistical 5.82%, ridge 5.73%, random forest 6.12%. The
best challenger was ridge for 116 gaps and random forest for 59. Against the known truth, where ridge was selected its error
was 4.54% vs 5.82% for the statistical method; where the random forest was selected it was **worse** (4.95% vs 4.76%).
The interface shows these figures in Plant Data and does not claim that every ML model improves on the statistical method.

By stream, ML helped for electricity (7.0% → 4.8%) and forklift diesel (5.6% → 4.9%) but not natural gas (3.7% vs 4.3%),
where the gate mostly kept the statistical estimate. Choosing the better of two challengers on the same back-test is mildly
optimistic; the 90% gate offsets part of that. Repeat on real data before relying on it.

## D · Decision explanation (`mezan_ai/explain.py`, `mezan_ai/llm.py`) — Implemented (language model optional)

**Default (always available).** A deterministic narrative generator builds a fact sheet from engine outputs (recommended
portfolio, expected and base-input NPV, quoted capex, both probabilities and their required levels, risk statistics,
switch points, discount-rate sweep, EVPI/EVPPI/EVSI) and writes six short sections, each naming the engine function it
rests on.

**Optional language model.** Configure with environment variables (`.env.example`): `MEZAN_LLM_PROVIDER` (`openai` for any
OpenAI-compatible endpoint, or `anthropic`), `MEZAN_LLM_API_KEY`, `MEZAN_LLM_MODEL`, optional `MEZAN_LLM_BASE_URL`. No key
is stored in code and no paid service is needed to run Mezan. The model only rewrites the verified fact sheet.

**Number verification.** Every number in the model's text is extracted and compared with the fact sheet (exact values and
their %, million and thousand forms, ±0.6% relative; integers ≤ 12 are treated as counts). Any unmatched number rejects the
whole text; the deterministic narrative is shown with the reason. Tested in `tests/test_ai.py`.

## E · Mezan Intelligence findings (formerly "AI Insights") (`mezan_ai/insights.py`) — Implemented

Rule-based selection and wording of findings from the current engine results, ledger, ML flags and classifier: pending
approvals and refusals, blocked baselines, ML flags, probability margins within two Monte Carlo standard errors, switch
points within 5% of the current value, robust high-sensitivity inputs, and whether information is worth its cost. Each
insight names its source component and evidence. Nothing is hard-coded: the statements change when the results change
(tested).

## What is not implemented

- No machine-learning model predicts emissions, prices, savings or costs.
- No AI component validates numerical results.
- No real-plant training data; all AI evaluation is synthetic.
- EVSI is computed for one measurement only (motor-system audit) — a calculation-engine feature, not AI.
- Investment timing is partially implemented (one project, one price) — calculation engine, not AI.

## References

- Liu, F. T., Ting, K. M., Zhou, Z.-H. (2008). Isolation Forest. *ICDM 2008*, 413–422. https://doi.org/10.1109/ICDM.2008.17
- Pedregosa, F. et al. (2011). Scikit-learn: Machine learning in Python. *JMLR* 12, 2825–2830.
- Iglewicz, B., Hoaglin, D. (1993). *How to Detect and Handle Outliers*. ASQC.
- Hoerl, A. E., Kennard, R. W. (1970). Ridge regression. *Technometrics* 12(1), 55–67. https://doi.org/10.1080/00401706.1970.10488634
- Breiman, L. (2001). Random forests. *Machine Learning* 45, 5–32. https://doi.org/10.1023/A:1010933404324
