# Mezan | ميزان app v3.0 — what changed (model v1.3 unchanged)

## Summary

App v3 replaces the v2.1 interface (Learning Mode / Presentation Mode, guided demo, Learning Center, long sidebar of
advanced settings) with one manufacturer-facing platform, **MEZAN | ميزان — AI-Assisted Industrial Investment Platform**,
and adds a labelled AI assistance layer. The calculation engine (`carbon_iq`, model v1.3) is unchanged.

## Changes to original model outputs

**None.** No equation, input, distribution, decision rule, threshold, seed or saved output was changed.

Verification:
- `diff` of `carbon_iq/` against the v2.1 upload: only `demo_view.py` removed (guided demo), plus display-only edits in
  `carbon_iq/ui/` (Learning Mode default off, one table cast to text, chart colours purple/gold).
- `tests/test_platform.py::test_defaults_reproduce_saved_run`: the v3 service layer reproduces `outputs/results.json`
  exactly at default settings (D1–D4 choices, D4 expected NPV SAR 2,557,033, P(target) 0.9999, P(budget) 0.98875, base-input
  NPV SAR 1,563,087, Scope 1+2 9,054 t, target 1,358 t, EVPI, every EVPPI and the EVSI).
- `tests/test_outputs.py::test_outputs_reproducible` (original): the pipeline regenerates identical outputs.

## New analysis helpers (no change to existing results)

- **Switch points refined by bisection** (`mezan_platform.analysis.switching`): the original 41-point sweep
  (`sensitivity.switch_points`) is kept; each change is narrowed to 1e-6 relative. At default settings the deterministic
  choice (D1) switches from A+B+C to A+B when compressed-air savings fall below **19.90%** (base 20.0%) or project C's cost
  exceeds **SAR 352,224** (+0.6%), and to A+C+D when motor-system savings fall below 8.61%. The electricity tariff does not
  change the choice anywhere in 0.18–0.26 SAR/kWh, although it moves NPV most (tornado swing SAR 2.02 M).
- **Discount-rate sweep for the primary rule** (`analysis.discount_switch`): D1 switches to A+B above **6.14%**; the primary
  rule D4 keeps A+B+C up to **10.02%** and then switches to A+B (20,000 scenarios, seed 20261024).

## Reconciliations of figures used in earlier presentation material

| Figure | Explanation |
|---|---|
| Compressed-air EVPPI SAR 30,115 (v2.1 app screenshot) vs SAR 35,954 (presentation) | Same variable, same rule (D3), same seed; different sample size. The v2.1 app defaulted to **5,000** scenarios (EVPPI SAR 30,115); the report run uses **20,000** (SAR 35,954). At 10,000: SAR 35,533. Both are below the assumed SAR 40,000 sub-metering cost. App v3 defaults to 20,000. |
| Carbon-target probability ">99.99%" | The 20,000-scenario run gives **0.9999** (99.99%, i.e. 2 of 20,000 futures miss the target); the independent 200,000-scenario validation gives 0.999955. At 5,000 scenarios the in-sample value is 1.0. |
| "Discount rate 8% or more → A+B" | Holds for the deterministic rule D1 (switch at 6.14%), not for the primary rule D4 (switch at 10.02%). |
| "Compressed-air savings below 20% → A+B" | The exact D1 switch point is 19.90%: the base case (20%) sits 0.5% above it. |

## Interface

- Removed: Learning Mode / Presentation Mode selector, guided demo, Learning Center, "Learn how this works" panels, the
  long advanced-settings sidebar. Method notes (`carbon_iq/learning.py`), the learning guide and validation reports remain
  available as documentation (Reports & Evidence → Documents; `docs/`).
- New navigation: Overview, Plant Data, Emissions, Investment Planner, Decision Intelligence, Reports & Evidence.
- Scenario settings drawer with grouped inputs, units, defaults, tooltips, validation, reset, a change indicator and a
  Run analysis action with progress feedback; simulations rerun only on Run analysis (cached on applied settings).
- Decision workflow tracker (nine steps) on the Overview; Mezan AI Insights on Overview, Plant Data and Decision
  Intelligence.
- Plant-data baseline can feed the analysis ("Approved plant data") only when every gap is resolved and every ML flag has
  been reviewed; otherwise the reference register is used and the interface says so.
- Executive decision report (HTML, printable), results JSON, portfolio and assumption CSVs, lineage, reproducibility table.
- Branding: every visible "CARBON IQ" replaced by Mezan, including file names and the contents of the Word/Excel
  documents; purple/gold theme. The Python package keeps its internal name `carbon_iq` (renaming would change every
  import, test and tool path).

## AI layer (new; see docs/AI_ML_METHODOLOGY.md)

Record classification (rules + TF-IDF/logistic regression), Isolation Forest anomaly detection (advisory), ML estimate
challengers with an evidence gate and reviewer opt-in, grounded explanation with optional language model and number
verification, AI Insights. Evaluated on synthetic data with `tools/evaluate_ai.py`.

## Data-quality corrections

None needed. The existing rules (never zero by default, refusal rules, reviewer approval, lineage) are reused as they were.

## Known limitations carried forward

Synthetic plant data; hypothetical MRC investment scenario; probabilities not calibrated against outcomes; ±7.7% baseline
uncertainty is model-based, not a validated confidence interval; EVSI for one measurement only; investment timing partial;
AI evaluation synthetic only; not externally validated.
