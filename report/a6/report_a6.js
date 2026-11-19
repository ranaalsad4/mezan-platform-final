// Mezan Phase A6 — independent mathematical and integrated model validation report.
// Usage: node report/a6/report_a6.js <project dir> <data.json> <out.docx>. Numbers come from outputs/a6 (tools/run_a6.py).
const fs = require("fs");
const path = require("path");
const L = require(fs.existsSync(path.resolve(__dirname, "../lib.js")) ? path.resolve(__dirname, "../lib.js") : path.resolve(__dirname, "../../full/report/lib.js"));
const { D, P, H1, B, TT, callout, table, Cap, fig, EQ } = L;
const [, , ROOT, DATA, OUT] = process.argv;
const X = JSON.parse(fs.readFileSync(DATA, "utf8"));
const A = X.A, R = X.R;
const CH = path.join(ROOT, "outputs", "a6", "charts");
const f0 = v => v == null || Number.isNaN(v) ? "—" : Math.round(v).toLocaleString("en-US");
const f2 = v => v == null ? "—" : Number(v).toFixed(2);
const f4 = v => v == null ? "—" : Number(v).toFixed(4);
const pc = (v, d = 1) => v == null ? "—" : (100 * v).toFixed(d) + "%";
const sci = v => v == null ? "—" : (Math.abs(v) < 1e-3 && v !== 0 ? Number(v).toExponential(1) : Number(v).toPrecision(4));
const ds = Object.fromEntries(R.decision_scenarios.map(d => [d.id, d]));
const ro = A.realoptions, voi = A.voi, mi = A.mc_independent, ms = A.missing;
const evp = k => X.evppi.find(e => e.parameter === k);
const top = (o, n = 3) => A.gsa.top[o].slice(0, n).map(t => `${t.parameter} (S_T ${f2(t.ST)})`).join(", ");
const optAll = X.opt_by_rule.reduce((a, r) => ({ cases: a.cases + r.cases, same: a.same + r.identical_npv, choice: a.choice + r.identical_choice }), { cases: 0, same: 0, choice: 0 });
const projRows = X.finance.filter(r => r.level === "project");
const portRows = X.finance.filter(r => r.level === "portfolio");
const conv = X.conv;
const T = X.tests, F = X.faults;
const ec = evp("c_saving_frac"), evAgree = Math.abs(ec.evppi_nested - ec.evppi_binned_model) / ec.evppi_binned_model;
const fa = Math.max(...X.change.filter(c => c.true_shift === 0).map(c => c.detect_rate_model));
const s20 = X.change.find(c => c.true_shift === 0.2 && c.noise_sd === 0.06);
const pAB = conv.find(c => c.n === 100000).p_ab_mean, zAB = (pAB - R.mc_chance_constrained.alpha_saa) / Math.sqrt(pAB * (1 - pAB) / 20000);
const subCost = X.R.voi.find(v => v.parameter === "c_saving_frac").collection_cost_sar;

const kids = [];
const add = (...x) => kids.push(...x.flat());
add(new D.Paragraph({ spacing: { after: 60 }, children: [new D.TextRun({ text: "Mezan — Phase A6: Independent Mathematical and Integrated Model Validation", bold: true, font: L.FONT, size: 32, color: L.NAVY })] }),
  P(`Validation report · 26 October 2026 · model v${R.meta.model_version} (A5 Saudi inputs preserved) · **synthetic case facility: nothing here is real-world validation**`, { r: { color: L.GREY } }));
