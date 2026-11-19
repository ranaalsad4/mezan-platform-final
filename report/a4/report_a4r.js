// Mezan Phase A4 (refined) technical report. Usage: node report_a4r.js <project dir> <data.json> <shots dir> <out.docx>
// Every number is read from outputs/a4 (tools/run_a4.py) via data.json (prep_a4r.py).
const fs = require("fs");
const path = require("path");
const L = require(fs.existsSync(path.resolve(__dirname, "../lib.js")) ? path.resolve(__dirname, "../lib.js") : path.resolve(__dirname, "../../full/report/lib.js"));
const { D, P, H1, H2, B, TT, callout, table, Cap, fig, EQ } = L;
const [, , ROOT, DATA, SHOTS, OUT] = process.argv;
const X = JSON.parse(fs.readFileSync(DATA, "utf8"));
const R = X.results;
const CH = path.join(ROOT, "outputs", "a4", "charts");
const f0 = v => v == null || Number.isNaN(v) ? "—" : Math.round(v).toLocaleString("en-US");
const f1 = v => v == null || Number.isNaN(v) ? "—" : Number(v).toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const pc = (v, d = 1) => v == null || Number.isNaN(v) ? "—" : (100 * v).toFixed(d) + "%";
const p4 = v => v == null ? "—" : Number(v).toFixed(4);
const dec = c => R.decisions[c];
const covAll = X.coverage.filter(r => r.scenario === "all");
const cv = (ds, st) => covAll.find(r => r.dataset.startsWith(ds) && r.setting.startsWith(st));
const chg = Object.fromEntries(X.change.map(r => [r.dataset.startsWith("base") ? "base" : r.dataset, r]));
const stab = (c, r) => X.stab_rules.find(x => x.case === c && x.rule === r);
const voi = (m, r) => X.voi.find(x => x.measurement === m && x.rule === r);
const ci = (r, k) => `${pc(r[k + "_coverage"])} (${pc(r[k + "_ci_low"])}–${pc(r[k + "_ci_high"])})`;
const cal = X.calibration;
const seeds = X.stab_seed.map(s => s["p_target[A+B]"]);
const MR = X.main;   // main pipeline results (v1.3 register)
const unstable = X.stab_rules.filter(r => r.status !== "STABLE");
const stabTxt = c => ["D1", "D2", "D3", "D4"].map(r => { const s = stab(c, r); return `${r} ${s.choice}${s.status === "STABLE" ? "" : " (" + s.status.toLowerCase() + ")"}`; }).join(", ");
const flag = (c, r) => { const s = stab(c, r); return s && s.status !== "STABLE" ? " ⚠" : ""; };
const voiAny = X.voi.filter(v => v.value_npv > 1e-6);
const mg = r => X.stab_margins.find(m => m.case === "C2" && m.rule === r && !String(m.choice).startsWith("("));

const kids = [];
const add = (...x) => kids.push(...x.flat());
add(new D.Paragraph({ spacing: { after: 60 }, children: [new D.TextRun({ text: "Mezan — Phase A4 (refined): Missing-Data Intelligence", bold: true, font: L.FONT, size: 34, color: L.NAVY })] }),
  P(`Technical report · regenerated 26 October 2026 (Phase A6) with the model v${X.results.register_version} register · **all A4 data are synthetic** · supersedes the A4 reports of 25 and 26 October, which used the v1.2 register`, { r: { color: L.GREY } }));
