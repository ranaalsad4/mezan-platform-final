"""Phase B: impact scorecard traces to the validated model outputs. (v3: the guided demo was removed from the app; the
Overview workspace showing the same numbers is tested in tests/test_app_v3.py.)"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
R = json.load(open(ROOT / "outputs" / "results.json"))
DS = {d["id"]: d for d in R["decision_scenarios"]}


def test_scorecard_values_trace_to_outputs():
    f = ROOT / "outputs" / "phase_b" / "scorecard_metrics.json"
    if not f.exists():
        pytest.skip("run python tools/build_phase_b.py first")
    rows = json.load(open(f))
    assert rows, "scorecard empty"
    for r in rows:
        assert r["traced_value"] == pytest.approx(r["value"], rel=1e-12, abs=1e-12), r["metric"]
