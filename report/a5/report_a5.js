// Mezan Phase A5 — Saudi-relevant carbon and financial methodology report.
// Usage: node report_a5.js <project dir> <data.json> <out.docx>. Every number is read from the pipeline outputs (prep_a5.py).
const fs = require("fs");
const path = require("path");
const L = require(fs.existsSync(path.resolve(__dirname, "../lib.js")) ? path.resolve(__dirname, "../lib.js") : path.resolve(__dirname, "../full/report/lib.js"));
const { D, P, H1, H2, B, TT, callout, table, Cap, fig, EQ } = L;
const [, , ROOT, DATA, OUT] = process.argv;
const X = JSON.parse(fs.readFileSync(DATA, "utf8"));
const S = X.S, R = X.R;
const CH = path.join(ROOT, "outputs", "a5", "charts");
const f0 = v => v == null || Number.isNaN(v) ? "—" : Math.round(v).toLocaleString("en-US");
const f1 = v => v == null ? "—" : Number(v).toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const fm = v => v == null ? "—" : (v / 1e6).toFixed(2) + "M";
const pc = (v, d = 1) => v == null || Number.isNaN(v) ? "—" : (100 * v).toFixed(d) + "%";
const p4 = v => v == null ? "—" : Number(v).toFixed(4);
const reg = Object.fromEntries(S.register.map(r => [r.key, r]));
const dec = Object.fromEntries(S.decisions.map(d => [d.rule.slice(0, 2), d]));
const prj = Object.fromEntries(S.projects.map(p => [p.project, p]));
const pf = Object.fromEntries(S.portfolios.map(p => [p.portfolio, p]));
const att = S.attribution;
const a12 = att[0], a13 = att[att.length - 1];
const only = k => att.find(a => a.case.startsWith("only: " + k));
const sc = (inp, id) => S.scenario_results.find(s => s.input === inp && s.id === id);
const inv = Object.fromEntries(S.inventory.map(i => [i.item, i]));
const ds = Object.fromEntries(R.decision_scenarios.map(d => [d.id, d]));
const sw = R.switch_points;
const dr = Object.fromEntries(R.discount_robustness.map(d => [d.rate, d]));
const voiC = R.voi.find(v => v.parameter === "c_saving_frac");
const tt = R.timing_tree;
const val = v => typeof v === "number" ? (Math.abs(v) >= 100 ? f0(v) : String(+v.toPrecision(4))) : v;
const pvSwitch = (5e6 - prj.B.capex_v13 - prj.C.capex_v13) / 1000;
const c2d1 = X.a4_stab.find(s => s.case === "C2" && s.rule === "D1");

const kids = [];
const add = (...x) => kids.push(...x.flat());
add(new D.Paragraph({ spacing: { after: 60 }, children: [new D.TextRun({ text: "Mezan — Phase A5: Carbon and Financial Data Strengthening", bold: true, font: L.FONT, size: 34, color: L.NAVY })] }),
  P(`Methodology report · 26 October 2026 · model v${S.model_version} · **the facility is hypothetical: no input is a factory observation and no cost is a supplier quotation**`, { r: { color: L.GREY } }));
add(callout([
  `**What changed.** ${S.n_changed} of ${S.register.length} register inputs changed (yellow rows in the source register). The grid factor is now **derived from two primary Saudi documents** (0.55 → ${val(reg.ef_grid.value_v13)} tCO2e/MWh), the methane price uses the **2025 regulated price** ($3.00 → $${reg.gas_price_usd.value_v13}/MMBtu), rooftop PV cost uses a **Riyadh market benchmark** (SAR 3,750 → ${f0(reg.pv_capex_kw.value_v13)}/kWp), PV output now **degrades** 0.5%/yr, and compressed-air savings are **lower (25% → 20%) with an ongoing leak-programme cost**. Two formula gaps were corrected (no PV degradation; MAC on undiscounted tonnes for a declining output).`,
  `**Effect.** All four decision rules now choose **${a13.deterministic}** (solar + motors + compressed air). D1 NPV SAR ${fm(a12.det_npv)} → ${fm(a13.det_npv)}; E[NPV] ${fm(a12.best_expected_e_npv)} → ${fm(a13.best_expected_e_npv)}; Scope 1+2 reduction ${f0(a12["t12[A+B]"])} → ${f0(a13["t12[A+B+C]"])} t/yr; P(target) ${p4(a13.cc_p_target)}; P(capex ≤ SAR 5M) ${pc(a13.cc_p_budget)}. The primary rule D4, **infeasible in v1.2**, is now feasible at SAR 5M.`,
  `**Why — stated plainly.** The recommendation change comes from **one input: the PV cost benchmark**. Applied alone it moves every rule to A+B+C; every other A5 change alone leaves D1 at A+B. With the v1.2 PV cost (scenario P1) D1 is A+B and D4 is still infeasible (minimum budget SAR ${fm(sc("pv_capex_kw", "P1").D4_min_budget)}). The benchmark is a single consultancy figure, not a quotation (gap A5-04).`,
  `**Fragile parts.** Project C is marginal (NPV SAR ${f0(prj.C.npv_v13)}; its savings switch point is at the base value). At discount rates of 8–12% the deterministic choice is A+B. The 2027 tariff schedule, 2026 gas price and all non-PV costs remain unconfirmed. Still open from earlier phases: **a run on real Google Colab (A1-01)** and **any validation on real industrial data (A4-01)**.`]));

