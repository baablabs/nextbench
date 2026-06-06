#!/usr/bin/env python3
"""Re-grade the 12 panel models' legacy battle outputs into NextBench v0.1 schema.

For each model in the discrimination panel, joins its raw legacy outputs with
the new-schema tasks (by metadata.legacy_id) and writes a clean per-model
JSONL into nextbench/outputs/<canonical-model-name>.jsonl.

These canonical output files are committed to the repo so that ANY submitter
or reviewer can re-grade any leaderboard row from raw outputs without rerunning
inference. The parity smoke test (smoke_test_parity.py) is preserved as a
trusted-baseline marker.

Output naming follows the lowercase-kebab convention used by run_eval.py:
  - BaaB Next 1B (Pretrain 2K)  ->  baab-next-1b-pretrain-2k.jsonl
  - qwen3-coder:30b             ->  qwen3-coder_30b.jsonl
  - codestral:22b               ->  codestral_22b.jsonl

Usage:
  python nextbench/scripts/regrade_legacy_outputs.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
LEGACY_OUTPUTS_DIR = ROOT / "eval" / "battle" / "outputs"
TASKS_DIR = ROOT / "nextbench" / "tasks"
OUT_DIR = ROOT / "nextbench" / "outputs"

# Maps legacy-output filename -> (canonical model id, display name, backend).
# Canonical id is what becomes outputs/<id>.jsonl and matches run_eval.py
# output slug convention.
PANEL: dict[str, tuple[str, str, str]] = {
    "codegemma_2b_battle.jsonl":         ("codegemma_2b",        "codegemma:2b",          "ollama"),
    "codestral_22b_battle.jsonl":        ("codestral_22b",       "codestral:22b",         "ollama"),
    "deepseek-coder_13b_battle.jsonl":   ("deepseek-coder_13b",  "deepseek-coder:1.3b",   "ollama"),
    "granite-code_3b_battle.jsonl":      ("granite-code_3b",     "granite-code:3b",       "ollama"),
    "granite-code_8b_battle.jsonl":      ("granite-code_8b",     "granite-code:8b",       "ollama"),
    "qwen25-coder_15b_battle.jsonl":     ("qwen25-coder_15b",    "qwen2.5-coder:1.5b",    "ollama"),
    "qwen25-coder_3b_battle.jsonl":      ("qwen25-coder_3b",     "qwen2.5-coder:3b",      "ollama"),
    "qwen25-coder_7b_battle.jsonl":      ("qwen25-coder_7b",     "qwen2.5-coder:7b",      "ollama"),
    "qwen3-coder_30b_battle.jsonl":      ("qwen3-coder_30b",     "qwen3-coder:30b",       "ollama"),
    "starcoder2_3b_battle.jsonl":        ("starcoder2_3b",       "starcoder2:3b",         "ollama"),
    "final_battle.jsonl":                ("baab-next-1b-pretrain-2k", "BaaB Next 1B (Pretrain 2K)", "litgpt"),
    "step-00008000_battle.jsonl":        ("baab-next-1b-pretrain-4k", "BaaB Next 1B (Pretrain 4K)", "litgpt"),
}

# Settings used for the canonical leaderboard runs (matches LEADERBOARD.md).
CANONICAL_SETTINGS = {
    "temperature": 0.0,
    "top_k": 1,
    "max_tokens": 500,
    "num_ctx": 4096,
    "raw": True,
}


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
    task_index = load_new_tasks_by_legacy_id()
    print(f"Loaded {len(task_index)} new-schema tasks indexed by legacy_id\n")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total_records = 0

    for legacy_fname, (canonical_id, display_name, backend) in PANEL.items():
        src = LEGACY_OUTPUTS_DIR / legacy_fname
        if not src.exists():
            print(f"  SKIP   {legacy_fname}  (missing)")
            continue

        dst = OUT_DIR / f"{canonical_id}.jsonl"
        settings = {**CANONICAL_SETTINGS, "backend": backend, "model": display_name}

        n_joined = 0
        n_missing = 0
        with open(src) as fin, open(dst, "w") as fout:
            for line in fin:
                legacy = json.loads(line)
                legacy_id = legacy.get("id")
                new_task = task_index.get(legacy_id)
                if not new_task:
                    n_missing += 1
                    continue
                joined = {
                    **new_task,
                    "output": legacy.get("output", ""),
                    "settings": settings,
                }
                fout.write(json.dumps(joined, ensure_ascii=False) + "\n")
                n_joined += 1

        warn = f"  ({n_missing} missing)" if n_missing else ""
        print(f"  WROTE  {dst.name:42s}  {n_joined} records{warn}")
        total_records += n_joined

    print(f"\nTotal: {total_records} records across {len(PANEL)} models")
    print(f"Output directory: {OUT_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
