// Mezan_Complete_Project.docx. All numbers are read from outputs/results.json; charts from outputs/charts.
const fs = require("fs");
const path = require("path");
const L = require("./lib");
const { D, NAVY, GREY, FONT, P, H1, H2, B, N, EQ, Cap, TT, callout, table, fig } = L;
const { Document, Packer, Paragraph, TextRun, Footer, AlignmentType, LevelFormat, PageNumber } = D;

const [, , ROOT, OUT] = process.argv;
const R = JSON.parse(fs.readFileSync(path.join(ROOT, "outputs/results.json"), "utf8"));
const TEST = JSON.parse(fs.readFileSync(path.join(ROOT, "outputs/test_summary.json"), "utf8"));
const FAULT = JSON.parse(fs.readFileSync(path.join(ROOT, "outputs/fault_injection.json"), "utf8"));
const XREC = JSON.parse(fs.readFileSync(path.join(ROOT, "outputs/excel_recalc.json"), "utf8"));
const A6 = fs.existsSync(path.join(ROOT, "outputs/a6/a6_results.json")) ? JSON.parse(fs.readFileSync(path.join(ROOT, "outputs/a6/a6_results.json"), "utf8")) : null;
if (A6 && fs.existsSync(path.join(ROOT, "outputs/a6/a6_workbook_check.json"))) A6.workbook = JSON.parse(fs.readFileSync(path.join(ROOT, "outputs/a6/a6_workbook_check.json"), "utf8"));
const DS = Object.fromEntries(R.decision_scenarios.map(d => [d.id, d])), LV = R.decision_levels, CR = R.capex_risk;
const KE = R.knife_edge, BA = R.budget_analysis, MB = BA.min_budget_by_portfolio, J = R.mc_joint, VC = R.voi_comparison_v11;
const TS = Object.fromEntries(R.tariff_scenarios.map(t => [t.id, t])), TEV = Object.fromEntries(R.tariff_evidence.map(t => [t.id, t]));
const ES = R.ef_scenarios, GS = R.gas_scenarios, PS = R.pv_capex_scenarios, AT = R.a5_attribution;
const A = Object.fromEntries(R.assumptions.map(a => [a.key, a]));
const feasible = J.feasible;
const CH = path.join(ROOT, "outputs/charts");

// ---------- formatting
const n0 = x => Math.round(x).toLocaleString("en-US");
const n1 = x => Number(x).toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const n2 = x => Number(x).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const M = x => (x < 0 ? "−" : "") + "SAR " + n2(Math.abs(x) / 1e6) + "M";
const K = x => (x < 0 ? "−" : "") + "SAR " + n0(Math.abs(x) / 1e3) + "k";
const S = x => (x < 0 ? "−" : "") + "SAR " + n0(Math.abs(x));
const pc = (x, d = 0) => (100 * x).toFixed(d) + "%";
const pr = Object.fromEntries(R.projects.map(p => [p.id, p]));
const st = R.scope_totals, ut = R.uncertainty_totals;
const opt = R.optimal, cc = R.mc_chance_constrained, be = R.mc_best_expected;
const mcp = Object.fromEntries(R.mc_portfolios.map(r => [r.portfolio, r]));
const voi = Object.fromEntries(R.voi.map(r => [r.parameter, r]));
const tree = R.timing_tree, gbm = R.timing_gbm, scan = R.timing_scan;
const NAMES = R.project_names;
const sw = R.switch_points;
const bSwitch = sw.b_saving_frac.changes.length ? sw.b_saving_frac.changes[0][0] : null;
const swList = Object.entries(sw).filter(([k, x]) => !x.robust).map(([k, x]) => `${k} at ${Number(x.changes[0][0]).toLocaleString("en-US", { maximumSignificantDigits: 4 })} (${x.changes[0][1]} → ${x.changes[0][2]})`);
const posP = R.projects.filter(p => p.npv > 0), negP = R.projects.filter(p => p.npv <= 0);
const dr = R.discount_robustness;
const motorMWh = 12000 * 0.45;
const regret = Object.fromEntries(R.regret.map(r => [r.portfolio, r]));

const URL = {
  btr1: "https://unfccc.int/sites/default/files/resource/KSA_BTR1_20250320-2.pdf",
  gastat21: "https://www.stats.gov.sa/sites/default/files/Electric_Energy_Statistics_2021_Ar.pdf",
  argaam21: "https://www.argaam.com/en/article/articledetail/id/1611319",
  spa27: "https://www.spa.gov.sa/en/N2709801",
  ajc25: "https://www.aljaziracapital.com.sa/media/jn3bxjbu/energy-price-reforms-jan-25-en.pdf",
  mees26: "https://www.mees.com/2026/1/2/news-in-brief/saudi-increases-diesel-prices/f2cdf290-e7df-11f0-aea8-4d31a1325bf5",
  kf25: "https://www.knightfrank.ae/site-assets/pdf/going-green-rooftop-solar-potential-in-the-gcc-2025.pdf",
  alz21: "https://pubs.sciepub.com/ajer/9/1/5/index.html",
  jk13: "https://doi.org/10.1002/pip.1182",
  fh23: "https://www.zvei.org/fileadmin/user_upload/Verband/Fachverbaende/Automation/Elektrische_Antriebe/Cemep_Studie/Cemep_Fraunhofer_study-motor-saving-potential-with-VSD-20231215.pdf",
  cac26: "https://www.compressedairchallenge.org/data/sites/1/media/library/factsheets2026/fact-sheet-7-compressed-air-system-leaks_updated2026.pdf",
  doeph: "https://www1.eere.energy.gov/manufacturing/tech_assistance/pdfs/et_preheated.pdf",
  bdo: "https://www.bdoalamri.com/en-gb/insights/practical-challenges-in-compiling-a-meaningful-esg-report",
  kapsarc25: "https://www.kapsarc.org/research/publications/navigating-global-sustainability-reporting-and-taxonomies-insights-for-saudi-arabia/",
  mdpi: "https://doi.org/10.3390/systems13040250",
  wef: "https://www.weforum.org/publications/emissions-measurement-in-supply-chains-business-realities-and-challenges",
  ghg: "https://ghgprotocol.org/corporate-standard", s2: "https://ghgprotocol.org/scope-2-guidance",
  s3: "https://ghgprotocol.org/corporate-value-chain-scope-3-standard", unc: "https://ghgprotocol.org/sites/default/files/2023-03/ghg-uncertainty.pdf",
  birge: "https://doi.org/10.1007/978-1-4614-0237-4", howard: "https://doi.org/10.1109/TSSC.1966.300074", saltelli: "https://doi.org/10.1002/9780470725184",
  hobbs: "https://doi.org/10.1016/0377-2217%2894%2900190-N", dp49: "https://doi.org/10.30573/KS--2026-DP49", dp24: "https://doi.org/10.30573/KS--2026-DP24",
  dixit: "https://press.princeton.edu/books/hardcover/9780691034102/investment-under-uncertainty", lsm: "https://doi.org/10.1093/rfs/14.1.113",
  ipcc: "https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_2_Ch2_Stationary_Combustion.pdf",
  desnz: "https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2025",
  worldsteel: "https://worldsteel.org/wider-sustainability/sustainability-indicators/sustainability-indicators-report-2025/",
  irena: "https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2025/Jul/IRENA_TEC_RPGC_in_2024_Summary_2025.pdf",
  doe: "https://nrel.gov/docs/fy01osti/28008.pdf", iea4e: "https://www.iea-4e.org/document/150/energy-efficiency-policy-opportunities-for-electric-motor-driven-systems",
  sec: "https://rise.esmap.org/data/files/library/saudi-arabia/Renewable%20Energy/Saudi%20Arabia%20Tariff%20Schedule_2022.pdf",
  agbi: "https://www.agbi.com/oil-and-gas/2026/01/saudi-companies-face-cost-increase-as-aramco-ups-diesel-price/",
  nasa: "https://profilesolar.com/locations/Saudi-Arabia/Riyadh/",
  argaam17: "https://www.argaam.com/en/article/articledetail/id/519195",
  spark25: "https://www.spark.sa/page/news_detail/3512",
  attaqa26: "https://attaqa.net/2026/10/25/%D8%B1%D9%81%D8%B9-%D8%A3%D8%B3%D8%B9%D8%A7%D8%B1-%D8%A7%D9%84%D9%83%D9%87%D8%B1%D8%A8%D8%A7%D8%A1-%D9%81%D9%8A-%D8%A7%D9%84%D8%B3%D8%B9%D9%88%D8%AF%D9%8A%D8%A9-%D9%84%D8%B9%D8%A7%D9%85-2027-%D9%88/",
  slg26: "https://saudilifeguide.com/saudi-electricity-tariff-2027/",
  national26: "https://www.thenationalnews.com/news/gulf/2026/10/25/saudi-arabia-announces-support-measures-as-electricity-and-water-tariffs-rise/",
  kfupm24: "https://sustainability.kfupm.edu.sa/documents/78/KFUPM_Greenhouse_Gas_Emissions_Inventory_for_2024_v2.pdf",
  dna21: "https://cdmdna.gov.sa/Resources/70/e179cf72596d15213c8772bf7a9dab642.pdf",
  ifi19: "https://unfccc.int/sites/default/files/resource/Harmonized_Grid_Emission_factor_data_set.pdf",
  saa: "https://doi.org/10.1007/s10957-009-9523-6",
};