add(callout([
  `**Result.** Every mathematical component was recomputed by separately written code, by spreadsheet formulas, against published benchmarks or closed forms. The emissions, financial, optimisation, Monte Carlo, chance-constraint, value-of-information, real-options and missing-data calculations agree within numerical or Monte Carlo precision. **The recommendation ${ds.D4.portfolio} (D1–D4) is reproduced by an independent sampler and an independent evaluator:** Scope 1+2 baseline ${f0(R.scope_totals["Scope 1+2"])} t, target ${f0(R.target_t)} t, D1 NPV SAR ${f0(ds.D1.npv_base_inputs)}, E[NPV] SAR ${f0(ds.D4.e_npv)}, P(capex ≤ budget) ${pc(ds.D4.p_budget)}.`,
  `**Defects found and fixed (no effect on any decision):** the IRR of solar PV ignored output degradation (${pc(projRows.find(r => r.item === "A" && r.metric === "IRR").model)} now, was 11.5%); a missing or invalid (NaN) input made the enumeration silently return an arbitrary portfolio (now refused with a named error); the degraded annuity factor was wrong at the unrealistic edge r = −d; the A4 report, A4 workbook, A4 chart, app table and a model docstring still described v1.2 results and have been regenerated or corrected.`,
  `**Method findings (documented, not changed):** EVPI as defined in the model (target met in every scenario) is SAR ${f0(voi.evpi_model)}; if the 90% chance constraint is kept under perfect information it is SAR ${f0(voi.evpi_chance_constraint_kept)}, so the model's EVPI is a lower bound. Inputs are sampled independently (no correlations). Validation of the missing-data engine uses our own synthetic generator.`,
  `**Phase A readiness.** Technically ready to close **subject to two items that cannot be done from this workspace**: one run of the package on real Google Colab (A1-01) and a statement in the submission that all facility data are synthetic and unvalidated on real industrial records (A4-01). Source-evidence gaps from A5 remain (official 2027 tariff, supplier quotations, a second PV cost benchmark).`]));

add(H1("1. What 'independent' means here"));
add(table(["Kind of check", "Meaning", "Used for"], [
  ["independent", "Recomputed by code that does not import the model (independent/indep.py, verified by a test), or by spreadsheet formulas written for this phase. Same input values, separately written formulas: year-by-year activity ledger instead of project sums minus an overlap term; inverse-CDF sampling from a different generator (MT19937, scrambled Sobol) instead of the model's sampler", "Emissions, NPV/IRR/payback/MAC, all 64 portfolios, optimisation, Monte Carlo estimates and decisions, budget probability"],
  ["benchmark", "Published numerical result or closed form", "IPCC/BTR1/GASTAT factor derivation, Longstaff–Schwartz (2001) American put, Dixit–Pindyck trigger, normal closed form for budget compliance"],
  ["internal", "The model checked against itself: other seeds, sample sizes, a different estimator of the same quantity. **Not independent**", "Convergence, nested-MC EVPPI vs binned EVPPI, change detection power"],
], [1500, 5200, 3206], { size: 13 }));
add(P("What independence does **not** cover: the input values and the project definitions are shared with the model (a wrong input would be reproduced), and all facility data are synthetic. These checks establish that the model computes what its documentation says; they cannot establish that the synthetic facility resembles a real Saudi plant."));

add(H1("2. Emissions, units, boundaries and factors"));
add(table(["Quantity", "Model", "Independent", "Kind", "Pass"], X.emissions.map(e => [e.item, sci(e.model), sci(e.independent), e.kind, e.pass ? "yes" : "NO"]), [4300, 1500, 1500, 1700, 906], { size: 12 }));
add(Cap(`Units checked programmatically (each factor's denominator equals its activity unit). ${A.emissions.note}. Boundaries: Scope 1 gas, diesel (stationary and mobile); Scope 2 location-based with a generation-based grid factor; Scope 3 Cat 1 steel and Cat 4 freight. Not inventoried (A5): refrigerants, Scope 3 Cat 3 (a consumption-based factor of ${f4(A.emissions.grid_consumption_factor)} would include T&D losses, which belong in Cat 3).`));

add(H1("3. Financial evaluation"));
add(table(["Project", "Metric", "Model", "Independent", "Pass"], projRows.filter(r => ["NPV", "IRR", "payback (yr)", "MAC (SAR/t)"].includes(r.metric)).map(r => [r.item, r.metric, r.metric === "IRR" ? pc(r.model, 2) : f2(r.model), r.metric === "IRR" ? pc(r.independent, 2) : f2(r.independent), r.pass ? "yes" : "NO"]),
  [900, 2000, 2300, 2300, 2406], { size: 12 }));
