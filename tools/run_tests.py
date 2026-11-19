"""Run the full regression suite and record the result (counts, skipped tests with reasons, environment).

    python tools/run_tests.py          -> outputs/test_summary.json
"""
import json
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    xml = ROOT / "outputs" / "junit.xml"
    xml.parent.mkdir(exist_ok=True)
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider", f"--junitxml={xml}", "tests"],
                       cwd=ROOT, capture_output=True, text=True)
    print(r.stdout[-3000:])
    suite = ET.parse(xml).getroot()
    suite = suite if suite.tag == "testsuite" else suite.find("testsuite")
    cases, skipped, failed = [], [], []
    for tc in suite.iter("testcase"):
        name = f"{tc.get('classname')}::{tc.get('name')}"
        cases.append(name)
        s = tc.find("skipped")
        if s is not None:
            skipped.append({"test": name, "reason": s.get("message", "")})
        if tc.find("failure") is not None or tc.find("error") is not None:
            failed.append(name)
    versions = {}
    for mod in ("numpy", "scipy", "pandas", "openpyxl", "matplotlib", "plotly", "streamlit", "pytest"):
        try:
            versions[mod] = __import__(mod).__version__
        except Exception:
            versions[mod] = None
    rc = {}
    p = ROOT / "outputs" / "excel_recalc.json"
    if p.exists():
        rc = json.loads(p.read_text())
    out = {"total": len(cases), "passed": len(cases) - len(skipped) - len(failed), "failed": len(failed), "skipped": len(skipped),
           "failed_tests": failed, "skipped_tests": skipped, "python": platform.python_version(), "platform": platform.platform(),
           "versions": versions, "excel_formulas": rc.get("total_formulas"), "excel_errors": rc.get("total_errors"),
           "excel_recalc": rc.get("status"), "line": r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""}
    (ROOT / "outputs" / "test_summary.json").write_text(json.dumps(out, indent=1))
    xml.unlink()
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