const body = [];
// ---------------------------------------------------------------- title page
body.push(new Paragraph({ spacing: { before: 1400, after: 60 }, children: [new TextRun({ text: "Mezan | ميزان", font: FONT, size: 64, bold: true, color: NAVY })] }));
body.push(new Paragraph({ spacing: { after: 240 }, children: [new TextRun({ text: "Carbon Investment Decision Support — complete project report", font: FONT, size: 32, color: NAVY })] }));
body.push(P("Research prototype for a hypothetical Saudi manufacturing facility · problem, benchmark, data, methods, implementation, results and validation", { r: { size: 22, color: GREY, italics: true } }));
body.push(new Paragraph({ spacing: { before: 400, after: 200 }, children: [new TextRun({ text: "October 2026 · Version 1.3 (Phase A5 carbon and financial data strengthening, 26 October 2026)", font: FONT, size: 22, color: GREY })] }));
body.push(callout([
  "**Status.** Mezan is a **research prototype**, not a production-ready industrial decision system. The case facility, its activity data and all project costs are **synthetic** (illustrative) values anchored to cited public sources where possible; they do not describe any real Saudi company. Results demonstrate the method and must not be read as investment advice or a verified GHG inventory.",
  "**Deliverables.** This report, Mezan_Data_Model.xlsx (live formulas), the Python package with automated tests, and a Streamlit interface. All three produce the same numbers; agreement is tested automatically.",
  "**Methods, not machine learning.** Mezan uses accounting, optimisation, simulation and decision analysis. It contains no trained or validated machine-learning model and is not described as AI-enabled.",
  `**Version 1.3 (A5).** Inputs re-audited against Saudi and public sources: grid factor ${A.ef_grid.value} tCO₂e/MWh derived from Saudi Arabia's 2025 UNFCCC transparency report and GASTAT (was 0.55, source never located); regulated methane price $${A.gas_price_usd.value}/MMBtu (was a $3 study anchor); rooftop PV cost SAR ${n0(A.pv_capex_kw.value)}/kWp from a Riyadh market benchmark (was an unsourced SAR 3,750); PV degradation, compressed-air savings and an ongoing leak-management cost added. These evidence-based changes move the recommendation (Section 6.9); the v1.2 register is kept as a comparison profile.`,
  "**Version 1.2.** Version 1.1 corrected the Phase A1 audit issues. Version 1.2 applies two management decisions of 25 October 2026: the 90% carbon chance constraint counts reductions against the fixed reporting baseline (baseline and emission-factor uncertainty are tested as sensitivities), and a 90% budget chance constraint is added. Chance constraints are now tightened for sampling error and validated on an independent 200,000-scenario sample. No equation of the project models changed.",
]));
body.push(new Paragraph({ spacing: { before: 400 }, children: [] }));
body.push(new Paragraph({ pageBreakBefore: true, children: [new TextRun({ text: "Contents", bold: true, font: FONT, size: 28, color: NAVY })] }));
["Executive summary", "1. Objectives and decision questions", "2. The problem and its Saudi relevance",
 "3. Competitor benchmark and defensible differentiation", "4. Manufacturing case-study specification",
 "5. Data foundation, assumptions and quality",
 "6. Methods, implementation and results (6.1 carbon accounting · 6.2 project economics · 6.3 portfolio optimization · 6.4 uncertainty · 6.5 value of information · 6.6 sensitivity · 6.7 investment timing · 6.8 integrated recommendation)",
 "7. Implementation architecture and validation", "8. Limitations and future development", "References",
 "Appendix A. Assumption register", "Appendix B. Using the workbook, code and prototype interface"].forEach(t => body.push(B(t)));

// ---------------------------------------------------------------- executive summary
body.push(H1("Executive summary", true));
body.push(P(`**Problem.** Saudi industrial organisations face growing pressure to measure and disclose emissions, but the energy, supplier, cost and emissions data needed to act are often held separately and are incomplete or uncertain. Measuring emissions does not by itself show which decarbonization investments to fund, how much to spend, when to act or how far to trust the answer.`));
body.push(P(`**What we built.** A working prototype that links six established methods in one reproducible workflow: GHG Protocol carbon accounting with uncertainty propagation; project economics (NPV, payback, marginal abatement cost); portfolio optimization under a budget and a carbon target; Monte Carlo and chance-constrained selection; value-of-information analysis; sensitivity and robustness testing; and an investment-timing (real-options) analysis adapted from KAPSARC's 2026 offshore study.`));
body.push(P(`**Case.** A hypothetical metal-fabrication plant near Riyadh emits ${n0(st.Total)} tCO₂e/yr (Scope 1 ${n0(st["Scope 1"])}, Scope 2 ${n0(st["Scope 2"])}, Scope 3 ${n0(st["Scope 3"])}); Scope 1+2 (${n0(st["Scope 1+2"])} t) is known to ±${n1(ut["Scope 1+2"].u95_pct)}% (95%). Management has SAR ${n2(R.meta.budget / 1e6)} million and a target of cutting Scope 1+2 by 15% (${n0(R.target_t)} t/yr). Six projects are evaluated: rooftop solar, motors with variable-speed drives, compressed-air repairs, furnace heat recovery, forklift electrification and a lower-carbon steel supplier.`));
body.push(TT("Key results (synthetic case)"));
body.push(table(["Question", "Answer from the prototype"], [
  ["Which projects pay?", `Positive NPV at the 18-halala reference tariff: ${posP.map(p => `${p.id} (${M(p.npv)})`).join(", ")}. Negative: ${negP.map(p => `${p.id} (${M(p.npv)}; MAC ${S(p.mac_sar_per_t)}/t)`).join(", ")}. Forklift electrification abates little because the grid is carbon-intensive; the steel switch reduces Scope 3 only.`],
  ["What should be funded under the budget?", `Ranking projects one by one funds ${R.baselines[0].portfolio} (${M(R.baselines[0].npv)}) and misses the target (${n0(R.baselines[0].scope12_t)} t/yr). The optimizer chooses **${opt.portfolio}**: ${M(opt.npv)}, ${n0(opt.scope12_t)} t/yr — the best NPV that meets the target.`],
  ["Primary decision rule", feasible ?
    `Maximise expected NPV with ≥90% probability of meeting the carbon target (fixed reporting baseline) **and** ≥90% probability that actual capital cost stays within SAR 5M: **${J.portfolio}** qualifies (${M(J.e_npv)}; target ${pc(J.p_target, 1)}; within budget ${pc(1 - J.p_over_budget, 1)}). The smallest budget at which the rule is feasible is ${S(MB[0].budget_needed)} (${MB[0].portfolio}).` :
    `Maximise expected NPV with ≥90% probability of meeting the carbon target (fixed reporting baseline) **and** ≥90% probability that actual capital cost stays within SAR 5M: **no portfolio qualifies**. The smallest budget that makes the rule feasible is **${S(MB[0].budget_needed)}** (${MB[0].portfolio}). No recommendation is forced.`],
  ["Carbon rule alone", `With only the 90% carbon requirement the validated choice is **${DS.D3.portfolio}** (${M(DS.D3.e_npv)}; target ${pc(DS.D3.p_target, 1)}; within budget ${pc(DS.D3.p_budget, 1)}). ${KE.portfolio} meets the target in ${pc(KE.p_in_sample, 2)} of the 20,000 scenarios and ${pc(KE.p_validation, 2)} of the 200,000-scenario validation sample${KE.p_validation < 0.9 ? " — below the requirement" : ""}.`],
  ["Comparison scenarios", `Deterministic optimum **${DS.D1.portfolio}** (NPV ${M(DS.D1.npv_base_inputs)} at base inputs); highest expected NPV **${DS.D2.portfolio}** (${M(DS.D2.e_npv)}; target ${pc(DS.D2.p_target, 1)}; within budget ${pc(DS.D2.p_budget, 1)}).`],
  ["What should we learn first?", R.evsi_audit.evsi > R.evsi_audit.audit_cost ?
    `A motor-system audit: knowing B's savings is worth ${M(voi.b_saving_frac.evppi_sar)} (a realistic audit ${M(R.evsi_audit.evsi)}; estimator noise floor ${M(R.voi_noise_floor)}) against an assumed SAR 80k cost.` :
    `Little: all uncertainty resolved is worth ${M(R.evpi)} (EVPI) and a motor-system audit ${M(R.evsi_audit.evsi)} against an assumed SAR 80k cost, because the recommended portfolio is robust to the uncertain inputs. Supplier-specific steel data has no value for this decision.`],
  ["When should we invest?", `Heat recovery: decision tree says **${tree.decision}** (option value of waiting ${K(tree.option_premium)}) at the regulated $${n2(tree.g_now_usd)}/MMBtu gas price.`],
], [2400, 7506], { boldFirst: true, size: 17 }));
body.push(P(feasible ?
  `**Recommendation (illustrative).** Under the decided risk rules the prototype recommends **${J.portfolio}** at SAR 5M. This depends mainly on the Riyadh rooftop-PV cost benchmark (SAR ${n0(A.pv_capex_kw.value)}/kWp): at the earlier SAR 3,750/kWp assumption the joint rule is infeasible (Section 6.9). Before committing: obtain formal PV quotations, confirm the 2027 tariff schedule, and treat compressed air (C) as marginal (NPV ${M(pr.C.npv)}).` :
  `**Recommendation (illustrative).** Under the decided risk rules there is no portfolio to approve at SAR 5M. Management can (a) raise the budget to about ${S(MB[0].budget_needed)} for ${MB[0].portfolio}, (b) accept a lower budget-compliance level — ${DS.D3.portfolio} stays within SAR 5M in ${pc(DS.D3.p_budget)} of scenarios — or (c) hold a contingency outside the decarbonization budget.`, { p: { spacing: { before: 120 } } }));
body.push(P(`**Validation.** ${TEST.total} automated tests: ${TEST.passed} passed, ${TEST.failed} failed, ${TEST.skipped} skipped (Python ${TEST.python}); the integer program equals exhaustive enumeration; the Monte Carlo baseline uncertainty (±${n1(R.mc_baseline_scope12.u95_pct)}%) confirms the analytic GHG Protocol propagation (±${n1(ut["Scope 1+2"].u95_pct)}%); ${XREC.total_formulas} Excel formulas recalculate without errors and match Python; ${FAULT.detected} of ${FAULT.faults} deliberately injected faults were detected (tools/fault_injection.py).`));

// ---------------------------------------------------------------- 1 objectives
body.push(H1("1. Objectives and decision questions"));
body.push(P("Mezan aims to convert incomplete operational, electricity, fuel, supplier and financial data into traceable emissions estimates and economically justified decarbonization investment recommendations. The prototype answers six questions:"));
[["What are the facility's emissions and how reliable are the estimates?", "Section 6.1"],
 ["Which decarbonization investments are financially and environmentally attractive?", "Section 6.2"],
 ["Which combination should be funded under a limited budget?", "Section 6.3"],
 ["How do uncertainty and data gaps affect recommendations?", "Sections 6.4 and 6.6"],
 ["Which missing information is worth collecting before investing?", "Section 6.5"],
 ["When should management invest now versus wait?", "Section 6.7"]].forEach(([q, s]) => body.push(N(`${q} *(${s})*`)));
body.push(P("**Prototype vs production.** The prototype demonstrates that the calculations work end to end and are internally consistent. A production system would additionally need real facility data pipelines, verified emission factors, formal quotations, user management and validation against real investment outcomes (Section 8).", { p: { spacing: { before: 100 } } }));

// ---------------------------------------------------------------- 2 problem
body.push(H1("2. The problem and its Saudi relevance"));
body.push(P(`The problem paper (October 2026) reviewed four sources. Their evidence supports the **data** side of the problem; the **decision** side — that this limits investment decisions — is our interpretation, which this prototype is designed to address and future pilots must test.`));
body.push(table(["Source (type)", "What it documents", "Relevance"], [
  [`[KAPSARC, 2025](${URL.kapsarc25}) (Saudi policy commentary)`, "Saudi sustainability reporting \"remains fragmented\"; voluntary Saudi Exchange ESG guidelines (2018); small suppliers may lack resources to provide accurate Scope 3 data; need for robust data-collection systems.", "Saudi context: the data foundation for decisions is still being built."],
  [`[BDO Saudi Arabia, 2025](${URL.bdo}) (advisory commentary, no survey data)`, "Energy spend, emissions and supplier data owned by different departments; reports compiled by spreadsheets and manual consolidation; Scope 3 hampered by inconsistent supplier data.", "Describes the fragmentation hypothesis in the Saudi market."],
  [`[Alorfi & Alsaadi, 2025](${URL.mdpi}) (peer-reviewed, Saudi manufacturing)`, "Data integration, infrastructure and cost barriers to data analytics; \"costs and the lack of an ROI\" most critical for manufacturing.", "General analytics barriers, not carbon-specific: shows return on data-driven initiatives is hard to justify."],
  [`[World Economic Forum, 2023](${URL.wef}) (international white paper)`, "Scope 3 ≈75% of company emissions on average (citing CDP); factors often industry averages; supplier data incomplete or inconsistent.", "International evidence on supplier-data limits."],
], [2700, 4500, 2706], { size: 16 }));
body.push(P(`**Problem statement.** Many Saudi industrial organisations face growing pressure to measure and disclose emissions, yet the energy, supplier, cost and emissions data they need often sit in separate systems and are incomplete or uncertain. Reporting alone does not show which decarbonization investments to fund. Managers need a reliable way to compare options on carbon and financial terms while accounting for data gaps.`, { p: { spacing: { before: 120 } } }));

