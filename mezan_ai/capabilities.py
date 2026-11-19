"""Register of AI/ML capabilities with their real technique and implementation status (shown in the interface and the
report; tested by tests/test_ai.py so the claims cannot drift from the code)."""

CAPABILITIES = [
    dict(id="A", name="Record classification", module="mezan_ai/classifier.py",
         technique="Hybrid: deterministic keyword + unit rules first; TF-IDF character n-gram + logistic regression text "
                   "classifier (scikit-learn) only when rules cannot decide",
         status="Implemented", output_label="Rule-based classification / ML classification (proposal)",
         evidence="outputs/ai/ai_evaluation.json → classification (grouped cross-validation by template; demo export)",
         limits="Trained on a curated synthetic corpus of 576 descriptions; not yet evaluated on real plant exports. "
                "Model probabilities are not calibrated. Every proposal needs reviewer confirmation."),
    dict(id="B", name="Anomaly detection", module="mezan_ai/anomaly.py",
         technique="Isolation Forest (scikit-learn) on month-level intensity features, alongside the existing robust z-score rules",
         status="Implemented (advisory)", output_label="ML flag",
         evidence="outputs/ai/ai_evaluation.json → anomaly (60 synthetic facilities, injected anomalies)",
         limits="Needs at least 18 months with complete features; otherwise not applied (disclosed). Scores are isolation "
                "scores, not probabilities. Flags never change a value."),
    dict(id="C", name="Missing-data assistance", module="mezan_ai/imputation.py",
         technique="Ridge regression and random forest challengers vs the existing statistical estimator, same leave-one-out "
                   "back-test; evidence gate (ML error < 90% of statistical) + reviewer choice",
         status="Implemented (gated, reviewer opt-in)", output_label="Statistical estimate / ML estimate (adopted by reviewer)",
         evidence="outputs/ai/ai_evaluation.json → imputation (30 synthetic facilities, known truth)",
         limits="Never bypasses refusal rules; never replaces an estimate automatically; evidence so far is synthetic only. "
                "Choosing the better of two challengers on the same back-test is mildly optimistic (the 90% gate offsets part of it)."),
    dict(id="D", name="Decision explanation", module="mezan_ai/explain.py",
         technique="Deterministic narrative generator from engine outputs; optional language model (OpenAI-compatible or "
                   "Anthropic API via environment variables) with automatic number verification",
         status="Implemented (language model optional)", output_label="Rule-based narrative / AI-generated explanation",
         evidence="tests/test_ai.py (number-verification guard rejects invented figures)",
         limits="Language model is off unless configured; any output with a number not in the engine outputs is rejected."),
    dict(id="E", name="Mezan Intelligence findings", module="mezan_ai/insights.py",
         technique="Rule-based selection and wording of findings from current engine, ledger, ML-flag and classifier results",
         status="Implemented", output_label="Insight (with source label)",
         evidence="tests/test_ai.py (insights change when results change)",
         limits="Selects and words findings; does not compute any quantity."),
]
NOT_AI = ("Emissions accounting, NPV/IRR/payback/MAC, Monte Carlo simulation, portfolio optimisation, chance constraints, "
          "sensitivity, switching, value of information and investment timing are computed by the calculation engine "
          "(carbon_iq, model v1.3). No AI component calculates or validates these results.")
