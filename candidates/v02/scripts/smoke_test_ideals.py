#!/usr/bin/env python3
"""Smoke test: verify each candidate task's ideal_output passes its own checks.

If a task's `ideal_output` doesn't score 4/4 against its own checks, the checks
are internally inconsistent — typically a regex typo, an over-strict must_contain
that doesn't actually appear in the ideal, or a forbidden token that the ideal
accidentally uses.

Run before any model evaluation. Anything less than 4/4 is a bug in the task,
not in the model.

Usage:
  python smoke_test_ideals.py
  python smoke_test_ideals.py --file candidates_002f.jsonl  # one file only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Hook into the project's grader so behavior is identical to production grading
SCRIPT_DIR = Path(__file__).resolve().parent
NEXTBENCH_ROOT = SCRIPT_DIR.parent.parent.parent
sys.path.insert(0, str(NEXTBENCH_ROOT))
from grade import grade_one  # noqa: E402

CANDIDATES_DIR = SCRIPT_DIR.parent


def smoke_test(jsonl_path: Path) -> tuple[int, list[tuple[dict, dict]]]:
    """Return (num_records, list_of_failures). Failures are (record, grade) pairs."""
    failures: list[tuple[dict, dict]] = []
    records = [json.loads(line) for line in open(jsonl_path) if line.strip()]
    for rec in records:
        grader_record = {
            "task_id": rec["task_id"],
            "category": rec.get("category", "?"),
            "subcategory": rec.get("subcategory", ""),
            "difficulty": rec.get("difficulty", "?"),
            "tags": rec.get("tags", []),
            "output": rec["ideal_output"],
            "checks": rec["checks"],
        }
        grade = grade_one(grader_record)
        if grade["score"] < 4:
            failures.append((rec, grade))
    return len(records), failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Test one specific candidates file")
    args = parser.parse_args()

    if args.file:
        files = [CANDIDATES_DIR / args.file]
    else:
        files = sorted(CANDIDATES_DIR.glob("candidates*.jsonl"))

    total = 0
    all_failures: list[tuple[str, dict, dict]] = []
    for f in files:
        n, failures = smoke_test(f)
        total += n
        for rec, grade in failures:
            all_failures.append((f.name, rec, grade))

    print(f"Tested {total} tasks across {len(files)} file(s)")
    if not all_failures:
        print("ALL PASSED — every ideal_output scores 4/4 against its own checks.")
        return 0

    print(f"\n{len(all_failures)} FAILURES:\n")
    for fname, rec, grade in all_failures:
        print(f"  [{grade['score']}/4] {grade['task_id']} ({fname})")
        if grade["missing_patterns"]:
            print(f"    missing must_contain: {grade['missing_patterns']}")
        if grade["found_forbidden"]:
            print(f"    found forbidden:      {grade['found_forbidden']}")
        if grade["missed_regexes"]:
            print(f"    missed regex:         {grade['missed_regexes']}")
        if not grade["length_ok"]:
            static = rec["checks"]["static"]
            print(
                f"    lines: {grade['n_lines']} "
                f"(need {static.get('min_lines', 0)}-{static.get('max_lines', 9999)})"
            )
    return 1


if __name__ == "__main__":
    sys.exit(main())
