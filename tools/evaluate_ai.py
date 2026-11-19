"""Evaluation of the AI/ML capabilities on SYNTHETIC data with known truth -> outputs/ai/.

  1. Record classification: rules only, ML only (grouped 5-fold cross-validation by template, so the model is scored on
     wording it never saw), hybrid; plus the unlabelled demo export.
  2. Anomaly detection: random synthetic facilities (carbon_iq.dataquality.synth.random_facility) with one injected
     anomaly in a 2026 energy stream-month (x0.6, x1.3, x1.5 or x2.0) and clean facilities; month-level detection rate and
     false alarms of Isolation Forest at three score thresholds vs the existing robust z-score rule.
  3. Missing-data estimation: random facilities with 2 months removed from each of electricity, natural gas and forklift
     diesel; absolute percentage error against the known truth for the statistical estimator, the best ML challenger,
     and the gated policy (ML only where the evidence gate passes).
All data are synthetic; results say nothing about real plants until repeated on real records.

    python tools/evaluate_ai.py            # ~3-5 minutes
    python tools/evaluate_ai.py --fast     # smaller study for tests
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from carbon_iq.dataquality import estimate as ES  # noqa: E402
from carbon_iq.dataquality import quality as DQ  # noqa: E402
from carbon_iq.dataquality import synth as DS  # noqa: E402
from mezan_ai import anomaly as AN  # noqa: E402
from mezan_ai import classifier as C  # noqa: E402
from mezan_ai import imputation as IM  # noqa: E402
from mezan_platform import datasets as DSet  # noqa: E402

OUT = ROOT / "outputs" / "ai"
FAST = "--fast" in sys.argv


def classification():
    from sklearn.model_selection import GroupKFold
    df = pd.read_csv(C.CORPUS)
    rule_pred = [C._rule(t, list(DQ.STREAMS))[0] for t in df.description]
    covered = np.array([p is not None for p in rule_pred])
    rule_acc = float(np.mean([p == s for p, s in zip(rule_pred, df.stream) if p is not None]))
    ml_correct = np.zeros(len(df), bool)
    for tr, te in GroupKFold(n_splits=5).split(df, df.stream, df.template):
        import sklearn.base
        m = sklearn.base.clone(C.model()).fit(df.description.iloc[tr], df.stream.iloc[tr])
        ml_correct[te] = m.predict(df.description.iloc[te]) == df.stream.iloc[te].values
    hybrid = np.where(covered, np.array([p == s for p, s in zip(rule_pred, df.stream)]), ml_correct)
    raw, truth = DSet.unlabelled_raw()
    res = C.classify(raw)
    demo = dict(records=len(raw), correct=int((res.proposed_stream == truth).sum()),
                unresolved=int((res.method == "unresolved").sum()),
                wrong=int(((res.proposed_stream != truth) & (res.method != "unresolved")).sum()),
                by_method=res.method.value_counts().to_dict())
    return dict(corpus_rows=len(df), templates=int(df.template.nunique()), rules_coverage=float(covered.mean()),
                rules_accuracy_when_decided=rule_acc, ml_grouped_cv_accuracy=float(ml_correct.mean()),
                hybrid_grouped_cv_accuracy=float(hybrid.mean()), demo_export=demo,
                note="Grouped CV holds out whole description templates. Corpus is curated synthetic text, not company records.")


def _inject(raw, rng):
    st = ["electricity", "natural_gas", "diesel_forklift"][int(rng.integers(0, 3))]
    per = f"2026-{int(rng.integers(1, 13)):02d}"
    f = float(rng.choice([0.6, 1.3, 1.5, 2.0]))
    i = raw[(raw.stream == st) & (raw.period == per)].index[0]
    raw.at[i, "value"] = raw.at[i, "value"] * f
    return raw, dict(stream=st, period=per, factor=f)


def anomaly(n=60):
    thresholds = (0.50, 0.55, 0.60)
    rows = []
    for j in range(n):
        rng = np.random.default_rng(9000 + j)
        raw = DS.random_facility(rng)
        clean = j % 3 == 0
        info = {}
        if not clean:
            raw, info = _inject(raw, rng)
        cells, _ = DQ.assess(raw, 2026)
        hist, _ = DQ.assess(raw, 2025)
        res = AN.detect(cells, hist, None)
        sc = res["scores"]
        s26 = sc[sc.period.str.startswith("2026")]
        rule_months = set(cells[cells.status == "outlier"].period)
        rec = dict(facility=j, clean=clean, applied=res["applied"], **info,
                   rule_hit=(info.get("period") in rule_months) if info else None,
                   rule_false=len(rule_months - {info.get("period")}))
        for t in thresholds:
            fl = set(s26[s26.anomaly_score >= t].period)
            rec[f"if_hit_{t:.2f}"] = (info.get("period") in fl) if info else None
            rec[f"if_false_{t:.2f}"] = len(fl - {info.get("period")})
        rows.append(rec)
    df = pd.DataFrame(rows)
    inj = df[~df.clean]
    summ = dict(facilities=n, injected=int(len(inj)), clean=int(df.clean.sum()),
                rule_detection_rate=float(inj.rule_hit.mean()), rule_false_alarms_per_year=float(df.rule_false.mean()))
    for t in thresholds:
        summ[f"if_detection_rate_{t:.2f}"] = float(inj[f"if_hit_{t:.2f}"].mean())
        summ[f"if_false_alarms_per_year_{t:.2f}"] = float(df[f"if_false_{t:.2f}"].mean())
        summ[f"combined_detection_rate_{t:.2f}"] = float((inj[f"if_hit_{t:.2f}"] | inj.rule_hit).mean())
    by = inj.groupby("factor").agg(rule=("rule_hit", "mean"), **{f"if_{t:.2f}": (f"if_hit_{t:.2f}", "mean") for t in thresholds})
    summ["detection_by_injected_factor"] = by.round(3).reset_index().to_dict(orient="records")
    return summ, df


def imputation(n=30):
    rows = []
    for j in range(n):
        rng = np.random.default_rng(7000 + j)
        truth = DS.random_facility(rng)
        raw = truth.copy()
        drops = []
        for st in ("electricity", "natural_gas", "diesel_forklift"):
            ms = rng.choice(np.arange(1, 13), size=2, replace=False)
            if abs(ms[0] - ms[1]) == 0:
                continue
            for m in ms:
                per = f"2026-{int(m):02d}"
                raw = raw.drop(raw[(raw.stream == st) & (raw.period == per)].index)
                drops.append((per, st))
        L = ES.Ledger(raw.reset_index(drop=True), 2026)
        ch = IM.challengers(L)
        tv = truth.set_index(["period", "stream"]).value
        for _, r in ch.iterrows():
            if (r.period, r.stream) not in drops:
                continue
            t = float(tv[(r.period, r.stream)])
            stat = abs(r.statistical_estimate - t) / t if r.statistical_estimate == r.statistical_estimate else np.nan
            ml = abs(r.ml_estimate - t) / t if r.ml_estimate == r.ml_estimate else np.nan
            rows.append(dict(facility=j, period=r.period, stream=r.stream, stat_ape=stat, ml_ape=ml, gate=r.gate_passed,
                             gated_ape=(ml if r.gate_passed else stat), selected_model=r.ml_key or "none",
                             stat_backtest=r.statistical_backtest_error, ridge_backtest=r.ridge_error, forest_backtest=r.forest_error))
    df = pd.DataFrame(rows)
    both = df.dropna(subset=["stat_ape", "ml_ape"])
    g = both[both.gate]
    summ = dict(facilities=n, gaps=int(len(df)), gaps_with_both=int(len(both)),
                statistical_mape=float(both.stat_ape.mean()), ml_mape=float(both.ml_ape.mean()),
                gated_policy_mape=float(both.gated_ape.mean()), gate_pass_share=float(both.gate.mean()),
                where_gate_passed=dict(n=int(len(g)), statistical_mape=float(g.stat_ape.mean()) if len(g) else None,
                                       ml_mape=float(g.ml_ape.mean()) if len(g) else None),
                by_stream=both.groupby("stream")[["stat_ape", "ml_ape", "gated_ape"]].mean().round(4).reset_index().to_dict(orient="records"),
                backtest_error_mean=dict(statistical=float(pd.to_numeric(both.stat_backtest, errors="coerce").mean()),
                                         ridge=float(pd.to_numeric(both.ridge_backtest, errors="coerce").mean()),
                                         forest=float(pd.to_numeric(both.forest_backtest, errors="coerce").mean())),
                selected_model_counts={str(k): int(v) for k, v in both.selected_model.value_counts().items()},
                true_error_by_selected_model=both.groupby("selected_model")[["stat_ape", "ml_ape"]].mean().round(4).reset_index()
                .to_dict(orient="records"))
    return summ, df


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    res = dict(meta=dict(fast=FAST, generated_by="tools/evaluate_ai.py", data="synthetic only"))
    res["classification"] = classification()
    a, adf = anomaly(18 if FAST else 60)
    res["anomaly"] = a
    i, idf = imputation(6 if FAST else 30)
    res["imputation"] = i
    res["meta"]["seconds"] = round(time.time() - t0, 1)
    name = "ai_evaluation_fast.json" if FAST else "ai_evaluation.json"
    (OUT / name).write_text(json.dumps(res, indent=1, default=float))
    if not FAST:
        adf.to_csv(OUT / "anomaly_evaluation_cases.csv", index=False)
        idf.to_csv(OUT / "imputation_evaluation_cases.csv", index=False)
    print(json.dumps(res, indent=1, default=float))
