# Mezan v2.1 — test results and remaining limitations (30 October 2026)

## Summary

| Check | Result |
|---|---|
| Phase B package as supplied (before v2) | 127 passed |
| v2.0 | 153 passed |
| **v2.1 full suite** (`python tools/run_tests.py`; Streamlit 1.66.1, pandas 3.1.0, NumPy 2.5.4) | **161 passed, 0 failed, 0 skipped** (1 warning, see V2-09) |
| Minimum supported versions (Streamlit 1.49.0, pandas 2.2.2, NumPy 2.0.0): `tests/test_v2.py` + `tests/test_b.py` | **38 passed** |
| Fault injection (`python tools/fault_injection.py`) | **28 / 28** deliberate errors detected |
| Analytical modules changed in v2 / v2.1 | **None** (`engine`, `optimize`, `uncertainty`, `decisions`, `voi`, `sensitivity`, `timing`, `pipeline`, `assumptions`, `dataquality/`, `independent/` identical to Phase B) |
| Synthetic results | Identical to the saved v1.3 run (A+B+C under D1–D4) |
| App launch | `streamlit run app.py` served HTTP 200; pages opened in a real browser; screenshots in `docs/v2/screenshots/` (11–14 show the v2.1 MRC screens) |

## What the 8 new v2.1 tests check (34 tests in `tests/test_v2.py`)

1. **Every method** has a numerical example, at least one methodology reference, code references whose main function's real source can be displayed, and a 20-second judge script (40–75 words).
2. **Scope 1 reconciliation:** CO2 + CH4/N2O = recalculated total; gap 140–150 t; gap < 10% of the uncertainty; GWP set changes < 5 t; the closing gas factor lies inside the IPCC range; a gross-CV reading would not match.
3. **Scope 2 labels:** the implied factor is "calculated" and not verified; the national average is not a utility-verified factor; no independently verified factor is available.
4. **Budget never raised:** with a SAR 40M budget the budget stays SAR 40M, no plan is forced, and minimum budgets above SAR 40M are reported; with a 20% target the app states the target is unreachable at any budget.
5. **Knife-edge flag** for the default MRC scenario (choice within 2 Monte Carlo standard errors of the budget rule).
6. **Synthetic app**, budget set to SAR 1M: the budget input keeps SAR 1M and the error explains the minimum budget and that Mezan does not raise it.
7. **Datasets stay separate:** MRC calculations leave the synthetic register unchanged; synthetic Presentation-Mode pages contain no "Ma'aden", "MRC" or "160,632"; MRC pages contain no synthetic headline numbers ("9,054", "1,358"); switching dataset and back leaves every synthetic metric identical.
8. **MRC guided demo** tells one story: "story so far" strip, the reported baseline 160,632 t, a recommendation for the hypothetical scenario and its limitations.

The earlier 26 v2 tests (MRC import and unit conversions, labelling, code references, both modes × both datasets × all pages, Next button) still pass.

## Method status (judged from the code)

17 fully implemented · 1 partially implemented (investment timing: one project, gas price only) · 3 not implemented (ROI, multi-criteria decision analysis with weights, risk register). Single-criterion ranking is listed separately as a comparison baseline and is not described as MCDA.

## Citations

MRC figures were read directly from the supplied data book (PDF pages 2, 5, 10, 11–13). Literature references were confirmed by web search (28–30 Oct 2026); the tests check link format only — open each link before quoting.

## Remaining limitations

1. **MRC Scope 2 factor:** 0.335 tCO2e/MWh is back-calculated from Ma'aden's report (derived, not verified); 0.573 is derived from national statistics. No independently verified factor for MRC's supply is available (V2-01).
2. **Scope 1 gap cause:** consistent within uncertainty; most likely a slightly different gas factor, but unconfirmed without Ma'aden's factors (V2-08). Energy basis (net vs gross) inferred, not stated (V2-02).
3. **MRC investment scenario is hypothetical** (sizes, scaled costs, end-use shares, SAR 70M budget, 8% target). Its recommendation (A+B+C) is a **knife-edge**: it needs SAR 69.9M of SAR 70M; the clearly passing alternative is A+C+D with a much lower expected NPV (V2-03, V2-07).
4. **Not run for MRC:** missing-data estimation (no monthly data), value of information and real options (no real cost or uncertainty data) (V2-04).
5. Pre-existing cosmetic RuntimeWarning in `dataquality/stability.margins` when no plan is feasible (V2-09; validated code left unchanged).
6. Carried: synthetic plant for the full method chain; missing-data calibration on synthetic data; independent sampling of inputs; no stakeholder interviews; real Google Colab run not confirmed; not externally validated.
