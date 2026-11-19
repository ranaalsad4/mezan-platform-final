"""App v3 AI layer: real techniques, honest labels, no invented numbers, no silent data changes."""
import importlib
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from carbon_iq.dataquality import estimate as ES
from carbon_iq.dataquality import synth as DS
from mezan_ai import anomaly as AN
from mezan_ai import classifier as C
from mezan_ai import explain as X
from mezan_ai import imputation as IM
from mezan_ai import insights as I
from mezan_ai.capabilities import CAPABILITIES
from mezan_platform import analysis as A
from mezan_platform import datasets as DSet

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def ledger():
    return ES.Ledger(DSet.demo_raw(), 2026, "PLANT-01")


@pytest.fixture(scope="module")
def run():
    return A.run(A.DEFAULTS.__class__(n=5000))


# ------------------------------------------------------------------ A: classification
def test_classifier_on_unlabelled_export_makes_no_wrong_assignment():
    raw, truth = DSet.unlabelled_raw()
    res = C.classify(raw)
    decided = res.method != "unresolved"
    assert (res.proposed_stream[decided] == truth[decided]).all()
    assert (res.proposed_stream == truth).mean() >= 0.95
    assert (res.method == "unresolved").sum() == 2 and (res.method == "ml").sum() > 0
    assert res.needs_review[res.method != "provided"].all()


def test_classifier_respects_units_and_keeps_provided_labels():
    df = pd.DataFrame(dict(description=["electricity bill", "Generator diesel", "anything"], unit=["L", "L", "MWh"],
                           stream=[None, None, "electricity"]))
    res = C.classify(df)
    assert res.proposed_stream[0] != "electricity"                  # a litre record can never be electricity
    assert res.proposed_stream[1] == "diesel_genset" and res.method[1] == "rule"
    assert res.method[2] == "provided"


def test_apply_mapping_sets_aside_unassigned_records_without_guessing():
    raw, truth = DSet.unlabelled_raw()
    res = C.classify(raw)
    mapped, aside = C.apply_mapping(raw, res.proposed_stream)
    assert len(aside) == 2 and len(mapped) == len(raw) - 2
    assert "stream" not in raw.columns                                # the original upload is untouched


# ------------------------------------------------------------------ B: anomaly detection
def test_isolation_forest_flags_the_injected_typo_and_never_changes_values(ledger):
    before = ledger.table.copy()
    r = AN.detect(ledger.cells, ledger.hist_cells, 2026)
    assert r["applied"] and "2026-05" in set(r["flags"].period)        # natural gas entered x10 in May
    assert r["technique"].startswith("Isolation Forest")
    assert ledger.table.equals(before)
    assert ((r["scores"].anomaly_score > 0) & (r["scores"].anomaly_score < 1)).all()


def test_isolation_forest_is_not_applied_on_too_few_months():
    raw = DSet.demo_raw()
    one_year = raw[raw.period.str.startswith("2026")]
    L = ES.Ledger(one_year, 2026, "PLANT-01")
    r = AN.detect(L.cells, L.hist_cells, 2026)
    assert not r["applied"] and "Rule-based checks only" in r["reason"]


# ------------------------------------------------------------------ C: ML estimate challengers
def test_ml_challenger_gate_and_adoption(ledger):
    import copy
    ch = IM.challengers(ledger)
    refused = ch[ch.statistical_method == "—"]
    assert len(refused) and not refused.gate_passed.any()              # ML never bypasses refusal rules
    failed = ch[~ch.gate_passed].iloc[0].to_dict()
    L = copy.deepcopy(ledger)
    with pytest.raises(ValueError):
        IM.adopt(L, failed)
    ok = ch[ch.gate_passed]
    if len(ok):
        row = ok.iloc[0].to_dict()
        IM.adopt(L, row)
        f = L.final().set_index(["period", "stream"])
        assert f.at[(row["period"], row["stream"]), "final_label"].startswith("estimated (ml_")
        assert f.at[(row["period"], row["stream"]), "final_value"] == pytest.approx(row["ml_estimate"])
        assert any("ML challenger adopted" in str(e["detail"]) for e in L.events)
    # nothing was replaced in the original ledger
    assert not ledger.table.method.astype(str).str.startswith("ml_").any()


