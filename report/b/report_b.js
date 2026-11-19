// Mezan_Phase_B_Competition_Package.docx — B1 demonstration, B2 feasibility, B3 impact, rubric mapping, limitations.
// Usage: node report/b/report_b.js <project dir> <out.docx>. All numbers are read from the run outputs.
const fs = require("fs");
const path = require("path");
const L = require(fs.existsSync(path.resolve(__dirname, "../lib.js")) ? path.resolve(__dirname, "../lib.js") : path.resolve(__dirname, "../../full/report/lib.js"));
const { D, P, H1, H2, B, TT, callout, table, Cap, fig } = L;
const [, , ROOT, OUT] = process.argv;
const J = f => JSON.parse(fs.readFileSync(path.join(ROOT, f), "utf8"));
const R = J("outputs/results.json"), A6 = J("outputs/a6/a6_results.json"), T = J("outputs/test_summary.json");
const SCL = J("outputs/phase_b/scorecard_metrics.json"), CHK = J("outputs/phase_b/scorecard_check.json"), DS_ = J("docs/phase_b/demo_script.json");
const SC = Object.fromEntries(SCL.map(r => [r.id, r]));
const ds = Object.fromEntries(R.decision_scenarios.map(d => [d.id, d])), D4 = ds.D4;
const f0 = v => v == null ? "—" : Math.round(v).toLocaleString("en-US");
const fm = v => v == null ? "—" : (v / 1e6).toFixed(2);
const pc = (p, d = 1) => p == null ? "—" : (p >= 1 - 0.5 * Math.pow(10, -(d + 2)) && p < 1 ? ">" + (100 - Math.pow(10, -d)).toFixed(d) + "%" : (100 * p).toFixed(d) + "%");
const SHOT = path.join(ROOT, "docs/phase_b/screenshots");
const cmp = CHK.comparison, mac = cmp.find(c => c.method.startsWith("Rank by abatement")), ciq = cmp[cmp.length - 1];
const cv = R.voi.find(v => v.parameter === "c_saving_frac");
const pvHi = R.pv_capex_scenarios.find(x => x.id === "P1");
const dr = Object.fromEntries(R.discount_robustness.map(d => [d.rate, d]));

const kids = [];
const add = (...x) => kids.push(...x.flat());
add(new D.Paragraph({ spacing: { after: 60 }, children: [new D.TextRun({ text: "Mezan — Phase B Competition Package", bold: true, font: L.FONT, size: 36, color: L.NAVY })] }),
  P(`B1 signature demonstration · B2 feasibility and scalability · B3 impact quantification · WE Rise rubric mapping · 26 October 2026 · model v${R.meta.model_version} (A6-checked)`, { r: { color: L.GREY } }));
add(callout([
  `**What this package is.** A competition-ready demonstration and evidence pack built on the existing, validated Mezan prototype. Nothing in the model was changed: same inputs, equations, constraints and results as the A6-validated v1.3 package. One presentation tab ("▶ Guided demo") and a scorecard builder were added.`,
  `**Headline (synthetic case, modelled):** for a hypothetical Riyadh metal-fabrication plant with SAR 5 M and a 15% target, Mezan recommends **${D4.portfolio}** (rooftop solar, efficient motors with variable-speed drives, compressed-air leak repair): ${f0(SC.I1.value)} tCO₂e/yr Scope 1+2 reduction against a ${f0(SC.S2.value)} t target, quoted capex SAR ${fm(SC.C1.value)} M, expected NPV SAR ${fm(SC.F2.value)} M, target met in ${pc(SC.P1.value, 2)} and budget kept in ${pc(SC.P2.value)} of 200,000 validation scenarios.`,
  `**Honest limits:** synthetic facility; no deployment, customers or verified savings; costs other than solar hypothetical; result depends on one solar cost benchmark and on compressed-air savings; not yet run on real Google Colab (A1-01); no real industrial validation (A4-01).`]));

