"""Fault injection: show that the test suite detects deliberate errors.

Each fault is applied to a temporary copy of the package; the named tests are run and must FAIL. The unmodified copy
is run first and must PASS. Results are written to outputs/fault_injection.json.

    python tools/fault_injection.py
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FAULTS = [
    ("double counting", "B-C overlap not removed from portfolio totals", "carbon_iq/engine.py",
     'tot["scope12_t"] = tot["scope12_t"] - inter["BC"]["scope12_t"]', 'tot["scope12_t"] = tot["scope12_t"]',
     "tests/test_engine.py::test_ledger_equals_portfolio_for_all_64_no_double_counting"),
    ("uncertainty rule", "uncertainties of a product added linearly instead of in quadrature", "carbon_iq/engine.py",
     "return math.sqrt(sum(u ** 2 for u in u_pct))", "return sum(u_pct)",
     "tests/test_engine.py::test_ghg_protocol_worked_example"),
    ("chance constraint", "target-probability requirement ignored", "carbon_iq/uncertainty.py",
     "ok = [k for k in cand if pt[k] >= alpha - 1e-12]", "ok = [k for k in cand if pt[k] >= 0]",
     "tests/test_decisions.py::test_chance_constraint_respected"),
    ("VOI baseline", "EVPI not measured against the prior decision", "carbon_iq/voi.py",
     "return float(best.mean() - e0)", "return float(best.mean())",
     "tests/test_decisions.py::test_no_uncertainty_no_information_value"),
    ("log-OU drift", "mean-reversion level not corrected for volatility", "carbon_iq/timing.py",
     "alpha = math.log(gbar) - sigma ** 2 / (4 * kappa)\n    a = math.exp(-kappa * dt)",
     "alpha = math.log(gbar)\n    a = math.exp(-kappa * dt)",
     "tests/test_timing.py::test_logou_long_run_mean"),
    ("reporting basis (v1.1)", "reporting basis silently ignored", "carbon_iq/uncertainty.py",
     'if basis == "reporting":', "if False:",
     "tests/test_v11.py::test_reporting_basis_uses_fixed_factors"),
    ("capital-cost risk (v1.1)", "actual capex replaced by the quote", "carbon_iq/uncertainty.py",
     "self.PCAP = X @ self.CAP", "self.PCAP = X @ np.vstack([np.full(self.n, self.capex_quote[i]) for i in self.ids])",
     "tests/test_v11.py::test_capex_risk_separates_quote_and_actual"),
    ("budget chance constraint (v1.2)", "budget-compliance requirement ignored", "carbon_iq/decisions.py",
     'and (beta is None or pr["p_budget"][k] >= beta - 1e-12)]', "]",
     "tests/test_v11.py::test_joint_budget_constraint_infeasible_and_not_forced"),
    ("sampling margin (v1.2)", "chance constraint not tightened for sampling error", "carbon_iq/uncertainty.py",
     "return min(1.0, alpha + conf_z * math.sqrt(alpha * (1 - alpha) / n))", "return alpha",
     "tests/test_v11.py::test_tightened_chance_constraint_and_validation"),
    ("activity uncertainty (v1.1)", "activity-data uncertainty dropped from the Monte Carlo", "carbon_iq/uncertainty.py",
     "out[k] = _draw({2: rng2, 3: rng3}.get(p.stream, rng), p, n)",
     "out[k] = np.full(n, p.value) if p.stream == 2 else _draw({3: rng3}.get(p.stream, rng), p, n)",
     "tests/test_v11.py::test_activity_uncertainty_in_register_and_used_by_both_methods"),
    ("missing as zero (A4)", "unresolved data gaps counted as zero", "carbon_iq/dataquality/estimate.py",
     'val.append(np.nan); lab.append("UNRESOLVED ("', 'val.append(0.0); lab.append("UNRESOLVED ("',
     "tests/test_a4.py::test_missing_never_becomes_zero"),
    ("original overwritten (A4)", "approved estimate written over the observed-value column", "carbon_iq/dataquality/estimate.py",
     '        self.table.at[i, "decided_by"], self.table.at[i, "decided_at"]',
     '        self.table.at[i, "value"] = row["estimate"] if decision == "approve" else row["value"]\n'
     '        self.table.at[i, "decided_by"], self.table.at[i, "decided_at"]',
     "tests/test_a4.py::test_lineage_preserves_original_and_records_decisions"),
    ("estimation uncertainty (A4)", "uncertainty of estimated values dropped from the Monte Carlo", "carbon_iq/dataquality/integrate.py",
     "prm[k] = prm0[k] * (val / base[k]) + sd * z[k]", "prm[k] = prm0[k] * (val / base[k])",
     "tests/test_a4.py::test_estimation_uncertainty_widens_simulation"),
    ("gap-length refusal (A4)", "long gaps estimated instead of refused", "carbon_iq/dataquality/estimate.py",
     "if run[m] > MAX_GAP_RUN:", "if False:",
     "tests/test_a4.py::test_refusal_rules"),
    ("unit conversion (A4)", "kWh treated as MWh", "carbon_iq/dataquality/quality.py",
     '"kwh": ("MWh", 0.001)', '"kwh": ("MWh", 1.0)',
     "tests/test_a4.py::test_kwh_conversion_exact"),
    ("change detection (A4.1)", "operational-change test silently skipped", "carbon_iq/dataquality/estimate.py",
     'if detect_changes and STREAMS[stream]["kind"] != "intermittent":', "if False:",
     "tests/test_a4.py::test_operational_change_detected_and_estimation_restricted"),
    ("calibration factor (A4.1)", "calibrated interval factor not applied", "carbon_iq/dataquality/estimate.py",
     'cal = (CAL_MONTHLY if (SETTINGS["calibrate"] if calibrate is None else calibrate) else 1.0)', "cal = 1.0",
     "tests/test_a4.py::test_calibration_switch_reproduces_first_release"),
    ("uncertain target (A4.1)", "baseline estimation error ignored in the carbon target", "carbon_iq/dataquality/integrate.py",
     "Ts = T + (dT if uncertain_target else 0.0)", "Ts = T",
     "tests/test_a4.py::test_uncertain_target_offset_is_exact"),
    ("pre-posterior conditioning (A4.1)", "information value computed without conditioning on the measurement", "carbon_iq/dataquality/integrate.py",
     "zc[k] = np.sqrt(1 - f * f) * row[j] + f * z[k]", "zc[k] = z[k]",
     "tests/test_a4.py::test_preposterior_value_of_information"),
    ("stability flag (A4.1)", "knife-edge margin never flagged", "carbon_iq/dataquality/stability.py",
     "sampling_unstable=bool(abs(m_se) < SE_LIMIT)))", "sampling_unstable=False))",
     "tests/test_a4.py::test_stability_flags_knife_edge_but_not_robust_rules"),
    ("PV degradation (A5)", "PV energy discounted without degradation", "carbon_iq/engine.py",
     'd["npv"] = -d["capex"] + (d["annual_cf"] - d["fixed_cf"]) * d["energy_af"] + d["fixed_cf"] * d["af"]',
     'd["npv"] = -d["capex"] + d["annual_cf"] * d["af"]',
     "tests/test_engine.py::test_project_a_by_hand"),
    ("leak-management cost (A5)", "compressed-air leak-management cost dropped", "carbon_iq/engine.py",
     'annual_cf=c_mwh * tariff_mwh - p.get("c_om", 0.0)', "annual_cf=c_mwh * tariff_mwh",
     "tests/test_engine.py::test_project_d_and_e_by_hand"),
    ("profile restore (A5)", "comparison profile leaks into the register after an exception", "carbon_iq/assumptions.py",
     "    finally:\n        P.update(saved)", "    except Exception:\n        raise\n    P.update(saved)",
     "tests/test_a5.py::test_v12_profile_reproduces_v12_and_restores"),
    ("MAC discounting (A5)", "MAC ignores the degraded output of PV", "carbon_iq/engine.py",
     'return -d["npv"] / (d.get("af_t", d["af"]) * t)', 'return -d["npv"] / (d["af"] * t)',
     "tests/test_a5.py::test_degraded_annuity_and_mac"),
    ("finite-input guard (A6)", "NaN inputs reach the optimiser unchecked", "carbon_iq/optimize.py",
     "    if bad:\n        raise ValueError", "    if False:\n        raise ValueError",
     "tests/test_a6.py::test_non_finite_inputs_are_refused_not_silently_optimised"),
    ("IRR with degradation (A6)", "PV IRR computed with constant cash flows", "carbon_iq/engine.py",
     '    if "energy_af" not in d or degradation == 0:', '    if True:',
     "tests/test_a6.py::test_project_irr_accounts_for_pv_degradation"),
    ("annuity edge (A6)", "degraded annuity returns n when r = -d", "carbon_iq/engine.py",
     "np.where(np.abs(den) < 1e-12, n / (1 + r),", "np.where(np.abs(den) < 1e-12, n,",
     "tests/test_a6.py::test_annuity_factors_stable_at_edges"),
    ("ledger overlap (A6)", "B-C overlap NPV ignores that C ends before B", "carbon_iq/engine.py",
     "annuity_factor(r, np.minimum(p[\"b_life\"], p[\"c_life\"]))", "annuity_factor(r, p[\"b_life\"])",
     "tests/test_a6.py::test_all_64_portfolios_ledger_npv_and_reduction"),
]


def copy_pkg(dst):
    for name in ("carbon_iq", "tests", "independent"):
        shutil.copytree(ROOT / name, dst / name, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("README.md", "requirements.txt", "requirements-lock.txt", "Mezan_Colab.ipynb", "app.py"):
        if (ROOT / name).exists():
            shutil.copy(ROOT / name, dst / name)


def run_tests(where, tests):
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *tests], cwd=where,
                       capture_output=True, text=True)
    return r.returncode, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:]


def main():
    results = []
    all_tests = sorted({f[5] for f in FAULTS})
    with tempfile.TemporaryDirectory() as tmp:
        clean = Path(tmp) / "clean"
        clean.mkdir()
        copy_pkg(clean)
        code, line = run_tests(clean, all_tests)
        baseline_ok = code == 0
        print(f"unmodified package: {'PASS' if baseline_ok else 'FAIL'} ({line})")
        for name, what, file, old, new, test in FAULTS:
            d = Path(tmp) / name.replace(" ", "_").replace("(", "").replace(")", "")
            d.mkdir()
            copy_pkg(d)
            f = d / file
            src = f.read_text()
            assert src.count(old) == 1, f"fault '{name}': pattern not found exactly once in {file}"
            f.write_text(src.replace(old, new))
            code, line = run_tests(d, [test])
            detected = code != 0
            results.append({"fault": name, "description": what, "file": file, "test": test, "detected": detected, "pytest": line})
            print(f"{'DETECTED' if detected else 'MISSED  '}  {name}: {what}  [{test.split('::')[1]}]")
    out = {"baseline_passes": baseline_ok, "faults": len(results), "detected": sum(r["detected"] for r in results), "results": results}
    (ROOT / "outputs").mkdir(exist_ok=True)
    (ROOT / "outputs" / "fault_injection.json").write_text(json.dumps(out, indent=1))
    print(f"{out['detected']}/{out['faults']} faults detected")
    return 0 if baseline_ok and out["detected"] == out["faults"] else 1


if __name__ == "__main__":
    sys.exit(main())