# ------------------------------------------------------------------ D: explanation
def test_explanation_numbers_all_come_from_the_engine(run):
    ex = X.explain(run, A.value_of_information(run), A.switching(run), None, A.tornado(run)[1], use_llm=False)
    assert ex["source"] == "deterministic"
    allowed = X.allowed_numbers(ex["facts"], [])
    text = " ".join(s["text"] for s in ex["sections"])
    assert X.verify_numbers(text, allowed) == []


def test_language_model_output_with_invented_numbers_is_rejected(run):
    bad = lambda url, headers, json, timeout: {"choices": [{"message": {"content": "Fund A+B+C, NPV SAR 3.1 million, 97% certain."}}]}  # noqa: E731
    ex = X.explain(run, post=bad)
    assert ex["source"] == "deterministic" and "not in the engine outputs" in ex["rejected"]
    rec = run["recommended"]
    good_text = f"Fund {rec['portfolio']}. Expected NPV SAR {rec['e_npv'] / 1e6:.2f} million; carbon target met in {100 * rec['p_target']:.2f}% of futures."
    good = lambda url, headers, json, timeout: {"choices": [{"message": {"content": good_text}}]}  # noqa: E731
    ex = X.explain(run, post=good)
    assert ex["source"] == "llm" and ex["llm_text"] == good_text and "AI-generated" in ex["label"]


def test_no_language_model_needed(monkeypatch, run):
    for k in ("MEZAN_LLM_API_KEY", "MEZAN_LLM_MODEL"):
        monkeypatch.delenv(k, raising=False)
    ex = X.explain(run)
    assert ex["source"] == "deterministic" and ex["sections"]


# ------------------------------------------------------------------ insights
def test_insights_follow_the_results(ledger):
    from dataclasses import replace
    ok = I.decision_insights(A.run(replace(A.DEFAULTS, n=5000)))
    bad = I.decision_insights(A.run(replace(A.DEFAULTS, n=5000, budget=1e6)))
    assert any("Recommended portfolio" in i.text for i in ok)
    assert any("No portfolio passes" in i.text and i.severity == "action" for i in bad)
    d = I.data_insights(ledger, AN.detect(ledger.cells, ledger.hist_cells, 2026))
    n_pend = int((ledger.table.decision == "pending").sum())
    assert any(f"{n_pend} monthly record(s)" in i.text for i in d)
    assert {i.kind for i in d} <= {"Rule-based check", "ML flag", "Statistical estimate", "ML classification"}


# ------------------------------------------------------------------ honesty of claims
def test_capability_register_matches_code():
    for c in CAPABILITIES:
        assert (ROOT / c["module"]).exists()
        assert c["status"].startswith(("Implemented", "Partial", "Not implemented"))
        assert c["limits"]
    src = (ROOT / "mezan_ai" / "anomaly.py").read_text()
    assert "IsolationForest" in src
    src = (ROOT / "mezan_ai" / "classifier.py").read_text()
    assert "LogisticRegression" in src and "TfidfVectorizer" in src


def test_no_ai_overclaims_in_code_and_docs():
    pat = re.compile(r"AI[- ]powered|AI[- ]enabled|AI (calculates|computes|validates|predicts)|predicts emissions", re.I)
    files = [ROOT / "README.md", ROOT / "app.py"] + sorted((ROOT / "carbon_iq").glob("*.py")) + sorted((ROOT / "mezan_ai").glob("*.py")) \
        + sorted((ROOT / "mezan_ui").rglob("*.py"))
    for f in files:
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if pat.search(line):   # allowed only when negated, or when it names the real ML technique it refers to
                assert re.search(r"\bno\b|\bnot\b|never|does not|without|n't|Isolation Forest", line, re.I), f"{f.name}:{i}: {line.strip()}"


def test_no_carbon_iq_branding_in_the_interface():
    for f in [ROOT / "app.py"] + sorted((ROOT / "mezan_ui").rglob("*.py")) + sorted((ROOT / "mezan_platform").glob("*.py")):
        assert "CARBON IQ" not in f.read_text(encoding="utf-8").upper().replace("CARBON_IQ", ""), f.name