// ---------------------------------------------------------------- 3 benchmark
body.push(H1("3. Competitor benchmark and defensible differentiation"));
body.push(P("The project team benchmarked five carbon-management platforms operating in or serving Saudi Arabia using their **publicly advertised capabilities**. The table below reproduces the team's benchmark; its entries were not independently re-verified for this report and carry no per-claim sources or access dates. Evidence-based re-benchmarking is scheduled for Phase A3; until then the table is the team's assessment, not verified evidence."));
body.push(table(["Capability", "Saudi Carbon", "SustainX", "SGS + Sami", "Schneider", "URIMPACT", "Mezan (prototype)"], [
  ["Carbon accounting", "✓", "✓", "✓", "✓", "✓", "✓ implemented"],
  ["AI analytics", "✓", "✓", "✓", "✓", "✓", "★ planned (no ML in prototype)"],
  ["Emissions reduction planning", "✓", "✓", "✓", "✓", "✓", "✓ implemented"],
  ["Financial analysis", "✓", "◇", "✓", "✓", "◇", "✓ implemented"],
  ["Supplier data analysis", "✓", "◇", "✓", "✓", "✓", "✓ basic (Scope 3 Cat 1, 4)"],
  ["Investment optimization under constraints", "◇", "◇", "◇", "◇", "◇", "★ prototype, not validated"],
  ["Quantified decision uncertainty", "◇", "◇", "◇", "◇", "◇", "★ prototype, not validated"],
  ["Value-of-information analysis", "◇", "◇", "◇", "◇", "◇", "★ prototype, not validated"],
  ["Investment decision robustness", "◇", "◇", "◇", "◇", "◇", "★ prototype, not validated"],
], [2550, 1100, 1000, 1050, 1050, 1100, 2056], { size: 15, center: [1100, 1000, 1050] }));
body.push(Cap("✓ = advertised (competitors) / implemented in the prototype (Mezan); ◇ = not clearly established from the reviewed materials — it does NOT mean the competitor lacks the capability; ★ = Mezan capability implemented on synthetic data but not validated on real decisions."));
body.push(P(`**Correction to the team table.** The original team table marked Mezan with ✓ for AI analytics. The prototype contains no machine-learning component (its methods are optimization, simulation and decision analysis), so this report marks AI analytics as planned (★). **Positioning.** Carbon accounting, reduction planning and financial evaluation already exist in the market. Mezan's potential advantage is narrower and testable: an integrated, uncertainty-aware **investment decision engine** that states what to fund, how much, how confident the recommendation is, and which data to collect first. We do not claim Mezan is the first platform in Saudi Arabia to offer any feature.`));

// ---------------------------------------------------------------- 4 case
body.push(H1("4. Manufacturing case-study specification"));
body.push(table(["Element", "Specification (hypothetical)"], [
  ["Facility", "Medium-sized metal-fabrication and assembly plant, Riyadh region; two shifts; 5,000 t/yr finished metal products"],
  ["Boundary", "Operational control. Scope 1 (natural gas for furnaces, diesel forklifts and generators); Scope 2 location-based grid electricity; Scope 3 Category 1 (purchased steel) and Category 4 (inbound road freight)"],
  ["Activity (annual)", "12,000 MWh electricity · 35,000 GJ natural gas · 80,000 L diesel · 6,000 t steel · 2.0 million t-km freight"],
  ["Budget and target", `SAR 5.0 million capital; cut Scope 1+2 by ≥15% (${n0(R.target_t)} t/yr); 90% required confidence under uncertainty; 6% real discount rate`],
  ["Operational constraints", "Roof area limits solar to 1,000 kWp; motor and compressed-air measures share compressor motors (overlap counted once); budget counts one-time capital; Scope 3 projects do not count toward the Scope 1+2 target"],
], [2300, 7606], { boldFirst: true, size: 17 }));
body.push(TT("Candidate projects (inputs in the assumption register)"));
body.push(table(["ID", "Project", "Main effect", "Capex", "Life"], [
  ["A", NAMES.A, `1,850 MWh in year 1, self-consumed; −${pc(A.pv_degradation.value, 1)}/yr degradation`, S(pr.A.capex), `${pr.A.life} y`],
  ["B", NAMES.B, "15% of non-compressor motor load + 3% of compressor load", S(pr.B.capex), `${pr.B.life} y`],
  ["C", NAMES.C, `${pc(A.c_saving_frac.value)} of compressed-air electricity (leaks ~20% → <10%, plus controls); leak programme ${S(A.c_om.value)}/yr`, S(pr.C.capex), `${pr.C.life} y`],
  ["D", NAMES.D, "15% of furnace gas (5,250 GJ/yr)", S(pr.D.capex), `${pr.D.life} y`],
  ["E", NAMES.E, "Removes 60,000 L diesel; adds 210 MWh electricity", S(pr.E.capex), `${pr.E.life} y`],
  ["F", NAMES.F, "3,000 t/yr from a DRI-EAF-type supplier (+SAR 80/t)", S(pr.F.capex) + " one-time", `${pr.F.life} y`],
], [500, 2900, 4100, 1500, 906], { size: 16 }));

// ---------------------------------------------------------------- 5 data
body.push(H1("5. Data foundation, assumptions and quality"));
const cnt = R.assumptions.reduce((a, x) => (a[x.status] = (a[x.status] || 0) + 1, a), {});
const ev = R.assumptions.reduce((a, x) => (a[x.evidence] = (a[x.evidence] || 0) + 1, a), {});
body.push(P(`All ${R.assumptions.length} inputs live in one register (carbon_iq/assumptions.py and the workbook) with value, unit, status, source or rationale and uncertainty distribution: **${cnt.verified || 0} verified** (cited public source, applicable here), **${cnt.derived || 0} derived** (computed from verified values), **${cnt.transferred || 0} transferred** (cited source from another country, sector or study), **${cnt.provisional || 0} provisional** (partial or secondary evidence, or a change announced; reported with scenarios) and **${cnt.hypothetical || 0} hypothetical** (case assumptions). Version 1.0 labelled the transferred and provisional values "verified"; the A1 audit corrected this. Synthetic data are never presented as real company data. Since v1.3 each input also carries an **evidence class** — external ${ev.external || 0}, derived ${ev.derived || 0}, hypothetical ${ev.hypothetical || 0}, measured ${ev.measured || 0} (the facility is synthetic, so nothing is a factory observation) — plus publication date, effective period and geographic applicability (Appendix A; workbook sheet Source Register).`));
body.push(table(["Input", "Value", "Status", "Source"], [
  ["Industrial electricity tariff", "SAR 0.18/kWh (reference)", "provisional", `[ECRA via Argaam, 13 Dec 2017](${URL.argaam17}): flat 0.18 from 1 Jan 2018; [SEC schedule 2022](${URL.sec}). Adjustment from 1 Jan 2027 officially announced ([SPA, 25 Oct 2026](${URL.spa27}), rates in an attachment not retrieved); 0.23 reported by news sources — scenarios below`],
  ["Diesel price", "SAR 1.79/L", "verified", `[Aramco price from 1 Jan 2026 (MEES)](${URL.mees26}); [AGBI](${URL.agbi})`],
  ["Industrial gas (methane) price", `USD ${A.gas_price_usd.value}/MMBtu`, "provisional", `[Al Jazira Capital, Jan 2025](${URL.ajc25}): Aramco methane $1.75 → $2.15 from 1 Jan 2025; 2026 rise reported but not quantified (scenarios G0–G2)`],
  ["Discount rate", "6% real", "transferred", `[KAPSARC DP49, Table D1](${URL.dp49}) — utility-context WACC applied to the facility; 4–12% tested`],
  ["Grid emission factor", `${A.ef_grid.value} tCO₂e/MWh`, "derived", `[KSA BTR1 (UNFCCC, 2025)](${URL.btr1}) Table 6: 2021 electricity-generation emissions 205,579 Gg CO₂e ÷ [GASTAT](${URL.gastat21}) 2021 generation 358,640 GWh ([Argaam](${URL.argaam21}))`],
  ["Natural gas factor", "56.15 kgCO₂e/GJ", "derived", `[IPCC 2006 Vol.2 Table 2.3](${URL.ipcc}) + AR5 GWPs`],
  ["Diesel / freight factors", "2.66155 kg/L · 0.10163 kg/t-km", "transferred", `[DESNZ 2025](${URL.desnz}) (UK proxies)`],
  ["Steel factors", "1.92 (avg) · 1.47 (DRI-EAF) · 0.69 (scrap-EAF) tCO₂/t", "transferred", `[worldsteel 2025 report](${URL.worldsteel}) (global averages as supplier proxies)`],
  ["PV yield", "1,850 kWh/kWp/yr (year 1)", "derived", `[Alzahrani & Nahhas 2021](${URL.alz21}): Riyadh fixed-tilt 2,008 kWh/kWp (PVsyst, PR 0.818) less ~8% for rooftop conditions (assumption)`],
  ["PV installed cost", `SAR ${n0(A.pv_capex_kw.value)}/kWp`, "transferred", `[Knight Frank 2025](${URL.kf25}): typical Riyadh fixed rooftop SAR 2.5/W from local providers (benchmark, not a quotation)`],
  ["PV degradation", `${pc(A.pv_degradation.value, 1)}/yr`, "transferred", `[Jordan & Kurtz 2013](${URL.jk13}) median field rate`],
  ["Compressed-air savings", `${pc(A.c_saving_frac.value)} + leak programme ${S(A.c_om.value)}/yr`, "derived / hypothetical", `[Compressed Air Challenge 2026](${URL.cac26}): leaks ~20% → <10% with quarterly surveys`],
  ["Motor + VSD savings", "15% of non-compressor motor load", "transferred", `[Fraunhofer ICT/CEMEP 2023](${URL.fh23}): fans 29%, pumps 15% market potential; [IEA 4E](${URL.iea4e}) motor share`],
  ["Heat-recovery savings", "15% of furnace gas", "transferred", `[US DOE Process Heating Tip Sheet #1](${URL.doeph}): 13–20% at 600°F air preheat`],
  ["Project costs, savings shares, activity data", "see register", "hypothetical", "Case assumptions with stated rationale and ranges"],
], [2300, 2600, 1100, 3906], { size: 15 }));
body.push(P("**Quality limitations.** (i) The grid factor is a 2021 national average derived from two official sources whose category boundaries are not reconciled; (ii) the 2027 tariff and 2026 gas price are not confirmed by primary documents; (iii) diesel and freight factors are UK proxies (diesel within 1% of IPCC defaults); (iv) supplier-specific steel factors are unknown and world averages are crude-steel, not product, intensities; (v) PV cost is a market benchmark and B–F costs are placeholders pending quotations; (vi) savings shares for B, C and D need audits; (vii) uncertainty distributions are judgement-based ranges.", { p: { spacing: { before: 100 } } }));
body.push(TT("Industrial electricity tariff: evidence (checked 25 October 2026)"));
body.push(table(["Scenario", "SAR/kWh", "Effective", "Evidence status", "Source"], R.tariff_evidence.map(t =>
  [`${t.id} ${t.label}`, n2(t.value), t.effective, t.status, t.url ? `[${t.source.slice(0, 150)}${t.source.length > 150 ? "…" : ""}](${t.url})` : t.source]),
  [2300, 800, 1400, 1900, 3506], { size: 14 }));