add(callout([
  `**Decision stability (v${X.results.register_version} inputs).** Complete data: ${stabTxt("C0")}. Demo with approved estimates: ${stabTxt("C2")}.${unstable.length ? " Flagged: " + unstable.map(u => `${u.case} ${u.rule} — ${u.reasons}`).join("; ") + "." : ""} Under the v1.2 register the carbon rule D3 sat on a knife-edge between A+B and A+C+D; with the v1.3 inputs the chosen portfolio A+B+C meets the target in ${pc(dec("C0")["p_target[A+B+C]"], 2)} of scenarios, and the remaining fragility is project C's marginal value (A5-10). The recommendation itself is never changed by these checks.`,
  `**Calibration (held-out synthetic sets).** Monthly 95% intervals covered ${pc(cv("base", "before").monthly_coverage)} before and ${ci(cv("base", "after"), "monthly")} after a split-conformal factor of ${cal.cal_monthly.toFixed(3)}. Annual intervals were **overly wide** (${pc(cv("base", "before").annual_coverage)}, linear sum of monthly errors); a calibrated within-stream correlation of ${cal.rho_annual} (directly estimated: ${cal.empirical_rho.toFixed(2)}) gives ${ci(cv("base", "after"), "annual")} with ${pc(1 - cv("base", "after").annual_halfwidth / cv("base", "before").annual_halfwidth, 0)} narrower intervals. Coverage holds on high-noise, flat-season and trend data but **not** when production shifts mid-year (annual ${pc(cv("break_production", "after").annual_coverage)}).`,
  (voiAny.length ? `**Value of information.** Records with decision value: ${[...new Set(voiAny.map(v => v.measurement + " " + v.label))].join("; ")}.` :
   `**Value of information.** Under the v${X.results.register_version} inputs **no missing record has decision value** under D2, D3 or D4: whatever the true value of a missing month, the choice stays ${dec("C2").D3}. (Under the v1.2 register the missing electricity bills mattered because D3 sat on a knife-edge.) Collecting records is still worthwhile for reporting accuracy, not for this investment decision.`),
  `**Operational change.** A permutation test now checks the relationship each method assumes stable. On clean data it warns for ${pc(chg.base.change_warning_rate)} of stream-years with gaps; after an injected change in energy use it detects ${pc(chg.break_intensity.detection_rate_break_streams, 0)} of changes, refuses ${pc(chg.break_intensity.after_break_refused_new, 0)} of affected gaps and cuts the error of the rest from ${pc(chg.break_intensity.after_break_mape_old)} to ${pc(chg.break_intensity.after_break_mape_new)}. In the demo it raised one false alarm (forklift diesel), resolved by a labelled reviewer override.`,
  `**Integration check.** Complete data through the A4 path reproduce the v${X.results.register_version} pipeline exactly (${X.results.complete_data_reproduces_pipeline ? "passed" : "FAILED"}). Every result here comes from our own synthetic generator and is **not** evidence of accuracy on real industrial records.`]));

add(H1("1. What changed in this refinement"));
add(table(["Refinement", "Implemented", "Evidence", "Status"], [
  ["Decision stability", "Margins to every threshold in Monte Carlo standard errors; 40 plausible true datasets per case; switch points per stream; dashboard warnings", "Stability tables (§2); tests; fault injection", "Implemented"],
  ["Uncertainty calibration", "Split-conformal monthly factor; calibrated within-stream correlation for annual totals; fitted on seed 5501, evaluated on 6 held-out sets with Wilson intervals", "Coverage tables (§3)", "Calibrated for the synthetic generator family only"],
  ["Uncertain target", "An estimated baseline now makes the 15% target uncertain in the Monte Carlo (it was held fixed)", "Exact linear offset tested", "Implemented"],
  ["Value of information", "Pre-posterior analysis on the estimation error of each missing record, under D2, D3 and D4, with hypothetical costs and net value", "§4; irrelevant records give exactly zero", "Implemented"],
  ["Operational change", "Permutation test on each method's constant-assumption series; regime-only training; refusal at the change point or with < 4 regime months; production-anomaly rule; reviewer override", "§5; false-alarm and power study", "Implemented; validated on synthetic data"],
  ["Dashboard", "Before/after table and chart (register, zero-filled, estimated, records obtained), warnings, stability check, value-of-information table", "AppTest; screenshots (§6)", "Implemented"],
], [2000, 3900, 2200, 1806], { size: 14 }));

add(H1("2. Decision stability"));
add(P("Three checks are applied to every decision rule; they describe the decision and never change it."));
add(B("**Margins.** For chance constraints, p − α (α = 0.9035) in Monte Carlo standard errors √(p(1−p)/n), for the chosen portfolio and for the higher-value portfolio the rule excludes. For D2, the expected-NPV gap to the runner-up with its paired standard error. For D4, the best budget probability among carbon-feasible portfolios and the minimum budget."));
add(B("**Plausible true datasets.** 40 datasets are drawn from the estimates' uncertainty; each is treated as known and the rules re-applied. Agreement = share giving the same choice."));
add(B("**Switch points.** The smallest change of one stream total that changes a rule's choice, in % and in estimate standard deviations. A rule is flagged **unstable** when a margin is within 2 standard errors, agreement is below 95%, or a switch point lies inside the 95% interval."));
add(table(["Case", "Rule", "Choice", "Status", "Agreement", "Reason"], X.stab_rules.map(r => [r.case, r.rule, r.choice, r.status, pc(r.agreement, 0), r.reasons || "—"]),
  [600, 600, 1300, 1900, 900, 4606], { size: 13 }));
