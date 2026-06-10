#!/usr/bin/env bash
# Run the 10 Ollama panel models on the 172 new v0.2 task_ids.
# Outputs land in outputs_new/<slug>.jsonl. The 2 baab-next-1b checkpoints
# run via run_eval_litgpt.py separately.
set -euo pipefail
cd "$(dirname "$0")/.."

TASK_IDS=new_task_ids_v02.txt
OUT_DIR=outputs_new
mkdir -p "$OUT_DIR"

MODELS=(
  "qwen3-coder:30b"
  "qwen2.5-coder:7b"
  "qwen2.5-coder:3b"
  "qwen2.5-coder:1.5b"
  "codestral:22b"
  "granite-code:8b"
  "granite-code:3b"
  "starcoder2:3b"
  "codegemma:2b"
  "deepseek-coder:1.3b"
)

for m in "${MODELS[@]}"; do
  slug=$(echo "$m" | sed 's/:/_/g; s/\./_/g')
  # Match the existing v0.1 slugs (no dots) so merging works.
  case "$slug" in
    qwen2_5-coder_1_5b) slug="qwen25-coder_15b" ;;
    qwen2_5-coder_*) slug="${slug/qwen2_5/qwen25}" ;;
    deepseek-coder_1_3b) slug="deepseek-coder_13b" ;;
  esac
  out="$OUT_DIR/${slug}.jsonl"
  if [[ -f "$out" ]]; then
    echo "[skip] $m -> $out (already exists)"
    continue
  fi
  echo "=== $m -> $out ==="
  python3 run_eval.py --backend ollama --model "$m" --task-ids "$TASK_IDS" --output "$out"
done
echo "DONE."
