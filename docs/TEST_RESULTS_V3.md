# Mezan app v3.0 — test results

**Run:** 18 November 2026, `python -m pytest -q`, Python 3.13.18, Linux, versions in `requirements-lock-v3.txt`
(streamlit 1.67.0, scikit-learn 1.9.1, numpy 2.5.3, pandas 3.0.5, scipy 1.18.1).

**Result: 184 passed, 0 failed, 0 skipped, in 90.8 s.** (Original v2.1 suite in the same environment: 161 passed.)

| File | Functions | Covers |
|---|---|---|
| test_platform.py | 10 | v3 service layer reproduces the saved model outputs exactly; settings validation; budget changes D3 vs D4; switch-point bisection; report contents |
| test_ai.py | 13 | classifier unit safety and accuracy on unseen wording; Isolation Forest applied/not-applied and flags; ML gate never bypasses refusals; LLM number verification rejects invented numbers; insights follow results |
| test_app_v3.py | 10 (21 cases) | every page renders for both facilities without exceptions; approval workflow; unlabelled-export flow; settings, run and reset; MRC labels; dataset separation |
| test_engine, test_decisions, test_timing, test_v11, test_outputs | 53 | original calculation-engine and reproducibility tests (unchanged except the app smoke test) |
| test_a4, test_a5, test_a6 | 60 | original data-quality, methodology-update and independent-validation tests |
| test_v2, test_b | 17 | MRC module and method-notes content; impact scorecard (v2 interface tests removed with the interface) |

Tests changed from v2.1: the guided-demo and Learning/Presentation Mode tests were removed with those features;
`test_outputs::test_streamlit_app_runs` and `test_a4::test_app_has_data_gap_tab_and_blocks_unresolved` were rewritten for
the v3 navigation; `test_v11::test_no_ai_or_ml_claims` now checks the calculation engine only (the AI layer is labelled
and documented separately). No assertion about a numerical result was loosened.

**Not covered by automated tests.** A live language-model endpoint (only a mocked response is tested); real plant data;
browser rendering (checked manually with screenshots); Excel formula agreement where LibreOffice is unavailable
(reported as skipped by `tools/run_tests.py`, not by pytest).
