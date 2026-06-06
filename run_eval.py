#!/usr/bin/env python3
"""NextBench eval runner — execute the benchmark against any model.

Loads tasks from nextbench/tasks/<category>.jsonl, sends each task's prompt to
the model backend, writes one output JSONL row per task. Output JSONL is the
input to grade.py.

Backends (v0.1):
  - ollama        local Ollama HTTP server (raw=true bypasses chat template)
  - openai        OpenAI-compatible Chat Completions endpoint (any provider)

Default settings (matched to the published leaderboard):
  temperature=0.0  top_k=1  max_tokens=500  num_ctx=4096

Usage:
  python run_eval.py --backend ollama --model qwen2.5-coder:7b
  python run_eval.py --backend openai --model gpt-4o-mini --api-base https://api.openai.com/v1
  python run_eval.py --backend ollama --model qwen3-coder:30b --category react
  python run_eval.py --backend ollama --model qwen2.5-coder:1.5b --limit 20
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
TASKS_DIR = ROOT / "tasks"
OUT_DIR = ROOT / "outputs"
OUT_DIR.mkdir(exist_ok=True)


# ──────────────────────────────────────────────────────────────────────────
# Loaders
# ──────────────────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────────────────
# Backends
# ──────────────────────────────────────────────────────────────────────────

def call_ollama(model: str, prompt: str, *, max_tokens: int, temperature: float, top_k: int,
                num_ctx: int, url: str, timeout: int) -> tuple[str, int]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "raw": True,  # bypass chat template — pure autocomplete shape
        "options": {
            "temperature": temperature,
            "top_k": top_k,
            "num_predict": max_tokens,
            "num_ctx": num_ctx,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body.get("response", ""), body.get("eval_count", 0)
    except urllib.error.URLError as e:
        return f"<<OLLAMA_ERROR: {e}>>", 0
    except Exception as e:
        return f"<<GENERATION_ERROR: {e}>>", 0


def call_openai(model: str, prompt: str, *, max_tokens: int, temperature: float,
                api_base: str, api_key: str, timeout: int) -> tuple[str, int]:
    # NOTE: completion tasks are autocomplete-shaped; we wrap as a single user
    # message and instruct the model to continue verbatim. This is the standard
    # "OpenAI-compatible chat" path used by Together, DeepInfra, OpenRouter, etc.
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Continue the code verbatim from where it ends. Output only code; do not repeat the prefix."},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    req = urllib.request.Request(api_base.rstrip("/") + "/chat/completions", data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        text = body["choices"][0]["message"]["content"] or ""
        tokens = body.get("usage", {}).get("completion_tokens", 0)
        return text, tokens
    except urllib.error.URLError as e:
        return f"<<OPENAI_ERROR: {e}>>", 0
    except Exception as e:
        return f"<<GENERATION_ERROR: {e}>>", 0


# ──────────────────────────────────────────────────────────────────────────
# Driver
# ──────────────────────────────────────────────────────────────────────────

def slug(model_name: str) -> str:
    return model_name.replace(":", "_").replace("/", "_").replace(".", "")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Model name (Ollama tag or OpenAI model id)")
    parser.add_argument("--backend", choices=["ollama", "openai"], default="ollama")
    parser.add_argument("--tasks-dir", default=str(TASKS_DIR))
    parser.add_argument("--category", default=None, help="Run only one category")
    parser.add_argument("--limit", type=int, default=0, help="Cap number of tasks")
    parser.add_argument("--output", default=None)
    parser.add_argument("--max-tokens", type=int, default=500)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-k", type=int, default=1)
    parser.add_argument("--num-ctx", type=int, default=4096)
    parser.add_argument("--ollama-url", default="http://localhost:11434/api/generate")
    parser.add_argument("--api-base", default="https://api.openai.com/v1")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()

    tasks = load_tasks(Path(args.tasks_dir), category=args.category)
    if args.limit:
        tasks = tasks[: args.limit]
    if not tasks:
        sys.exit("No tasks loaded.")

    if args.backend == "openai":
        api_key = os.environ.get(args.api_key_env, "")
        if not api_key:
            sys.exit(f"Missing API key — set {args.api_key_env} in env")

    out_path = Path(args.output) if args.output else (OUT_DIR / f"{slug(args.model)}.jsonl")
    print(f"Backend: {args.backend}", flush=True)
    print(f"Model:   {args.model}", flush=True)
    print(f"Tasks:   {len(tasks)}  (category={args.category or 'all'})", flush=True)
    print(f"Output:  {out_path}", flush=True)

    settings = {
        "backend": args.backend,
        "model": args.model,
        "temperature": args.temperature,
        "top_k": args.top_k,
        "max_tokens": args.max_tokens,
        "num_ctx": args.num_ctx,
    }

    out_f = open(out_path, "w")
    start = time.time()
    last_log = start
    total_tokens = 0

    for i, task in enumerate(tasks):
        prompt = task["prompt"]
        try:
            if args.backend == "ollama":
                output, eval_count = call_ollama(
                    args.model, prompt,
                    max_tokens=args.max_tokens, temperature=args.temperature,
                    top_k=args.top_k, num_ctx=args.num_ctx,
                    url=args.ollama_url, timeout=args.timeout,
                )
            else:
                output, eval_count = call_openai(
                    args.model, prompt,
                    max_tokens=args.max_tokens, temperature=args.temperature,
                    api_base=args.api_base, api_key=api_key,  # type: ignore[name-defined]
                    timeout=args.timeout,
                )
            total_tokens += eval_count
        except Exception as e:
            output, eval_count = f"<<GENERATION_ERROR: {e}>>", 0

        record = {**task, "output": output, "settings": settings, "eval_tokens": eval_count}
        out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
        out_f.flush()

        if time.time() - last_log > 30 or i + 1 == len(tasks):
            elapsed = time.time() - start
            rate = (i + 1) / elapsed if elapsed else 0
            eta_min = (len(tasks) - i - 1) / rate / 60 if rate else 0
            tok_rate = total_tokens / elapsed if elapsed else 0
            print(f"[{int(elapsed)}s] {i+1}/{len(tasks)} rate={rate:.2f}/s tok/s={tok_rate:.0f} eta_min={eta_min:.1f}", flush=True)
            last_log = time.time()

    out_f.close()
    elapsed = time.time() - start
    print(f"\nDONE: {len(tasks)} tasks in {elapsed/60:.1f} min -> {out_path}", flush=True)


if __name__ == "__main__":
    main()
