"""A6 charts and the validation-tables workbook (outputs/a6/Mezan_A6_Validation_Tables.xlsx) from outputs/a6/*.csv."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
A6 = HERE / "outputs" / "a6"
CH = A6 / "charts"; CH.mkdir(exist_ok=True)
R = json.load(open(A6 / "a6_results.json"))
NAVY, GREEN, GREY, RED = "#1F4E46", "#7FB069", "#9AA5B1", "#B03A2E"
rd = lambda f: pd.read_csv(A6 / f)  # noqa: E731

# ------------------------------------------------------------------ chart 1: Monte Carlo convergence
g = rd("a6_mc_convergence_summary.csv")
c = rd("a6_mc_convergence.csv")
fig, ax = plt.subplots(1, 3, figsize=(11, 3.3))
for a_, (col, title, scale) in zip(ax, (("e_npv_ABC", "E[NPV] of A+B+C (SAR M)", 1e6), ("p_target_AB", "P(target) of A+B", 1),
                                         ("p_budget_ABC", "P(capex ≤ budget) of A+B+C", 1))):
    a_.scatter(c.n, c[col] / scale, s=8, color=GREY, label="10 seeds per size")
    a_.plot(g.n, c.groupby("n")[col].mean() / scale, color=NAVY, marker="o", label="mean")
    a_.set_xscale("log"); a_.set_title(title, fontsize=9, loc="left"); a_.spines[["top", "right"]].set_visible(False)
    a_.set_xlabel("scenarios (log scale)")
ax[1].axhline(0.9035, color=RED, ls="--", lw=1, label="tightened 90% level")
ax[2].axhline(0.9035, color=RED, ls="--", lw=1)
ax[1].legend(fontsize=7, frameon=False)
fig.tight_layout(); fig.savefig(CH / "a6_1_convergence.png", dpi=170); plt.close(fig)

# ------------------------------------------------------------------ chart 2: standard error vs theory
fig, ax = plt.subplots(figsize=(5.2, 3.2))
ax.loglog(g.n, g.e_npv_sd, "o-", color=NAVY, label="sd across seeds (observed)")
ax.loglog(g.n, g.e_npv_sd_theory, "--", color=RED, label="σ/√n (theory)")
ax.set_xlabel("scenarios"); ax.set_ylabel("SAR"); ax.set_title("Monte Carlo error of E[NPV](A+B+C)", fontsize=9, loc="left")
ax.legend(fontsize=7, frameon=False); ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(CH / "a6_2_standard_error.png", dpi=170); plt.close(fig)

# ------------------------------------------------------------------ chart 3: optimisation map (budget x target)
o = rd("a6_optimization.csv")
o = o[o.exclusive == "none"].copy()
o["milp"] = o.milp.fillna("infeasible")
cats = sorted(o.milp.unique(), key=lambda s: (s == "infeasible", s))
idx = {k: i for i, k in enumerate(cats)}
B_, T_ = np.sort(o.budget.unique()), np.sort(o.target.unique())
M = np.full((len(T_), len(B_)), np.nan)
for r in o.itertuples():
    M[np.searchsorted(T_, r.target), np.searchsorted(B_, r.budget)] = idx[r.milp]
fig, ax = plt.subplots(figsize=(10, 4.4))
cmap = plt.get_cmap("tab20", len(cats))
im = ax.imshow(M, origin="lower", aspect="auto", cmap=cmap, extent=[B_[0] / 1e6 - 0.125, B_[-1] / 1e6 + 0.125, T_[0] - 50, T_[-1] + 50],
               vmin=-0.5, vmax=len(cats) - 0.5)
cb = fig.colorbar(im, ticks=range(len(cats))); cb.ax.set_yticklabels(cats, fontsize=7)
ax.plot([5], [1358], "k*", ms=12); ax.annotate("case: SAR 5M, 1,358 t", (5, 1358), xytext=(5.4, 1700), fontsize=8, arrowprops=dict(arrowstyle="->"))
ax.set_xlabel("budget (SAR million)"); ax.set_ylabel("Scope 1+2 target (t/yr)")
ax.set_title(f"Deterministic optimum over {len(o)} budget/target cases: MILP = model enumeration = independent enumeration in every case", fontsize=9, loc="left")
fig.tight_layout(); fig.savefig(CH / "a6_3_optimization_map.png", dpi=170); plt.close(fig)

# ------------------------------------------------------------------ chart 4: global sensitivity
s = rd("a6_gsa_sobol.csv")
outs = ["1[scenario-best portfolio = A+B+C]", "NPV(A+B+C) - NPV(A+B)", "NPV(A+B+C)", "Reduction(A+B+C) - target"]
fig, ax = plt.subplots(1, 4, figsize=(13, 3.6))
for a_, out in zip(ax, outs):
    d = s[s.output == out].sort_values("ST", ascending=False).head(7)[::-1]
    y = np.arange(len(d))
    a_.barh(y - 0.2, d.ST.clip(lower=0), 0.4, color=NAVY, label="total effect S_T")
    a_.barh(y + 0.2, d.S1.clip(lower=0), 0.4, color=GREEN, label="first order S_1")
    a_.set_yticks(y, d.parameter, fontsize=7); a_.set_xlim(0, 1); a_.set_title(out, fontsize=8, loc="left")
    a_.spines[["top", "right"]].set_visible(False)
ax[0].legend(fontsize=7, frameon=False, loc="lower right")
fig.tight_layout(); fig.savefig(CH / "a6_4_sobol.png", dpi=170); plt.close(fig)

# ------------------------------------------------------------------ chart 5: change detection (model vs independent test)
cd = rd("a6_change_detection_independent.csv")
fig, ax = plt.subplots(figsize=(6, 3.2))
for sd_, m in ((0.03, "o"), (0.06, "s")):
    d = cd[cd.noise_sd == sd_]
    ax.plot(d.true_shift * 100, d.detect_rate_model, m + "-", color=NAVY, label=f"model, noise sd {sd_:.0%}")
    ax.plot(d.true_shift * 100, d.detect_rate_independent, m + "--", color=RED, mfc="none", label=f"independent test, noise sd {sd_:.0%}")
ax.set_xlabel("true step change (%)"); ax.set_ylabel("detection rate"); ax.set_title("Operational-change test on simple synthetic series", fontsize=9, loc="left")
ax.legend(fontsize=7, frameon=False); ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(CH / "a6_5_change_detection.png", dpi=170); plt.close(fig)

# ------------------------------------------------------------------ validation tables workbook
summ = o.groupby("milp").agg(cases=("budget", "size")).reset_index().rename(columns={"milp": "optimum"})
full = rd("a6_optimization.csv")
opt_summary = full.groupby("exclusive").agg(cases=("budget", "size"), identical_choice=("same_choice", "sum"), identical_npv=("same_value", "sum"),
                                            infeasible=("milp", lambda x: int(x.isna().sum()))).reset_index()
with pd.ExcelWriter(A6 / "Mezan_A6_Validation_Tables.xlsx", engine="openpyxl") as w:
    pd.DataFrame({"Mezan Phase A6 validation tables": [
        f"Model v{R.get('model_version')}; synthetic case facility. Nothing here is real-world validation.",
        "Kind of check: independent = recomputed by code that does not import the model (independent/indep.py) or by spreadsheet formulas; "
        "benchmark = published value or closed form; internal = the model against itself (seeds, sample sizes).",
        "Sheets: Optimization summary | Optimization cases | Optimum by budget (no rule) | Finance | Emissions | MC independent | MC convergence | "
        "MC convergence summary | Budget closed form | VOI | Missing data | Change detection | Sobol"]}).to_excel(w, sheet_name="README", index=False)
    opt_summary.to_excel(w, sheet_name="Optimization summary", index=False)
    full.to_excel(w, sheet_name="Optimization cases", index=False)
    summ.to_excel(w, sheet_name="Optimum by budget (no rule)", index=False)
    rd("a6_finance.csv").to_excel(w, sheet_name="Finance", index=False)
    rd("a6_emissions.csv").to_excel(w, sheet_name="Emissions", index=False)
    rd("a6_mc_independent.csv").to_excel(w, sheet_name="MC independent", index=False)
    c.to_excel(w, sheet_name="MC convergence", index=False)
    g.to_excel(w, sheet_name="MC convergence summary", index=False)
    rd("a6_chance_budget_analytic.csv").to_excel(w, sheet_name="Budget closed form", index=False)
    rd("a6_voi_evppi.csv").to_excel(w, sheet_name="VOI", index=False)
    rd("a6_missing_coverage.csv").to_excel(w, sheet_name="Missing data", index=False)
    cd.to_excel(w, sheet_name="Change detection", index=False)
    s.to_excel(w, sheet_name="Sobol", index=False)
from openpyxl import load_workbook  # noqa: E402
from openpyxl.styles import Font, PatternFill  # noqa: E402
wb = load_workbook(A6 / "Mezan_A6_Validation_Tables.xlsx")
for ws in wb.worksheets:
    for cc in ws[1]:
        cc.font = Font(bold=True, color="FFFFFF"); cc.fill = PatternFill("solid", fgColor="1F4E46")
    ws.freeze_panes = "A2"
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = min(60, max(10, max(len(str(x.value or "")) for x in col[:200]) + 2))
wb.save(A6 / "Mezan_A6_Validation_Tables.xlsx")
print("ok", sorted(p.name for p in CH.iterdir()))