// ---------------------------------------------------------------- B1
add(H1("B1 — Signature live demonstration"));
add(P(`**Scenario (reproducible).** Register defaults of model v${R.meta.model_version}; Monte Carlo ${R.meta.scenarios.toLocaleString("en-US")} scenarios, seed ${R.meta.seed}, validation ${R.meta.n_validation.toLocaleString("en-US")} scenarios; missing-data demo = the A4 synthetic dataset (a degraded copy of a known truth). The guided demo reads these saved outputs, so it shows exactly the validated numbers on any machine (checked by tests/test_b.py) and needs no live computation. The other ten tabs stay available for live what-if questions.`));
add(TT("Demo script (about 2 minutes 50 seconds)"));
add(table(["Time", "Step / screen", "What to say", "Point to make"], DS_.steps.map(s => [s.time, `${s.step}\n(${s.screen})`, s.say, s.point]), [900, 1500, 5000, 2506], { size: 12 }));
add(TT("Screens"));
[[1, "Step 1 — the factory, its emissions, budget and target."], [2, "Step 2 — incomplete records detected; decision not ready."], [3, "Step 3 — estimates with intervals and warnings; zero-filling shown as the wrong practice."],
 [5, "Step 5 — traditional ranking vs Mezan."], [6, "Step 6 — probability of meeting the target and staying within budget."], [7, "Step 7 — value of collecting information before investing."], [8, "Step 8 — recommendation and trade-offs."]]
  .forEach(([i, c]) => add(fig(SHOT, `demo_step${i}.png`, `Figure B1.${i} — ${c}`, 560)));
add(Cap("Step 4 (project table) is in docs/phase_b/screenshots/demo_step4.png. All screenshots captured from the live app with docs/phase_b/capture_screenshots.js (Playwright); re-capture after any rerun."));
add(TT("Pre-flight checklist"));
DS_.preflight.forEach(x => add(B(x)));
add(TT("Backup walkthrough if the live dashboard fails"));
DS_.backup.forEach(x => add(B(x)));
add(TT("Google Colab"));
DS_.colab.slice(0, -1).forEach(x => add(P(x, { r: { font: "Consolas", size: 17 } })));
add(P(`**${DS_.colab[DS_.colab.length - 1]}**`));

