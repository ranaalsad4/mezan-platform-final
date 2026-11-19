"""AI capability B - anomaly detection on monthly operating records.

Two detectors, shown side by side and labelled separately:
  * Rule-based (existing, carbon_iq.dataquality.quality): per stream, a robust z-score of the month's energy intensity
    (|z| > 3.5, Iglewicz & Hoaglin 1993) plus unit-scale and zero rules. These flags drive the ledger's review queue.
  * ML (this module): Isolation Forest (Liu, Ting & Zhou 2008; scikit-learn) on MONTH-level feature vectors that combine
    streams - log energy intensity (electricity, natural gas and forklift diesel per tonne of output), log operating
    hours per tonne, log output, and the month's position in the year (sin/cos, so a recurring summer peak is not
    flagged). It looks for months whose combination of intensities is unusual, which single-stream z-scores can miss.

Isolation Forest flags are ADVISORY: they never change a value. A reviewer confirms or dismisses each flag; confirmed
flags are written to the audit trail and listed in the report. Anomaly scores are relative isolation scores
(higher = easier to isolate), not probabilities. A month is flagged when its score is at least THRESHOLD (0.55),
a level chosen on synthetic injected-anomaly data (tools/evaluate_ai.py), not a calibrated error rate.

The forest is only fitted when at least MIN_MONTHS months have complete features. With fewer, the module returns
applied=False with the reason, and only the rule-based checks are used (disclosed in the interface).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MIN_MONTHS = 18
MAX_IMPUTED = 1          # months with one missing energy feature are scored with that feature at its median (disclosed)
FEATURE_STREAMS = ("electricity", "natural_gas", "diesel_forklift", "operating_hours")
FEATURE_TEXT = {"log_production": "output (t)", "electricity": "electricity per tonne", "natural_gas": "natural gas per tonne",
                "diesel_forklift": "forklift diesel per tonne", "operating_hours": "operating hours per tonne",
                "month_sin": "season", "month_cos": "season"}
USE_STATUSES = ("measured", "converted", "outlier")     # outliers keep their recorded value here: that is what is tested
N_TREES = 300
THRESHOLD = 0.55        # chosen in tools/evaluate_ai.py (synthetic study): 0.50 gave ~4 false alarms per plant-year,
                        # 0.55 gave 78% detection with ~1.1 false alarms, 0.60 detected only 18% (outputs/ai/ai_evaluation.json)
SEED = 20261024


def features(cells: pd.DataFrame, hist_cells: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per month with complete features. Index = period. Values recorded as missing/zero are not imputed."""
    frames = [c for c in (hist_cells, cells) if c is not None]
    allc = pd.concat(frames, ignore_index=True)
    allc = allc[allc.status.isin(USE_STATUSES) & (allc.value > 0)]
    wide = allc.pivot_table(index="period", columns="stream", values="value", aggfunc="first")
    if "production" not in wide:
        return pd.DataFrame()
    f = pd.DataFrame(index=wide.index)
    f["log_production"] = np.log(wide["production"])
    for s in FEATURE_STREAMS:
        if s in wide:
            f[s] = np.log(wide[s] / wide["production"])
    month = pd.Series([int(p[5:7]) for p in f.index], index=f.index)
    f["month_sin"] = np.sin(2 * np.pi * month / 12)
    f["month_cos"] = np.cos(2 * np.pi * month / 12)
    energy = [c for c in FEATURE_STREAMS if c in f]
    n_missing = f[energy].isna().sum(axis=1)
    f = f[n_missing <= MAX_IMPUTED].copy()
    f["n_imputed"] = n_missing[f.index]
    for c in energy:                     # at most one energy feature per month: its median, so it adds no anomaly signal
        f[c] = f[c].fillna(f[c].median())
    return f.dropna()


def _robust_z(col):
    med = np.median(col)
    mad = np.median(np.abs(col - med))
    return np.zeros_like(col) if mad == 0 else 0.6745 * (col - med) / mad


