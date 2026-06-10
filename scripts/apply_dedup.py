#!/usr/bin/env python3
"""Apply the dedup proposal — physically retire tasks from tasks/<category>.jsonl.

Reads dedup_proposal.json (produced by propose_dedup.py) and:
  1. Filters retired task_ids out of each tasks/<category>.jsonl
  2. Writes retired records to retired_v01.jsonl as a permanent record
     (so we can recover if a retirement turns out to be wrong)

Idempotent: running it twice does nothing the second time.

Usage:
  python scripts/apply_dedup.py --dry-run
  python scripts/apply_dedup.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
PROPOSAL = ROOT / "dedup_proposal.json"
RETIRED_LOG = ROOT / "retired_v01.jsonl"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not PROPOSAL.exists():
        sys.exit(f"Missing {PROPOSAL} — run scripts/propose_dedup.py first")
    proposal = json.loads(PROPOSAL.read_text())

    retire_set: set[str] = set(proposal["saturated_retirements"]) | set(proposal["redundant_retirements"])
    print(f"Proposal calls for retiring {len(retire_set)} task(s)")
    print(f"  saturated: {len(proposal['saturated_retirements'])}")
    print(f"  redundant: {len(proposal['redundant_retirements'])}")

    # Walk every tasks/*.jsonl, partition into keep vs retire
    file_changes: dict[str, tuple[int, int]] = {}  # filename -> (kept, retired)
    retired_records: list[dict] = []

    for cat_file in sorted(TASKS_DIR.glob("*.jsonl")):
        records = [json.loads(line) for line in open(cat_file) if line.strip()]
        keep = [r for r in records if r["task_id"] not in retire_set]
        retire = [r for r in records if r["task_id"] in retire_set]
        if retire:
            file_changes[cat_file.name] = (len(keep), len(retire))
            retired_records.extend(retire)
            if not args.dry_run:
                with open(cat_file, "w") as f:
                    for r in keep:
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")

    found = sum(retired for _, retired in file_changes.values())
    not_found = len(retire_set) - found
    if not_found > 0:
        missing = sorted(retire_set - {r["task_id"] for r in retired_records})
        print(f"\nWARNING: {not_found} retirement task_ids not found in tasks/ — already retired?")
        for tid in missing[:10]:
            print(f"  {tid}")

    print(f"\nPer-file changes:")
    for fname in sorted(file_changes):
        kept, retired = file_changes[fname]
        print(f"  {fname:30s} kept={kept:3d}  retired={retired}")

    print(f"\nTotal retired: {len(retired_records)}")
    print(f"Total remaining: {sum(k for k, _ in file_changes.values())} (per affected files)")

    if not args.dry_run and retired_records:
        # Append-mode log so we don't clobber a previous run's record
        with open(RETIRED_LOG, "a") as f:
            for r in retired_records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\nRetired records appended to: {RETIRED_LOG}")

    if args.dry_run:
        print("\n[dry-run] no files modified")

    return 0


if __name__ == "__main__":
    sys.exit(main())