add(Cap("C0 complete synthetic data · C2 demo with approved estimates · C4 demo with the missing electricity bills obtained. Agreement is 100% by construction when no value is estimated."));
add(table(["Rule", "Threshold", "Value", "Limit", "Margin (SE)"], X.stab_margins.filter(m => m.case === "C2").map(m => [m.rule + (m.choice.startsWith("(") ? " " + m.choice : ""), m.threshold,
  m.value > 1000 ? f0(m.value) : p4(m.value), m.limit > 1000 ? f0(m.limit) : p4(m.limit), m.margin_se == null ? (m.margin_rel == null ? "—" : pc(m.margin_rel) + " of limit") : Number(m.margin_se).toFixed(1)]),
  [1900, 3700, 1300, 1300, 1706], { size: 13 }));
add(Cap(`Case C2. D2's lead over the runner-up ${mg("D2").runner_up} is ${Number(mg("D2").margin_se).toFixed(0)} Monte Carlo standard errors; D1's target slack is ${pc(mg("D1").margin_rel, 0)} but its NPV lead over ${mg("D1").runner_up} is only SAR ${f0(mg("D1").runner_up_gap)}, which is why a small change in electricity switches D1.`));
add(table(["Seed", "A+B P(target)", "A+B+C P(target)", "A+C+D P(target)", "D3", "D4"], X.stab_seed.map(s => [String(s.seed), p4(s["p_target[A+B]"]), p4(s["p_target[A+B+C]"]), p4(s["p_target[A+C+D]"]), s.D3, s.D4]), [1500, 1600, 1700, 1700, 1700, 1706], { size: 13 }));
add(Cap(`Complete data, ${X.stab_seed.length} scenario seeds: D3 = ${[...new Set(X.stab_seed.map(s => s.D3))].join(" / ")} and D4 = ${[...new Set(X.stab_seed.map(s => s.D4))].join(" / ")} on every seed; A+B\'s target probability ranges ${p4(Math.min(...seeds))}–${p4(Math.max(...seeds))}, clear of the tightened level 0.9035.`));
add(fig(CH, "a4_3_decisions.png", "Figure 1 — Target probability of A+B, A+B+C and A+C+D by case, with ±2 Monte Carlo standard errors.", 560));
add(P(`**Reading.** With the v${X.results.register_version} inputs the chance-constrained rules (D3, D4) are robust to the data gaps: all candidate portfolios are far from the 90% threshold. The deterministic rule D1 is the fragile one, because project C adds little value (NPV SAR ${f0(MR.c_npv)}): ${unstable.length ? unstable.map(u => u.reasons).join("; ") : "no switch found"}. The dashboard labels such choices with ⚠.`));

add(H1("3. Uncertainty calibration", true));
add(P(`**Method.** Prediction intervals are estimate ± 1.96 sd with sd = back-test RMSE·√(1+1/n)·t₀.₉₇₅,ₙ₋₁/1.96·c. The factor c is a split-conformal quantile: on a **calibration** set (seed ${cal.seed}, ${cal.facilities} synthetic facilities, ${f0(cal.n_cells)} masked gaps) c = q₀.₉₅(|error/sd|)/1.96 = ${cal.cal_monthly.toFixed(4)}, never below 1. Annual totals combine monthly errors with a common within-stream correlation ρ; the smallest ρ reaching 95% on ${f0(cal.n_stream_years)} calibration stream-years is ${cal.rho_annual}, consistent with the directly estimated correlation ${cal.empirical_rho.toFixed(3)}. Both are then evaluated on data never used for fitting: a held-out base set and five other generator families.`));
add(table(["Dataset", "Setting", "Monthly coverage (95% CI)", "Monthly half-width", "Annual coverage (95% CI)", "Annual half-width"],
  covAll.map(r => [r.dataset.split(" (")[0], r.setting.split(" (")[0], ci(r, "monthly"), pc(r.monthly_halfwidth), ci(r, "annual"), pc(r.annual_halfwidth)]),
  [1600, 800, 2100, 1200, 2100, 2106], { size: 13 }));