def detect(cells: pd.DataFrame, hist_cells: pd.DataFrame | None = None, reporting_year: int | None = None,
           seed: int = SEED, min_months: int = MIN_MONTHS) -> dict:
    """Fit Isolation Forest on all months with complete features and report the reporting-year months it flags."""
    f = features(cells, hist_cells)
    info = dict(technique="Isolation Forest (scikit-learn), month-level intensity features", n_months=len(f), min_months=min_months,
                features=[c for c in f.columns if c != "n_imputed"], seed=seed,
                n_months_imputed=int((f["n_imputed"] > 0).sum()) if len(f) else 0)
    if len(f) < min_months:
        return dict(info, applied=False, flags=pd.DataFrame(), scores=pd.DataFrame(),
                    reason=(f"only {len(f)} months have complete features (output plus every energy stream); at least "
                            f"{min_months} are needed for a defensible Isolation Forest. Rule-based checks only."))
    from sklearn.ensemble import IsolationForest
    imputed = f.pop("n_imputed")
    X = f.values
    forest = IsolationForest(n_estimators=N_TREES, contamination="auto", random_state=seed).fit(X)
    score = -forest.score_samples(X)                     # higher = more anomalous (Liu et al. score s in (0, 1))
    flag = score >= THRESHOLD
    z = pd.DataFrame({c: _robust_z(f[c].values) for c in f.columns if not c.startswith("month_")}, index=f.index)
    rows = []
    for i, per in enumerate(f.index):
        top = z.loc[per].abs().sort_values(ascending=False)
        drivers = [f"{FEATURE_TEXT.get(c, c)} ({'+' if z.loc[per, c] > 0 else '−'}{abs(z.loc[per, c]):.1f} robust sd)"
                   for c in top.index[:2] if abs(z.loc[per, c]) >= 1.5]
        rows.append(dict(period=per, anomaly_score=float(score[i]), flagged=bool(flag[i]), features_imputed=int(imputed[per]),
                         drivers="; ".join(drivers) or "unusual combination of features (no single feature beyond 1.5 robust sd)",
                         **{f"feat_{c}": float(f.loc[per, c]) for c in f.columns}))
    scores = pd.DataFrame(rows).sort_values("anomaly_score", ascending=False).reset_index(drop=True)
    yr = str(reporting_year) if reporting_year else None
    flags = scores[scores.flagged & (scores.period.str.startswith(yr) if yr else True)].copy()
    flags["why"] = flags.apply(lambda r: f"Month {r.period}: isolation score {r.anomaly_score:.2f} (flag threshold {THRESHOLD:.2f}); drivers: "
                                         f"{r.drivers}" + (" (one energy feature missing, scored at its median)" if r.features_imputed else "")
                                         + ". Check the source records before approving the baseline.", axis=1)
    return dict(info, applied=True, flags=flags, scores=scores, reason="",
                threshold=THRESHOLD, n_flagged=int(len(flags)))


def compare_with_rules(result: dict, cells: pd.DataFrame) -> pd.DataFrame:
    """For each ML-flagged month: which rule-based issues the ledger already found in that month (agreement table)."""
    if not result.get("applied") or result["flags"].empty:
        return pd.DataFrame(columns=["period", "anomaly_score", "rule_based_issues", "ml_only"])
    out = []
    for _, r in result["flags"].iterrows():
        g = cells[(cells.period == r.period) & cells.issues.map(len).gt(0)]
        rule = sorted({f"{s}: {i.split(':')[0]}" for s, iss in zip(g.stream, g.issues) for i in iss
                       if not i.startswith(("LEGITIMATE_ZERO", "UNIT_CONVERTED", "DUPLICATE_IDENTICAL"))})
        out.append(dict(period=r.period, anomaly_score=round(r.anomaly_score, 3), drivers=r.drivers,
                        rule_based_issues="; ".join(rule) or "none", ml_only=not rule))
    return pd.DataFrame(out)
