"""Plain unit tests for the plumbing around the model (no model call needed).

Evals test the MODEL-DEPENDENT behavior; unit tests like these cover everything else.
Knowing which is which is part of this week's lesson."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import assistant  # noqa: E402


def test_retrieve_finds_parking_policy():
    policies = assistant.load_policies()
    hits = assistant.retrieve("How much is a parking permit?", policies)
    assert any("$120" in hit for hit in hits)


def test_retrieve_returns_nothing_for_unrelated_question():
    policies = assistant.load_policies()
    assert assistant.retrieve("zzz qqq xyzzy", policies) == []


def test_build_messages_marks_missing_context():
    messages = assistant.build_messages("anything", [], "system prompt")
    assert "(no matching policy found)" in messages[1]["content"]
    assert messages[0]["role"] == "system"


def test_load_prompt_unknown_version_raises():
    try:
        assistant.load_prompt("v999")
    except FileNotFoundError:
        return
    raise AssertionError("expected FileNotFoundError")
