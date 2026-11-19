"""AI capability A - record classification into Mezan's activity streams.

Technique (hybrid, in this order):
  1. Provided label   a record whose `stream` is already a valid schema stream is kept (no AI involved).
  2. Semantic rules   deterministic keyword lexicon (English + Arabic) restricted to streams whose canonical unit
                      matches the record's unit (quality.UNITS). A unique best keyword match, or a unit that admits only
                      one stream, decides.
  3. ML text model    TF-IDF character n-grams (2-5, word-boundary) + multinomial logistic regression (scikit-learn),
                      trained on the curated SYNTHETIC corpus mezan_ai/data/record_descriptions.csv. Used only when the
                      rules cannot decide; its probabilities are restricted to unit-compatible streams and renormalised.
                      A proposal needs probability >= ML_MIN_PROB, otherwise the record is left for the reviewer.
Every non-provided result is a PROPOSAL: the reviewer accepts or edits it before the record enters the data-quality
ledger. Model probabilities are not calibrated confidence levels. The raw upload is never modified.
"""
from __future__ import annotations

import functools
import re
from pathlib import Path

import numpy as np
import pandas as pd

from carbon_iq.dataquality.quality import STREAMS, UNITS

CORPUS = Path(__file__).resolve().parent / "data" / "record_descriptions.csv"
ML_MIN_PROB = 0.60
TEXT_COLS = ("description", "stream", "source", "note", "account", "meter")

LEXICON = {
    "electricity": ["electric", "electricity", "power", "grid", "sec ", "saudi electricity", "kwh", "mwh", "incomer", "mdb",
                    "substation", "كهرباء", "الكهربائية"],
    "natural_gas": ["natural gas", "gas", "methane", "burner", "furnace", "aramco", "pipeline", "ng ", "غاز"],
    "diesel_forklift": ["forklift", "fork lift", "lift truck", "mhe", "material handling", "fleet", "fuel card", "loader",
                        "yard vehicle", "الرافعات", "المناولة"],
    "diesel_genset": ["generator", "genset", "dg set", "dg-", "standby", "emergency power", "backup power", "مولد", "المولد"],
    "production": ["production", "output", "finished", "shipped", "despatch", "dispatch", "good output", "الإنتاج", "انتاج"],
    "operating_hours": ["operating hours", "run hours", "running time", "uptime", "machine hours", "operating time",
                        "ساعات التشغيل", "ساعات تشغيل"],
    "steel_purchased": ["steel", "coil", "plate", "rebar", "billet", "raw material", "goods receipt", "purchase", "الحديد", "الصلب"],
    "freight": ["freight", "haulage", "trucking", "logistics", "transport", "tonne-km", "tkm", "t-km", "carrier", "نقل", "شحن"],
}
METHOD_LABELS = {"provided": "Provided label (schema)", "rule": "Rule-based (keywords + unit)",
                 "ml": "ML text classifier (TF-IDF + logistic regression)", "unresolved": "Needs reviewer"}


def _canon_unit(u):
    if u is None or (isinstance(u, float) and np.isnan(u)):
        return None
    return UNITS.get(str(u).strip().lower(), (None,))[0]


def compatible_streams(unit):
    cu = _canon_unit(unit)
    if cu is None:
        return list(STREAMS)
    return [s for s, c in STREAMS.items() if c["unit"] == cu]


def _text(row):
    parts = []
    for c in TEXT_COLS:
        if c in row and isinstance(row[c], str) and row[c].strip() and not (c == "stream" and row[c] in STREAMS):
            parts.append(row[c].strip())
    return " ".join(parts)


@functools.lru_cache(maxsize=1)
def model():
    """Train the text classifier on the curated corpus (a few hundred rows; well under a second)."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    df = pd.read_csv(CORPUS)
    pipe = make_pipeline(TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), lowercase=True, sublinear_tf=True, min_df=1),
                         LogisticRegression(max_iter=2000, C=4.0))
    pipe.fit(df.description, df.stream)
    return pipe


def corpus_info():
    df = pd.read_csv(CORPUS)
    return dict(rows=len(df), templates=int(df.template.nunique()), streams=int(df.stream.nunique()), path=str(CORPUS.name))


def _rule(text, cands):
    t = " " + text.lower() + " "
    hits = {s: sum(1 for kw in LEXICON[s] if kw in t) for s in cands}
    best = max(hits.values()) if hits else 0
    if best > 0:
        top = [s for s, h in hits.items() if h == best]
        if len(top) == 1:
            kws = [kw.strip() for kw in LEXICON[top[0]] if kw in t]
            return top[0], f"keywords: {', '.join(kws)}"
    if len(cands) == 1:
        return cands[0], "unit admits only this stream"
    return None, (f"ambiguous keywords ({', '.join(s for s, h in hits.items() if h == best)})" if best > 0 else "no keyword match")


def classify(df: pd.DataFrame) -> pd.DataFrame:
    """One proposal per record. Columns: proposed_stream, method, method_label, ml_probability, evidence, needs_review."""
    out = []
    pipe = None
    for _, r in df.iterrows():
        row = r.to_dict()
        given = row.get("stream")
        if isinstance(given, str) and given in STREAMS:
            out.append(dict(proposed_stream=given, method="provided", ml_probability=np.nan, evidence="valid schema stream",
                            needs_review=False))
            continue
        cands = compatible_streams(row.get("unit"))
        text = _text(row)
        if not text:
            out.append(dict(proposed_stream=cands[0] if len(cands) == 1 else "", method="rule" if len(cands) == 1 else "unresolved",
                            ml_probability=np.nan, evidence="no description; unit only" if len(cands) == 1 else "no description",
                            needs_review=True))
            continue
        s, why = _rule(text, cands)
        if s:
            out.append(dict(proposed_stream=s, method="rule", ml_probability=np.nan, evidence=why, needs_review=True))
            continue
        pipe = pipe or model()
        proba = pipe.predict_proba([text])[0]
        classes = list(pipe.classes_)
        sub = np.array([proba[classes.index(c)] if c in classes else 0.0 for c in cands])
        if sub.sum() <= 0:
            out.append(dict(proposed_stream="", method="unresolved", ml_probability=np.nan, evidence=why, needs_review=True))
            continue
        sub = sub / sub.sum()
        j = int(np.argmax(sub))
        order = np.argsort(-sub)
        ev = "; ".join(f"{cands[i]} {sub[i]:.2f}" for i in order[:2]) + f" (rules: {why})"
        if sub[j] >= ML_MIN_PROB:
            out.append(dict(proposed_stream=cands[j], method="ml", ml_probability=float(sub[j]), evidence=ev, needs_review=True))
        else:
            out.append(dict(proposed_stream="", method="unresolved", ml_probability=float(sub[j]), evidence=ev, needs_review=True))
    res = pd.DataFrame(out, index=df.index)
    res["method_label"] = res.method.map(METHOD_LABELS)
    return res


def apply_mapping(raw: pd.DataFrame, streams: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Copy of `raw` with the reviewed stream labels. Records without a valid stream are set aside (they are NOT
    guessed): their months then count as missing in the data-quality ledger. Returns (mapped, set_aside)."""
    mapped = raw.copy()
    mapped["stream"] = streams.reindex(raw.index).fillna("")
    ok = mapped["stream"].isin(list(STREAMS))
    return mapped[ok].copy(), mapped[~ok].copy()


_PERIOD = re.compile(r"^\d{4}-\d{2}$")


def needs_classification(raw: pd.DataFrame) -> bool:
    return "stream" not in raw.columns or not raw["stream"].isin(list(STREAMS)).all()
