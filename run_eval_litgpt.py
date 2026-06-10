#!/usr/bin/env python3
"""LitGPT-backed eval runner — writes outputs in the same JSONL shape as run_eval.py.

Loads a LitGPT checkpoint dir, sends each task's prompt to the model, writes
one output record per task in the format grade.py expects. Use this for the
baab-next-1b checkpoints (which aren't loaded as Ollama tags).

Default settings match run_eval.py (the published-leaderboard settings):
  temperature=0.0  top_k=1  max_new_tokens=500

Use the project venv (./venv) — litgpt is installed there.

Usage:
  ./venv/bin/python nextbench/run_eval_litgpt.py \\
      --checkpoint checkpoints/run8_1b/final \\
      --model-name baab-next-1b-pretrain-2k \\
      --tasks-dir nextbench/tasks_v02_only \\
      --output nextbench/outputs_v02/baab-next-1b-pretrain-2k.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def load_tasks(tasks_dir: Path, category: str | None = None) -> list[dict]:
    if category:
        paths = [tasks_dir / f"{category}.jsonl"]
        if not paths[0].exists():
            sys.exit(f"No tasks file for category {category!r} at {paths[0]}")
    else:
        paths = sorted(tasks_dir.glob("*.jsonl"))
    tasks: list[dict] = []
    for path in paths:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    tasks.append(json.loads(line))
    return tasks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True, help="LitGPT checkpoint directory")
    parser.add_argument("--model-name", required=True,
                        help="Logical model name (used in settings + output identification)")
    parser.add_argument("--tasks-dir", required=True)
    parser.add_argument("--category", default=None)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--task-ids", default=None,
                        help="Path to file with one task_id per line; only those tasks run")
    parser.add_argument("--append", action="store_true",
                        help="Append to output file instead of overwriting")
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-tokens", type=int, default=500)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-k", type=int, default=1)
    args = parser.parse_args()

    tasks = load_tasks(Path(args.tasks_dir), category=args.category)
    if args.task_ids:
        wanted = {ln.strip() for ln in open(args.task_ids) if ln.strip()}
        tasks = [t for t in tasks if t["task_id"] in wanted]
        missing = wanted - {t["task_id"] for t in tasks}
        if missing:
            print(f"WARN: {len(missing)} task_ids not found in corpus (first 5: {list(missing)[:5]})", flush=True)
    if args.limit:
        tasks = tasks[: args.limit]
    if not tasks:
        sys.exit("No tasks loaded.")

    print(f"Backend:    litgpt", flush=True)
    print(f"Checkpoint: {args.checkpoint}", flush=True)
    print(f"Model name: {args.model_name}", flush=True)
    print(f"Tasks:      {len(tasks)}  (category={args.category or 'all'})", flush=True)
    print(f"Output:     {args.output}", flush=True)

    # The training checkpoints pickled refs to `scripts.binary_data_module` —
    # add the webdev-model root to sys.path so the unpickler can resolve them.
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Lazy import so the --help path doesn't require torch installed
    from litgpt import LLM
    print(f"Loading checkpoint...", flush=True)
    llm = LLM.load(args.checkpoint)
    print(f"Loaded.", flush=True)

    settings = {
        "backend": "litgpt",
        "model": args.model_name,
        "checkpoint": args.checkpoint,
        "temperature": args.temperature,
        "top_k": args.top_k,
        "max_tokens": args.max_tokens,
    }

    # litgpt's generate doesn't accept temperature=0 directly; emulate greedy
    # via tiny temperature + top_k=1
    gen_temp = max(args.temperature, 1e-6)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_f = open(out_path, "a" if args.append else "w")
    start = time.time()
    last_log = start

    for i, task in enumerate(tasks):
        prompt = task["prompt"]
        try:
            output = llm.generate(
                prompt,
                max_new_tokens=args.max_tokens,
                temperature=gen_temp,
                top_k=args.top_k,
            )
            # litgpt sometimes returns prompt+continuation; strip the prefix
            if output.startswith(prompt):
                output = output[len(prompt):]
            eval_count = 0  # litgpt doesn't expose token counts in the same way
        except Exception as e:
            output, eval_count = f"<<GENERATION_ERROR: {e}>>", 0

        record = {**task, "output": output, "settings": settings, "eval_tokens": eval_count}
        out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
        out_f.flush()

        if time.time() - last_log > 30 or i + 1 == len(tasks):
            elapsed = time.time() - start
            rate = (i + 1) / elapsed if elapsed else 0
            eta_min = (len(tasks) - i - 1) / rate / 60 if rate else 0
            print(f"[{int(elapsed)}s] {i+1}/{len(tasks)} rate={rate:.2f}/s eta_min={eta_min:.1f}", flush=True)
            last_log = time.time()

    out_f.close()
    elapsed = time.time() - start
    print(f"\nDONE: {len(tasks)} tasks in {elapsed/60:.1f} min -> {out_path}", flush=True)


if __name__ == "__main__":
    main()
