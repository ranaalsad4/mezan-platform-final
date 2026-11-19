# Mezan | ميزان app v3.1 — competition-ready product experience (model v1.3 unchanged)

## Baseline before changes
Uploaded v3.0 package extracted and identical to the delivered v3.0 build. `python -m pytest -q`: **184 passed** (101 s).

## Changes to model outputs
**None.** No file of the calculation engine (`carbon_iq/*.py`, `carbon_iq/dataquality/*`) changed. Two display-only files in
`carbon_iq/ui/` lost emoji characters in four strings. `tests/test_platform.py::test_defaults_reproduce_saved_run` still
reproduces `outputs/results.json` exactly. The AI evaluation was re-run: every existing figure is identical; three evidence
keys were added (ridge and random-forest back-test errors, how often each was selected, and their true error).

## Discrepancies found and fixed
| Issue | Fix |
|---|---|
| A run started from the stale-results banner was drawn with the old "Assumptions changed" warning (found by a new test) | Both run buttons now apply the settings in their click callback, before any element is drawn |
| `mezan_ai/imputation.py` docstring said 300 random-forest trees; the code uses 120 | Docstring corrected (documentation only) |
| Test margins displayed as e.g. "1,363.5 SE" when a probability is close to 1 | Shown as "> 100 SE", or "all futures pass" when every simulated future passes |
| Negative zero ("SAR -0") in value-of-information tables | Values below 0.5 SAR display as SAR 0 |
| VoI table mixed numbers and text in one column (Arrow conversion warning) | Formatted as text |
| "Mezan AI Insights" implied AI for a rule-based component | Renamed **Mezan Intelligence** (findings selected and worded by rules) |

## Product experience
- **Brand.** Rounded-square icon extracted from the supplied logo (crop, fitted corner radius, anti-aliased transparent mask,
  background colour removed from edge pixels; no redesign) → `assets/mezan_icon_{32..512}.png`, `favicon.png/.ico`. Used in the
  sidebar, global header, browser tab and the HTML and PDF reports. The supplied logo is 580×132 px, so the icon's native size is
  87 px; larger files are high-quality upscales (sharp at the sizes used, ≤ 2× on high-density screens).
- **Palette.** #211540, #493581, #D2B16B, #F1EDF8, #F8F9FC; green/amber/red only for statuses.
- **Navigation.** Icon buttons with a highlighted active page; facility selector with high contrast plus a card showing
  facility, reporting year and data status; icon rail (labels kept for screen readers) between 768 and 1,180 px; Streamlit's
  collapsible sidebar on phones.
- **Global header** with logo, facility, data basis, run identity or *Results out of date*, and the configuration panel.
- **Investment & Scenario Configuration**: four groups; percentages instead of decimals; target shown in tCO₂e/yr; two risk
  requirements explained as separate tests; advanced settings in an expander; reset; change indicator.
- **Pages** rebuilt around management questions: title, one-sentence purpose, prioritised summary, charts, expandable methodology
  and evidence, next action.
- **Decision Intelligence**: eight functional question cards; answers (direct answer, key number, chart, management action,
  method, evidence) generated from the current run; selection persists across reruns and navigation; switching thresholds drawn
  as visual indicators labelled D1 or D4; value of information as EVPI / EVPPI / EVSI cards, "Upper-bound net value (EVPPI −
  cost)"; timing as invest-now vs wait with % and USD/MMBtu inputs; three-layer AI architecture with live execution status.
- **Reports**: one report content model rendered to HTML (shown inline, no nested scrolling) and to a direct multi-page A4 PDF
  (ReportLab: page breaks, repeated table headers, header band, page numbers); lineage and audit exports; AI capability and
  evidence register with method, status, evaluation, live result, limitations and evidence for every capability.
- **Charts**: titles and legends on separate rows, automargins, no clipped data labels, horizontal bars for long names, hover
  text with units, one explanatory sentence under every significant chart.
- **Tables**: readable column names, units, status highlighting, progress bars for probabilities, filters where useful; original
  technical codes kept in expandable evidence.

## New dependency
`reportlab>=4.0` (open source, no service) for the PDF; `pillow` (already installed with Streamlit) for the favicon.

## Tests
New `tests/test_app_v31.py` (20 cases): navigation, full project names, all eight question cards, persistence of the selected
question, answers following a new run, percentage settings and the stale-results guard, the unavailable-data case, operation
without a language model, report exports matching the active run (PDF multi-page), brand assets, MRC configuration, and a
check for unsupported claims. Existing UI tests updated for the new page names and labels; no numerical assertion loosened.