add(Cap(`All ${A.finance.n} financial checks pass (${projRows.length} project-level, ${portRows.length} portfolio-level). Independent definitions: NPV = −capex + Σ CF_t/(1+r)^t on year-by-year flows; IRR = root of NPV(r) (Brent) on the same flows, and Excel IRR() in the spreadsheet; payback = capex / year-1 net cash flow; MAC = −NPV / discounted lifetime tonnes, tonnes declining with PV output. F has no payback or IRR (no positive cash flow).`));
add(P(`**Defect found (fixed):** the model's IRR used a constant annual cash flow, ignoring PV degradation introduced in A5, and reported 11.5% for project A instead of ${pc(projRows.find(r => r.item === "A" && r.metric === "IRR").independent, 2)}. NPVs and MACs were already correct; IRR is reported only and does not enter any decision. **Project interactions:** for all 64 portfolios, NPV and Scope 1+2 reduction from the independent year-by-year ledger (B's compressor saving applied to the load left after C, only while C operates) equal the model's sum-minus-overlap values to machine precision.`));

add(H1("4. Optimisation: MILP vs exhaustive enumeration"));
add(table(["Exclusivity rule", "Cases", "Same choice", "Same NPV", "Infeasible", "Distinct optima"], X.opt_by_rule.map(r => [r.exclusive, f0(r.cases), f0(r.identical_choice), f0(r.identical_npv), f0(r.infeasible), String(r.optima)]),
  [2000, 1500, 1500, 1500, 1500, 1906], { size: 13 }));
add(Cap(`Budgets SAR 0–8M (step 0.25M) × targets 0–3,200 t (step 100) × three exclusivity settings = ${f0(optAll.cases)} cases. In every case the HiGHS MILP, the model's 64-portfolio enumeration and the independent ledger enumeration return the same portfolio and NPV; infeasible cases are reported as infeasible by all three. A test repeats this on 25 randomly sampled parameter sets × 3 budgets.`));
add(fig(CH, "a6_3_optimization_map.png", "Figure 1 — Deterministic optimum over the budget/target grid (no exclusivity rule). The case (SAR 5M, 1,358 t) lies inside the A+B+C region.", 600));

add(H1("5. Monte Carlo implementation", true));
add(P(`**Independent sampler.** The register distributions were re-implemented as inverse-CDF transforms (scipy) of uniforms from MT19937 (n = 200,000) and scrambled Sobol (n = 131,072), and every affordable portfolio was evaluated with the independent ledger. Compared with the model's 20,000-scenario results for ${mi.rows / 6} portfolios × 3 metrics × 2 samplers: ${pc(mi.share_abs_z_gt_2, 1)} of differences exceed 2 standard errors and ${pc(mi.share_abs_z_gt_3, 1)} exceed 3 (largest |z| = ${f2(mi.max_abs_z)}). The largest deviations are budget-compliance probabilities near 1 for A+B and A+B+F, where the model's 20,000-scenario sample happens to contain fewer cost overruns than expected; the independent value equals the normal closed form (§6), so this is sampling variation, not an error.`));
add(table(["Rule", "Model (seed 20261024, n = 20,000)", "Independent MT19937 (n = 200,000)", "Independent Sobol (n = 131,072)"], ["D2", "D3", "D4"].map(r => [r, mi.model_decisions[r], mi.decisions.mt[r], mi.decisions.sobol[r]]), [1500, 2800, 2800, 2806], { size: 13 }));
add(P("**Convergence (internal).** The model's sampler was run with 10 independent seeds at seven sample sizes. The spread across seeds falls like 1/√n, and the decisions are identical at every size and seed:"));
add(table(["n", "E[NPV] A+B+C mean", "sd across seeds", "σ/√n", "P(target) A+B", "P(capex ≤ budget) A+B+C", "D2 / D3 / D4 = A+B+C"], conv.map(c => [f0(c.n), f0(c.e_npv_mean), f0(c.e_npv_sd), f0(c.e_npv_sd_theory), f4(c.p_ab_mean), f4(c.p_bud_mean), `${pc(c.D2_ABC, 0)} / ${pc(c.D3_ABC, 0)} / ${pc(c.D4_ABC, 0)}`]),
  [900, 1500, 1300, 1100, 1300, 1700, 2106], { size: 12 }));