body.push(P(`The 18-halala flat industrial rate is documented for 2018–2026, which settles the v1.0 question about consumption bands (industrial use has no band). Three news reports published on 25 October 2026 state that the industrial rate becomes 23 halalas/kWh from 1 January 2027 ([Attaqa](${URL.attaqa26}), [Saudi Life Guide](${URL.slg26}); [The National](${URL.national26}), citing SPA, confirms the rise without rates). Saudi Energy officially announced the adjustment on 25 October 2026 ([SPA](${URL.spa27})), but the rate table is in an attachment that could not be retrieved, so the official schedule and any industrial fixed fees were not obtained; a 2-halala surcharge for facilities that do not qualify for the intensive-consumption tariff ([SPARK notice, Apr 2025](${URL.spark25})) is ambiguous for SEC customers. The model therefore keeps 0.18 as the reference and reports every result under the four scenarios (Section 6.6) rather than asserting one rate for 2027 onwards.`));
body.push(TT("Grid emission factor: evidence (replaced in v1.3)"));
body.push(table(["Evidence", "tCO₂/MWh", "Access and use"], R.ef_evidence.map(e => [`[${e.what}](${e.url})`, n2(e.value).replace(/0$/, ""), `${e.access}. ${e.use}`]),
  [3900, 900, 5106], { size: 14 }));
body.push(P(`Saudi Arabia's First Biennial Transparency Report to the UNFCCC ([BTR1, 2025](${URL.btr1}), Table 6) reports 205,579 Gg CO₂e (AR5 GWPs) from electricity generation (IPCC category 1.A.1.a.i) in 2021; GASTAT reports 358,640 GWh generated that year ([Argaam](${URL.argaam21}); [GASTAT 2021](${URL.gastat21}): 359 TWh). Their ratio, **${A.ef_grid.value} tCO₂e/MWh**, is a defensible location-based grid average from primary Saudi sources and is close to the Saudi DNA 2021 factor (0.568, as cited by [KFUPM](${URL.kfupm24})). It replaces the v1.2 project factor (0.55), whose source table was never located; 0.55 and 0.568 remain as scenarios E0/E1. The ±10% range is kept for the 2021 vintage and unreconciled category boundaries. Dividing by consumption instead (301,600 GWh) gives 0.682, which includes transmission and distribution losses that the GHG Protocol places in Scope 3 Category 3 (not yet in the inventory boundary). The IFI harmonised factors (0.475 / 0.650) are marginal crediting factors and are listed for context only.`));

// ---------------------------------------------------------------- 6 methods
body.push(H1("6. Methods, implementation and results"));
body.push(P("Each subsection states the method (with its source), what the prototype computes, the equation used and the result for the case. Where a method is our adaptation rather than the source's own application, this is stated."));

body.push(H2("6.1 Carbon accounting and emissions uncertainty"));
body.push(P(`Method: [GHG Protocol Corporate Standard](${URL.ghg}), [Scope 2 Guidance](${URL.s2}), [Scope 3 Standard](${URL.s3}) and [uncertainty guidance](${URL.unc}). Emissions are activity × factor; first-order propagation combines ±% (95%) uncertainties under the guidance's assumptions (normal, unbiased, independent errors below 60%):`));
body.push(EQ("E_{i} = A_{i} × EF_{i}      U_{i} = √(U_{A}^{2} + U_{EF}^{2})      U_{total} = √Σ(E_{i}·U_{i})^{2} ⁄ ΣE_{i}"));
body.push(...fig(CH, "c1_emissions_by_source.png", "Figure 1. Baseline emissions by source (synthetic facility).", 620));
body.push(...fig(CH, "c2_data_quality.png", "Figure 2. Uncertainty by source; labels use the guidance's High/Good/Fair/Poor scale.", 620));
body.push(P(`Scope 1+2 is known to ±${n1(ut["Scope 1+2"].u95_pct)}% and the total to ±${n1(ut.Total.u95_pct)}%, dominated by Scope 3 steel (±21.6%) and freight (±35.6%). A Monte Carlo check of Scope 1+2 gives ±${n1(R.mc_baseline_scope12.u95_pct)}%, confirming the analytic result. Since v1.1 both methods use the same activity-data uncertainties from the register (v1.0 hard-coded four of them in the analytic table only). **Why first:** reductions are measured against this baseline, and a decision cannot be more reliable than the data behind it.`));

body.push(H2("6.2 Project economics"));
body.push(P("Each project's net present value and marginal abatement cost (MAC) use end-of-year real cash flows at 6%:"));
body.push(EQ("NPV_{i} = −C_{i} + CF_{i} × AF(r, T_{i}),   AF = (1 − (1 + r)^{−T}) ⁄ r,   MAC_{i} = −NPV_{i} ⁄ (AF × ΔE_{i})"));
body.push(P(`For solar the year-1 output declines by d = ${pc(A.pv_degradation.value, 1)} per year, so energy savings and tonnes use the degraded factor AF_{d} = (1 − ((1−d)/(1+r))^{T}) ⁄ (r + d) and O&M the ordinary annuity factor; MAC divides −NPV by discounted lifetime tonnes. Compressed air (C) carries an annual leak-management cost.`));
body.push(table(["Project", "Capex", "Net cash flow/yr", "NPV", "Scope 1+2 t/yr", "Scope 3 t/yr", "MAC SAR/t", "Payback"], R.projects.map(p =>
  [`${p.id} ${p.name}`, S(p.capex), S(p.annual_cf), S(p.npv), n1(p.scope12_t), n1(p.scope3_t), n0(p.mac_sar_per_t), p.payback_y ? `${n1(p.payback_y)} y` : "never"]),
  [2900, 1050, 1150, 1100, 900, 850, 850, 1106], { size: 15 }));
body.push(...fig(CH, "c3_mac_curve.png", "Figure 3. Marginal abatement cost curve (bar width = tonnes avoided per year).", 620));
body.push(P(`Forklift electrification abates little (${n1(pr.E.scope12_t)} t/yr) because the Saudi grid factor (${A.ef_grid.value} t/MWh) is high: the 210 MWh added offsets most of the diesel saved. The steel switch avoids the most tonnes (${n0(pr.F.scope3_t)} t/yr) but in Scope 3, which the Scope 1+2 target does not count. Solar's NPV (${M(pr.A.npv)}) rests on the Riyadh rooftop-cost benchmark; at the earlier SAR 3,750/kWp it would be ${M(pr.A.npv - (3750 - A.pv_capex_kw.value) * 1000)} (same other inputs). Compressed air is marginal (${M(pr.C.npv)}) once the leak-management cost is included.`));

body.push(H2("6.3 Portfolio optimization"));
body.push(P(`Method: binary integer programming, as reviewed for utility resource planning by [Hobbs (1995)](${URL.hobbs}) (full text not accessible to us; the manufacturing formulation is our adaptation). The overlap between B and C (compressor motors) is linearised so it is counted once:`));
body.push(EQ("max Σ x_{i}NPV_{i} − y_{BC}NPV_{BC}   s.t.  Σ x_{i}C_{i} ≤ B,  Σ x_{i}ΔE_{i} − y_{BC}ΔE_{BC} ≥ T,  y_{BC} ≥ x_{B}+x_{C}−1,  x, y ∈ {0,1}"));
body.push(P(`Solved with scipy's HiGHS mixed-integer solver and checked by enumerating all 64 portfolios (both give ${opt.portfolio}); the workbook repeats the enumeration with live formulas.`));
body.push(...fig(CH, "c4_frontier_methods.png", "Figure 4. Best achievable NPV for each Scope 1+2 target, and what simple ranking rules choose.", 620));
body.push(table(["Approach", "Portfolio", "Capex", "NPV", "Scope 1+2 t/yr", "Meets target"], [
  ...R.baselines.map(b => [b.method, b.portfolio, S(b.capex), S(b.npv), n1(b.scope12_t), b.meets_target ? "yes" : "no"]),
  ["Optimization (budget + target)", opt.portfolio, S(opt.capex), S(opt.npv), n1(opt.scope12_t), "yes"],
], [3300, 1300, 1300, 1300, 1300, 1406], { size: 16, highlight: (i) => i === 3 }));
body.push(P(`Ranking rules choose ${R.baselines.map(b => `${b.portfolio} (${b.method}; ${b.meets_target ? "meets" : "misses"} the target)`).join(", ")}. The optimizer chooses ${opt.portfolio}; meeting the target costs ${K(R.optimal_no_target.npv - opt.npv)} of NPV against the unconstrained optimum (${R.optimal_no_target.portfolio}). Ledger check: for A+B+C the shared activity ledger gives ${n1(R.ledger_check.abc_ledger)} t/yr versus ${n1(R.ledger_check.abc_naive)} t/yr if the overlap were double counted.`, { p: { spacing: { before: 100 } } }));

body.push(H2("6.4 Uncertainty and stochastic optimization"));
body.push(P(`Method: Monte Carlo evaluation and sample-average approximation of a chance-constrained program ([Birge & Louveaux, 2011](${URL.birge})). Twenty thousand joint scenarios draw tariff, prices, savings shares, costs, PV yield and emission factors from the register's ranges (common random numbers for all portfolios). **Evaluation** reports the spread of a fixed portfolio; **optimization** chooses the portfolio across all scenarios:`));
body.push(EQ("max_{x} (1/S) Σ_{s} NPV(x, ξ_{s})   s.t.  Pr[ΔE^{rep}(x, ξ) ≥ T] ≥ α,   Pr[Σ_{i} x_{i}C_{i}(ξ) ≤ B] ≥ β,   α = β = 0.90"));
body.push(P(`ΔE^{rep} counts reductions with the fixed reporting factors against the fixed reporting baseline (management decision). Because the probabilities are estimated from S = ${n0(LV.n)} scenarios, each constraint is imposed in-sample at the tightened level α + 1.645·√(α(1−α)/S) = ${LV.alpha_saa.toFixed(4)}, and the chosen portfolio is checked on an independent sample of ${n0(LV.n_validation)} scenarios ([Pagnoncelli, Ahmed & Shapiro, 2009](${URL.saa}); [Birge & Louveaux, 2011](${URL.birge})).`));
body.push(...fig(CH, "c5_mc_distribution.png", "Figure 5. NPV distributions of the highest-expected-NPV portfolio and the validated carbon-reliable portfolio.", 620));
body.push(table(["Portfolio", "E[NPV]", "5th pct", "P(NPV<0)", "P(target)", "P(target) validation", "P(capex ≤ budget)", "P(target) sampled factors"], ["A+B", "A+C+D", "B+C", "A+C"].map(k => {
  const r = mcp[k]; return [k, S(r.e_npv), S(r.p5_npv), pc(r.p_loss, 1), pc(r.p_target, 1), pc(r.p_target_val, 1), pc(r.p_budget, 1), pc(r.p_target_physical, 1)]; }),
  [1000, 1300, 1300, 1000, 1000, 1300, 1300, 1706], { size: 15 }));