add(H1("1. Scope, evidence rules and what was not changed"));
add(P("A5 audits every input that feeds the carbon inventory and the investment economics, replaces values only where a defensible public source exists, and keeps all other values as labelled assumptions with scenarios or ranges. Methods (accounting, optimisation, Monte Carlo, chance constraints, value of information, real options, A4 missing-data engine) are unchanged apart from the two formula corrections in §6."));
add(table(["Evidence class", "Meaning", "Inputs"], [
  ["measured", "Observed at the facility", `${S.evidence_counts.measured || 0} — the facility is synthetic`],
  ["external", "Taken from a cited external source (government, utility, standard, study, benchmark)", String(S.evidence_counts.external || 0)],
  ["derived", "Computed from external values with a stated method", String(S.evidence_counts.derived || 0)],
  ["hypothetical", "Illustrative assumption for the synthetic case — not company data, not a quotation", String(S.evidence_counts.hypothetical || 0)],
  ["estimated", "Filled at run time by the A4 missing-data engine, with uncertainty; never stored in the register", "0 (run-time only)"],
], [1600, 6000, 2306], { size: 15 }));
add(Cap(`Quality status (separate from evidence class): ${Object.entries(S.status_counts).map(([k, v]) => `${k} ${v}`).join(", ")}. "Transferred" means a cited value from another country, sector or scale whose applicability is an assumption.`));
add(P("**Source priority applied:** (1) Saudi government and regulator publications (UNFCCC submissions of the Kingdom, GASTAT, SPA, ECRA via reported statements); (2) Saudi Aramco/SEC prices as reported by reputable Saudi financial sources (Al Jazira Capital, Argaam, MEES); (3) Saudi-market benchmarks (Knight Frank Riyadh survey; Riyadh PV simulation study); (4) international standards and peer-reviewed or industry studies (IPCC, GHG Protocol, worldsteel, DESNZ, Fraunhofer/CEMEP, US DOE, Compressed Air Challenge). Every source carries its publication date, effective period, geography and URL in the register."));

add(H1("2. Input audit — what changed and why"));
add(table(["Input", "v1.2", "v1.3", "Evidence", "Source (published)", "Applicability / decision"],
  ["ef_grid", "gas_price_usd", "pv_capex_kw", "pv_yield", "pv_degradation", "c_saving_frac", "c_om", "tree_g_reform", "e_kwh_per_l"].map(k => {
    const r = reg[k]; return [`${k} (${r.unit})`, val(r.value_v12), val(r.value_v13), `${r.evidence_class} / ${r.quality_status}`, r.published || "—",
      (r.change ? r.change + ". " : "") + (r.geography || "")]; }),
  [1500, 700, 700, 1300, 1500, 4206], { size: 12 }));