// ---------------------------------------------------------------- B2
add(H1("B2 — Feasibility and scalability", true));
add(fig(path.join(ROOT, "docs/phase_b"), "architecture.png", "Figure B2.1 — Mezan architecture: every box is existing, tested prototype code; a pilot adds data templates and a named reviewer.", 600));
add(TT("Minimum data requirements for an industrial pilot"));
add(table(["Data", "Granularity and period", "Typical source / owner", "Why", "Prototype handles today"], [
  ["Grid electricity", "Monthly kWh or MWh, 24 months (current + previous year)", "SEC bills / account portal — energy manager", "Scope 2; seasonal-history estimation needs the previous year", "Yes (CSV, unit conversion, gap estimation)"],
  ["Natural gas / LPG", "Monthly GJ or m³ with heating value, 24 months", "Supplier statements — utilities", "Scope 1; heat-recovery case", "Yes (GJ; other units need a conversion entry)"],
  ["Diesel", "Monthly litres by use (vehicles, generators), 24 months", "Fuel cards, logs — logistics / maintenance", "Scope 1; forklift case", "Yes"],
  ["Production output", "Monthly tonnes or units", "ERP / production reports", "Intensity-based estimation of gaps", "Yes"],
  ["Purchased steel (or main material)", "Monthly tonnes by supplier", "Procurement", "Scope 3 Cat 1; supplier switch", "Yes (generic factors; supplier EPDs if available)"],
  ["Candidate projects", "Capex quote, expected savings, life, O&M", "Engineering / suppliers", "Investment options (replace hypothetical costs)", "Yes (register entries)"],
  ["Finance rules", "Budget, hurdle (discount) rate, target, required confidence", "Finance / management", "Decision rule", "Yes (sidebar and register)"],
  ["Sub-metering (optional)", "Compressed-air or motor-system kWh for 1–3 months", "Facility engineering", "Highest value of information in the case", "Value computed; data entry as a register update"],
], [1500, 2000, 2000, 2100, 2306], { size: 11 }));
add(TT("Pilot roadmap (one facility, about 16 weeks)"));
add(table(["Stage", "Weeks", "Activities", "Responsible", "Acceptance criteria"], [
  ["0 · Agreement and scoping", "1–2", "Data-sharing agreement and NDA; select streams and projects; name the reviewer", "Facility sponsor, Mezan team", "Signed agreement; data list and reviewer named"],
  ["1 · Data onboarding", "3–5", "Export 24 months of records into the CSV template; run data-quality checks; resolve findings with the reviewer", "Energy manager (data), Mezan team (checks)", "All findings decided and logged; every month accounted for; annual totals reconcile with bills within 1%"],
  ["2 · Baseline and back-test on real data", "6–8", "Compute baseline; mask known months and measure estimation error and interval coverage (closes A4-01 for this site)", "Mezan team; reviewer signs off", "Baseline agreed by the facility; masked-month coverage of 95% intervals reported with confidence interval; errors documented"],
  ["3 · Project options and costs", "8–12", "Replace hypothetical costs with supplier quotations; confirm tariff and gas price; optional sub-metering", "Engineering, procurement, finance", "Every project input labelled measured / quoted / external; no hypothetical cost left in the decision set"],
  ["4 · Decision analysis and workshop", "13–14", "Run portfolio, probabilities, sensitivity and value of information; management workshop", "Mezan team, management", "Python, Excel and report figures agree; trade-offs presented; management decision recorded"],
  ["5 · Review and go / no-go", "15–16", "Independent review of the method and inputs; lessons; decide on scale-up", "Independent reviewer, sponsor", "Review report; list of corrections; go / no-go"],
], [1700, 700, 3200, 1900, 2406], { size: 11 }));
add(TT("Data privacy, cybersecurity, auditability and human review"));
add(B("**Data minimisation and location.** The model needs operational totals, not personal data. Driver or staff names in fuel logs are removed before upload. The prototype runs locally (laptop or the facility's server); no data leave the facility unless the facility chooses a cloud host. If any personal data are processed, Saudi Arabia's Personal Data Protection Law applies (enforceable since 14 September 2024; regulator SDAIA; transfers abroad need approved safeguards) [Clyde & Co, 10 Sep 2024]."));
add(B("**Cybersecurity.** For a facility that is part of critical national infrastructure, the NCA Essential Cybersecurity Controls ECC-2:2024 apply to the hosting and access set-up [Clyde & Co, 16 Jan 2025]; the prototype itself has no user management or encryption, so a production version would run inside the facility's controlled environment with its access controls."));
add(B("**Auditability.** Uploaded files are kept unchanged and fingerprinted (SHA-256); every estimate, warning, reviewer decision and override is recorded in a lineage table; all inputs live in one source register with evidence class, date and URL; run outputs carry a hash manifest; Python, Excel and Word figures are cross-checked automatically."));
add(B("**Human review.** No estimate enters a decision without reviewer approval; flagged operational changes need an explicit, labelled override; the tool reports options, probabilities and trade-offs — management decides."));
add(TT("Key implementation risks and mitigations"));
add(table(["Risk", "Effect", "Mitigation"], [
  ["Records incomplete or in many formats", "Delays; biased baseline", "CSV template; data-quality engine; estimates only with reviewer approval; gaps never set to zero"],
  ["Estimation less accurate on real data than on synthetic data", "Wrong totals", "Stage 2 back-test on masked real months before any decision; refit calibration factors on the facility's data"],
  ["Hypothetical costs and savings", "Wrong portfolio", "Supplier quotations and sub-metering in stage 3; value of information shows which matter"],
  ["Tariff or gas-price changes", "NPV changes", "Scenarios already built in (18–26 halalas; three gas prices); rerun when official schedules are published"],
  ["Over-trust in probabilities", "False confidence", "Probabilities shown with their assumptions; independence of inputs stated; sensitivity and switch points shown"],
  ["Prototype software limits (single site, no access control, English only)", "Not production-ready", "Pilot runs in a controlled environment; production requirements listed below"],
  ["Not yet run on real Google Colab", "Demo or pilot set-up failure", "Rehearse once on Colab and on a clean laptop before the competition (A1-01)"],
], [2600, 2000, 5306], { size: 11 }));
add(TT("Adapting to another Saudi facility or sector"));
add(B("**Another manufacturing plant:** replace the activity data and project list in the register; the Saudi grid factor, fuel factors, tariff and gas scenarios are reused; no code change."));
add(B("**Energy-intensive industries (cement, steel, petrochemicals):** add process (IPPU) emission sources and their factors, the intensive-industry tariff categories, and the relevant project types; the accounting, optimisation, risk and information-value engine is unchanged."));
add(B("**Several sites:** run per site today; a joint multi-site budget needs a small extension of the optimiser (more binary variables, same method)."));
add(TT("Existing prototype capabilities vs production requirements"));
add(table(["Area", "Exists in the prototype (tested)", "Needed for production"], [
  ["Data input", "CSV/Excel upload, unit conversion, 8 activity streams, gap detection and estimation with lineage", "Connectors (ERP, utility portals, meters); more units and streams; Arabic interface"],
  ["Accounting", "Scope 1, 2 (location-based), Scope 3 Cat 1 and 4; Saudi grid factor", "Refrigerants, Scope 3 Cat 3, market-based Scope 2 instruments; third-party verification"],
  ["Decision engine", "NPV/IRR/MAC, MILP, Monte Carlo, chance constraints, value of information, timing", "Input correlations; multi-site and multi-year budgets"],
  ["Validation", "123 automated tests, fault injection, independent recalculation (A6) — on synthetic data", "Back-tests on real facility records; independent expert review"],
  ["Platform", "Single-user Streamlit app, local or Colab (Colab run pending)", "User management, access control, encryption, in-Kingdom hosting where required, support"],
], [1500, 4300, 4106], { size: 11 }));

