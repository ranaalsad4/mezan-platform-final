# MEZAN | ميزان — AI-Assisted Industrial Investment Platform

<img src="assets/mezan_icon_256.png" alt="Mezan logo" width="72" align="left" style="margin-right:12px">

**App v3.1 · model v1.3 (unchanged) · research prototype.** Mezan helps Saudi manufacturers decide which decarbonisation
projects to fund: it turns incomplete operating records into a reviewed Scope 1 and 2 baseline, evaluates every portfolio of
candidate projects across thousands of simulated futures against a capital budget, a carbon target and two separate risk
requirements, and explains what could change the recommendation and whether better information is worth buying.

> **Status.** Research prototype · synthetic plant and published company data · model estimates, not verified factory
> outcomes · not externally validated · not investment advice.

## Run locally

Requires Python 3.11–3.13 (https://www.python.org/downloads/; on Windows tick "Add Python to PATH").

```bash
cd Mezan
python -m pip install -r requirements.txt      # once, a few minutes (exact tested versions: requirements-lock-v3.txt)
python -m streamlit run app.py                 # opens http://localhost:8501
python -m pytest -q                            # full test suite (~2 minutes)
```

On macOS/Linux use `python3` if `python` is not found. Stop the app with `Ctrl + C`. The first page load runs the default
analysis (20,000 simulated futures, ~10 s); later pages reuse it.

## Run in Google Colab

Upload `MEZAN_Competition_Ready_Platform.zip` to the Colab Files panel, then run (or open `Mezan_Colab.ipynb`):

```python
!unzip -q -o /content/MEZAN_Competition_Ready_Platform.zip -d /content
%cd /content/Mezan
!pip install -q -r requirements.txt
!nohup streamlit run app.py --server.port 8501 --server.headless true > st.log 2>&1 &
import time; time.sleep(10)
from google.colab.output import eval_js; print(eval_js("google.colab.kernel.proxyPort(8501)"))
```

`%cd` must be on its own line. Open the printed link.

## Optional language-model configuration

Mezan is fully usable without any API key: the decision explanation is then a deterministic, rule-based narrative built
from engine outputs, and the interface says so. To let a language model reword that verified fact sheet, copy
`.env.example` to `.env` (never commit it) or set environment variables:

| Variable | Meaning |
|---|---|
| `MEZAN_LLM_PROVIDER` | `openai` (any OpenAI-compatible endpoint) or `anthropic` |
| `MEZAN_LLM_API_KEY` | your key (read from the environment only; never stored in code) |
| `MEZAN_LLM_MODEL` | model name offered by your provider |
| `MEZAN_LLM_BASE_URL` | optional, for OpenAI-compatible endpoints |
| `MEZAN_LLM_TIMEOUT` | optional, seconds (default 30) |

Every number in the model's text is checked against the engine outputs; any unmatched number rejects the whole text and the
deterministic narrative is shown with the reason. Status: Decision Intelligence → *How does Mezan use AI?*

## The application

Brand: the Mezan icon (`assets/`, extracted from the supplied logo without redesign) appears in the sidebar, the global
header, the browser tab (favicon) and the HTML and PDF reports.

| Section | Management question | Contents |
|---|---|---|
| 1 Executive Overview | What is the recommended investment decision? | Recommended portfolio with full project names, expected NPV, capital, both probabilities, Scope 1/2 baseline, data readiness, Mezan Intelligence (ML findings, data-quality warnings, financial findings, recommendation — evidence expandable), decision-workflow tracker reflecting actual completion |
| 2 Plant Data | Can I trust my operational data? | Dataset or CSV upload, AI-assisted stream classification, quality assessment with readable findings (technical codes kept in evidence), Isolation Forest anomaly review, statistical estimates with ranges and reviewer decisions, ridge / random-forest challengers with real evaluation results, annual totals and readiness, audit trail and lineage |
| 3 Carbon & Emissions | Where are my emissions coming from, and how reliable is my baseline? | Footprint summary, breakdown and largest source, energy on a common GJ scale (diesel not converted), model-based uncertainty and its sources, why data quality matters (zero-filling understatement from live outputs), grid-factor sensitivity, emission factors and references |
| 4 Investment Planner | Which projects should I fund with my capital? | Recommendation panel (value vs risk), project catalogue cards, portfolio comparison and why the winner wins, opportunity map, NPV / capex / carbon-reduction uncertainty, decision methodology (D4 primary) in an expander |
| 5 Decision Intelligence | Why is this best, what could change it, is more information worth it? | Eight question cards; each answer gives a direct answer, the key number, a chart, a management action, the method and evidence — all generated from the current run |
| 6 Reports & Evidence | Can I explain, verify and defend it? | Executive Decision Report (PDF and HTML), results JSON, portfolio and assumption CSVs, lineage and audit records, AI capability and evidence register, assumptions, references, limitations, reproducibility, documents |

**Investment & Scenario Configuration** (header, every page): investment objectives (budget in SAR, carbon target in % with
the equivalent tCO₂e/yr), risk requirements (two separate probabilities), financial and energy assumptions (real discount
rate in %, tariff in SAR/kWh, gas price in USD/MMBtu) and advanced simulation settings (scenario count, seed, target
convention, reference vs approved operational data). Editing never reruns the simulation; **Run investment analysis**
does. While edited settings have not been run, every page shows a *Results out of date* warning with a run button.

**Facilities.** *Synthetic Saudi metal-fabrication plant* — every input hypothetical. *Ma'aden Rolling Company (MRC)* —
2025 energy and emissions as reported by Ma'aden (Sustainability Data Book 2025, PDF page 5); every investment number is a
hypothetical Mezan scenario, not a Ma'aden value, plan or endorsement.

## What is AI and what is calculation

| Component | Technique | Status |
|---|---|---|
| Record classification | Keyword + unit rules, then TF-IDF + logistic regression (scikit-learn) when rules cannot decide; reviewer confirms | Implemented |
| Anomaly detection | Isolation Forest on month-level intensity features, beside the robust z-score rules; advisory flags, reviewer confirms/dismisses | Implemented (advisory) |
| Missing-data assistance | Ridge and random-forest challengers vs the statistical estimator, same back-test; evidence gate + reviewer choice | Implemented (gated, opt-in) |
| Decision explanation | Deterministic narrative from engine outputs; optional language model with number verification | Implemented (LLM optional) |
| Mezan Intelligence findings | Rule-based selection and wording of current findings, each with its source | Implemented |
| Emissions, NPV/IRR/payback/MAC, Monte Carlo, optimisation, chance constraints, sensitivity, switching, value of information, timing | Calculation engine (`carbon_iq`, model v1.3) | AI does not compute or validate these |
| Investment timing | Decision tree + GBM trigger, one project and one price | Partially implemented |
| EVSI | Motor-system audit only | Implemented for one measurement |

Details, evaluation and limits: `docs/AI_ML_METHODOLOGY.md`. Evaluation results (synthetic): `outputs/ai/ai_evaluation.json`
(`python tools/evaluate_ai.py`). What changed: `docs/CHANGES_V3.md` (v3.0) and `docs/CHANGES_V31.md` (v3.1). Demo script: `docs/DEMO_GUIDE_V3.md`.
Test results: `docs/TEST_RESULTS_V31.md`.

## Code structure (v3.1)

```
app.py              entry point: sidebar navigation, global header, configuration panel, routing to the six workspaces
assets/             Mezan icon (transparent PNG 32–512 px, native crop), favicon, original logo
mezan_ui/           interface only: theme, state and caching, settings drawer, components, pages/ (one module per workspace + MRC)
mezan_platform/     service layer without Streamlit: analysis (runs the engine for given settings), datasets, labels, report
mezan_ai/           AI layer: classifier, anomaly, imputation, explain, llm, insights, capabilities; data/ training corpus
carbon_iq/          calculation engine, model v1.3 — unchanged in v3 (except two display lines in carbon_iq/ui)
tools/              evaluate_ai.py, build_classifier_corpus.py and the earlier run/validation/report tools
tests/              test_platform.py, test_ai.py, test_app_v3.py and the original engine, data-quality and validation suites
```

---

## Technical documentation of the calculation engine (Phases A1–B; model v1.3, unchanged in v3)

### Mezan — Carbon Investment Decision Support (research prototype, model v1.3 + A4 missing-data module, mathematically checked in A6)

Mezan turns incomplete operational, energy, supplier and financial data into traceable emissions estimates and
economically justified decarbonization investment recommendations. It is applied to a **hypothetical** medium-sized
metal-fabrication plant in the Riyadh region.

**Status:** research prototype. The facility data are synthetic, and the project costs are illustrative assumptions
anchored to public sources. Outputs are not a verified GHG inventory, not investment advice and not a
production-ready industrial system.

**Calculation engine: methods, not machine learning.** The engine (`carbon_iq`) uses carbon accounting, financial analysis,
integer optimisation, Monte Carlo simulation, value-of-information and real-options analysis; it contains no machine-learning
model. The separate, labelled AI assistance layer added in app v3 (`mezan_ai`) is described above and in
`docs/AI_ML_METHODOLOGY.md`; it never produces the engine's quantitative results.

## What it answers

| Question | Method | Module |
|---|---|---|
| Are the activity data complete and plausible, and what if they are not? | Rule-based checks (units, duplicates, invalid values, robust z-score outliers, missing vs legitimate zeros); statistical gap estimation with leave-one-out prediction intervals and refusal rules; reviewer approval; lineage ledger (A4) | `dataquality/` |
| What are the emissions and how reliable are they? | GHG Protocol accounting; first-order uncertainty propagation, checked by Monte Carlo | `engine.py` |
| Which investments are attractive? | NPV, payback, IRR, marginal abatement cost (SAR/tCO2e) | `engine.py` |
| Which combination fits the budget? | Binary integer program (scipy HiGHS), checked by exhaustive enumeration; compared with ranking rules | `optimize.py` |
| How do uncertainty and data gaps change the answer? | Monte Carlo over 20,000 joint scenarios; three decision objectives; capital-cost risk | `uncertainty.py`, `decisions.py` |
| What information is worth collecting first? | EVPI, EVPPI and EVSI under the same decision rule | `voi.py` |
| Which assumptions drive the answer? | Tornado chart, first-order variance indices, switch points, discount-rate robustness; tariff and grid-factor scenarios | `sensitivity.py`, `decisions.py` |
| Invest now or wait? | Reform decision tree (prototype); KAPSARC DP49-style log-OU least-squares Monte Carlo and GBM closed-form trigger (extension) | `timing.py` |

All inputs, with their value, unit, status (verified, derived, transferred, provisional or hypothetical), evidence class
(external, derived or hypothetical; none measured), source, publication date, effective period, geography and
distribution, are defined in one place: `carbon_iq/assumptions.py`.

## Decision rules

All rules use the same 20,000 scenarios (seed 20261024). The carbon target is counted against the **fixed reporting
baseline** (management decision, 25 Oct 2026); baseline and emission-factor uncertainty are sensitivity scenarios.
Chance constraints are imposed at a sampling-tightened level (0.9035 for 90% with 20,000 scenarios) and validated on an
independent 200,000-scenario sample (seed 20261025).

| ID | Rule | Role |
|---|---|---|
| D1 | max NPV at base inputs, quoted capex ≤ budget, reduction ≥ target | comparison |
| D2 | max E[NPV], quoted capex ≤ budget | comparison |
| D3 | D2 + P(target met) ≥ 90% | carbon-only rule |
| D4 | D3 + P(actual capex ≤ SAR 5M) ≥ 90% | **primary recommendation rule** |
| S1 / S2 | D3 with sampled emission factors / with an uncertain baseline | sensitivity |

If D4 has no feasible portfolio, none is forced: the model reports the minimum budget that makes it feasible, the
budget curve and the choices at alternative risk thresholds (`outputs/minimum_budget.csv`, `budget_curve.csv`,
`risk_thresholds.csv`). Both probabilities (target and budget compliance) are reported for every portfolio.

## Missing-data intelligence (Phase A4, refined 26 Oct 2026)

`carbon_iq/dataquality/` checks monthly activity records (long format: site, period, stream, value, unit), proposes
estimates for gaps and feeds the reviewed annual totals, with their estimation uncertainty, into the unchanged
emissions, Monte Carlo and portfolio engines. All A4 validation uses **synthetic** data.

- **Never zero by default.** Blank, absent or unusable values are *missing*; zeros are accepted only for intermittent or
  lumpy streams or a documented shutdown. Unresolved gaps block the decision.
- **Estimation** (statistical, no machine learning): production intensity, seasonal history, mean of measured months;
  the method with the lowest leave-one-out back-test error is proposed. Refusals: fewer than 6 measured months, more
  than 3 consecutive missing months, back-test error above 25%, no eligible method, or an operational change (below).
- **Operational change detection:** a permutation test (p < 0.01, shift ≥ 10%) on the quantity each method assumes
  constant. After a change, only same-regime months are used; estimation is refused with fewer than 4 such months or
  when the gap sits at the change point. A reviewer may override (labelled in the lineage).
- **Calibrated uncertainty:** 95% prediction intervals widened by a split-conformal factor (1.090) and annual totals
  combined with a calibrated within-stream correlation (0.12), both fitted on synthetic calibration facilities
  (`tools/calibrate_a4.py`) and checked on six held-out synthetic sets. Not yet validated on real data.
- **Decision integration:** estimated parts enter the Monte Carlo; an estimated baseline also makes the 15% target
  uncertain. Complete data reproduce the register-based pipeline exactly (v1.3; v1.2 under its profile).
- **Decision stability** (`stability.py`): margins to every threshold in Monte Carlo standard errors, agreement over
  plausible true datasets, and switch points; the dashboard warns when a rule is unstable (under v1.3 inputs D1 is data-unstable on the demo estimates because project C is marginal; under v1.2 inputs D3 was).
- **Value of information** (`integrate.information_value`): pre-posterior value of collecting each missing record
  under D2, D3 and D4 with hypothetical staff-time costs and net value.
- **Lineage:** the uploaded table is kept unchanged (SHA-256); every estimate, warning, decision and reviewer is logged.

```bash
python tools/calibrate_a4.py      # optional: refit calibration (outputs/a4/calibration.json; ~5 min)
python tools/run_a4.py            # demo, stability, value of information, validation -> outputs/a4/ + Mezan_A4_Data_Quality.xlsx (~25 min)
python tools/run_a4.py --fast     # quick check (~4 min)
```

In app v3 this workflow is the **Plant Data** workspace (findings, reviewer decisions, approved baseline) and the
**Emissions** scenario comparison (register, gaps as zero, approved estimates). Report: `docs/Mezan_A4_Missing_Data_Report.docx`.

## Competition demonstration

App v3 has no separate demo mode: the live workspaces are the demonstration. A 3–5 minute script is in
`docs/DEMO_GUIDE_V3.md`. The Phase B guided demo, its script and screenshots (v2 interface) are archived in `docs/phase_b/`;
the impact scorecard (`python tools/build_phase_b.py`) is unchanged.

## Independent validation (Phase A6)

`independent/indep.py` recomputes the inventory, cash flows, NPV/IRR/payback/MAC, all 64 portfolios and the Monte Carlo
decisions with separately written code (it does not import `carbon_iq`); `tools/run_a6.py` compares it with the model and
with published benchmarks and closed forms; `tools/build_a6_workbook.py` repeats the deterministic chain in spreadsheet
formulas. Everything agrees within numerical or Monte Carlo precision; four minor defects were fixed (see ISSUE_LOG A6).
This is mathematical and synthetic validation, **not** validation on real industrial data.

```bash
python tools/run_a6.py               # ~10 min -> outputs/a6/ (CSV, a6_results.json, charts)
python tools/build_a6_workbook.py    # independent spreadsheet + LibreOffice recalculation
python tools/build_a6_tables.py      # validation tables workbook and charts
python tools/consistency_a6.py       # Python / Excel / Streamlit / Word consistency scan
```

## Engine tools (Python 3.11–3.13)

```bash
pip install -r requirements.txt          # minimum versions; exact tested versions: requirements-lock.txt
python run_all.py                        # ~30 s, ~1 GB RAM: outputs/ (CSV, JSON, charts) + Mezan_Data_Model.xlsx
python tools/run_tests.py                # full regression suite -> outputs/test_summary.json
python tools/fault_injection.py          # shows that the tests catch 28 deliberate errors
python tools/build_a5_register.py        # A5 source register and before/after workbooks -> outputs/a5/
streamlit run app.py                     # interactive prototype at http://localhost:8501
```

- `python run_all.py --fast` skips the slower real-options trigger scans.
- The Excel workbook's formulas are recalculated with LibreOffice (`carbon_iq/recalc.py`) when it is installed; the
  result is recorded in `outputs/excel_recalc.json`. Without LibreOffice the two Excel-agreement tests are reported
  as skipped (never silently), and Excel recalculates the file when it is opened.

### Google Colab

Upload `Mezan.zip` to the Colab file panel (or open `Mezan_Colab.ipynb`), then run:

```python
!unzip -q -o /content/Mezan.zip -d /content
%cd /content/Mezan
!pip install -q -r requirements.txt
!apt-get -qq update > /dev/null && apt-get -qq install -y libreoffice-calc > /dev/null   # optional: Excel formula checks
!python run_all.py
!python tools/run_tests.py
!python tools/run_a4.py --fast
!python tools/run_a6.py emissions finance optimization   # optional: A6 independent checks (fast sections)
!nohup streamlit run app.py --server.port 8501 --server.headless true > st.log 2>&1 &
from google.colab.output import eval_js; print(eval_js("google.colab.kernel.proxyPort(8501)"))
```

`%cd` must be on its own line: in a line that starts with `!` the whole line goes to the shell, so a `%cd` after
`&&` is not executed (this was the v1.0 bug).

## Reproducing results

- All results are deterministic for a given seed: Monte Carlo seed 20261024, LSMC seed 2026. Distributions added
  in v1.1 use an independent random stream, so the v1.0 draws of every other input are unchanged.
- `outputs/manifest.json` lists SHA-256 hashes of every data output (and of the charts, which depend on the
  matplotlib version); `tests/test_outputs.py` checks reproducibility. Hashes match exactly on repeated runs and in
  the `requirements-lock.txt` environment; at the minimum versions (NumPy 2.0, Python 3.11) the last floating-point
  digit of some values differs (largest absolute difference found: below 1e-9 SAR), with identical decisions and figures.
- `tests/test_outputs.py` recalculates the workbook and checks that its live Excel formulas equal the Python
  engine (baseline, uncertainty, NPVs, NPV() cash flows, the 64-portfolio optimum, decision objectives, decision tree
  and GBM trigger).
- `tools/crosscheck.py` compares Python, Excel and the Word report figure by figure; `tools/compare_versions.py`
  lists every changed assumption and its effect on the results.

## Key results (synthetic case, model v1.3 — illustrative, not advice)

| Item | Value |
|---|---|
| Baseline emissions | Scope 1 2,178 · Scope 2 6,876 · Scope 3 11,723 tCO2e/yr; Scope 1+2 ±7.7% (95%); target 1,358 t/yr |
| D1 Deterministic optimum | A+B+C (solar + motors + compressed air): NPV SAR 1.56M at base inputs, 1,755 t/yr |
| D2 Highest expected NPV | A+B+C: E[NPV] SAR 2.56M |
| D3 Carbon ≥90% (validated) | A+B+C: target met 99.99% (validation 99.996%) |
| **D4 Carbon ≥90% + budget ≥90% (primary)** | **A+B+C, feasible at SAR 5M**: within budget 98.9% (validation 98.8%); quoted capex SAR 4.05M |
| What drives the change from v1.2 | The Riyadh rooftop-PV cost benchmark (SAR 2,500/kWp). With the v1.2 PV cost (3,750) D1 is A+B and D4 is infeasible (needs SAR 5.44M) |
| Fragility | C is marginal (NPV SAR 16.5k). App v3 bisection: the deterministic choice (D1) switches to A+B if compressed-air savings fall below 19.90% (base 20%), project C costs more than SAR 352,224 (+0.6%) or the discount rate exceeds 6.14% (base 6%); the primary rule D4 keeps A+B+C up to a discount rate of 10.0% (bisection to 0.01 percentage point) |
| Industrial tariff | 0.18 SAR/kWh 2018–2026 (reference); adjustment from 1 Jan 2027 officially announced, 0.23 reported (rates not retrieved); A+B+C in all four tariff scenarios |
| Grid emission factor | 0.573 tCO2e/MWh derived from the KSA BTR1 (2021 inventory) and GASTAT 2021 generation |
| Information value | EVPI SAR 56k; motor audit EVSI 0; compressed-air sub-metering EVPPI SAR 36k vs cost SAR 40k |
| Heat-recovery timing | Wait for the gas-price decision (investing now: NPV −SAR 220k) |

v1.2 results remain reproducible with `assumptions.use_profile("v1.2")`; `outputs/a5_attribution.csv` shows the effect
of each A5 change alone. A5 deliverables: `outputs/a5/` (source register, before/after comparison) and
`docs/Mezan_A5_Carbon_Financial_Methodology.docx`.

**Validated** = calculations, Python/Excel/Word agreement, reproducibility, injected-fault detection and out-of-sample
feasibility of the reported choices. **Illustrative** = everything that depends on the synthetic facility data,
judgement-based ranges, and the unconfirmed tariff and grid factor.

## Folder

```
carbon_iq/        engines (assumptions, engine, optimize, uncertainty, decisions, voi, sensitivity, timing, pipeline,
                  charts, workbook, recalc); dataquality/ (quality, estimate, integrate, stability, synth, validate, workbook_a4)
run_all.py        end-to-end run      app.py   Streamlit interface      tests/   pytest suite
tools/            run_tests.py, fault_injection.py, crosscheck.py, compare_versions.py, calibrate_a4.py, run_a4.py,
                  build_a5_register.py, run_a6.py, build_a6_workbook.py, build_a6_tables.py, consistency_a6.py
independent/      separately written re-implementation used by A6 (does not import carbon_iq)
report/           build.js + lib.js: regenerate the Word report (node, npm package "docx")
outputs/          CSV tables, results.json, manifest.json, test_summary.json, fault_injection.json, charts/*.png
outputs/phase_b/  Phase B impact scorecard and trace check
outputs/a6/       A6 validation results, independent workbook, validation tables, charts
outputs/a5/       A5 source register, before/after comparison, a5_summary.json
outputs/a4/       A4 demo, lineage, decision comparison, data VOI, validation study, charts
docs/             A2-A6 reports and matrices; AI_ML_METHODOLOGY.md, CHANGES_V3.md, DEMO_GUIDE_V3.md, TEST_RESULTS_V3.md
docs/phase_b/     archived v2 guided-demo script, screenshots, architecture diagram
docs/v2/          v2 method guide (.docx/.md), MRC source register (.xlsx/.csv), methods diagram, v2 test results
carbon_iq/mrc.py  v2 MRC case study (reported data, recalculation checks, hypothetical scenario on the unchanged engine)
carbon_iq/learning.py   method notes for every method (status, 7 elements, code references; documentation, not shown in the app)
carbon_iq/ui/     MRC screens and source panels reused by mezan_ui; learning_center.py kept only for tools/build_v2_docs.py
.streamlit/       Mezan colour theme (purple / gold)
outputs/ai/       AI evaluation (tools/evaluate_ai.py)
Mezan_Data_Model.xlsx   Mezan_A4_Data_Quality.xlsx   Mezan_Complete_Project.docx   Mezan_Colab.ipynb   CHANGELOG.md   ISSUE_LOG.md
```
