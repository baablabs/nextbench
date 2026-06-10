#!/usr/bin/env python3
"""Promote v0.2 candidates into the canonical tasks/ corpus.

Reads every candidates_002*.jsonl, bumps metadata.benchmark_version from
"0.2-candidate" to "0.2", and appends to the matching nextbench/tasks/<category>.jsonl.

Also writes a sidecar `tasks_v02_only/<category>.jsonl` tree containing JUST
the 54 new tasks, so the eval pass can target the new corpus without
re-grading the v0.1 tasks. The sidecar tree mirrors the tasks/ schema so
run_eval.py can load it via `--tasks-dir tasks_v02_only`.

Idempotent: re-running won't duplicate records (it checks task_id against
the current corpus before appending).

Usage:
  python promote_to_corpus.py            # actually do the promotion
  python promote_to_corpus.py --dry-run  # show what would change
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CANDIDATES_DIR = SCRIPT_DIR.parent
NEXTBENCH_ROOT = CANDIDATES_DIR.parent.parent
TASKS_DIR = NEXTBENCH_ROOT / "tasks"
V02_ONLY_DIR = NEXTBENCH_ROOT / "tasks_v02_only"

BATCH_FILES = [
    "candidates_002a.jsonl",
    "candidates_002b.jsonl",
    "candidates_002c.jsonl",
    "candidates_002d.jsonl",
    "candidates_002e.jsonl",
    "candidates_002f.jsonl",
    "candidates_003a.jsonl",
    "candidates_003b.jsonl",
    "candidates_003c.jsonl",
    "candidates_003d.jsonl",
    "candidates_003e.jsonl",
    "candidates_003f.jsonl",
    "candidates_003g.jsonl",
    "candidates_003h.jsonl",
    "candidates_003i.jsonl",
    "candidates_003j.jsonl",
    "candidates_003k.jsonl",
]


def load_existing_task_ids() -> set[str]:
    existing: set[str] = set()
    if not TASKS_DIR.exists():
        return existing
    for path in TASKS_DIR.glob("*.jsonl"):
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if "task_id" in rec:
                    existing.add(rec["task_id"])
            except json.JSONDecodeError:
                pass
    return existing


def promote_record(rec: dict) -> dict:
    """Bump benchmark_version from candidate to release."""
    promoted = json.loads(json.dumps(rec))  # deep copy
    md = promoted.setdefault("metadata", {})
    if md.get("benchmark_version") == "0.2-candidate":
        md["benchmark_version"] = "0.2"
    return promoted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    existing = load_existing_task_ids()
    by_category: dict[str, list[dict]] = defaultdict(list)
    skipped_dupes: list[str] = []
    total_seen = 0

    for fname in BATCH_FILES:
        path = CANDIDATES_DIR / fname
        if not path.exists():
            print(f"WARN: {fname} not found, skipping")
            continue
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            total_seen += 1
            if rec["task_id"] in existing:
                skipped_dupes.append(rec["task_id"])
                continue
            promoted = promote_record(rec)
            by_category[promoted["category"]].append(promoted)

    print(f"Read {total_seen} candidates across {len(BATCH_FILES)} batches")
    if skipped_dupes:
        print(f"Skipped {len(skipped_dupes)} dupes (already in tasks/): {skipped_dupes[:3]}...")

    print(f"\nBy category (new only):")
    for cat in sorted(by_category):
        print(f"  {cat:20s} +{len(by_category[cat])}")
    print(f"  TOTAL              +{sum(len(v) for v in by_category.values())}")

    if args.dry_run:
        print("\n[dry-run] no files written")
        return 0

    # Append to canonical tasks/<category>.jsonl
    for cat, recs in by_category.items():
        path = TASKS_DIR / f"{cat}.jsonl"
        with open(path, "a") as f:
            for rec in recs:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"  appended {len(recs)} -> {path.name}")

    # Write tasks_v02_only/<category>.jsonl (fresh — overwrite)
    V02_ONLY_DIR.mkdir(exist_ok=True)
    for cat, recs in by_category.items():
        path = V02_ONLY_DIR / f"{cat}.jsonl"
        with open(path, "w") as f:
            for rec in recs:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"\nWrote v0.2-only mini-corpus to {V02_ONLY_DIR}/ ({len(by_category)} category files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
