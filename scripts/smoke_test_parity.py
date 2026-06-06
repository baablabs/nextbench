#!/usr/bin/env python3
"""Parity smoke test: re-grade legacy battle outputs through the NextBench grader.

Joins legacy outputs (eval/battle/outputs/*_battle.jsonl) with the new-schema
tasks via metadata.legacy_id, then runs grade.py. If the new grader's total
matches the legacy 91.4% baseline (and per-category scores match), the schema
migration is correctness-equivalent.

Usage:
  python nextbench/scripts/smoke_test_parity.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
LEGACY_OUTPUTS = ROOT / "eval" / "battle" / "outputs" / "final_battle.jsonl"
TASKS_DIR = ROOT / "nextbench" / "tasks"
JOINED_OUT = ROOT / "nextbench" / "outputs" / "_parity_run8_final.jsonl"
GRADER = ROOT / "nextbench" / "grade.py"


def load_new_tasks_by_legacy_id() -> dict[str, dict]:
    index: dict[str, dict] = {}
    for path in sorted(TASKS_DIR.glob("*.jsonl")):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                task = json.loads(line)
                legacy_id = task.get("metadata", {}).get("legacy_id")
                if legacy_id:
                    index[legacy_id] = task
    return index


def main():
    if not LEGACY_OUTPUTS.exists():
        sys.exit(f"Missing legacy outputs at {LEGACY_OUTPUTS}")
    new_by_id = load_new_tasks_by_legacy_id()
    print(f"Loaded {len(new_by_id)} new-schema tasks indexed by legacy_id")

    JOINED_OUT.parent.mkdir(parents=True, exist_ok=True)
    joined_count = 0
    missing = []
    with open(LEGACY_OUTPUTS) as src, open(JOINED_OUT, "w") as dst:
        for line in src:
            legacy = json.loads(line)
            legacy_id = legacy.get("id")
            new_task = new_by_id.get(legacy_id)
            if not new_task:
                missing.append(legacy_id)
                continue
            joined = {
                **new_task,
                "output": legacy.get("output", ""),
                "settings": {"backend": "litgpt", "model": "baab-next-1b-pretrain-2k"},
            }
            dst.write(json.dumps(joined, ensure_ascii=False) + "\n")
            joined_count += 1

    print(f"Joined {joined_count} records into {JOINED_OUT.relative_to(ROOT)}")
    if missing:
        print(f"WARNING: {len(missing)} legacy ids had no new-schema match: {missing[:5]}...")

    print("\n" + "=" * 64)
    print("Running NextBench grader on joined records...")
    print("=" * 64)
    result = subprocess.run(
        ["python3", str(GRADER), "--input", str(JOINED_OUT)],
        capture_output=False,
    )
    if result.returncode != 0:
        sys.exit(f"Grader failed with exit code {result.returncode}")


if __name__ == "__main__":
    main()