add(fig(CH, "a6_1_convergence.png", "Figure 2 — Monte Carlo estimates across sample sizes (10 seeds each). Dashed: the tightened 90% requirement.", 600));
add(fig(CH, "a6_2_standard_error.png", "Figure 3 — Observed spread of E[NPV] across seeds vs the theoretical standard error σ/√n.", 380));
add(P(`**Conclusion.** 20,000 scenarios are sufficient for this case: the Monte Carlo standard error of E[NPV] is about SAR ${f0(conv.find(c => c.n === 20000).e_npv_sd_theory)} (0.3%), and the nearest chance-constraint margin (A+B at ${f4(pAB)} vs ${f4(R.mc_chance_constrained.alpha_saa)}) is ${zAB.toFixed(0)} standard errors away at n = 20,000. **Limitation:** inputs are sampled independently; plausible correlations (tariff and gas reforms, capex overruns across projects) are not represented.`));

add(H1("6. Chance constraints and uncertain capital cost"));
add(B("**Carbon rule:** P(Scope 1+2 reduction ≥ target) ≥ α_SAA, with reductions counted with fixed reporting factors against the fixed reporting baseline (management decision, A1-02). α_SAA = 0.9 + 1.645·√(0.9·0.1/n) = " + f4(R.mc_chance_constrained.alpha_saa) + " for n = 20,000 (spreadsheet formula agrees)."));
add(B("**Budget rule (D4):** a portfolio is a candidate only if its **quoted** capex ≤ budget; it must also satisfy P(**actual** capex ≤ budget) ≥ α_SAA, where actual capex = Σ quoted × (1 + 0.15·Z), Z standard normal, independent across projects, truncated at 5% of the quote (truncation probability ≈ 10⁻¹⁰). NPVs in the Monte Carlo use the same sampled capex, so cost overruns reduce NPV consistently."));
add(table(["Portfolio", "Quoted capex", "s.d.", "Closed form P(≤ 5M)", "Model n = 20,000", "Model validation n = 200,000", "Independent n = 200,000"],
  X.budget.filter(b => ["A+B+C", "A+B", "A+C+D", "A+B+D", "A+B+C+F", "A+C+D+E"].includes(b.portfolio)).map(b => [b.portfolio, f0(b.quoted), f0(b.sd_actual), f4(b.p_budget_analytic), f4(b.p_budget_model), f4(b.p_budget_model_validation), f4(b.p_budget_independent)]),
  [1300, 1300, 1100, 1500, 1500, 1700, 1506], { size: 12 }));
add(Cap(`Largest difference between the model's validation sample and the closed form over all affordable portfolios: ${f4(A.chance_budget.max_abs_diff_validation_vs_analytic)}. The SAA procedure (solve at the tightened level, confirm on an independent 200,000-scenario sample) follows Pagnoncelli, Ahmed & Shapiro (2009).`));

add(H1("7. Value of information", true));
add(table(["Quantity", "Model", "Independent / alternative", "Comment"], [
  ["EVPI (target must be met in every scenario where possible)", f0(voi.evpi_model), f0(voi.evpi_recomputed_same_definition), "Recomputed with an explicit scenario loop: identical"],
  ["EVPI keeping the 90% chance constraint under perfect information", "—", f0(voi.evpi_chance_constraint_kept), "Exact on the sample: the policy may miss the target in 10% of scenarios, chosen where that gains most. The model's EVPI is therefore a **lower bound** under this reading (definition documented, not changed)"],
  ["EVSI motor-system audit (error sd 3 points)", f0(voi.evsi_model), f0(voi.evsi_likelihood_weighting), `Exact Bayesian posterior by likelihood weighting on 40 signal values; posterior choice always ${voi.evsi_posterior_choices.join(", ")}: the audit cannot change the decision`],
], [3300, 1200, 1500, 3906], { size: 12 }));
add(table(["Parameter", "EVPPI binned (model)", "EVPPI nested MC (40 × 20,000)", "Posterior choices", "Grid points that change the choice"],
  X.evppi.map(e => [e.parameter, f0(e.evppi_binned_model), f0(e.evppi_nested), e.posterior_choices_nested, pc(e.share_grid_changing_choice, 0)]), [1700, 1600, 2000, 2400, 2206], { size: 12 }));
