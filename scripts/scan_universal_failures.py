#!/usr/bin/env python3
"""Scan the existing model outputs for tasks where every model fails the same check.

If a `must_contain` token is missing in every single model's output for a given
task, that token is almost certainly buggy — either it appears only in the prompt
(so the model wouldn't naturally re-emit it), or the canonical "correct" answer
doesn't actually contain it. Same logic applies inverted to `must_not_contain`
(token forbidden but unavoidable) and `must_match_regex` (regex that no real
output can match).

This is the v0.1 equivalent of the candidates/v02 self-grading smoke test —
we can't feed an ideal_output (v0.1 tasks don't have one), but we have 10
real model outputs per task, which is even better signal.

Usage:
  python scan_universal_failures.py
  python scan_universal_failures.py --min-models 8  # at least 8/10 must fail
  python scan_universal_failures.py --verbose       # show every flagged task in detail
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-models", type=int, default=0,
                        help="Min number of models that must fail a check to flag it. "
                             "0 = flag only if ALL models fail (strictest, default).")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--outputs-dir", default=str(OUTPUTS_DIR))
    args = parser.parse_args()

    outputs_dir = Path(args.outputs_dir)
    output_files = sorted(p for p in outputs_dir.glob("*.jsonl")
                          if not p.name.startswith("_"))
    if not output_files:
        sys.exit(f"No model outputs found in {outputs_dir}")

    print(f"Scanning {len(output_files)} model outputs:")
    for f in output_files:
        print(f"  {f.name}")
    n_models = len(output_files)
    threshold = args.min_models if args.min_models > 0 else n_models

    # Per task_id: list[set[token]] across models
    missing_per_task: dict[str, list[set[str]]] = defaultdict(list)
    forbidden_per_task: dict[str, list[set[str]]] = defaultdict(list)
    regex_per_task: dict[str, list[set[str]]] = defaultdict(list)
    task_seen_in: dict[str, int] = defaultdict(int)

    for f in output_files:
        for line in open(f):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            g = grade_one(rec)
            tid = g["task_id"]
            missing_per_task[tid].append(set(g["missing_patterns"]))
            forbidden_per_task[tid].append(set(g["found_forbidden"]))
            regex_per_task[tid].append(set(g["missed_regexes"]))
            task_seen_in[tid] += 1

    # Aggregate: for each task, count how many models missed each token
    print(f"\nTotal unique tasks seen across outputs: {len(task_seen_in)}")
    print(f"Flagging tokens missed by >= {threshold}/{n_models} models\n")

    suspects: list[tuple[str, set[str], set[str], set[str]]] = []
    for tid in sorted(missing_per_task):
        # token -> num models that missed it
        miss_count: dict[str, int] = defaultdict(int)
        for s in missing_per_task[tid]:
            for tok in s:
                miss_count[tok] += 1
        forb_count: dict[str, int] = defaultdict(int)
        for s in forbidden_per_task[tid]:
            for tok in s:
                forb_count[tok] += 1
        rgx_count: dict[str, int] = defaultdict(int)
        for s in regex_per_task[tid]:
            for tok in s:
                rgx_count[tok] += 1

        universally_missing = {t for t, c in miss_count.items() if c >= threshold}
        universally_forbidden = {t for t, c in forb_count.items() if c >= threshold}
        universally_regex_missed = {t for t, c in rgx_count.items() if c >= threshold}

        if universally_missing or universally_forbidden or universally_regex_missed:
            suspects.append((tid, universally_missing, universally_forbidden, universally_regex_missed))

    print(f"FOUND {len(suspects)} suspect tasks ({100*len(suspects)/len(task_seen_in):.1f}% of corpus)\n")

    if args.verbose or len(suspects) <= 30:
        for tid, m, f, r in suspects:
            print(f"  {tid}")
            if m:
                print(f"    must_contain never hit:      {sorted(m)}")
            if f:
                print(f"    must_not_contain always hit: {sorted(f)}")
            if r:
                print(f"    must_match_regex never hit:  {sorted(r)}")
    else:
        # Summary mode
        from collections import Counter
        cats = Counter(tid.split(".")[0] for tid, *_ in suspects)
        print("By category:")
        for c, n in cats.most_common():
            print(f"  {c:20s} {n}")
        print("\n(Re-run with --verbose to see all suspect tasks)")

    return 0 if not suspects else 1


if __name__ == "__main__":
    sys.exit(main())