// ---------------------------------------------------------------- B3
add(H1("B3 — Impact quantification", true));
add(P(`All values come from the A6-checked run outputs; Mezan_Phase_B_Impact_Scorecard.xlsx lists each one with its unit, source path, evidence type and limitation, and re-reads every source (trace check: ${CHK.derived["All trace checks pass"] ? "all pass" : "FAILED"}). **All impacts are modelled for a synthetic facility — they are not realised or verified savings.**`));
const sc = (id, fmt) => { const r = SC[id]; return [r.metric, fmt(r.value), r.unit, r.evidence]; };
add(table(["Metric", "Value", "Unit", "Evidence"], [
  sc("S1", f0), sc("S2", f0), sc("I1", f0), sc("I2", f0), sc("I3", f0),
  ["Reduction as share of the Scope 1+2 baseline", pc(CHK.derived["Reduction as % of Scope 1+2 baseline"]), "%", "formula on the values above"],
  sc("C1", f0), sc("C2", f0), sc("F1", f0), sc("F2", f0), sc("F3", f0), sc("F4", v => pc(v)),
  sc("F5", v => pc(v)), sc("F6", v => pc(v)), sc("F7", v => pc(v)), sc("F8", f0), sc("F9", f0), sc("F10", f0),
  sc("P1", v => pc(v, 2)), sc("P2", v => pc(v)),
  sc("V1", f0), sc("V2", f0), sc("V3", f0), sc("V4", f0), sc("V5", f0), sc("V6", f0),
], [4600, 1500, 1300, 2506], { size: 11 }));
add(Cap("Do not add: NPV and expected NPV (two views of one benefit); project NPVs and the portfolio NPV (the B–C overlap is removed only at portfolio level); deterministic and expected reductions. Payback and IRR are per project, not additive. EVPI bounds the other information values; they are not additive either."));
add(TT("Comparison with traditional investment selection"));
add(P("**Baseline definition.** Projects are ranked one at a time (by NPV per riyal, by NPV, or by abatement cost — cheapest tonne first, the usual MAC-curve practice) and funded in that order while the quoted budget allows, with no treatment of uncertainty. Each resulting portfolio is then evaluated with the same 200,000 validation scenarios."));
add(table(["Selection method", "Portfolio", "Quoted capex (SAR M)", "NPV base (SAR M)", "Expected NPV (SAR M)", "P(target)", "P(capex ≤ budget)", "P(NPV < 0)"],
  cmp.map(c => [c.method, c.portfolio, fm(c.quoted_capex), fm(c.npv_base), fm(c.e_npv), pc(c.p_target, 2), pc(c.p_budget), pc(c.p_loss)]), [2500, 1100, 1000, 1000, 1100, 1000, 1100, 1106], { size: 11 }));