body.push(P(`Expected NPVs exceed the deterministic values because the tariff range is skewed upward (possible reform). ${be.portfolio} has the highest expected NPV; it meets the target in ${pc(DS.D2.p_target, 1)} of scenarios and stays within budget in ${pc(DS.D2.p_budget, 1)}. ${DS.D3.portfolio === be.portfolio ? "The carbon rule chooses the same portfolio." : `The carbon rule chooses ${DS.D3.portfolio} (target ${pc(DS.D3.p_target, 1)}, within budget ${pc(DS.D3.p_budget, 1)}).`}`));
body.push(TT("Decision rules: comparison, primary and sensitivity scenarios (same scenarios)"));
body.push(table(["ID", "Rule", "Portfolio", "E[NPV]", "P(target)", "P(target) validation", "P(capex ≤ budget)", "P(capex ≤ budget) validation", "Status"], R.decision_scenarios.map(d =>
  [d.id, `${d.rule} — *${d.category}*`, d.portfolio, d.e_npv != null ? S(d.e_npv) : "—", d.p_target != null ? pc(d.p_target, 1) : "—", d.p_target_val != null ? pc(d.p_target_val, 1) : "—",
   d.p_budget != null ? pc(d.p_budget, 1) : "—", d.p_budget_val != null ? pc(d.p_budget_val, 1) : "—", d.status]),
  [500, 2600, 900, 1050, 800, 900, 900, 950, 1306], { size: 13, highlight: (r, j) => R.decision_scenarios[r].id === "D4" }));
body.push(Cap("P(target) uses the primary basis (fixed reporting baseline) for every row so the rows are comparable; S1 and S2 apply their own basis when choosing (S1: sampled factors, P(target) " + pc(DS.S1.p_target_own_basis, 1) + "; S2: uncertain baseline, " + pc(DS.S2.p_target_own_basis, 1) + "). Validation: independent sample of " + n0(LV.n_validation) + " scenarios."));
R.objectives_explanation.forEach(t => body.push(P(t)));
body.push(P(`**These differences are correct and are not reconciled.** D1 ignores uncertainty; D2 values outcomes by their average; D3 adds a reliability requirement on the carbon target; D4 adds the same requirement on the budget. The deterministic, expected-NPV and carbon-only results are kept as comparison scenarios.`));
body.push(TT("Sampling check of the knife-edge portfolio"));
body.push(table(["Sample", "P(target) of " + KE.portfolio], [
  [`Main sample (${n0(KE.n)} scenarios, seed 20261024)`, pc(KE.p_in_sample, 2) + ` (s.e. ${pc(KE.se_in_sample, 2)})`],
  [`Validation sample (${n0(KE.n_validation)} scenarios, seed 20261025)`, `${pc(KE.p_validation, 2)} (95% CI ${pc(KE.ci95_validation[0], 2)}–${pc(KE.ci95_validation[1], 2)})`],
  ...KE.other_seeds.map(o => [`Other ${n0(KE.n)}-scenario samples, seed ${o.seed}`, pc(o.p_target, 2)])],
  [6000, 3906], { size: 15 }));
body.push(P(KE.p_validation < 0.905 ?
  `The probability is within sampling error of the 90% requirement, which is why the chance constraints are tightened and validated.` :
  `In v1.2 this probability was 89.9% (within sampling error of 90%); with the v1.3 grid factor and PV inputs A+B meets the target in ${pc(KE.p_validation, 2)} of the validation sample, and the recommended ${DS.D3.portfolio} in ${pc(DS.D3.p_target_val, 2)}, so the tightened and validated rule no longer decides a knife-edge.`));
body.push(TT("Budget chance constraint: infeasibility, minimum budget and alternative thresholds"));
body.push(table(["Target-reliable portfolio", "Budget needed for ≥90% compliance", "E[NPV]", "P(target)", "P(target) validation"], MB.slice(0, 4).map(x =>
  [x.portfolio, S(x.budget_needed), S(x.e_npv), pc(x.p_target, 1), pc(x.p_target_val, 1)]), [2400, 2500, 1700, 1500, 1806], { size: 15 }));
const betas = [...new Set(BA.thresholds.map(t => t.beta))].sort(), alphas = [...new Set(BA.thresholds.map(t => t.alpha))].sort();
body.push(table(["P(target) ≥", ...betas.map(b => `P(capex ≤ SAR 5M) ≥ ${pc(b)}`)], alphas.map(a => [pc(a), ...betas.map(b => BA.thresholds.find(t => t.alpha === a && t.beta === b).portfolio)]),
  [1400, ...betas.map(() => Math.floor(8506 / betas.length))], { size: 14 }));
body.push(Cap("Choice at the SAR 5M budget for alternative reliability levels (tightened in-sample, validated out-of-sample)."));
body.push(P(`With the decided 90%/90% levels the minimum budget for the joint rule is ${S(MB[0].budget_needed)} (${MB[0].portfolio}; ${pc(MB[0].budget_needed / R.meta.budget - 1, 1)} relative to the current budget)${feasible ? `, so the rule is feasible at SAR 5M and chooses ${J.portfolio}` : ""}. The budget curve and the full threshold grid are in the workbook (sheet Decision Objectives) and outputs/budget_curve.csv.`));
body.push(TT("Capital cost: quoted vs uncertain actual cost"));
body.push(table(["Portfolio", "Quoted capex", "Mean actual capex", "90th pct", "P(capex > budget)", "P(target met)", "P(target and budget)"], CR.table.filter(r => ["A+B", "A+C+D", "B+C", "A+C", "A+D"].includes(r.portfolio)).map(r =>
  [r.portfolio, S(r.capex), S(r.e_capex), S(r.p90_capex), pc(r.p_over_budget, 1), pc(r.p_target, 1), pc(r.p_target_and_budget, 1)]),
  [1100, 1400, 1500, 1400, 1400, 1400, 1706], { size: 15 }));

body.push(H2("6.5 Value of information"));
body.push(P(`Method: [Howard (1966)](${URL.howard}) information value theory, computed under the carbon decision rule D3 of Section 6.4 (maximise expected NPV subject to the tightened 90% target probability on the primary basis):`));
body.push(EQ("EVPI = E_{θ}[max_{d} V(d, θ)] − max_{d} E_{θ}[V(d, θ)]     EVPPI_{X}: resolve input X only     EVSI: imperfect measurement"));
body.push(...fig(CH, "c6_value_of_information.png", "Figure 6. Expected value of resolving each uncertainty (bars) against the cost of collecting it (red marks).", 620));
const vcmp = Object.fromEntries(VC.ranking.map(r => [r.parameter, r.evppi_sar]));
body.push(table(["Information", "EVPPI", "EVPPI − noise floor", "Collection cost", "EVPPI, v1.1 rule (comparison)"], R.voi.map(r =>
  [r.information, S(r.evppi_sar), S(r.net_of_noise_floor), r.collection_cost_sar != null ? S(r.collection_cost_sar) : "not collectable / not estimated", vcmp[r.parameter] != null ? S(vcmp[r.parameter]) : "—"]),
  [3700, 1300, 1600, 1700, 1606], { size: 15 }));
body.push(P(`EVPI (all uncertainty resolved) is ${M(R.evpi)}; a dummy irrelevant variable gives ${S(R.voi_noise_floor)} (noise floor). The highest single item is ${R.voi[0].information} (EVPPI ${M(R.voi[0].evppi_sar)}); the motor-system audit is worth ${M(R.evsi_audit.evsi)} (EVSI) against an assumed SAR 80k cost. In v1.2, when A+B sat on the 90% boundary, the audit was worth SAR 0.58M; with the v1.3 inputs the recommended portfolio is robust to B's savings, so information that cannot change the choice has little value. **Value of information differs from data quality:** steel supplier data is among the least certain inputs (±21.6%) yet has no value, because the Scope 3 project cannot change the Scope 1+2 decision.`));

body.push(H2("6.6 Sensitivity analysis and decision robustness"));
body.push(P(`Method: [Saltelli et al. (2008)](${URL.saltelli}). *Uncertainty analysis* measures the spread of outcomes (6.4); *sensitivity analysis* finds which inputs cause it (one-way tornado and first-order variance indices S_{i} = Var(E[Y|X_{i}]) ⁄ Var(Y), estimated by binning the Monte Carlo sample); *robustness testing* asks whether the **recommendation** changes (switch points).`));
body.push(...fig(CH, "c7_tornado.png", `Figure 7. NPV of the deterministic optimum (${opt.portfolio}) with each input at its 5th and 95th percentile.`, 600));
body.push(...fig(CH, "c9_sobol_decision.png", "Figure 8. Inputs driving the choice between the two leading portfolios (first-order indices).", 580));
const swRows = Object.entries(sw).map(([k, x]) => [k, x.robust ? "robust over tested range" : x.changes.map(c => `at ${Number(c[0]).toLocaleString("en-US", { maximumSignificantDigits: 4 })}: ${c[1]} → ${c[2]}`).join("; ")]);
body.push(table(["Input varied (others at base)", "Effect on the deterministic optimum"], swRows, [3000, 6906], { size: 15 }));
body.push(P(`Inputs whose variation within their ranges changes the deterministic optimum: ${swList.length ? swList.join("; ") : "none"}. Compressed-air savings switch the choice at the base value itself (C's NPV is close to zero), so the inclusion of C is marginal; solar cost no longer switches the choice within ±29% of the benchmark. Discount rate: ${dr.map(d => `${pc(d.rate)} → ${d.with_target}`).join(", ")} (with the target).`));
body.push(TT("Tariff scenarios (full re-optimisation; in the Monte Carlo the tariff is fixed at the scenario value)"));
body.push(table(["Scenario", "SAR/kWh", "D1 Deterministic", "NPV", "D2 Highest E[NPV]", "E[NPV]", "D3 Carbon", "E[NPV]", "D4 Carbon + budget"], R.tariff_scenarios.map(t =>
  [`${t.id} ${t.label}`, n2(t.tariff), t.deterministic, S(t.det_npv), t.best_expected, S(t.best_expected_e_npv), t.chance_constrained, t.cc_e_npv != null ? S(t.cc_e_npv) : "—", t.joint]),
  [2200, 650, 950, 1050, 950, 1050, 950, 1050, 1056], { size: 13 }));
