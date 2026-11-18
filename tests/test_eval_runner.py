"""Tests for the eval harness itself: a gate you cannot trust is worse than no gate."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evals"))

import run_evals  # noqa: E402


def result(answer, latency=50.0):
    return {"answer": answer, "latency_ms": latency, "total_tokens": 10}


def test_contains_is_case_insensitive():
    ok, _ = run_evals.check_one({"type": "contains", "value": "6 pm"}, result("Open until 6 PM."))
    assert ok


def test_not_contains_fails_when_present():
    ok, _ = run_evals.check_one({"type": "not_contains", "value": "full refund"},
                                result("You get a full refund."))
    assert not ok


def test_refuses_recognizes_refusal():
    ok, _ = run_evals.check_one({"type": "refuses"},
                                result("I don't have that information. Please ask."))
    assert ok


def test_refuses_fails_on_confident_answer():
    ok, _ = run_evals.check_one({"type": "refuses"}, result("Absolutely! That is available."))
    assert not ok


def test_latency_check():
    ok, _ = run_evals.check_one({"type": "max_latency_ms", "value": 100}, result("x", 250.0))
    assert not ok


def test_unknown_check_type_raises():
    with pytest.raises(ValueError):
        run_evals.check_one({"type": "vibes"}, result("x"))


def test_summarize_computes_pass_rate():
    rows = [{"passed": True, "latency_ms": 10, "total_tokens": 5},
            {"passed": False, "latency_ms": 30, "total_tokens": 7}]
    report = run_evals.summarize(rows, "v1")
    assert report["pass_rate"] == 0.5
    assert report["avg_latency_ms"] == 20.0
    assert report["total_tokens"] == 12