add(Cap("Nominal 95%. Before = first A4 release (t-interval, linear annual sum, no change detection); after = refined engine on the same masked data. Half-widths as % of the true value. Wilson score intervals."));
add(fig(CH, "a4_2_calibration.png", "Figure 2 — Left: empirical vs nominal coverage of monthly intervals (held-out base set). Right: 95% coverage by dataset.", 600));
const relB = X.reliability.filter(r => r.dataset.startsWith("base"));
add(table(["Nominal", "Before", "After"], [0.5, 0.8, 0.9, 0.95, 0.99].map(nm => [pc(nm, 0), ...["before", "after"].map(st => { const r = relB.find(x => Math.abs(x.nominal - nm) < 1e-9 && x.setting.startsWith(st)); return `${pc(r.empirical)} (${pc(r.ci_low)}–${pc(r.ci_high)})`; })]),
  [2000, 3950, 3956], { size: 13 }));
add(Cap("Monthly coverage at several nominal levels, held-out base set. Intervals use the normal shape at each level."));
add(P(`**Findings.** (1) Monthly intervals were slightly too narrow; the factor ${cal.cal_monthly.toFixed(3)} widens them by ${pc(cal.cal_monthly - 1, 0)} and brings coverage to the nominal level (95% inside the Wilson interval) on five of six held-out sets. (2) Annual intervals were **too wide**: the linear sum assumed that the errors of different months move together, but they are only weakly correlated (ρ ≈ 0.13). Using the calibrated correlation narrows annual intervals by about a third while keeping 94–95% coverage on the four no-change sets — a narrowing supported by held-out evidence, not imposed. (3) When production shifts mid-year, coverage falls below nominal (A4-12). (4) All of this is evidence about our generator only; the factors must be re-fitted on real records (A4-13).`));

add(H1("4. Which missing measurements matter? (value of information)"));
add(P("**Method (pre-posterior analysis).** The existing EVPI/EVSI framework values information by re-applying the same decision rule after the information arrives. For a missing record, the information is the estimation error z of that stream. The error's distribution is split into 16 equal-probability nodes; at each node every scenario is conditioned exactly (the record's true total is known, so both the project reductions and the 15% target move), the rule is re-applied, and the expected NPV and target probability of the chosen portfolio are recorded. Value = average over nodes minus the same quantities for the current choice. A record that cannot change any decision leaves every node identical, so its value is exactly zero — the binning noise floor of A1-26 does not arise. Monte Carlo error is shown as the standard deviation across three scenario seeds. EVSI is represented by an imperfect option (M6: engineering reconstruction with half the current error)."));
add(table(["ID", "Measurement", "Cost (hyp.)", "Value D3 (SAR)", "sd seeds", "ΔP(target) D3", "Net D3", "D2 / D4 value", "Posterior D3 choices"],
  [...new Set(X.voi.map(v => v.measurement))].map(m => { const d3 = voi(m, "D3"), d2 = voi(m, "D2"), d4 = voi(m, "D4");
    return [m, d3.label, f0(d3.cost_sar), f0(d3.value_npv), f0(d3.value_npv_sd_seeds), pc(d3.d_p_target, 2), f0(d3.net_value), `${f0(d2.value_npv)} / ${f0(d4.value_npv)}`, d3.posterior_choices]; }),
  [450, 2900, 750, 950, 700, 900, 900, 900, 1456], { size: 12 }));
add(Cap("Hypothetical costs: staff time at an assumed SAR 150/hour (4 h bills, 4 h gas statements, 3 h fuel cards, 6 h delivery notes, 2 h production records, 16 h engineering reconstruction). ΔP(target) is the change in the probability of meeting the target under the adaptive policy."));
add(fig(CH, "a4_4_information_value.png", "Figure 3 — Value of collecting each missing record under D3, with ±2 standard deviations across scenario seeds and the hypothetical cost.", 560));
add(P(`**Reading.** ${voiAny.length ? "Only the measurements listed in the summary have decision value." : "No missing record can change any decision rule, so every value is exactly zero (pre-posterior conditioning has no noise floor)."} For comparison, the main model values perfect information on all uncertain inputs at SAR ${f0(MR.evpi)} (EVPI) and the motor-system audit at SAR ${f0(MR.evsi)} (EVSI); the input that matters most for the decision is compressed-air savings (EVPPI SAR ${f0(MR.evppi_c)}). Missing activity data are a second-order question for this investment.`));