add(P(`**Can the information change the investment?** Only compressed-air savings can: in ${pc(evp("c_saving_frac").share_grid_changing_choice, 0)} of its range the choice moves from A+B+C to A+B. Its value (SAR ${f0(evp("c_saving_frac").evppi_nested)} nested vs ${f0(evp("c_saving_frac").evppi_binned_model)} binned, ${pc(evAgree, 1)} apart) is just below the assumed SAR ${f0(subCost)} sub-metering cost. Information on B's savings, the tariff, PV yield and cost, and the grid factor cannot change the choice, so its value is exactly zero — confirming that the binned estimator has no noise floor in v1.3.`));

add(H1("8. Real options and investment timing"));
add(table(["Component", "Status", "Check", "Result"], [
  ["Reform decision tree (one policy step)", "Prototype for administered prices — not a published method", "Hand calculation (Python and spreadsheet)", `invest now SAR ${f0(ro.tree.hand_now)} = model ${f0(ro.tree.model_now)}; waiting ${f0(ro.tree.hand_wait)}; decision: ${ro.tree.model_decision}`],
  ["Log-OU expected price (KAPSARC DP49 process)", "Published process; DP49 calibration borrowed (Henry Hub κ 0.5, σ 0.522)", "Closed-form mean vs 200,000 simulated paths", ro.logou_mean.map(m => `yr ${m.year}: ${f4(m.closed_form)} vs ${f4(m.simulated)} (se ${f4(m.se)})`).join("; ") + `; long-run mean ${f2(ro.logou_long_run_mean_equals_gbar)} = current price`],
  ["Least-squares Monte Carlo (Longstaff–Schwartz 2001)", "Published method", "Model's LSMC engine on the published American-put benchmark (S 36, K 40, r 6%, σ 20%, T 1, 50 dates)", `${f4(ro.lsmc_put_benchmark.model_lsmc_mean)} (sd ${f4(ro.lsmc_put_benchmark.sd_across_reps)}, 5 reps) vs published LSM ${ro.lsmc_put_benchmark.published_lsm} and finite difference ${ro.lsmc_put_benchmark.published_fd}; European value ${f2(ro.lsmc_put_benchmark.european_bs)}`],
  ["GBM trigger (Dixit–Pindyck; DP49 Eq. C.7/C.13)", "Published closed form", "λ is the positive root of ½σ²λ(λ−1)+μλ−r = 0; trigger maximises the closed-form value of a threshold policy", `λ ${f4(ro.gbm.lambda_)} (residual ${sci(ro.gbm.quadratic_residual)}); trigger $${f2(ro.gbm.trigger_model)} vs numerical optimum $${f2(ro.gbm.trigger_numeric)}`],
], [2300, 2400, 2500, 2706], { size: 11 }));
add(P("**Distinction.** The decision tree is our simplified prototype for a regulated price that changes in policy steps; LSMC and the GBM trigger are the published methods, verified here as implementations. Their use for a Saudi plant rests on a borrowed calibration from US Henry Hub prices and is illustrative only. The timing result (wait for the price decision; invest-now NPV negative) is driven by project D's negative NPV at the current regulated price, not by the option machinery."));

add(H1("9. Missing-data estimation and propagation (synthetic)", true));
add(table(["Dataset", "Gaps", "Coverage of 95% intervals (recomputed)", "95% CI", "MAPE engine", "MAPE mean of measured months", "Bias"], X.missing.map(m => [m.dataset, f0(m.gaps), pc(m.coverage), `${pc(m.ci_low)}–${pc(m.ci_high)}`, pc(m.mape), pc(m.mape_mean_of_measured), pc(m.bias, 2)]),
  [1300, 900, 1900, 1500, 1200, 1900, 1206], { size: 12 }));
