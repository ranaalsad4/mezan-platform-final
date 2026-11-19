"""Mezan AI assistance layer.

Four capabilities, each labelled with the technique it really uses (see CAPABILITIES and docs/AI_ML_METHODOLOGY.md):
  A  record classification   hybrid: deterministic semantic rules (keywords + unit dimension) first; a TF-IDF +
                              logistic-regression text classifier (scikit-learn) proposes a stream only when the rules
                              cannot decide; every proposal needs reviewer confirmation
  B  anomaly detection       Isolation Forest (scikit-learn) on month-level energy-intensity features, alongside the
                              existing rule-based robust z-score checks; advisory flags with reviewer accept/dismiss
  C  missing-data assistance machine-learning challengers (ridge regression, random forest) back-tested against the
                              existing statistical estimator with the same leave-one-out protocol; adopted for a cell
                              only when the evidence gate passes AND a reviewer chooses it
  D  decision explanation    narrative grounded in calculation-engine outputs; deterministic template by default,
                              optional language model (environment variables) whose numbers are verified against the
                              engine's outputs before display

AI never produces emissions, NPV, probabilities or any other quantitative result: those come from carbon_iq.
"""
