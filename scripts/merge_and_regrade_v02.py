#!/usr/bin/env python3
"""Merge v0.1 outputs + v0.2 incremental outputs and re-grade against current checks.

For each model in the 12-panel:
  1. Load outputs/<slug>.jsonl  (v0.1 outputs — pre-dedup, 355 rows).
  2. Drop rows whose task_id is no longer in the current corpus (the 77 retired).
  3. Append outputs_new/<slug>.jsonl  (172 new task outputs).
  4. For every row, overwrite `checks` with the CURRENT task's checks (so fixes
     post-promotion take effect on retained rows).
  5. Write outputs_450/<slug>.jsonl.

This gives us a clean 450-row scoreboard per model that's graded under the
current rules. We then run grade.py over outputs_450/ to get the leaderboard.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
OLD = ROOT / "outputs"
NEW = ROOT / "outputs_new"
OUT = ROOT / "outputs_450"

PANEL = [
    "baab-next-1b-pretrain-2k",
    "baab-next-1b-pretrain-4k",
    "baab-next-1b-pretrain-4k-v2",
    "codegemma_2b",
    "codestral_22b",
    "deepseek-coder_13b",
    "granite-code_3b",
    "granite-code_8b",
    "qwen25-coder_15b",
    "qwen25-coder_3b",
    "qwen25-coder_7b",
    "qwen3-coder_30b",
    "starcoder2_3b",
]


def load_current_tasks() -> dict[str, dict]:
    idx = {}
    for fp in sorted(TASKS_DIR.glob("*.jsonl")):
        with open(fp) as f:
            for line in f:
                if line.strip():
                    t = json.loads(line)
                    idx[t["task_id"]] = t
    return idx


def merge_model(slug: str, current: dict[str, dict]) -> tuple[int, int, int]:
    """Return (kept_from_old, added_from_new, retired_skipped)."""
    OUT.mkdir(exist_ok=True)
    out_path = OUT / f"{slug}.jsonl"

    kept = added = retired = 0
    seen = set()
    with open(out_path, "w") as out_f:
        # Retained from v0.1
        old_path = OLD / f"{slug}.jsonl"
        if old_path.exists():
            with open(old_path) as f:
                for line in f:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    tid = row["task_id"]
                    if tid not in current:
                        retired += 1
                        continue
                    # Overwrite checks with current task's checks
                    row["checks"] = current[tid]["checks"]
                    out_f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    seen.add(tid)
                    kept += 1

        # New v0.2 outputs
        new_path = NEW / f"{slug}.jsonl"
        if new_path.exists():
            with open(new_path) as f:
                for line in f:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    tid = row["task_id"]
                    if tid in seen:
                        continue  # avoid dupes
                    if tid not in current:
                        retired += 1
                        continue
                    row["checks"] = current[tid]["checks"]
                    out_f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    added += 1

    return kept, added, retired


def main():
    current = load_current_tasks()
    print(f"Current corpus: {len(current)} tasks")
    print()
    print(f"{'model':<32} {'kept':>6} {'added':>6} {'retired':>8} {'total':>6}")
    for slug in PANEL:
        kept, added, retired = merge_model(slug, current)
        print(f"{slug:<32} {kept:>6} {added:>6} {retired:>8} {kept+added:>6}")


if __name__ == "__main__":
    main()
