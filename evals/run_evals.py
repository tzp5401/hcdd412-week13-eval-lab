"""Eval runner for the CampusConnect assistant.

Usage (from the repo root, with the mock LLM running on port 9000 or via docker compose):
    python evals/run_evals.py
    python evals/run_evals.py --prompt-version v2 --min-pass-rate 0.9

Reads evals/cases.jsonl, asks the assistant each question, applies each case's checks,
prints a table, writes eval-report.json, and EXITS NON-ZERO if the pass rate is below the
threshold. That exit code is what lets a CI pipeline block a bad prompt change.

Check types:
    contains         the answer must contain `value` (case-insensitive)
    not_contains     the answer must NOT contain `value` (case-insensitive)
    refuses          the answer must admit it does not have the information
    max_latency_ms   the call must finish within `value` milliseconds
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

import assistant  # noqa: E402

REFUSAL_PHRASES = ("don't have that information", "do not have that information")


def check_one(check, result):
    """Return (passed, reason) for a single check against one assistant result."""
    kind = check["type"]
    answer = result["answer"].lower()
    if kind == "contains":
        ok = check["value"].lower() in answer
        return ok, f"expected to contain '{check['value']}'"
    if kind == "not_contains":
        ok = check["value"].lower() not in answer
        return ok, f"expected NOT to contain '{check['value']}'"
    if kind == "refuses":
        ok = any(phrase in answer for phrase in REFUSAL_PHRASES)
        return ok, "expected the assistant to say it does not have that information"
    if kind == "max_latency_ms":
        ok = result["latency_ms"] <= check["value"]
        return ok, f"expected latency <= {check['value']} ms (was {result['latency_ms']})"
    raise ValueError(f"Unknown check type: {kind}")


def load_cases(path):
    cases = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def run_case(case, prompt_version):
    result = assistant.ask(case["question"], prompt_version=prompt_version)
    failures = []
    for check in case["checks"]:
        passed, reason = check_one(check, result)
        if not passed:
            failures.append(reason)
    return {
        "id": case["id"],
        "question": case["question"],
        "answer": result["answer"],
        "passed": not failures,
        "failures": failures,
        "latency_ms": result["latency_ms"],
        "total_tokens": result["total_tokens"],
    }


def summarize(results, prompt_version):
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    return {
        "prompt_version": prompt_version,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total_cases": total,
        "passed": passed,
        "pass_rate": round(passed / total, 3) if total else 0.0,
        "avg_latency_ms": round(sum(r["latency_ms"] for r in results) / total, 1) if total else 0.0,
        "total_tokens": sum(r["total_tokens"] for r in results),
        "results": results,
    }


def regression_gate(baseline, current):
    """PART 3 OF THE LAB -- YOU IMPLEMENT THIS.

    Compare two report dicts (the saved baseline and the current run) and return a list of
    human-readable problems. Return an empty list when the change is safe to ship.
    Suggested rules to consider (pick and justify your own):
      - any case that PASSED in the baseline but FAILS now is a regression
      - pass rate must not drop
      - average latency or total tokens must not grow by more than some percentage
    """
    return []  # TODO: replace with your gate logic


def main():
    parser = argparse.ArgumentParser(description="Run the CampusConnect evals.")
    parser.add_argument("--cases", default=str(ROOT / "evals" / "cases.jsonl"))
    parser.add_argument("--prompt-version", default=assistant.PROMPT_VERSION)
    parser.add_argument("--min-pass-rate", type=float, default=0.8)
    parser.add_argument("--report", default=str(ROOT / "eval-report.json"))
    parser.add_argument("--baseline", help="path to a saved eval report to compare against")
    args = parser.parse_args()

    cases = load_cases(args.cases)
    started = time.perf_counter()
    results = [run_case(case, args.prompt_version) for case in cases]
    report = summarize(results, args.prompt_version)

    print(f"Prompt version: {report['prompt_version']}   Cases: {report['total_cases']}")
    for r in results:
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"  [{mark}] {r['id']}")
        for failure in r["failures"]:
            print(f"         - {failure}")
            print(f"         - answer was: {r['answer']}")
    print(f"Pass rate: {report['pass_rate']:.0%} ({report['passed']}/{report['total_cases']})  "
          f"avg latency: {report['avg_latency_ms']} ms  tokens: {report['total_tokens']}  "
          f"({time.perf_counter() - started:.1f}s total)")

    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")

    problems = []
    if report["pass_rate"] < args.min_pass_rate:
        problems.append(f"pass rate {report['pass_rate']:.0%} is below the required "
                        f"{args.min_pass_rate:.0%}")
    if args.baseline:
        baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        problems.extend(regression_gate(baseline, report))

    if problems:
        print("EVAL GATE: FAILED")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("EVAL GATE: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