body.push(P(`Choices across the four tariffs — D1: ${[...new Set(R.tariff_scenarios.map(t => t.deterministic))].join("/")}; D3: ${[...new Set(R.tariff_scenarios.map(t => t.chance_constrained))].join("/")}; D4: ${[...new Set(R.tariff_scenarios.map(t => t.joint))].join("/")} (tariffs change savings, not capital cost or emissions). At the 2027 tariff reported in the press (${TS.T2.tariff} SAR/kWh) the deterministic NPV of ${TS.T2.deterministic} rises from ${M(TS.T0.det_npv)} to ${M(TS.T2.det_npv)}. If the tariff stays at 0.18 for certain, the highest-expected-NPV portfolio is ${TS.T0.best_expected} and the carbon-rule ${TS.T0.chance_constrained} has E[NPV] ${S(TS.T0.cc_e_npv)}.`));
body.push(TT("Grid-factor scenario"));
body.push(table(["Scenario", "tCO₂/MWh", "Target t/yr", "D1", "D2 (P target)", "D3 carbon (P target)", "D4 carbon + budget"], ES.map(e =>
  [e.label, String(e.ef_grid), n0(e.target_t), e.deterministic, `${e.best_expected} (${pc(e.best_expected_p_target, 1)})`, `${e.chance_constrained} (${e.cc_p_target != null ? pc(e.cc_p_target, 1) : "—"})`, e.joint]),
  [2600, 800, 900, 800, 1600, 1800, 1406], { size: 14 }));
body.push(P(`Across the three factors (0.55, 0.568, ${A.ef_grid.value}) the carbon rule chooses ${ES.map(e => e.chance_constrained).join(" / ")} and the joint rule ${ES.map(e => e.joint).join(" / ")}. In v1.2 (expensive PV) the factor mattered for the carbon rule; with the v1.3 inputs it does not change the choice.`));
body.push(TT("Industrial gas price and rooftop PV cost scenarios (v1.3)"));
body.push(table(["Scenario", "Value", "D1", "NPV", "D3 Carbon", "D4 Carbon + budget", "Minimum budget for D4"], [
  ...GS.map(g => [`${g.id} ${g.label}`, `$${n2(g.gas_price_usd)}/MMBtu`, g.deterministic, S(g.det_npv), g.chance_constrained, g.joint, S(g.joint_min_budget)]),
  ...PS.map(p => [`${p.id} ${p.label}`, `SAR ${n0(p.pv_capex_kw)}/kWp`, p.deterministic, S(p.det_npv), p.chance_constrained, p.joint, S(p.joint_min_budget)])],
  [2900, 1200, 900, 1100, 1000, 1300, 1506], { size: 14 }));
body.push(P(`The gas price affects only heat recovery (D), which is not in the recommended portfolio, so G0–G2 leave the choices unchanged. The PV cost is decisive: at the v1.2 assumption of SAR 3,750/kWp the joint rule becomes ${PS[1].joint} (minimum budget ${S(PS[1].joint_min_budget)}). A formal PV quotation is therefore the most valuable piece of evidence for this decision.`));

body.push(H2("6.7 Investment timing (real options)"));
body.push(P(`Method: real-options analysis of irreversible investment ([Dixit & Pindyck, 1994](${URL.dixit})) as applied by [KAPSARC DP49 (Albalawi & Sirin, 2026)](${URL.dp49}) to Saudi offshore decarbonization: the gas price follows a log-Ornstein–Uhlenbeck process (κ = 0.5, σ = 0.522; DP49's mean of $3/MMBtu is replaced since v1.3 by the current regulated price $${n2(tree.g_now_usd)}), the stopping problem is solved with least-squares Monte Carlo ([Longstaff & Schwartz, 2001](${URL.lsm})), and a GBM closed form gives a benchmark trigger. DP49's offshore results are **not** transferred to manufacturing; only the method and its calibration are reused, and the application to heat recovery D is our adaptation.`));
body.push(EQ("Invest now if NPV_{now} ≥ V_{wait};   GBM trigger G^{*} = λ⁄(λ−1) × (C + O&M·A_{r}) ⁄ (A_{μ}·q)   (DP49 Eq. C.7, C.13)"));
body.push(...fig(CH, "c8_timing.png", "Figure 9. Left: reform decision tree (prototype method). Right: log-OU LSMC extension — value of investing now vs optimal waiting by long-run gas price.", 640));
body.push(table(["Timing result for D (heat recovery)", "Value"], [
  [`Static NPV at today's $${n2(tree.g_now_usd)}/MMBtu`, S(tree.npv_if_no_reform_at_t1)],
  ["Static break-even gas price", `$${n2(tree.static_breakeven_usd)}/MMBtu`],
  [`Decision tree: invest now (reform p = ${tree.p_reform}, to $${tree.g_reform_usd})`, S(tree.npv_invest_now)],
  ["Decision tree: wait one year for the decision", S(tree.value_wait_one_year)],
  ["Option value of waiting → decision", `${K(tree.option_premium)} → ${tree.decision}`],
  ["LSMC (log-OU, 5,000 + 5,000 paths): long-run price at which investing now beats waiting", scan.trigger_usd ? `≈ $${n2(scan.trigger_usd)}/MMBtu (grid step $0.25)` : "not reached"],
  ["GBM closed-form trigger (benchmark)", `$${n2(gbm.trigger_usd)}/MMBtu (multiplier ${n2(gbm.multiplier)})`],
], [6200, 3706], { size: 16 }));
body.push(P(`**Interpretation and limits.** For an administered industrial gas price that changes by policy decision, the **decision tree** is the defensible prototype method: it shows that waiting for the price decision is worth ${K(tree.option_premium)} and remains preferable even at reform probabilities (70–90%) where investing now already has a positive NPV — the classic real-options result that a positive NPV is not sufficient. The LSMC extension, using DP49's market-gas volatility, gives a trigger of about $${n2(scan.trigger_usd)}/MMBtu (κ 0.2–1.0 and σ 0.3–0.75 move it between $${Math.min(...R.timing_sens.map(x => x.trigger_usd))} and $${Math.max(...R.timing_sens.map(x => x.trigger_usd))}); because an administered price does not fluctuate monthly with Henry Hub volatility, this figure illustrates the method rather than guiding the decision. The GBM benchmark overstates the trigger, as DP49 also notes. Timing is consistent with the portfolio: ${opt.portfolio.includes("D") ? `D is in the recommended portfolio, so deferral would cost ${n0(tree.deferred_t_year1)} t in year 1 — a trade-off management must judge explicitly` : "D is not in the recommended portfolio, so its timing does not affect the target"}. The deferral uncertainty (price policy, resolved by time) differs from the audit uncertainty (savings, resolved by measurement), so the option value and the information value are not double counted.`));

body.push(H2("6.8 Integrated workflow and final recommendation"));
body.push(table(["Stage", "Input", "Calculation", "Output"], [
  ["1 Data", "Bills, fuel cards, procurement, carrier data", "Validation, status tagging, proxy estimates", "Activity register"],
  ["2 Carbon footprint", "Activity, emission factors", "E = A × EF by scope", "Baseline by source and scope"],
  ["3 Data quality", "Error ranges", "First-order propagation + Monte Carlo check", "Baseline ± range"],
  ["4 Project modelling", "Costs, savings, prices", "NPV, MAC, shared ledger", "Project economics"],
  ["5 Optimization", "Budget, target, rules", "Integer program / enumeration", "Optimal portfolio"],
  ["6 Uncertainty", "Distributions", "20,000 scenarios, chance constraint", "Robust portfolio"],
  ["7 Information value", "Collection costs", "EVPI, EVPPI, EVSI", "What to learn first"],
  ["8 Sensitivity", "All inputs", "Tornado, variance indices, switch points", "Key drivers"],
  ["9 Timing", "Deferrable projects", "Decision tree; LSMC extension", "Invest now / wait"],
  ["10 Recommendation", "Stages 2–9", "Rules + explanation", "Management decision memo"],
], [1700, 2500, 3200, 2506], { size: 15 }));
body.push(P("The workflow is iterative: the audit recommended in stage 7 updates stages 4–6, after which the portfolio choice is re-run."));
body.push(callout([
  feasible ?
  `**Recommendation to management (synthetic case).** (1) **Primary rule result:** **${J.portfolio}** meets both the 90% carbon (${pc(J.p_target, 1)}) and the 90% budget (${pc(1 - J.p_over_budget, 1)}) requirements at SAR 5M, with E[NPV] ${M(J.e_npv)}; the deterministic, expected-NPV and carbon rules agree. (2) The result depends on the Riyadh rooftop-PV cost benchmark: obtain **formal PV quotations** first — at SAR 3,750/kWp the joint rule is ${PS[1].joint} (Section 6.6). (3) Treat **compressed air (C)** as marginal (NPV ${M(pr.C.npv)}): include it only with a committed leak-management programme. (4) The motor-system audit is not worth its assumed cost for this decision (EVSI ${M(R.evsi_audit.evsi)}). (5) Heat recovery: ${tree.decision.toLowerCase()} at the regulated gas price. (6) Do not electrify forklifts for carbon reasons while the grid factor stays near ${A.ef_grid.value} t/MWh. (7) Confirm the 2027 industrial tariff from the official Saudi Energy schedule before committing.` :
  `**Recommendation to management (synthetic case).** (1) **Primary rule result:** no portfolio meets both the 90% carbon and the 90% budget requirements at SAR 5M; the rule becomes feasible at about ${S(MB[0].budget_needed)} (${MB[0].portfolio}). (2) Obtain formal quotations, confirm the 2027 tariff and re-run.`,
], "E2F0D9", "3E8E7E"));

