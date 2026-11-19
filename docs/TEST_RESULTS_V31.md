# Mezan app v3.1 — validation and test results

## Automated tests
**Run:** 19 November 2026, `python -m pytest -q`, Python 3.13.18, Linux. Streamlit 1.67.0, scikit-learn 1.9.1,
ReportLab 5.0.1, NumPy 2.5.3, pandas 3.0.5, SciPy 1.18.1, Plotly 7.1.0, Pillow 12.3.0.

| Run | Result |
|---|---|
| Baseline (uploaded v3.0, before any change) | 184 passed, 0 failed (101 s) |
| **Final (v3.1)** | **203 passed, 0 failed, 0 skipped (112 s)** |

New: `tests/test_app_v31.py`, 20 cases (navigation; full project names; each of the eight question cards; question persistence;
answers follow a new run; percentage settings and the stale-results guard; unavailable data; no language model; report exports
match the active run and the PDF is multi-page; brand assets; MRC configuration; no unsupported claims). Updated for new page
names and labels: `tests/test_app_v3.py`, `tests/test_platform.py` (case of "Limitations"), `tests/test_ai.py` (the overclaim
guard accepts "AI-powered" only on a line that names the Isolation Forest it refers to). No numerical assertion was loosened.
During development the new tests found one real defect (stale warning drawn during a banner-started run), now fixed.

## Output integrity
- Engine files unchanged (directory diff against the upload); saved model outputs reproduced exactly at default settings.
- AI evaluation re-run (`python tools/evaluate_ai.py`): all previous figures identical; three evidence keys added.

## Rendered-page inspection (Chromium via Playwright, Streamlit server)
| Check | Result |
|---|---|
| All six pages, synthetic plant, 1,440 px | Render without exceptions; screenshots reviewed |
| Eight Decision Intelligence answers | Each renders without exceptions; screenshots reviewed |
| MRC facility | Renders; reported and hypothetical labels present |
| 1,024 px (laptop) | Sidebar collapses to an icon rail; no broken words |
| 390 px (phone) | Sidebar collapses; cards, header and hero stack vertically; the workflow tracker scrolls horizontally |
| PDF report | 6 A4 pages at default settings, page breaks, repeated table headers, logo and page numbers (rendered and inspected) |
| Server log | One Arrow mixed-type warning found and fixed |

## Known limitations and unresolved items
- The supplied logo is 580×132 px, so the extracted icon is 87 px natively; the 256 and 512 px files are upscaled. A vector or
  higher-resolution original would give sharper large renderings.
- The workflow tracker scrolls horizontally on phones rather than wrapping.
- Language-model path tested with a mocked model only; not run against a live endpoint.
- Arabic text is not drawn in the PDF (ReportLab does not shape Arabic script without extra packages); the PDF uses "MEZAN".
- Everything listed in Reports & Evidence → Limitations (synthetic data, hypothetical MRC investments, modelled probabilities,
  partial timing, one EVSI, synthetic AI evaluation, not externally validated).
