#!/usr/bin/env python3
"""Surface saturated v0.1 tasks — tasks where every model in the panel scores 4/4.

A saturated task contributes nothing to leaderboard signal: it can't separate a
weak model from a strong one. Retiring saturated tasks shrinks the corpus
without losing measurement power.

Output: a per-task report with category, difficulty, current pass rate, and
whether the task should be retired (default cutoff: 100% pass rate).

Usage:
  python scripts/scan_saturated.py
  python scripts/scan_saturated.py --threshold 0.92  # tasks where >=92% pass
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from grade import grade_one  # noqa: E402

OUTPUTS_DIR = ROOT / "outputs"
TASKS_DIR = ROOT / "tasks"


def load_current_checks() -> dict[str, dict]:
    by_id: dict[str, dict] = {}
    for path in TASKS_DIR.glob("*.jsonl"):
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            by_id[rec["task_id"]] = {
                "checks": rec["checks"],
                "category": rec.get("category", "?"),
                "subcategory": rec.get("subcategory", "?"),
                "difficulty": rec.get("difficulty", "?"),
                "tags": rec.get("tags", []),
            }
    return by_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=1.0,
                        help="Fraction of models that must pass (4/4) for task to be flagged. Default 1.0 (all).")
    parser.add_argument("--no-by-category", action="store_true")
    args = parser.parse_args()

    current = load_current_checks()
    output_files = sorted(p for p in OUTPUTS_DIR.glob("*.jsonl")
                          if not p.name.startswith("_"))
    n_models = len(output_files)
    print(f"Scanning {n_models} models against {len(current)} v0.1 tasks")
    print(f"Saturation threshold: {args.threshold*100:.0f}% of models scoring 4/4\n")

    # task_id -> count of models scoring 4/4
    pass_count: dict[str, int] = defaultdict(int)
    seen_in: dict[str, int] = defaultdict(int)
    for f in output_files:
        for line in open(f):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            tid = rec["task_id"]
            seen_in[tid] += 1
            # Re-grade with current checks (post-fix)
            if tid in current:
                rec_current = dict(rec)
                rec_current["checks"] = current[tid]["checks"]
                g = grade_one(rec_current)
            else:
                g = grade_one(rec)
            if g["score"] == 4:
                pass_count[tid] += 1

    saturated = []
    for tid, n_pass in pass_count.items():
        if seen_in[tid] == 0:
            continue
        rate = n_pass / seen_in[tid]
        if rate >= args.threshold:
            saturated.append((tid, n_pass, seen_in[tid], rate))

    saturated.sort(key=lambda x: (-x[3], x[0]))
    print(f"Saturated tasks: {len(saturated)} / {len(seen_in)} ({100*len(saturated)/len(seen_in):.1f}%)\n")

    if not args.no_by_category:
        by_cat: dict[str, int] = defaultdict(int)
        for tid, *_ in saturated:
            by_cat[current.get(tid, {}).get("category", "?")] += 1
        print("By category:")
        for cat in sorted(by_cat, key=lambda c: -by_cat[c]):
            print(f"  {cat:20s} {by_cat[cat]}")
        print()

    print(f"{'task_id':50s}  pass    rate  cat                 diff")
    for tid, n_pass, n, rate in saturated[:80]:
        info = current.get(tid, {})
        print(f"  {tid:48s}  {n_pass:2d}/{n}  {rate*100:5.1f}%  "
              f"{info.get('category', '?'):18s} {info.get('difficulty', '?')}")
    if len(saturated) > 80:
        print(f"\n  ... and {len(saturated) - 80} more")

    return 0


if __name__ == "__main__":
    sys.exit(main())