// ---------------------------------------------------------------- 7 implementation
body.push(H1("7. Implementation architecture and validation"));
body.push(table(["Component", "Role"], [
  ["carbon_iq/assumptions.py", "Single register of all inputs: value, unit, status, source, distribution"],
  ["engine.py", "Baseline accounting, uncertainty propagation, finance primitives, project models, shared activity ledger"],
  ["optimize.py", "HiGHS integer program, exhaustive enumeration, ranking baselines, efficient frontier"],
  ["uncertainty.py · voi.py · sensitivity.py · timing.py", "Monte Carlo and chance constraints (incl. actual-capex risk and counting basis); EVPI/EVPPI/EVSI; tornado, variance indices, switch points; decision tree, LSMC, GBM trigger"],
  ["decisions.py (v1.1)", "Three decision objectives, counting-basis comparison, capital-cost risk, tariff and grid-factor scenarios"],
  ["recalc.py (v1.1)", "Portable LibreOffice recalculation of the workbook; status recorded in outputs/excel_recalc.json"],
  ["tools/ (v1.1)", "run_tests.py (suite + summary), fault_injection.py, crosscheck.py (Python vs Excel vs Word), compare_versions.py"],
  ["pipeline.py · run_all.py", "End-to-end run writing CSV/JSON/charts, the Excel model and a SHA-256 manifest"],
  ["Mezan_Data_Model.xlsx", "19 sheets (including Source Register and A5 Changes); deterministic chain as live formulas (including the 64-portfolio optimum and the decision tree); simulation results as labelled values"],
  ["app.py", "Streamlit interface: budget, target, confidence, prices and discount rate recompute all results"],
  ["tests/", `${TEST.total} automated tests (engine, decisions, timing, outputs, v1.1–v1.2 rules, A4 data quality, A5 inputs, A6 independent checks)`],
], [3300, 6606], { size: 16 }));
body.push(TT("Validation evidence"));
body.push(table(["Check", "Result"], [
  ["Automated tests (python tools/run_tests.py)", `${TEST.passed} passed, ${TEST.failed} failed, ${TEST.skipped} skipped (Python ${TEST.python}, NumPy ${TEST.versions.numpy}, Streamlit ${TEST.versions.streamlit})`],
  ["Minimum versions and Colab", "Suite also run with the minimum versions in requirements.txt (Python 3.11) and by executing the README Colab cell in IPython (see A1 completion report)"],
  ["Hand calculations", "Baseline factors, IPCC gas factor, project A/D/E/F cash flows and reductions, NPV/IRR/payback, decision tree, GBM λ"],
  ["GHG Protocol worked example", "110 t ±4% + 90 t ±24% → ±11.0% reproduced"],
  ["Analytic vs simulation uncertainty", `Scope 1+2: ±${n1(ut["Scope 1+2"].u95_pct)}% first-order vs ±${n1(R.mc_baseline_scope12.u95_pct)}% Monte Carlo`],
  ["Optimization", A6 ? `MILP = model enumeration = independent enumeration (separate code) in all ${A6.optimization.cases.toLocaleString("en-US")} budget/target/exclusivity cases (A6); ${A6.optimization.infeasible_cases.toLocaleString("en-US")} infeasible cases reported as infeasible` : "MILP = enumeration in 8 budget/target cases, with an exclusivity rule and an infeasible case"],
  ...(A6 ? [["Independent recalculation (A6)", `Emissions ${A6.emissions.passed}/${A6.emissions.n} and finance ${A6.finance.passed}/${A6.finance.n} checks agree with separately written code; independent spreadsheet ${A6.workbook ? A6.workbook.checks + " checks, all pass: " + A6.workbook.all_pass : ""}; independent Monte Carlo sampler gives the same D2/D3/D4 choices (see the A6 validation report)`]] : []),
  ["No double counting", "Ledger reduction equals portfolio reduction for all 64 portfolios; overlap removed only when B and C are both chosen"],
  ["Value-of-information sanity", "0 ≤ EVPPI ≤ EVPI; irrelevant variable → 0; no uncertainty → EVPI = 0; EVSI ≤ EVPPI"],
  ["Excel vs Python", `${XREC.total_formulas} formulas, ${XREC.total_errors} errors (v1.0 reported 920 because LibreOffice stores 24 TRUE/FALSE constants as formulas); baseline, uncertainty, NPVs, Excel NPV() cash flows, optimum, objectives, tree and trigger equal Python`],
  ["Reproducibility", "Fixed seeds; identical results on repeated runs; SHA-256 manifest of all outputs"],
  ["Fault injection (tools/fault_injection.py)", `${FAULT.detected} of ${FAULT.faults} deliberate errors detected: ${FAULT.results.map(r => r.fault).join(", ")}`],
], [3300, 6606], { size: 16 }));
body.push(TT("Changes from version 1.0 and their effect on results"));
body.push(table(["Change (A1 issue)", "Effect on results"], [
  ["Colab cell corrected; notebook added (A1-01)", "None (execution only)"],
  ["Minimum versions: NumPy ≥ 2.0, Streamlit ≥ 1.49 and others; lock file (A1-03)", "None (v1.0 outputs were already identical across versions)"],
  ["'AI-Enabled' removed from titles (A1-04)", "None"],
  ["Status labels: 12 'verified' values relabelled transferred (10) or provisional (2: tariff, grid factor) (A1-07, A1-13)", "None (labels only)"],
  ["Activity uncertainties (diesel ±5/±10%, steel ±2%, freight ±20%) moved into the register and sampled (A1-09)", `Analytic uncertainty unchanged; Monte Carlo check ±7.50% → ±${n2(R.mc_baseline_scope12.u95_pct)}%; EVPI SAR 651,351 → ${S(R.evpi)}; all decisions unchanged`],
  ["v1.2: carbon chance constraint on the fixed reporting baseline (management decision; A1-02)", `In v1.2 the carbon rule picked A+C+D after tightening (A+B in-sample at 90.3%). v1.3 sensitivities: sampled factors ${DS.S1.portfolio}, uncertain baseline ${DS.S2.portfolio}`],
  ["v1.2: 90% budget chance constraint (management decision; A1-10)", "Primary rule infeasible at SAR 5M in v1.2; minimum budget SAR 5,202,423 (A+C+D)"],
  ["v1.2: chance constraints tightened for sampling error and validated on 200,000 scenarios", "Carbon rule A+B → A+C+D in v1.2; VOI under the v1.2 rule had a noise floor of SAR 269,985 (v1.1: 0)"],
  ["v1.3 (A5): grid factor, gas price, PV cost and degradation, compressed-air savings and leak cost re-sourced (Section 6.9)", `Optimum ${AT[0].deterministic} → ${opt.portfolio}; primary rule ${AT[0].joint} → ${J.portfolio}; EVPI SAR 0.65M → ${M(R.evpi)}`],
  ["Tariff and grid-factor scenarios (A1-08, A1-07)", "New scenario results; reference results unchanged"],
  ["VOI collection costs linked to inputs; solar-capex row relabelled 'cost not estimated' (A1-18)", "None"],
], [5000, 4906], { size: 15 }));

body.push(TT("What is validated and what is illustrative"));
body.push(table(["Validated (checked by tests, cross-checks or independent samples)", "Illustrative (depends on synthetic or unconfirmed inputs)"], [
  ["Calculations: accounting, NPV, MAC, uncertainty propagation, optimisation (MILP = enumeration), ledger without double counting", "All facility activity data, project costs and savings shares (synthetic case)"],
  ["Internal consistency: Python = Excel (live formulas) = Word figures; reproducible outputs; injected faults detected", "Distribution ranges (judgement-based), the 2027 tariff, the grid factor, the gas-price anchor and transferred factors"],
  ["Chance-constraint feasibility of the reported choices on an independent 200,000-scenario sample", "Every portfolio choice, NPV and probability as advice for a real plant"],
  ["Statistical behaviour of the decision rules (sampling error, tightening)", "Value-of-information magnitudes under the new rule (noise floor; method revision in A6)"],
], [4953, 4953], { size: 15 }));

// ---------------------------------------------------------------- 8 limitations
body.push(H1("8. Limitations and future development"));
[
  "**Synthetic case.** Activity data and project costs are illustrative; results show how the method behaves, not what any facility should do.",
  "**Data proxies.** Grid factor derived from 2021 national statistics (category boundaries not reconciled); 2027 industrial tariff and 2026 gas price not confirmed by primary documents; PV cost is a market benchmark, other project costs are placeholders; UK diesel and freight factors; world-average crude-steel factors; savings shares unverified until audits.",
  "**Decision framing.** Management fixed the counting basis (fixed reporting baseline) and the 90% budget requirement on 25 October 2026. In v1.2 no portfolio was feasible at SAR 5M; with the v1.3 inputs the rule is feasible, but this rests on the PV cost benchmark.",
  "**Inventory boundary.** Refrigerant leakage (Scope 1), upstream fuel and grid-loss emissions (Scope 3 Category 3) and other purchased goods are outside the prototype boundary; Scope 2 is location-based only (no market-based instruments are modelled).",
  "**Competitor benchmark.** The table in Section 3 is the team's unsourced assessment; evidence-based benchmarking is Phase A3.",
  "**Uncertainty model.** Inputs are sampled independently from judgement-based ranges; correlations (e.g. between tariff and gas price reform) and model uncertainty are not represented. First-order variance indices omit interactions (total-effect indices are an extension).",
  "**Optimization scope.** Single period, one budget, binary projects; no partial sizing, phasing, financing, taxes or escalation. Enumeration is exact here; larger cases rely on the MILP.",
  "**Timing.** The decision tree assumes one reform event; the LSMC extension borrows a market-gas calibration that does not describe administered prices; DP49 results are not transferred.",
  "**Value of information.** Binning estimators (20 bins) carry small sampling error near a threshold; audit and data costs are assumptions.",
  "**No machine learning.** The prototype uses optimization, simulation and decision analysis; machine-learning features (e.g. gap filling, anomaly detection) are possible future work and are not claimed.",
].forEach(x => body.push(B(x)));
body.push(TT("Future development"));
[
  "Pilot on a real Saudi facility: connect metered data, procurement and quotations; validate recommendations against outcomes.",
  "Obtain the official 2027 tariff schedule, formal PV and equipment quotations, the plant's real gas supply and price; obtain supplier-specific steel and freight data; add refrigerants, Scope 3 Category 3 and market-based Scope 2.",
  "Model correlated uncertainties, multi-period budgets and phased investment (two-stage recourse), and total-effect sensitivity indices.",
  "Add documented machine-learning components only where they demonstrably improve estimates (e.g. missing-month imputation with uncertainty).",
].forEach(x => body.push(B(x)));
body.push(P("**Changes from the earlier methodology paper.** The methodology paper used illustrative project numbers (e.g. 2,700 MWh solar). This prototype replaces them with source-anchored inputs (1,000 kWp at 1,850 kWh/kWp, SEC tariff, KAPSARC 6% rate, IPCC/DESNZ/worldsteel factors), so case results differ; the methods and their integration are unchanged.", { p: { spacing: { before: 120 } } }));