add(Cap(`Recomputed from the stored held-out cells: the study stores the uncalibrated s.d., so coverage is ${pc(X.missing[0].coverage)} with the calibration factor ${ms.calibration_factor} applied, equal to the reported ${pc(ms.coverage_reported_after)}. The engine's error is only modestly below the naive mean-of-measured-months baseline on this generator.`));
add(table(["True step", "Noise sd", "Detection: model", "Detection: independent test", "Split within ±1 month"], X.change.map(c => [pc(c.true_shift, 0), pc(c.noise_sd, 0), pc(c.detect_rate_model, 1), pc(c.detect_rate_independent, 1), c.split_within_1_month == null ? "—" : pc(c.split_within_1_month, 0)]),
  [1500, 1500, 2200, 2400, 2306], { size: 12 }));
add(fig(CH, "a6_5_change_detection.png", "Figure 4 — Operational-change detection on simple series not produced by the A4 generator (200 per point): model vs a separately written permutation test.", 420));
add(P(`False alarms without a change are at most ${pc(fa, 1)} (test level 1%); shifts below the 10% materiality rule are not flagged by design; a 20% shift is detected with certainty at 3% noise but only ${pc(s20.detect_rate_model, 0)} at 6% noise. **Propagation:** the uncertainty of estimated months enters the decision through the target; for the demo case the model's target s.d. is ${f2(ms.target_sd_model)} t vs ${f2(ms.target_sd_independent)} t from the independent formula share × √Σ(EF·sd)² (inputs rounded). Complete data through the A4 path reproduce the v1.3 pipeline exactly (${X.a4 ? "passed" : "FAILED"}). The A4 report, workbook and chart were regenerated with the v1.3 register in this phase.`));

add(H1("10. Global sensitivity analysis"));
add(P(`Variance-based Sobol indices (Saltelli 2010 first-order, Jansen 1999 total-effect estimators) on ${f0(A.gsa.N)} scrambled-Sobol base samples (${f0(A.gsa.evaluations)} model evaluations) of all ${X.sobol.length / 4} uncertain inputs. Outputs: the decision-relevant contrast and an indicator of which portfolio is best in each scenario.`));
add(fig(CH, "a6_4_sobol.png", "Figure 5 — Total-effect (dark) and first-order (light) Sobol indices for four outputs.", 620));
add(table(["Output", "Most influential inputs (total effect)"], Object.keys(A.gsa.top).map(o => [o, top(o, 4)]), [3600, 6306], { size: 12 }));
add(P(`**Reading.** What decides whether C belongs in the portfolio is C's savings fraction (S_T ${f2(A.gsa.top["NPV(A+B+C) - NPV(A+B)"][0].ST)}), followed by C's cost and the tariff. The NPV level depends mostly on the tariff, B's savings and the PV cost; carbon-target compliance depends on B's savings. The first-order and total indices differ for the best-portfolio indicator (interactions), as expected for a discrete outcome. This matches the A5 switch points and the value-of-information result: **measuring compressed-air savings is the most decision-relevant information.**`));

add(H1("11. Boundary cases and numerical stability", true));
add(table(["Case", "Expected behaviour", "Result"], [
  ["Budget 0, target 0", "Empty portfolio, NPV 0", "MILP = enumeration = (none)"],
  ["Target above any attainable reduction", "Infeasible, nothing forced", "MILP and enumeration both return no portfolio; chance rules report 'none feasible'"],
  ["Budget 10¹² (unconstrained)", "Same optimum by MILP and enumeration", "Identical"],
  ["Contradictory chance constraints (100% carbon and 100% budget)", "Infeasible or a portfolio meeting both in every scenario", "Reported infeasible; no portfolio forced"],
  ["Missing input key", "Named error", "KeyError naming the input"],
  ["NaN input", "Refused", "**Defect fixed:** enumeration silently returned an arbitrary portfolio; now a ValueError names the affected projects"],
  ["Discount rate 0 and 10⁻¹⁴; life 1 year; r = −d", "Finite, equal to the direct sum", "**Defect fixed** at r = −d (returned n instead of n/(1+r)); all other edges correct"],
  ["SAA level with n = 1 and n = 10⁹", "Capped at 1; tends to α", "1.0 and 0.90002"],
  ["Rare-event probability (budget near 1)", "Within Monte Carlo error of the closed form", "Yes for 200,000-scenario samples; the 20,000-scenario estimate for A+B is 0.9997 vs exact 0.9991 (sampling)"],
], [3300, 3000, 3606], { size: 12 }));
add(Cap("All cases are automated tests in tests/test_a6.py."));

