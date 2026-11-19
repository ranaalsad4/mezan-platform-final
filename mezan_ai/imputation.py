"""AI capability C - machine-learning challengers for missing-data estimation.

The existing statistical estimator (carbon_iq.dataquality.estimate: production intensity, seasonal history or mean,
chosen by leave-one-out back-test) stays the default. For every gap it proposes, this module fits two ML challengers on
the same stream's usable months (previous and reporting year):
  ridge   ridge regression (scikit-learn) on output, operating hours, month (sin/cos) and a year indicator
  forest  random-forest regression (scikit-learn, 120 trees, min 2 samples per leaf) on the same features
and back-tests them with the SAME leave-one-out protocol on the reporting year's measured months (relative RMSE).

Evidence gate - an ML estimate may be ADOPTED for a cell only if all hold:
  1. the statistical estimator produced a proposal (ML never bypasses a refusal rule such as GAP_TOO_LONG or
     OPERATIONAL_CHANGE),
  2. at least MIN_TRAIN usable months are available,
  3. the challenger's back-test error is below GATE_RATIO x the statistical method's back-test error, and
  4. a reviewer explicitly chooses it (adopt()). Nothing is replaced automatically.
Prediction intervals for an adopted ML estimate use the statistical estimator's formula (back-test RMSE x sqrt(1+1/n) x
t-quantile, x the synthetic calibration factor), so the downstream uncertainty treatment is unchanged.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import t as T_DIST

from carbon_iq.dataquality import estimate as ES

GATE_RATIO = 0.90
MIN_TRAIN = 15
SEED = 20261024
MODEL_TEXT = {"ridge": "ridge regression (scikit-learn)", "forest": "random forest regression (scikit-learn)"}


def _frame(L, stream):
    """Feature/target table for one stream over both years. Target NaN where not usable."""
    frames = [c for c in (L.hist_cells, L.cells) if c is not None]
    allc = pd.concat(frames, ignore_index=True)
    usable = allc.status.isin(ES.USABLE)
    w = allc.assign(v=allc.value.where(usable)).pivot_table(index="period", columns="stream", values="v", aggfunc="first")
    w = w.reindex(sorted(set(allc.period)))
    df = pd.DataFrame(index=w.index)
    df["production"] = w.get("production")
    df["operating_hours"] = w.get("operating_hours")
    m = np.array([int(p[5:7]) for p in df.index])
    df["month_sin"], df["month_cos"] = np.sin(2 * np.pi * m / 12), np.cos(2 * np.pi * m / 12)
    df["year"] = [int(p[:4]) - L.year for p in df.index]
    df["y"] = w.get(stream)
    return df


def _model(kind):
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    if kind == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    return RandomForestRegressor(n_estimators=120, min_samples_leaf=2, random_state=SEED)


def _cols(df, stream):
    cols = ["month_sin", "month_cos", "year"]
    for c in ("production", "operating_hours"):
        if c != stream and df[c].notna().sum() >= MIN_TRAIN:
            cols.insert(0, c)
    return cols


def _loo(df, cols, kind, year_prefix):
    train = df.dropna(subset=cols + ["y"])
    test_idx = [p for p in train.index if p.startswith(year_prefix)]
    err = []
    for p in test_idx:
        tr = train.drop(index=p)
        if len(tr) < MIN_TRAIN - 1:
            return None
        m = _model(kind).fit(tr[cols].values, tr.y.values)
        err.append(float(m.predict(train.loc[[p], cols].values)[0] - train.at[p, "y"]))
    if len(err) < 4:
        return None
    rmse = float(np.sqrt(np.mean(np.square(err))))
    level = float(train.loc[test_idx, "y"].mean())
    return rmse, len(err), (rmse / level if level else np.inf)


def challengers(L) -> pd.DataFrame:
    """One row per pending gap: statistical proposal vs the ML challengers and the evidence-gate result."""
    rows = []
    pend = L.table[L.table.decision == "pending"]
    cache = {}
    for _, r in pend.iterrows():
        stream = r.stream
        if stream not in cache:
            df = _frame(L, stream)
            cols = _cols(df, stream)
            fits = {k: _loo(df, cols, k, str(L.year)) for k in MODEL_TEXT}
            cache[stream] = (df, cols, fits)
        df, cols, fits = cache[stream]
        cand = json.loads(r.candidates) if r.candidates else {}
        stat_rel = cand.get(r.method, {}).get("rel") if r.method else None
        n_train = int(df.dropna(subset=cols + ["y"]).shape[0])
        feat_ok = r.period in df.index and df.loc[r.period, cols].notna().all()
        best = None
        for k, f in fits.items():
            if f is not None and (best is None or f[2] < fits[best][2]):
                best = k
        est = np.nan
        if best and feat_ok:
            tr = df.dropna(subset=cols + ["y"]).drop(index=r.period, errors="ignore")
            est = float(_model(best).fit(tr[cols].values, tr.y.values).predict(df.loc[[r.period], cols].values)[0])
        reasons = []
        if r.refusal:
            reasons.append(f"statistical estimator refused ({r.refusal.split(':')[0]}); ML may not bypass refusal rules")
        if n_train < MIN_TRAIN:
            reasons.append(f"only {n_train} usable months (< {MIN_TRAIN})")
        if not feat_ok:
            reasons.append("features missing for this month")
        if best is None:
            reasons.append("ML back-test not possible")
        if best and stat_rel is not None and not fits[best][2] < GATE_RATIO * stat_rel:
            reasons.append(f"ML back-test error {fits[best][2]:.1%} not below {GATE_RATIO:.0%} of the statistical method's {stat_rel:.1%}")
        if est == est and est < 0:
            reasons.append("negative prediction")
        passed = not reasons
        rows.append(dict(period=r.period, stream=stream, status=r.status,
                         statistical_method=r.method or "—", statistical_estimate=r.estimate, statistical_backtest_error=stat_rel,
                         ml_model=MODEL_TEXT.get(best, "—") if best else "—", ml_key=best or "", ml_estimate=est,
                         ml_backtest_error=fits[best][2] if best else np.nan, ml_rmse=fits[best][0] if best else np.nan,
                         ml_n=fits[best][1] if best else 0, ridge_error=(fits["ridge"] or (None, None, np.nan))[2],
                         forest_error=(fits["forest"] or (None, None, np.nan))[2], n_train=n_train,
                         gate_passed=passed, gate_reason="evidence gate passed" if passed else "; ".join(reasons)))
    return pd.DataFrame(rows)


def adopt(L, row, by="reviewer"):
    """Use the ML estimate for one cell after the gate passed. Records method, interval and an audit event, then
    approves the cell through the ledger's own decision function."""
    if not row["gate_passed"]:
        raise ValueError(f"evidence gate not passed: {row['gate_reason']}")
    i = L._idx(L.table[(L.table.period == row["period"]) & (L.table.stream == row["stream"])].site.iloc[0], row["period"], row["stream"])
    n = int(row["ml_n"])
    sd = float(row["ml_rmse"]) * np.sqrt(1 + 1 / n) * T_DIST.ppf(0.975, max(n - 1, 1)) / 1.96 * (ES.CAL_MONTHLY if L.calibrate else 1.0)
    L.table.at[i, "method"] = f"ml_{row['ml_key']}"
    L.table.at[i, "estimate"] = float(row["ml_estimate"])
    L.table.at[i, "sd"] = sd
    L.table.at[i, "low95"] = max(0.0, float(row["ml_estimate"]) - 1.96 * sd)
    L.table.at[i, "high95"] = float(row["ml_estimate"]) + 1.96 * sd
    note = (f"ML challenger adopted: {row['ml_model']}; back-test error {row['ml_backtest_error']:.1%} vs statistical "
            f"{row['statistical_backtest_error']:.1%} (gate {GATE_RATIO:.0%})")
    L.decide(L.table.at[i, "site"], row["period"], row["stream"], "approve", by, note)
    return sd