add(Cap("Full register (61 inputs with sources, notes, uncertainty and URLs): Mezan_A5_Source_Register.xlsx, sheet Register; also the Source Register sheet of Mezan_Data_Model.xlsx."));
add(TT("Inputs audited and kept"));
add(table(["Input", "Value", "Evidence", "Audit finding"], [
  ["Industrial tariff", `${reg.tariff.value_v13} SAR/kWh`, "external / provisional", "Last officially documented flat industrial rate (2018–2026). SPA (25 Oct 2026) confirms an adjustment from 1 Jan 2027, but the rates are in an attachment not retrieved; 23 halalas is from secondary sources. Kept as reference; scenarios T0–T3."],
  ["Diesel price", `${reg.diesel_price.value_v13} SAR/L`, "external / verified", "Aramco price from 1 Jan 2026 confirmed (MEES, 2 Jan 2026)."],
  ["Natural gas factor", `${val(reg.ef_gas.value_v13)} t/GJ`, "external / transferred", "IPCC 2006 defaults with AR5 GWPs, as in the Kingdom's BTR1 inventory; AR6 GWPs would change it by +0.005% (negligible)."],
  ["Diesel factor", `${val(reg.ef_diesel.value_v13)} t/L`, "external / transferred", "Cross-checked against IPCC 2006 (+0.6%)."],
  ["Steel factors", `${reg.ef_steel_incumbent.value_v13} / ${reg.ef_steel_alt.value_v13} t/t`, "external / transferred", "worldsteel 2025 (2024 data). Crude-steel boundary, i.e. lower than a cradle-to-gate product factor (A5-07)."],
  ["Freight factor", `${val(reg.ef_freight.value_v13 * 1000)} kg/t-km`, "external / transferred", "DESNZ 2025 UK HGV; no Saudi freight factor found (A1-20, A5-08)."],
  ["Motor savings (B)", `${reg.b_saving_frac.value_v13}`, "external / transferred", "Consistent with Fraunhofer/CEMEP Dec 2023 (fans 29%, pumps 15%); plant audit needed."],
  ["Heat-recovery savings (D)", `${reg.d_saving_frac.value_v13}`, "external / transferred", "US DOE tip sheet (2007): 13–20% gas saving with combustion-air preheat."],
  ["Discount rate", `${pc(reg.discount_rate.value_v13, 0)} real`, "external / transferred", "KAPSARC DP49 WACC in a Saudi energy-investment context; a private manufacturer's hurdle rate is likely higher (A5-12)."],
  ["Lifetimes", "PV 25; B, D 15; C, E, F 10 yr", "PV external; others hypothetical", "PV life from KAPSARC DP49; others engineering assumptions."],
  ["Capex B, C, D, E; F premium", "SAR 1.2M, 0.35M, 0.6M, 0.9M; 80/t", "hypothetical", "No supplier quotation; no public benchmark of adequate quality (§5). ±15% capex uncertainty and the budget chance constraint carry the risk."],
  ["Activity data", "12,000 MWh; 35,000 GJ; 80,000 L; 6,000 t", "hypothetical", "Synthetic facility. Missing months handled by the A4 engine (estimated, never zero by default)."],
], [1700, 1700, 1500, 5006], { size: 12 }));

add(H1("3. Grid emission factor: derivation from Saudi primary sources", true));
add(P(`The v1.2 factor (0.55 tCO2e/MWh) had no located source (A1-07). A5 derives the national location-based factor from the Kingdom's own UNFCCC inventory and the national statistics office:`));
add(EQ("EF_{grid} = E_{1.A.1.a.i, 2021} / G_{2021} = 205,579 Gg CO_{2}e / 358,640 GWh = 0.573 tCO_{2}e/MWh generated"));
add(B("**Numerator:** KSA First Biennial Transparency Report (UNFCCC, March 2025), Table 6, IPCC category 1.A.1.a.i electricity generation, 2021, AR5 GWPs."));
add(B("**Denominator:** GASTAT Electric Energy Statistics 2021 (359 TWh generated; 358,640 GWh as reported by Argaam, 26 Dec 2022)."));
add(B("**Corroboration:** the Saudi Designated National Authority 2021 grid factor 0.568 (as cited by KFUPM's 2024 inventory) differs by 0.9%."));
add(B("**Boundary:** a generation-based factor is the GHG Protocol location-based factor. Dividing the same emissions by consumption (301,600 GWh) gives 0.682, which includes T&D losses and power-plant own use; those belong in Scope 3 Category 3, so using 0.682 for Scope 2 would mix boundaries."));
add(table(["Evidence", "Value", "Use"], R.ef_evidence.map(e => [e.what, String(e.value), e.use]), [5800, 900, 3206], { size: 12 }));
add(P(`**Limits (A5-13).** 2021 is the latest official inventory year; the 2024 generation mix includes more renewables and would likely give a lower factor. Category 1.A.1.a.i may include some co-generation for desalination. An SEC-specific factor was not publicly retrievable. Uncertainty: normal, 5% (1 sd). Effect: target 1,316.7 → ${f1(inv["Target (15% of Scope 1+2), t"].v13)} t; Scope 2 6,600 → ${f0(inv["Scope 2"].v13)} t. Alone, it moved D3 from A+C+D to A+B (A+B's target probability rose from 0.903 to ${p4(only("ef_grid")["p_target[A+B]"])}).`));

