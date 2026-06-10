#!/usr/bin/env python3
"""Regrade existing model outputs against the CURRENT tasks/ check definitions.

Existing outputs/<model>.jsonl files have the checks frozen at eval time — they
don't reflect post-hoc fixes to the task corpus. This tool loads current
checks from tasks/<category>.jsonl by task_id, substitutes them into each
output record, regrades, and reports score deltas.

Use after fixing buggy v0.1 checks (e.g. fix_v01_bugs.py) to confirm fixes
actually moved scores without needing to re-run inference on 12 models.

Usage:
  python regrade_with_current_checks.py
  python regrade_with_current_checks.py --outputs-dir outputs_v02 --tasks-dir tasks_v02_only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from grade import grade_one  # noqa: E402


def load_current_checks(tasks_dir: Path) -> dict[str, dict]:
    by_id: dict[str, dict] = {}
    for path in tasks_dir.glob("*.jsonl"):
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            by_id[rec["task_id"]] = rec["checks"]
    return by_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs-dir", default=str(ROOT / "outputs"))
    parser.add_argument("--tasks-dir", default=str(ROOT / "tasks"))
    parser.add_argument("--show-deltas-only", action="store_true",
                        help="Only print models with score changes vs frozen checks")
    args = parser.parse_args()

    outputs_dir = Path(args.outputs_dir)
    tasks_dir = Path(args.tasks_dir)
    current_checks = load_current_checks(tasks_dir)
    output_files = sorted(p for p in outputs_dir.glob("*.jsonl")
                          if not p.name.startswith("_"))

    print(f"Regrading {len(output_files)} models against {len(current_checks)} current tasks\n")
    print(f"{'Model':30s}  {'Frozen':>10s}  {'Current':>10s}  {'Delta':>8s}  {'Tasks moved':>12s}")
    print("-" * 80)

    results = []
    for f in output_files:
        n_tasks = 0
        n_moved = 0
        frozen_total = 0
        current_total = 0
        max_total = 0
        for line in open(f):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            tid = rec["task_id"]
            n_tasks += 1
            frozen_score = grade_one(rec)["score"]
            frozen_total += frozen_score
            max_total += 4
            if tid in current_checks:
                rec_current = dict(rec)
                rec_current["checks"] = current_checks[tid]
                current_score = grade_one(rec_current)["score"]
            else:
                current_score = frozen_score
            current_total += current_score
            if current_score != frozen_score:
                n_moved += 1
        delta = current_total - frozen_total
        if args.show_deltas_only and delta == 0:
            continue
        pct_frozen = 100 * frozen_total / max_total if max_total else 0
        pct_current = 100 * current_total / max_total if max_total else 0
        sign = "+" if delta >= 0 else ""
        results.append((f.stem, frozen_total, current_total, delta, n_moved, pct_frozen, pct_current))
        print(f"{f.stem:30s}  {frozen_total:4d} ({pct_frozen:5.1f}%)  {current_total:4d} ({pct_current:5.1f}%)  {sign}{delta:+4d}      {n_moved:4d}")

    print("-" * 80)
    avg_delta = sum(r[3] for r in results) / len(results) if results else 0
    avg_moved = sum(r[4] for r in results) / len(results) if results else 0
    print(f"{'AVG':30s}  {'':>10s}  {'':>10s}  {avg_delta:+8.1f}     {avg_moved:7.1f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
