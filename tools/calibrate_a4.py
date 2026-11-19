"""Fit the A4 interval calibration on SYNTHETIC calibration facilities (never on the test sets).

    python tools/calibrate_a4.py        -> outputs/a4/calibration.json

Monthly: split-conformal factor on |error / sd| (never below 1). Annual: smallest common within-stream error
correlation rho reaching 95% coverage. The values are then written as CAL_MONTHLY and RHO_ANNUAL in
carbon_iq/dataquality/estimate.py (a test checks that the two agree). Held-out evaluation: tools/run_a4.py.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from carbon_iq.dataquality import validate as VA  # noqa: E402

N_CAL, SEED_CAL = 100, 5501


def main():
    cells, ann = VA.study(N_CAL, seed=SEED_CAL, scenarios=VA.CAL_SCENARIOS, variant="base", workers=2)
    res = VA.calibrate(cells, ann)
    res.update(seed=SEED_CAL, facilities=N_CAL, variant="base", scenarios=list(VA.CAL_SCENARIOS),
               note="SYNTHETIC calibration set; factors are generator-specific and must be re-fitted on real data")
    out = HERE / "outputs" / "a4"; out.mkdir(parents=True, exist_ok=True)
    json.dump(res, open(out / "calibration.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