add(H1("4. Energy prices"));
add(TT("Electricity tariff"));
add(table(["Scenario", "SAR/kWh", "Evidence", "D1", "D1 NPV", "D4"], S.scenario_results.filter(s => s.input === "tariff").map(s => {
  const e = R.tariff_evidence.find(t => t.id === s.id); return [`${s.id} ${s.label}`, String(s.value), e.status, s.D1, f0(s.D1_npv), s.D4]; }),
  [3300, 800, 2400, 900, 1300, 1206], { size: 12 }));
add(Cap("Each scenario fixes the tariff and reruns the full deterministic and Monte Carlo analysis (20,000 scenarios). A+B+C in all four."));
add(P(`The Monte Carlo tariff distribution is triangular (0.18, 0.18, 0.26), upward-skewed for possible reform (A1-24). With the tariff fixed at 0.18 (T0), the expected NPV of A+B+C is SAR ${fm(sc("tariff", "T0").D2_e_npv)} instead of ${fm(a13.best_expected_e_npv)}: lower, but still positive. Energy-intensive industrial categories have separate tariffs (Cabinet decision reported in 2021: 12/18/18/24 halalas by category); the case plant is assumed not to qualify.`));
add(TT("Natural gas and diesel"));
add(P(`**Methane:** Aramco's regulated price for industrial users rose from $1.75 to **$2.15/MMBtu on 1 Jan 2025** (Al Jazira Capital, Jan 2025, summarising Aramco notices). A further 10–20% rise in 2026 was reported by a secondary source only. v1.2's $3.00 was a modelling anchor from KAPSARC DP49, not a price. Scenarios G0 $2.15, G1 $2.47, G2 $3.00 all give A+B+C: gas only affects project D, which is negative in all three. Whether a Riyadh fabrication plant can obtain piped sales gas at this price (rather than LPG or diesel) is unverified (A5-02). **Diesel:** SAR 1.79/L from 1 Jan 2026 (MEES), unchanged in the register.`));
add(P(`**Heat-recovery timing** uses the current gas price: the reform scenario becomes +50% on $2.15 = $${tt.g_reform_usd}. Investing now in D has NPV SAR ${f0(tt.npv_invest_now)}; the decision is to wait for the price decision (static break-even gas price $${Number(tt.static_breakeven_usd).toFixed(2)}/MMBtu).`));

add(H1("5. Investment costs, savings and public benchmarks", true));
add(P(`**Rooftop PV cost.** Knight Frank's 2025 GCC rooftop-solar report gives a typical fixed-mount rooftop installation cost of **SAR 2.5/W** from Riyadh-based providers. This replaces v1.2's SAR 3.75/W, which was an assumed 1.45× mark-up on IRENA's utility-scale cost with no direct source. Because it is a single market survey figure and not a quotation for this roof, the 1-sd uncertainty was widened from 10% to 15% and the old value is kept as scenario P1.`));
add(P(`**Why PV cost decides the portfolio.** At SAR 3,750/kWp, A+B costs SAR 4.95M, so adding C (SAR 0.35M) breaks the SAR 5M budget, and the expected capex overrun makes D4 infeasible. A+B+C fits within the quoted budget for PV costs up to SAR ${f0(pvSwitch)}/kWp. The switch-point scan over the ±35% Monte Carlo range (SAR ${f0(sw.pv_capex_kw.range[0])}–${f0(sw.pv_capex_kw.range[1])}) found no change of the risk-based choice.`));
add(P(`**PV yield and degradation.** Yield 1,850 kWh/kWp/yr (range 1,650–2,010; Alzahrani & Nahhas 2021 simulated 2,008 for a Riyadh utility plant; rooftop −8% is an assumption). Degradation 0.5%/yr (median of ~2,000 field rates, Jordan & Kurtz 2013; range 0.3–1.0%; hot-desert sites tend to be higher). v1.2 assumed constant output for 25 years.`));
add(P(`**Compressed air.** Leaks are ~20–30% of capacity in poorly maintained systems and below 10% in well-maintained ones (Compressed Air Challenge fact sheet 7, 2026): repair recovers ~10–15 points, pressure and controls ~5 → **20%** (v1.2 used the full 25% leak share, which assumes leaks can be eliminated). Savings persist only with a leak programme, now costed at a hypothetical SAR 15,000/yr.`));
add(TT("Public cost benchmarks searched (never supplier quotations)"));
add(table(["Parameter", "Model value", "Public evidence found", "Use"], S.bench.map(b => [b.parameter, b.model_value || b["model value"], b["public evidence found"], b.use]),
  [1300, 1500, 3800, 3306], { size: 12 }));