add(P(`**Reading.** Ranking by NPV gives the same portfolio as Mezan in this case; the difference Mezan makes there is the quantified confidence (target, budget, downside) and the knowledge of which inputs could overturn it. Compared with abatement-cost ranking, Mezan avoids heat recovery and the steel switch, which raises expected NPV from SAR ${fm(mac.e_npv)} M to ${fm(ciq.e_npv)} M, budget compliance from ${pc(mac.p_budget)} to ${pc(ciq.p_budget)}, and lowers the chance of a loss from ${pc(mac.p_loss)} to ${pc(ciq.p_loss)}, while still meeting the Scope 1+2 target (the abatement-cost portfolio also cuts ${f0(R.projects.find(p => p.id === "F").scope3_t)} t of Scope 3, which the Scope 1+2 target does not count).`));
add(TT("Data quality and information value"));
add(B(`Counting missing months as zero would understate Scope 1+2 by ${pc(-CHK.derived["Error in Scope 1+2 if missing months were counted as zero"])} (${f0(SC.Q1.value)} vs ${f0(SC.Q2.value)} t) and change the recommendation; Mezan blocks this.`));
add(B(`Perfect information on everything is worth SAR ${f0(SC.V1.value)} (SAR ${f0(SC.V2.value)} under the alternative definition) — about ${pc(SC.V1.value / SC.F2.value)} of the expected NPV. Only compressed-air sub-metering can change the decision (SAR ${f0(SC.V3.value)} vs an assumed SAR ${f0(SC.V4.value)} cost); the missing monthly records and the motor audit cannot.`));
add(TT("Sensitivity of the main results"));
add(table(["Uncertain assumption", "Scenarios tested", "Effect on the recommendation"], [
  ["Industrial tariff (2027 rates not retrieved)", R.tariff_scenarios.map(t => t.tariff.toFixed(2)).join(" / ") + " SAR/kWh", `D4 = ${[...new Set(R.tariff_scenarios.map(t => t.joint))].join(", ")} in all; NPV rises with the tariff`],
  ["Rooftop solar cost (one benchmark)", R.pv_capex_scenarios.map(t => f0(t.pv_capex_kw)).join(" / ") + " SAR/kWp", `At ${f0(pvHi.pv_capex_kw)}: D1 ${pvHi.deterministic}, D4 ${pvHi.joint} (needs SAR ${fm(pvHi.joint_min_budget)} M)`],
  ["Methane price", R.gas_scenarios.map(t => t.gas_price_usd.toFixed(2)).join(" / ") + " USD/MMBtu", `D4 = ${[...new Set(R.gas_scenarios.map(t => t.joint))].join(", ")}`],
  ["Grid emission factor", R.ef_scenarios.map(t => t.ef_grid).join(" / ") + " t/MWh", `D4 = ${[...new Set(R.ef_scenarios.map(t => t.joint))].join(", ")}`],
  ["Real discount rate", R.discount_robustness.map(d => pc(d.rate, 0)).join(" / "), R.discount_robustness.map(d => `${pc(d.rate, 0)}: ${d.with_target}`).join("; ")],
  ["Compressed-air savings", "10–30%", `Switch at ${R.switch_points.c_saving_frac.changes[0][0].toFixed(2)}: below it A+B is preferred; dominant input in the Sobol analysis (A6)`],
], [2500, 2500, 4906], { size: 11 }));

// ---------------------------------------------------------------- rubric
add(H1("WE Rise rubric mapping", true));
add(P("How each Phase B deliverable supports the official criteria (weights from the WE Rise judging rubric). No score is implied; the right-hand column names what the judges may still find missing."));
add(table(["Criterion (weight)", "What the package shows", "Where", "Remaining gap"], [
  ["1.1 Concept & Relevance (15%)", "Saudi industrial decarbonization under incomplete data; national 278 Mt NDC commitment, industry as the largest fuel-combustion CO₂ source, voluntary and limited disclosure (A2); Saudi grid factor, tariff and gas prices (A5)", "B1 step 1; A2 report; demo script", "Problem validated by desk research only; no interviews with Saudi manufacturers yet (A2)"],
  ["1.2 Feasibility (20%)", "Working prototype; minimum data list; 16-week pilot with acceptance criteria; privacy, cyber and audit design; risks and mitigations; 123 tests and independent recalculation", "B2; A6 report; scorecard", "No real facility data; Colab run pending; costs hypothetical"],
  ["1.3 Innovation & Technical Merit (20%)", "Chance-constrained portfolio optimisation with budget risk, value of information and missing-data estimation in one decision — features not advertised by the nine benchmarked competitors (A3); mathematically checked (A6)", "B1 steps 5–7; A3; A6", "Absence of competitor claims is not proof of absence; methods are established, their combination is the novelty"],
  ["1.4 Impact (20%)", `Modelled ${f0(SC.I1.value)} tCO₂e/yr and SAR ${fm(SC.F2.value)} M expected NPV for one plant; avoided poor choices vs abatement-cost ranking; adaptable to other plants and sectors`, "B3; B2 adaptation", "Sector-wide impact not quantified; savings not verified"],
  ["2.1 Storytelling (12.5%)", "Eight-step narrative: problem → messy data → honest estimates → options → better decision → confidence → what to measure → action", "B1 script", "Rehearsal needed"],
  ["2.2 Pitch Delivery (12.5%)", "Live guided demo with fixed, validated numbers; backup PDF; anticipated questions answered from the scorecard and sensitivity sheet", "B1; Demo Guide PDF; scorecard", "Pitch slides not yet prepared (Phase C)"],
], [1900, 4100, 1600, 2306], { size: 11 }));