// ---------------------------------------------------------------- references
body.push(H1("References"));
[
  `Albalawi, A. & El-Houjeiri, H. (2026). *Decarbonization Pathways for Offshore Oil Power Systems: The Case of Saudi Arabia*. KAPSARC. [doi.org/10.30573/KS--2026-DP24](${URL.dp24})`,
  `Albalawi, A. & Sirin, S.M. (2026). *Decarbonization Investments Under Uncertainty: A Real-Option Analysis of Renewable Energy Investments for Offshore Oil Platforms in Saudi Arabia*. KAPSARC Discussion Paper. [doi.org/10.30573/KS--2026-DP49](${URL.dp49})`,
  `Alorfi, A.S. & Alsaadi, N. (2025). Barriers to the adoption of big data analytics in Saudi Arabia's manufacturing sector. *Systems* 13(4), 250. [doi.org/10.3390/systems13040250](${URL.mdpi})`,
  `BDO Saudi Arabia: Sharjeel, A.R. & Zaidi, S.M.A. (2025). *Practical challenges in compiling a meaningful ESG report*. [bdoalamri.com](${URL.bdo})`,
  `Birge, J.R. & Louveaux, F. (2011). *Introduction to Stochastic Programming* (2nd ed.). Springer. [doi.org/10.1007/978-1-4614-0237-4](${URL.birge})`,
  `Dixit, A.K. & Pindyck, R.S. (1994). *Investment under Uncertainty*. Princeton University Press. [press.princeton.edu](${URL.dixit})`,
  `GHG Protocol (n.d.). *Short Guidance for Calculating Measurement and Estimation Uncertainty for GHG Emissions*. WRI/WBCSD. [PDF](${URL.unc})`,
  `GHG Protocol: *Corporate Accounting and Reporting Standard* (rev. ed., 2004) [link](${URL.ghg}); *Scope 2 Guidance* (2015) [link](${URL.s2}); *Corporate Value Chain (Scope 3) Standard* (2011) [link](${URL.s3})`,
  `Hobbs, B.F. (1995). Optimization methods for electric utility resource planning. *European Journal of Operational Research* 83(1), 1–20. [doi.org/10.1016/0377-2217(94)00190-N](${URL.hobbs})`,
  `Howard, R.A. (1966). Information value theory. *IEEE Transactions on Systems Science and Cybernetics* 2(1), 22–26. [doi.org/10.1109/TSSC.1966.300074](${URL.howard})`,
  `IEA 4E EMSA (2025). *Policy Brief #9: Electric motor systems*. [iea-4e.org](${URL.iea4e})`,
  `IPCC (2006). *2006 IPCC Guidelines for National GHG Inventories*, Vol. 2, Ch. 2 Stationary Combustion. [PDF](${URL.ipcc})`,
  `IRENA (2025). *Renewable Power Generation Costs in 2024* (summary). [PDF](${URL.irena})`,
  `KAPSARC: Yousef, F. et al. (2025). *Navigating Global Sustainability Reporting and Taxonomies: Insights for Saudi Arabia*. [kapsarc.org](${URL.kapsarc25})`,
  `Longstaff, F.A. & Schwartz, E.S. (2001). Valuing American options by simulation. *Review of Financial Studies* 14(1), 113–147. [doi.org/10.1093/rfs/14.1.113](${URL.lsm})`,
  `Pagnoncelli, B.K., Ahmed, S. & Shapiro, A. (2009). Sample average approximation method for chance constrained programming: theory and applications. *Journal of Optimization Theory and Applications* 142(2), 399–416. [doi.org/10.1007/s10957-009-9523-6](${URL.saa})`,
  `Saltelli, A. et al. (2008). *Global Sensitivity Analysis: The Primer*. Wiley. [doi.org/10.1002/9780470725184](${URL.saltelli})`,
  `Saudi Electricity Company. *Consumption tariffs* (applied since 1 Jan 2018), via ESMAP RISE. [PDF](${URL.sec})`,
  `UK DESNZ (2025). *Greenhouse gas reporting: conversion factors 2025*. [gov.uk](${URL.desnz})`,
  `US DOE (2000). *Minimize Compressed Air Leaks*, Compressed Air Tip Sheet #3. [PDF](${URL.doe})`,
  `World Economic Forum (2023). *Emissions Measurement in Supply Chains: Business Realities and Challenges*. [weforum.org](${URL.wef})`,
  `worldsteel (2025). *Sustainability Indicators Report 2025*. [worldsteel.org](${URL.worldsteel})`,
  `AGBI (Jan 2026). *Saudi companies face cost increase as Aramco ups diesel price*. [agbi.com](${URL.agbi}); NASA POWER irradiance for Riyadh via [profilesolar.com](${URL.nasa})`,
  `Argaam (13 Dec 2017). *Saudi Arabia to hike electricity tariffs from January 1* (ECRA statement). [argaam.com](${URL.argaam17})`,
  `Attaqa (25 Oct 2026). Saudi electricity prices raised for 2027 (in Arabic). [attaqa.net](${URL.attaqa26}); Saudi Life Guide (25 Oct 2026). *Saudi Electricity Tariff 2027*. [saudilifeguide.com](${URL.slg26})`,
  `The National (25 Oct 2026). *Saudi Arabia announces support measures as electricity and water tariffs rise*. [thenationalnews.com](${URL.national26})`,
  `SPARK Utilities (27 Apr 2025). Intensive electricity consumption tariff notice. [spark.sa](${URL.spark25})`,
  `KFUPM (2025). *Greenhouse Gas Emissions Inventory for 2024* (cites Saudi DNA, *Development of the Kingdom's Updated Grid Emission Factor 2021*). [PDF](${URL.kfupm24})`,
  `IFI Technical Working Group (Jul 2019). *Harmonized IFI Default Grid Factors*, v2.0. UNFCCC. [PDF](${URL.ifi19})`,
  `Kingdom of Saudi Arabia (2025). *First Biennial Transparency Report* (UNFCCC). [PDF](${URL.btr1}); GASTAT (2022). *Electric Energy Statistics 2021* (Arabic). [PDF](${URL.gastat21})`,
  `Saudi Press Agency (25 Oct 2026). *Saudi Energy announces electricity service tariff adjustment from January 1, 2027*. [spa.gov.sa](${URL.spa27})`,
  `Al Jazira Capital (Jan 2025). *The potential impacts of feedstock price hikes*. [PDF](${URL.ajc25}); MEES (2 Jan 2026). *Saudi increases diesel prices*. [mees.com](${URL.mees26})`,
  `Knight Frank (2025). *Going Green: Rooftop solar potential in the GCC*. [PDF](${URL.kf25}); Alzahrani, G.S. & Nahhas, A.M. (2021). Analytical study of power generation by PV system for Al-Riyadh and Al-Jubail. *American Journal of Energy Research* 9(1), 45–55. [link](${URL.alz21})`,
  `Jordan, D.C. & Kurtz, S.R. (2013). Photovoltaic degradation rates — an analytical review. *Progress in Photovoltaics* 21(1), 12–29. [doi.org/10.1002/pip.1182](${URL.jk13})`,
  `Schröder, A., Liebertseder, J. & Doppelbauer, M. (2023). *Study on the energy-saving potential of electric motors with variable-speed drives in the EU*. Fraunhofer ICT for CEMEP. [PDF](${URL.fh23})`,
  `Compressed Air Challenge (2026). *Fact sheet 7: Compressed air system leaks*. [PDF](${URL.cac26}); US DOE (2007). *Process Heating Tip Sheet #1: Preheated combustion air*. [PDF](${URL.doeph})`,
].forEach(r => body.push(new Paragraph({ spacing: { after: 60 }, indent: { left: 300, hanging: 300 }, children: L.runs(r, { size: 17 }) })));

// ---------------------------------------------------------------- appendices
body.push(H1("Appendix A. Assumption register", true));
body.push(P(`All ${R.assumptions.length} inputs as used in this report, the workbook and the code. Status: verified = cited public source, applicable here; derived = calculated from verified values; transferred = cited source from another context; provisional = partial or secondary evidence, or a change announced; hypothetical = case assumption. Distributions are the Monte Carlo ranges.`));
const distTxt = d => !d ? "fixed" : d.replace(/[()']/g, "").replace("normal_rel,", "normal, s.d. ×").replace("triangular,", "triangular").replace("uniform,", "uniform").replace("lognormal,", "lognormal σ");
body.push(table(["Key", "Value", "Unit", "Status / evidence", "Source / rationale", "Range"], R.assumptions.map(a =>
  [a.key, Number(a.value).toLocaleString("en-US", { maximumSignificantDigits: 6 }), a.unit, `${a.status} / ${a.evidence}`, a.source + (a.published ? ` (published ${a.published})` : ""), distTxt(a.dist)]),
  [1500, 950, 1250, 1150, 3800, 1256], { size: 13 }));
body.push(H1("Appendix B. Using the workbook, code and prototype interface"));
body.push(TT("Excel data model (Mezan_Data_Model.xlsx)"));
body.push(table(["Sheet", "Contents"], [
  ["README · Dashboard", "Guide, colour legend, data dictionary; management summary linked to the model"],
  ["Facility Profile · Production & Operations · Electricity & Fuel · Suppliers & Logistics", "Case definition and synthetic monthly/annual activity data with prices"],
  ["Emission Factors · Baseline Emissions · Data Quality", "Factors with sources; activity × factor; GHG Protocol propagation (formulas)"],
  ["Investment Alternatives · Financials & Cash Flows", "Project inputs, physical effects, NPV, MAC, payback; 25-year cash flows with Excel NPV() cross-check"],
  ["Optimization", "All 64 portfolios evaluated by formula; optimum by INDEX/MATCH; ranking baselines"],
  ["Monte Carlo · Decision Objectives", "Python results (purple) incl. actual-capex risk; three objectives with live NPV links, counting basis, budget risk, tariff and grid-factor scenarios"],
  ["Value of Information · Sensitivity", "Python results (purple); collection costs linked to inputs and net value of information as formulas"],
  ["Investment Timing", "Reform decision tree and GBM trigger as formulas; LSMC scan as Python values"],
], [3900, 6006], { size: 16 }));
body.push(P("Edit blue input cells only. Deterministic results update immediately; purple simulation results require re-running python run_all.py. Status cells use a drop-down (verified / derived / transferred / provisional / hypothetical) and numeric inputs are validated as non-negative.", { p: { spacing: { before: 100 } } }));
body.push(TT("Running the prototype"));
body.push(EQ("pip install -r requirements.txt  →  python run_all.py  →  python tools/run_tests.py  →  streamlit run app.py"));
body.push(P("In Google Colab use Mezan_Colab.ipynb or the README cell; `%cd /content/Mezan` must be on its own line. Installing LibreOffice (one apt-get line) enables the Excel-agreement tests; otherwise they are reported as skipped."));
body.push(P("run_all.py writes outputs/ (CSV tables, results.json, charts, manifest.json) and regenerates the workbook in about 20 seconds. The Streamlit interface recomputes every result when the budget, target, confidence level, prices or discount rate change; it uses 5,000 scenarios by default, so its simulated figures differ slightly from the 20,000-scenario values in this report."));
body.push(...fig(__dirname, "app_uncertainty.png", "Figure 10. Prototype interface: decision rules tab (default settings, 5,000 scenarios; primary basis and 90% budget rule).", 600));

const doc = new Document({
  creator: "Mezan project team", title: "Mezan | ميزان – Complete Project Report (v1.3)", features: { updateFields: true },
  styles: { default: { document: { run: { font: FONT, size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 28, bold: true, font: FONT, color: NAVY }, paragraph: { outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 23, bold: true, font: FONT, color: NAVY }, paragraph: { outlineLevel: 1 } }] },
  numbering: { config: [
    { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 240 } } } }] },
    { reference: "num", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 300 } } } }] }] },
  sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1000, right: 1000, bottom: 1000, left: 1000 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
      new TextRun({ text: "Mezan  |  Research prototype · synthetic case  |  Page ", font: FONT, size: 15, color: "6B7C93" }),
      new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 15, color: "6B7C93" })] })] }) },
    children: body }],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync(OUT, b); console.log("written", OUT); });
