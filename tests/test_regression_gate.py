"""Part 3 of the lab: remove the skip marker once you have implemented regression_gate()
in evals/run_evals.py, then add at least two more tests of your own."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evals"))

import run_evals  # noqa: E402


@pytest.mark.skip(reason="Part 3: implement regression_gate() first")
def test_gate_flags_case_that_used_to_pass():
    baseline = {"results": [{"id": "a", "passed": True}], "pass_rate": 1.0}
    current = {"results": [{"id": "a", "passed": False}], "pass_rate": 0.0}
    assert run_evals.regression_gate(baseline, current)  # non-empty list = problems found


@pytest.mark.skip(reason="Part 3: implement regression_gate() first")
def test_gate_allows_identical_runs():
    report = {"results": [{"id": "a", "passed": True}], "pass_rate": 1.0}
    assert run_evals.regression_gate(report, report) == []
