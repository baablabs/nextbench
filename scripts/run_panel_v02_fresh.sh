#!/usr/bin/env bash
# Fresh full eval — 10 Ollama panel models against the full 450-task v0.2 corpus.
# Outputs land in outputs_fresh/<slug>.jsonl. The 2/3 baab-next-1b checkpoints
# run via run_baab_v02_fresh.sh separately.
#
# This exists because the "merged" outputs_450/ joins v0.1 outputs (278 rows)
# with v0.2-incremental outputs (172 rows). The merged result is mathematically
# equivalent to a fresh full eval IFF nothing drifted (Ollama version, model
# tag content, prompts, decoding determinism). Running fresh closes the
# equivalence question for the public v0.2 release.

set -euo pipefail
cd "$(dirname "$0")/.."

OUT_DIR=outputs_fresh
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
  case "$slug" in
    qwen2_5-coder_1_5b) slug="qwen25-coder_15b" ;;
    qwen2_5-coder_*) slug="${slug/qwen2_5/qwen25}" ;;
    deepseek-coder_1_3b) slug="deepseek-coder_13b" ;;
  esac
  out="$OUT_DIR/${slug}.jsonl"
  if [[ -f "$out" ]] && [[ $(wc -l < "$out") -eq 450 ]]; then
    echo "[skip] $m -> $out (already 450 rows)"
    continue
  fi
  echo "=== $m -> $out ==="
  python3 run_eval.py --backend ollama --model "$m" --output "$out"
done
echo "DONE."