// ---------------------------------------------------------------- limitations and status
add(H1("Limitations and open issues"));
[
  "Synthetic facility; no deployment, customers or verified savings. All impacts are modelled.",
  "Costs other than solar are hypothetical; solar rests on one public benchmark (A5-04); 2027 tariff rates not retrieved (A5-01); 2026 gas price unconfirmed (A5-02).",
  "No validation on real industrial records (A4-01); validation is mathematical and synthetic (A6).",
  "Not yet run on real Google Colab (A1-01).",
  "Inputs sampled independently (A6-07); refrigerants and Scope 3 Category 3 not inventoried (A5-05, A5-06).",
  "Problem hypotheses (H1–H6) not yet tested in interviews (A2).",
].forEach(x => add(B(x)));
add(TT("Phase B status"));
add(table(["Item", "Status"], [
  ["Reused", "All model code, data, calculations, charts and validated outputs; existing app tabs; A4 demo dataset and chart; A5 register; A6 results"],
  ["Changed", "Added the '▶ Guided demo' tab (presentation of saved outputs, no new calculation), tools/build_phase_b.py (scorecard), tools/phase_b_content.py (script), tools/draw_architecture.py, 4 tests; fixed one stale case label; the app's tab count changes from 10 to 11"],
  ["Tests", `${T.passed} of ${T.total} passed, ${T.failed} failed, ${T.skipped} skipped (including the demo and scorecard trace tests)`],
  ["Demo ready", "Yes, for a synthetic-case demonstration, provided the pre-flight checklist is run and the Colab rehearsal (A1-01) is done if Colab is used"],
  ["Phase B ready to close", "Yes, with A1-01, A4-01 and the A5 evidence gaps carried forward"],
], [2000, 7906], { size: 12 }));
add(TT("Sources added in Phase B"));
add(B("Clyde & Co (10 Sep 2024). Saudi Arabia's Personal Data Protection Law becomes enforceable. [clydeco.com](https://www.clydeco.com/en/insights/2024/09/saudi-arabia-s-personal-data-protection-law-become)"));
add(B("Clyde & Co (16 Jan 2025). Saudi Arabia's Essential Cybersecurity Controls 2024 (ECC-2). [clydeco.com](https://www.clydeco.com/en/insights/2025/01/saudi-arabia-essential-cybersecurity-controls)"));
add(B("WE Rise Project Competition Judging Rubric (provided by the team)."));

const doc = new D.Document({
  styles: { default: { document: { run: { font: L.FONT, size: L.SZ } } } },
  numbering: { config: [
    { reference: "bul", levels: [{ level: 0, format: D.LevelFormat.BULLET, text: "•", alignment: D.AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 240 } } } }] },
    { reference: "num", levels: [{ level: 0, format: D.LevelFormat.DECIMAL, text: "%1.", alignment: D.AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 300 } } } }] }] },
  sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1000, bottom: 1000, left: 1000, right: 1000 } } },
    footers: { default: new D.Footer({ children: [new D.Paragraph({ alignment: D.AlignmentType.RIGHT, children: [new D.TextRun({ text: "Mezan · Phase B · synthetic case, modelled results · page ", size: 16, color: L.GREY }), new D.TextRun({ children: [D.PageNumber.CURRENT], size: 16, color: L.GREY })] })] }) },
    children: kids }] });
D.Packer.toBuffer(doc).then(b => { fs.writeFileSync(OUT, b); console.log("saved", OUT); });