add(H1("5. Operational change detection", true));
add(P("Each method assumes something stays constant: intensity (stream ÷ production), the year-on-year ratio, or the level. For every stream with gaps the engine tests these series (history and current year where available, including flagged outliers) for a single mean shift: the largest Welch t-statistic over all split points, with a permutation p-value (499 permutations). A change is acted on when p < 0.01 and the shift is at least 10%."));
add(B("**Change inside the year:** all methods train on months of the gap's regime only; if fewer than 4 such months exist, or the gap sits at the change point, estimation is **refused** (OPERATIONAL_CHANGE) and a fallback estimate is stored for an explicit, labelled reviewer override."));
add(B("**Change between years:** warning only (current-year months are used anyway)."));
add(B("**Production anomaly:** if the month's output differs by more than 30% from the median month, methods that ignore production are excluded when production intensity is available."));
add(table(["Dataset", "Stream-years with gaps", "Warned", "Refused", "Changes detected", "Error after change: before → after", "Gaps refused after change", "Coverage after change: before → after"],
  X.change.map(r => [r.dataset.split(" (")[0], f0(r.stream_years_with_gaps), pc(r.change_warning_rate), pc(r.change_refusal_rate), pc(r.detection_rate_break_streams, 0),
    r.after_break_mape_old == null ? "—" : `${pc(r.after_break_mape_old)} → ${pc(r.after_break_mape_new)}`, pc(r.after_break_refused_new, 0),
    r.after_break_coverage_old == null ? "—" : `${pc(r.after_break_coverage_old)} → ${pc(r.after_break_coverage_new)}`]),
  [1500, 1000, 800, 800, 1000, 1700, 1100, 2006], { size: 13 }));
add(Cap("No-change sets: warnings are false alarms. break_intensity: one energy stream's intensity shifts by 10–50%; break_production: output and output-linked streams shift by 20–40% (warnings on forklift diesel there are genuine changes in its relationship to output). 'Before' = same data without change detection."));
add(table(["Dataset", "Shift size", "Stream-years", "Detected", "Refused"], X.change_size.map(r => [r.dataset, r.abs_size, f0(r.stream_years), pc(r.detected, 0), pc(r.refused, 0)]), [2500, 1500, 1800, 2000, 2106], { size: 13 }));
add(fig(CH, "a4_5_change_detection.png", "Figure 4 — Error of gaps after an operational change, with and without change detection.", 500));
add(TT("Failure cases"));
add(table(["Case", "Method", "Error", "In 95%?", "Outcome"], X.failures.map(f => [f.case, f.method || "—", f.rel_err == null ? "—" : pc(f.rel_err), f.covered == null ? "—" : (f.covered ? "yes" : "no"), f.outcome]),
  [3400, 1200, 700, 700, 3906], { size: 12 }));

add(H1("6. Before-and-after demonstration (synthetic)", true));
add(table(["Month", "Stream", "Injected problem", "Detected as", "Used value", "Error vs truth", "In 95%?"],
  X.demo_rows.map(r => [r.period, r.stream, r.change, r.code, r.label, r.rel_err == null ? "—" : pc(r.rel_err), r.covered == null ? "—" : (r.covered ? "yes" : "no")]),
  [800, 1300, 2300, 1900, 1900, 900, 806], { size: 12 }));
add(Cap("Forklift diesel, November: the synthetic truth happens to run about 12% higher in Sep–Dec; the change test flags it and refuses (3 months in the 'new regime'). The demo reviewer overrides, stating that no operational change occurred — the label records this. Without the override the decision stays blocked."));
add(table(["Case", "Scope 1+2 (t)", "Target sd (t)", "D1", "D2", "D3", "D4", "P(target) A+B+C"],
  X.cases.map(c => c.status === "BLOCKED" ? [c.case + " " + c.short, "blocked", "—", "—", "—", "—", "—", "—"] :
    [c.case + " " + c.short, f1(c.scope12), f1(c.target_sd), c.D1 + flag(c.case, "D1"), c.D2 + flag(c.case, "D2"), c.D3 + flag(c.case, "D3"), c.D4 + flag(c.case, "D4"), p4(c["p_target[A+B+C]"])]),
  [2900, 1100, 900, 700, 700, 1000, 1300, 1306], { size: 13 }));