add(H1("6. Financial formula review"));
add(EQ("NPV = −I_{0} + Σ_{t=1..n} CF_{t}/(1+r)^{t};   AF(r,n) = (1 − (1+r)^{−n})/r"));
add(EQ("PV with degradation d:   AF_{d} = Σ (1−d)^{t−1}/(1+r)^{t} = (1 − ((1−d)/(1+r))^{n})/(r + d)"));
add(EQ("NPV_{A} = −I_{A} + (energy savings)·AF_{d} − O&M·AF;   MAC = −NPV / (AF_{t} × year-1 tonnes)"));
add(EQ("B and C together: B's compressor-motor saving acts on the load left after C → overlap = E_{comp}·b_{comp}·c, removed once"));
add(P(`Every formula was recomputed independently with explicit year-by-year cash flows (tools/build_a5_register.py): **${S.fin_checks.filter(c => c.pass).length} of ${S.fin_checks.length} checks agree to machine precision**.`));
add(table(["Check", "Independent", "Model", "Pass"], S.fin_checks.map(c => [c.check, Math.abs(c.model) > 100 ? f0(c.independent) : Number(c.independent).toFixed(4), Math.abs(c.model) > 100 ? f0(c.model) : Number(c.model).toFixed(4), c.pass ? "yes" : "NO"]),
  [5600, 1500, 1500, 1306], { size: 12 }));
add(table(["Item", "Finding"], S.fin_notes.map(n => [n.item, n.finding]), [2000, 7906], { size: 12 }));

add(H1("7. GHG Protocol boundary review", true));
add(P("Operational-control approach; reporting year = year 1 of the projects. Reviewed against the GHG Protocol Corporate Standard, Scope 2 Guidance (2015) and Scope 3 Standard (2011)."));
add(table(["Scope", "Source", "Treatment", "Comment"], S.boundary.map(b => [b.scope, b["source category"], b.treatment, b["basis / comment"]]), [1100, 2500, 1700, 4606], { size: 12 }));
add(Cap(`Two boundary gaps remain and are not added to totals: Scope 1 refrigerants (A5-05) and Scope 3 Category 3 (A5-06; T&D/own-use part indicatively ${f0(S.t_and_d_proxy)} t, an upper bound).`));

add(H1("8. Before-and-after results"));
add(P("Same code, seed (20261024) and 20,000 scenarios; only register inputs differ. New random inputs use a separate stream, so the v1.2 draws are unchanged and the v1.2 profile reproduces every v1.2 result exactly."));
add(table(["Rule", "v1.2 choice", "v1.3 choice", "Metric", "v1.2", "v1.3"], S.decisions.map(d => [d.rule, d.v12, d.v13, d.metric,
  d.value_v12 > 10 ? f0(d.value_v12) : p4(d.value_v12), d.value_v13 > 10 ? f0(d.value_v13) : p4(d.value_v13)]), [2600, 1100, 1000, 2700, 1200, 1306], { size: 12 }));
add(table(["Inventory (t CO2e/yr)", "v1.2", "v1.3", "Change"], S.inventory.map(i => [i.item, f1(i.v12), f1(i.v13), f1(i.change)]), [4000, 1900, 1900, 2106], { size: 12 }));
add(table(["Project", "Capex v1.2", "Capex v1.3", "NPV v1.2", "NPV v1.3", "t/yr v1.2", "t/yr v1.3", "MAC v1.2", "MAC v1.3"],
  S.projects.map(p => [`${p.project} ${p.name}`, f0(p.capex_v12), f0(p.capex_v13), f0(p.npv_v12), f0(p.npv_v13), f1(p.t_v12), f1(p.t_v13), f0(p.mac_v12), f0(p.mac_v13)]),
  [2500, 900, 900, 1000, 1000, 800, 800, 900, 1106], { size: 11 }));