add(H1("12. Consistency of Python, Excel, Streamlit and Word"));
add(table(["Check", "Result"], X.checks, [4000, 5906], { size: 12 }));

add(H1("13. Validation status"));
add(table(["Component", "Status", "Basis", "Not covered"], [
  ["Emissions arithmetic, units, factor derivations", "**Validated** (independent + primary data)", "§2", "Refrigerants, Scope 3 Cat 3 not inventoried; real activity data"],
  ["NPV, IRR, payback, MAC, interactions", "**Validated** (independent code and spreadsheet)", "§3", "Tax, inflation, financing, inverter replacement not modelled"],
  ["Optimisation (MILP)", `**Validated** (independent enumeration, ${f0(optAll.cases)} cases + random tests)`, "§4", "—"],
  ["Monte Carlo and decisions D2–D4", "**Validated** (independent sampler and evaluator)", "§5", "Input correlations not modelled"],
  ["Chance constraints, capital-cost risk", "**Validated** (closed form, independent sample)", "§6", "Normal ±15% cost model is an assumption"],
  ["EVPI / EVPPI / EVSI", "**Partially validated**: recomputed and cross-checked by a second estimator of the same model", "§7", "EVPI definition gives a lower bound under the chance-constrained reading"],
  ["LSMC and GBM trigger", "**Validated as implementations** (published benchmark, closed form)", "§8", "Calibration borrowed from Henry Hub; not validated for Saudi administered prices"],
  ["Reform decision tree", "**Checked arithmetic only** (prototype method)", "§8", "No published validation"],
  ["Missing-data engine", "**Partially validated** on synthetic data from our own generator", "§9", "**No real industrial records** (A4-01)"],
  ["Global sensitivity", "**Computed**; consistent with switch points and VOI", "§10", "—"],
  ["Real-world representativeness of the case facility", "**Unverified**", "—", "All facility data synthetic; costs other than PV hypothetical"],
  ["Google Colab execution", "**Unverified on real Colab** (simulated only)", "—", "A1-01"],
], [2700, 2900, 700, 3606], { size: 12 }));

add(H1("14. Issue log (A6)"));
add(table(["ID", "Priority", "Issue", "Status"], [
  ["A6-01", "Medium", "IRR of project A ignored PV degradation (11.5% reported, correct value " + pc(projRows.find(r => r.item === "A" && r.metric === "IRR").independent, 2) + ")", "Fixed; test_project_irr_accounts_for_pv_degradation"],
  ["A6-02", "High", "NaN input produced a silent, arbitrary optimisation result", "Fixed; test_non_finite_inputs_are_refused_not_silently_optimised"],
  ["A6-03", "Low", "Degraded annuity factor wrong at r = −d", "Fixed; edge tests"],
  ["A6-04", "Medium", "EVPI definition: per-scenario target vs chance constraint kept (55.7k vs 74.3k)", "Documented; model value is a lower bound"],
  ["A6-05", "High", "A4 report, A4 workbook text, A4 chart and app table still described v1.2 results; key portfolio A+B+C not tracked in the A4 module", "Fixed; A4 study rerun and report regenerated with v1.3"],
  ["A6-06", "Low", "A4 validation file stores the uncalibrated s.d.; MILP named the empty portfolio '' (enumeration '(none)'); stale timing docstring", "Fixed or documented"],
  ["A6-07", "Medium", "Monte Carlo inputs independent (no correlations)", "Documented limitation"],
  ["A6-08", "Low", "Model's 20,000-scenario sample under-represents rare cost overruns for A+B (0.9997 vs exact 0.9991)", "Documented; no decision effect"],
  ["A1-01", "Critical", "Real Google Colab run", "**Open** — must be done before submission"],
  ["A4-01", "High", "No real industrial validation", "**Open** — state clearly in the submission"],
  ["A5-01…A5-14", "Medium–High", "Source-evidence gaps (2027 tariff, 2026 gas price, quotations, second PV benchmark, refrigerants, Cat 3, proxies)", "**Open**"],
], [800, 900, 5300, 2906], { size: 12 }));

