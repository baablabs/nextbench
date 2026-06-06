#!/usr/bin/env python3
"""NextBench grader — deterministic scoring of model output against task checks.

Reads one or more output JSONL files (produced by run_eval.py) and applies the
static-check rubric defined in each task's checks.static block:

    1. PATTERN_HIT   — every must_contain substring is present (case-insensitive)
    2. NO_FORBIDDEN  — no must_not_contain substring is present
    3. REGEX_HIT     — every must_match_regex pattern matches
    4. LENGTH_OK     — output line count is within [min_lines, max_lines]

Score per task: 0-4. Total possible: 4 × N_tasks.
checks.execution and checks.judge are intentionally ignored in v0.1.

Usage:
  python grade.py --input outputs/baab-next-1b-pretrain-2k.jsonl
  python grade.py --input <a.jsonl> <b.jsonl> --compare
  python grade.py --input outputs/*.jsonl --detail --top-n 30
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


# Length rule (preserved from battle grader):
#   - For prompts with very tight max_lines (<= 6), enforce both min and max
#     (these are EOT-discipline tests — short utility functions).
#   - For all other prompts, only enforce min (we don't penalise verbose tails
#     here; the stop-signal SFT mix targets that separately).
TIGHT_MAX_THRESHOLD = 6


def grade_one(record: dict) -> dict:
    """Score a single (task + output) record. Returns flat dict of signals + score."""
    output = record.get("output", "") or ""
    checks = record.get("checks") or {}
    static = checks.get("static") or {}

    must_contain = static.get("must_contain") or []
    must_not_contain = static.get("must_not_contain") or []
    must_match_regex = static.get("must_match_regex") or []
    min_lines = static.get("min_lines", 0)
    max_lines = static.get("max_lines", 9999)

    out_lower = output.lower()

    missing_patterns = [p for p in must_contain if p.lower() not in out_lower]
    pattern_hit = 1 if not missing_patterns else 0

    found_forbidden = [p for p in must_not_contain if p.lower() in out_lower]
    no_forbidden = 1 if not found_forbidden else 0

    missed_regexes = [r for r in must_match_regex if not re.search(r, output, re.IGNORECASE | re.MULTILINE)]
    regex_hit = 1 if not missed_regexes else 0

    n_lines = output.count("\n") + 1 if output.strip() else 0
    if max_lines <= TIGHT_MAX_THRESHOLD:
        length_ok = 1 if min_lines <= n_lines <= max_lines else 0
    else:
        length_ok = 1 if n_lines >= min_lines else 0

    score = pattern_hit + no_forbidden + regex_hit + length_ok
    return {
        "task_id": record.get("task_id") or record.get("id", "?"),
        "category": record.get("category", "?"),
        "subcategory": record.get("subcategory", ""),
        "difficulty": record.get("difficulty", "?"),
        "tags": record.get("tags", []),
        "score": score,
        "max": 4,
        "pattern_hit": pattern_hit,
        "no_forbidden": no_forbidden,
        "regex_hit": regex_hit,
        "length_ok": length_ok,
        "missing_patterns": missing_patterns,
        "found_forbidden": found_forbidden,
        "missed_regexes": missed_regexes,
        "n_lines": n_lines,
    }


def grade_file(path: Path) -> tuple[list[dict], list[dict]]:
    records = [json.loads(line) for line in open(path)]
    return records, [grade_one(r) for r in records]


def _aggregate(grades: list[dict], key_fn) -> dict[str, tuple[int, int]]:
    bucket: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for g in grades:
        for k in key_fn(g):
            bucket[k][0] += g["score"]
            bucket[k][1] += g["max"]
    return {k: (s, m) for k, (s, m) in bucket.items()}


def summary(grades: list[dict], label: str = "") -> dict:
    total = sum(g["score"] for g in grades)
    max_total = sum(g["max"] for g in grades)
    pct = 100 * total / max_total if max_total else 0
    print(f"\n{'='*64}")
    print(f"{label}")
    print(f"{'='*64}")
    print(f"OVERALL: {total}/{max_total} = {pct:.2f}%")

    by_cat = _aggregate(grades, lambda g: [g["category"]])
    print(f"\nBy category:")
    for cat in sorted(by_cat, key=lambda c: -by_cat[c][0] / max(1, by_cat[c][1])):
        s, m = by_cat[cat]
        print(f"  {s:4d}/{m:4d}  {100*s/m:5.1f}%   {cat}")

    by_diff = _aggregate(grades, lambda g: [g["difficulty"]])
    print(f"\nBy difficulty:")
    for d in ("trivial", "mid", "hard"):
        if d in by_diff:
            s, m = by_diff[d]
            print(f"  {s:4d}/{m:4d}  {100*s/m:5.1f}%   {d}")

    by_tag = _aggregate(grades, lambda g: g["tags"])
    print(f"\nBy tag (top 10 by coverage):")
    top_tags = sorted(by_tag.items(), key=lambda kv: -kv[1][1])[:10]
    for tag, (s, m) in top_tags:
        print(f"  {s:4d}/{m:4d}  {100*s/m:5.1f}%   {tag}")

    print(f"\nSignal pass rates:")
    for k in ("pattern_hit", "no_forbidden", "regex_hit", "length_ok"):
        n = sum(g[k] for g in grades)
        total_n = len(grades)
        print(f"  {k:15s}  {n:4d}/{total_n}  {100*n/total_n:5.1f}%")

    return {"total": total, "max": max_total, "pct": pct, "label": label}


def detail_misses(records: list[dict], grades: list[dict], top_n: int = 20):
    paired = sorted(zip(records, grades), key=lambda p: (p[1]["score"], p[1]["category"]))
    print(f"\nWorst {top_n} tasks:")
    for record, grade in paired[:top_n]:
        reasons = []
        if grade["missing_patterns"]:
            reasons.append(f"missing={grade['missing_patterns'][:3]}")
        if grade["found_forbidden"]:
            reasons.append(f"forbidden={grade['found_forbidden'][:2]}")
        if grade["missed_regexes"]:
            reasons.append(f"missed-regex={grade['missed_regexes'][:2]}")
        if not grade["length_ok"]:
            static = (record.get("checks") or {}).get("static") or {}
            reasons.append(f"lines={grade['n_lines']} (need {static.get('min_lines', 0)}-{static.get('max_lines', 9999)})")
        print(f"  [{grade['score']}/4] {grade['task_id']:50s} {' | '.join(reasons)[:140]}")


def compare(all_results: list[tuple[str, list[dict], int, int, float]]):
    print(f"\n{'='*64}")
    print("COMPARE")
    print(f"{'='*64}")
    cats = sorted({g["category"] for _, grades, *_ in all_results for g in grades})
    header = f"{'category':22s}  " + "  ".join(f"{lab[:14]:>14s}" for lab, *_ in all_results)
    print(header)
    for cat in cats:
        row = [cat]
        for label, grades, *_ in all_results:
            s = sum(g["score"] for g in grades if g["category"] == cat)
            m = sum(g["max"] for g in grades if g["category"] == cat)
            row.append(f"{s}/{m} ({100*s/m:.0f}%)" if m else "n/a")
        print(f"{row[0]:22s}  " + "  ".join(f"{r:>14s}" for r in row[1:]))
    print(f"\n{'TOTAL':22s}  " + "  ".join(f"{t}/{m} ({p:.1f}%)".rjust(14) for _, _, t, m, p in all_results))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", nargs="+", required=True, help="One or more output JSONL files")
    parser.add_argument("--compare", action="store_true", help="Side-by-side comparison if multiple inputs")
    parser.add_argument("--detail", action="store_true", help="Print worst tasks per file")
    parser.add_argument("--top-n", type=int, default=20)
    args = parser.parse_args()

    all_results: list[tuple[str, list[dict], int, int, float]] = []
    for path_str in args.input:
        path = Path(path_str)
        label = path.stem
        records, grades = grade_file(path)
        s = summary(grades, label=label)
        if args.detail:
            detail_misses(records, grades, top_n=args.top_n)
        all_results.append((label, grades, s["total"], s["max"], s["pct"]))

    if args.compare and len(all_results) > 1:
        compare(all_results)


if __name__ == "__main__":
    main()