add(Cap("NPV and MAC in SAR (MAC per tCO2e; negative = saves money). F reduces Scope 3 only."));
add(table(["Portfolio", "Capex", "NPV (base)", "E[NPV]", "Reduction t/yr", "P(target)", "P(capex ≤ 5M)"],
  S.portfolios.map(p => [p.portfolio, `${fm(p.capex_v12)} → ${fm(p.capex_v13)}`, `${fm(p.npv_v12)} → ${fm(p.npv_v13)}`, `${fm(p.e_npv_v12)} → ${fm(p.e_npv_v13)}`,
    `${f0(p.t12_v12)} → ${f0(p.t12_v13)}`, `${p4(p.p_target_v12)} → ${p4(p.p_target_v13)}`, `${pc(p.p_budget_v12)} → ${pc(p.p_budget_v13)}`]),
  [1100, 1500, 1500, 1500, 1300, 1600, 1406], { size: 12 }));
add(fig(CH, "a5_1_npv.png", "Figure 1 — Left: project NPV before and after. Right: D1 NPV and choice with each A5 change applied alone to the v1.2 register.", 600));
add(fig(CH, "a5_2_probabilities.png", "Figure 2 — Probability of meeting the target and of staying within the SAR 5M budget, before and after (dashed: 90% requirement).", 600));
add(TT("Attribution: each change alone (others at v1.2)"));
add(table(["Change applied alone", "Target t", "D1", "D1 NPV", "D2", "D3", "D4", "Min. budget D4"], att.map(a => [a.case === "v1.2 register" ? "v1.2 register" : a.case.startsWith("v1.3") ? "v1.3 register (all)" : a.change,
  f1(a.target_t), a.deterministic, f0(a.det_npv), a.best_expected, a.chance_constrained, a.joint, f0(a.joint_min_budget)]), [3300, 800, 800, 1000, 800, 900, 1100, 1206], { size: 11 }));
add(Cap("Effects are not additive. Only the PV cost changes the recommendation on its own. The grid factor alone moves D3 to A+B; degradation alone cuts D1 NPV to SAR " + f0(only("pv_degradation").det_npv) + "; the compressed-air revision alone lowers A+C+D's target probability to " + p4(only("c_saving_frac").cc_p_target) + "."));
add(TT("Scenario and discount-rate robustness (v1.3)"));
add(table(["Input", "Scenario", "D1", "D1 NPV", "D2", "D3", "D4", "Min. budget D4"], S.scenario_results.filter(s => s.input !== "tariff").map(s => [s.input, `${s.id} ${s.label}`, s.D1, f0(s.D1_npv), s.D2, s.D3, s.D4, f0(s.D4_min_budget)]),
  [1300, 3200, 800, 1000, 800, 800, 900, 1106], { size: 11 }));
add(table(["Real discount rate", ...R.discount_robustness.map(d => pc(d.rate, 0))], [
  ["D1 choice", ...R.discount_robustness.map(d => d.with_target)], ["D1 NPV (SAR)", ...R.discount_robustness.map(d => f0(d.npv_with_target))]],
  [2400, 1250, 1250, 1250, 1250, 1250, 1256], { size: 12 }));
add(P(`**Switch points (v1.3).** C's savings fraction switches A+B+C ↔ A+B at ${val(sw.c_saving_frac.changes[0][0])} (the base value) and C's capex at SAR ${f0(sw.c_capex.changes[0][0])} (base 350,000): C is a knife-edge (A5-10). B's savings switch at ${sw.b_saving_frac.changes[0][0]}; gas price at $${Number(sw.gas_price_usd.changes[0][0]).toFixed(2)} adds D. Tariff, PV yield, PV cost (±35%), B capex, grid factor and D savings do not change the choice within their ranges. Value of information: EVPI SAR ${f0(R.evpi)}; compressed-air sub-metering EVPPI SAR ${f0(voiC.evppi_sar)} against a hypothetical SAR ${f0(voiC.collection_cost_sar)} cost; motor audit EVSI ${f0(R.evsi_audit.evsi)}. First-order variance analysis of NPV(${R.sobol_decision_pair[0]}) − NPV(${R.sobol_decision_pair[1]}): C's savings fraction explains ${pc(R.sobol_decision.c_saving_frac, 0)}, C's capex ${pc(R.sobol_decision.c_capex, 0)}, the tariff ${pc(R.sobol_decision.tariff, 0)} — measuring compressed-air savings is the information that matters.`));