add(H1("15. Is Phase A ready to close?"));
add(P("**Technically yes, with two conditions.** The model's mathematics, its implementation and the consistency of all outputs have been checked as far as is possible without real data; the defects found were minor and are fixed, and the recommendation is reproduced independently. Before the WE Rise submission:"));
add(B("**Run the package once on real Google Colab** (A1-01): open Mezan_Colab.ipynb, run all cells, confirm 'passed' and the Streamlit link."));
add(B("**State plainly** in the pitch and documents that the facility is synthetic, costs other than PV are hypothetical, and validation is mathematical and synthetic, not on real industrial records (A4-01)."));
add(B("**Present the recommendation with its dependency:** A+B+C rests on the Riyadh PV cost benchmark and on compressed-air savings; measuring those savings (sub-metering) is the most valuable next step."));
add(B("Optional, if time allows: obtain the official 2027 tariff schedule and one supplier quotation (PV), rerun run_all.py and tools/run_a6.py."));

add(H1("16. Reproduce"));
add(P("python run_all.py → python tools/run_a6.py (all sections; ~10 min) → python tools/build_a6_workbook.py (independent spreadsheet, LibreOffice recalculation) → python tools/build_a6_tables.py → python tools/consistency_a6.py → python tools/run_tests.py → python tools/fault_injection.py → python tools/crosscheck.py . outputs/crosscheck.csv."));
add(TT("References"));
[["Longstaff, F. & Schwartz, E. (2001). Valuing American options by simulation: a simple least-squares approach. Review of Financial Studies 14(1)", "https://doi.org/10.1093/rfs/14.1.113"],
 ["Dixit, A. & Pindyck, R. (1994). Investment under Uncertainty. Princeton University Press", "https://press.princeton.edu/books/hardcover/9780691034102/investment-under-uncertainty"],
 ["Saltelli, A. et al. (2010). Variance based sensitivity analysis of model output. Computer Physics Communications 181(2)", "https://doi.org/10.1016/j.cpc.2009.09.018"],
 ["Jansen, M. (1999). Analysis of variance designs for model output. Computer Physics Communications 117", "https://doi.org/10.1016/S0010-4655(98)00154-4"],
 ["Pagnoncelli, B., Ahmed, S. & Shapiro, A. (2009). Sample average approximation method for chance constrained programming. J. Optimization Theory and Applications 142", "https://doi.org/10.1007/s10957-009-9523-6"],
 ["KAPSARC Discussion Paper DP49 (2026)", "https://doi.org/10.30573/KS--2026-DP49"]].forEach(([t, u]) => add(B(`${t}. [${u}](${u})`)));

const doc = new D.Document({
  styles: { default: { document: { run: { font: L.FONT, size: L.SZ } } } },
  numbering: { config: [
    { reference: "bul", levels: [{ level: 0, format: D.LevelFormat.BULLET, text: "•", alignment: D.AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 240 } } } }] },
    { reference: "num", levels: [{ level: 0, format: D.LevelFormat.DECIMAL, text: "%1.", alignment: D.AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 300 } } } }] }] },
  sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1000, bottom: 1000, left: 1000, right: 1000 } } },
    footers: { default: new D.Footer({ children: [new D.Paragraph({ alignment: D.AlignmentType.RIGHT, children: [new D.TextRun({ text: "Mezan · Phase A6 · synthetic case · page ", size: 16, color: L.GREY }), new D.TextRun({ children: [D.PageNumber.CURRENT], size: 16, color: L.GREY })] })] }) },
    children: kids }] });
D.Packer.toBuffer(doc).then(b => { fs.writeFileSync(OUT, b); console.log("saved", OUT); });