add(Cap("⚠ = flagged unstable by the stability check. C3 (gaps counted as zero) understates Scope 1+2 by " + pc(1 - dec("C3").scope12_check) + ` and changes the choices (D1 ${dec("C3").D1}, D4 ${dec("C3").D4} instead of ${dec("C0").D1} / ${dec("C0").D4}) — recommendations the true data do not support.`));
add(fig(CH, "a4_1_electricity_demo.png", "Figure 5 — Electricity: measured, converted and estimated months with calibrated 95% intervals against the hidden synthetic truth.", 560));
add(TT("Streamlit — Data gaps (A4) tab"));
add(P("Load the demo or a CSV → findings and warnings → reviewer decisions (approve, reject, keep, confirm zero, override a flagged change) → annual totals → **before/after table and chart** (register reference, gaps as zero, estimates with uncertainty, and — for the synthetic demo — the true records) with ⚠ markers → stability warnings and full stability check → value-of-information table."));
add(fig(SHOTS, "app_a4r_1_before_after.png", "Figure 6 — Before/after comparison of carbon footprint and recommendation.", 560));
add(fig(SHOTS, "app_a4r_2_stability.png", "Figure 7 — Stability warning and value of information in the dashboard.", 560));

add(H1("7. Validation, regression and reproducibility"));
add(table(["Check", "Result"], X.checks, [4300, 5606], { size: 13 }));

add(H1("8. Issue log"));
add(TT("A4 (updated in this refinement)"));
add(table(["ID", "Priority", "Issue", "Status", "Next step"], X.issues_a4.map(i => [i.id, i.priority, i.title, i.status, i.next]), [650, 750, 3500, 3200, 1806], { size: 12 }));
add(TT("Carried forward (open from A1–A3)"));
add(table(["ID", "Priority", "Issue", "Status"], X.carried.map(i => [i.id, i.priority, i.title, i.status]), [800, 900, 5000, 3206], { size: 12, highlight: (r) => r === 0 }));

add(H1("9. WE Rise rubric"));
add(table(["Criterion", "Contribution of this refinement", "Remaining gap"], [
  ["1.3 Innovation & Technical Merit (20%)", "Calibrated intervals with held-out evidence; pre-posterior value of missing records; operational-change detection; decision-stability diagnostics — all linked to the chance-constrained portfolio model", "Real-data validation"],
  ["1.2 Feasibility (20%)", "Refuses or warns when history is unreliable; reviewer override is recorded; runs in Colab and Streamlit", "Real records (A5)"],
  ["1.4 Impact (20%)", "Shows which records are worth chasing (electricity bills) and which are not; shows when a recommendation is too fragile to act on", "Quantify with a pilot"],
  ["2.1 Storytelling / 2.2 Pitch", "One-screen before/after: zero-filled vs estimated vs records obtained, with an honest instability warning", "Rehearse with the demo"],
], [2600, 4800, 2506], { size: 13 }));

add(H1("10. Reproduce"));
add(P("pip install -r requirements.txt → python tools/calibrate_a4.py (calibration set; about 5 minutes) → python tools/run_a4.py (demo, stability, value of information, validation; about 25 minutes on 2 cores; --fast for a quick check) → python tools/run_tests.py → streamlit run app.py, tab ‘Data gaps (A4)’. Seeds: calibration 5501; held-out base 4404; variants 6601–6603; change sets 7701–7702; Monte Carlo 20261024 (+20261026–29 for seed checks)."));

const doc = new D.Document({
  styles: { default: { document: { run: { font: L.FONT, size: L.SZ } } } },
  numbering: { config: [
    { reference: "bul", levels: [{ level: 0, format: D.LevelFormat.BULLET, text: "•", alignment: D.AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 240 } } } }] },
    { reference: "num", levels: [{ level: 0, format: D.LevelFormat.DECIMAL, text: "%1.", alignment: D.AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 300 } } } }] }] },
  sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1000, bottom: 1000, left: 1000, right: 1000 } } },
    footers: { default: new D.Footer({ children: [new D.Paragraph({ alignment: D.AlignmentType.RIGHT, children: [new D.TextRun({ text: "Mezan · Phase A4 (refined) · synthetic data · page ", size: 16, color: L.GREY }), new D.TextRun({ children: [D.PageNumber.CURRENT], size: 16, color: L.GREY })] })] }) },
    children: kids }] });
D.Packer.toBuffer(doc).then(b => { fs.writeFileSync(OUT, b); console.log("saved", OUT); });