add(H1("9. Missing-data module (A4) under v1.3 inputs", true));
add(P(`The full A4 study was rerun with the v1.3 register. Complete synthetic data reproduce the v1.3 pipeline exactly (${X.a4_res === true ? "check passed" : "check: " + X.a4_res}). With the demo's approved estimates, D2, D3 and D4 are stable (A+B+C); **D1 is now data-unstable**: ${c2d1 ? c2d1.reasons : "—"} (agreement ${c2d1 ? pc(c2d1.agreement, 0) : "—"}), because C is marginal. The value of every missing record is now zero — no decision depends on them — whereas under v1.2 the electricity bills mattered for the D3 knife-edge. A4 calibration and change-detection results do not depend on the register and are unchanged.`));
add(table(["Case", "Rule", "Choice", "Status", "Agreement"], X.a4_stab.map(s => [s.case, s.rule, s.choice, s.status, pc(s.agreement, 0)]), [1500, 1500, 2000, 3000, 1906], { size: 12 }));

add(H1("10. Validation and regression"));
add(table(["Check", "Result"], X.checks, [4300, 5606], { size: 12 }));

add(H1("11. Remaining evidence gaps and issue log"));
add(table(["ID", "Priority", "Gap", "How handled now"], S.gaps.filter(g => g.id.startsWith("A5")).map(g => [g.id, g.priority, g.gap, g["how handled now"]]), [700, 800, 5000, 3406], { size: 12 }));
add(TT("Carried forward (still open)"));
add(table(["ID", "Priority", "Issue", "Status after A5"], [
  ["A1-01", "Critical", "Run on real Google Colab", "Still open: verified only in a simulated Colab environment"],
  ["A4-01", "High", "No real industrial validation", "Still open: all facility data and A4 validation are synthetic"],
  ["A1-24", "High", "E[NPV] relies on the upward-skewed tariff range", "Open; still positive with the tariff fixed at 0.18"],
  ["A1-26 / A1-16", "High / Medium", "VOI estimator noise; EVPPI binning error", "Open (A6)"],
  ["A4-02…A4-13", "Medium", "Calibration and change detection fitted on synthetic data only", "Open (requires real data)"],
  ["A1-19, A1-20, A1-23", "Low", "PV self-consumption (hourly); UK proxies; minimum-version float differences", "Open (documented)"],
  ["A1-27", "High", "D4 infeasible at SAR 5M", "Feasible under v1.3 — but only because of the PV cost benchmark (A5-04)"],
], [1300, 1100, 3800, 3706], { size: 12 }));
add(P("Full log with verification: ISSUE_LOG.md (A1–A5)."));

add(H1("12. Sources (accessed 25–26 October 2026)"));
[
  ["Kingdom of Saudi Arabia, First Biennial Transparency Report, UNFCCC, March 2025 (Table 6, 2021 inventory)", "https://unfccc.int/sites/default/files/resource/KSA_BTR1_20250320-2.pdf"],
  ["GASTAT, Electric Energy Statistics 2021 (Arabic), 2022", "https://www.stats.gov.sa/sites/default/files/Electric_Energy_Statistics_2021_Ar.pdf"],
  ["Argaam, GASTAT: Saudi electricity generation 2021, 26 Dec 2022", "https://www.argaam.com/en/article/articledetail/id/1611319"],
  ["Saudi Press Agency, electricity tariff adjustment from 1 Jan 2027, 25 Oct 2026", "https://www.spa.gov.sa/en/N2709801"],
  ["Argaam (ECRA statement), industrial tariff 18 halalas, 13 Dec 2017", "https://www.argaam.com/en/article/articledetail/id/519195"],
  ["Al Jazira Capital, Energy price reforms, January 2025", "https://www.aljaziracapital.com.sa/media/jn3bxjbu/energy-price-reforms-jan-25-en.pdf"],
  ["MEES, Saudi increases diesel prices, 2 Jan 2026", "https://www.mees.com/2026/1/2/news-in-brief/saudi-increases-diesel-prices/f2cdf290-e7df-11f0-aea8-4d31a1325bf5"],
  ["Knight Frank, Going Green: Rooftop solar potential in the GCC, 2025", "https://www.knightfrank.ae/site-assets/pdf/going-green-rooftop-solar-potential-in-the-gcc-2025.pdf"],
  ["Alzahrani & Nahhas, American Journal of Energy Research 9(1), 2021 (Riyadh PV simulation)", "https://pubs.sciepub.com/ajer/9/1/5/index.html"],
  ["Jordan & Kurtz, Photovoltaic degradation rates — an analytical review, Prog. Photovolt. 21, 2013", "https://doi.org/10.1002/pip.1182"],
  ["Fraunhofer ICT / CEMEP, Motor saving potential with VSD, 15 Dec 2023", "https://www.zvei.org/fileadmin/user_upload/Verband/Fachverbaende/Automation/Elektrische_Antriebe/Cemep_Studie/Cemep_Fraunhofer_study-motor-saving-potential-with-VSD-20231215.pdf"],
  ["Compressed Air Challenge, Fact sheet 7: Compressed air system leaks, updated 2026", "https://www.compressedairchallenge.org/data/sites/1/media/library/factsheets2026/fact-sheet-7-compressed-air-system-leaks_updated2026.pdf"],
  ["US DOE, Process Heating Tip Sheet #1: Preheated combustion air, Nov 2007", "https://www1.eere.energy.gov/manufacturing/tech_assistance/pdfs/et_preheated.pdf"],
  ["KAPSARC Discussion Paper DP49, 2026 (discount rate, PV life, gas-price process)", "https://doi.org/10.30573/KS--2026-DP49"],
  ["worldsteel, Sustainability Indicators 2025", "https://worldsteel.org/wider-sustainability/sustainability-indicators/sustainability-indicators-report-2025/"],
  ["UK DESNZ, GHG conversion factors 2025, June 2025", "https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2025"],
  ["IPCC 2006 Guidelines, Vol. 2 Ch. 2 Stationary Combustion", "https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_2_Ch2_Stationary_Combustion.pdf"],
  ["GHG Protocol, Global Warming Potential values, August 2024", "https://ghgprotocol.org/sites/default/files/2024-08/Global-Warming-Potential-Values%20%28August%202024%29.pdf"],
  ["Saudi DNA, Grid emission factor 2021 (as cited by KFUPM GHG inventory 2024)", "https://sustainability.kfupm.edu.sa/documents/78/KFUPM_Greenhouse_Gas_Emissions_Inventory_for_2024_v2.pdf"],
  ["Clemson University IAC, example recommendation: adjustable frequency drives (undated; order-of-magnitude check only)", "https://cecas.clemson.edu/iac/wp-content/uploads/2020/07/Use-Adjustable-Frequency-Drive-or-Multiple-Speed-Motors-on-Existing-System.pdf"],
].forEach(([t, u]) => add(B(`${t}. [${u}](${u})`)));

add(H1("13. Reproduce"));
add(P("pip install -r requirements.txt → python run_all.py (outputs, workbook, a5_attribution.csv, gas/PV/grid/tariff scenarios) → python tools/build_a5_register.py (source register and before/after workbooks) → python tools/run_tests.py → python tools/fault_injection.py → python tools/crosscheck.py. The v1.2 results are reproduced in Python with `with assumptions.use_profile(\"v1.2\"): ...`."));

const doc = new D.Document({
  styles: { default: { document: { run: { font: L.FONT, size: L.SZ } } } },
  numbering: { config: [
    { reference: "bul", levels: [{ level: 0, format: D.LevelFormat.BULLET, text: "•", alignment: D.AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 240 } } } }] },
    { reference: "num", levels: [{ level: 0, format: D.LevelFormat.DECIMAL, text: "%1.", alignment: D.AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 300 } } } }] }] },
  sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1000, bottom: 1000, left: 1000, right: 1000 } } },
    footers: { default: new D.Footer({ children: [new D.Paragraph({ alignment: D.AlignmentType.RIGHT, children: [new D.TextRun({ text: "Mezan · Phase A5 · hypothetical facility · page ", size: 16, color: L.GREY }), new D.TextRun({ children: [D.PageNumber.CURRENT], size: 16, color: L.GREY })] })] }) },
    children: kids }] });
D.Packer.toBuffer(doc).then(b => { fs.writeFileSync(OUT, b); console.log("saved", OUT); });
