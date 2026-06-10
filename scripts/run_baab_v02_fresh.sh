#!/usr/bin/env bash
# Fresh full eval — 3 baab-next-1b checkpoints against the full 450-task v0.2
# corpus via litgpt. Outputs land in outputs_fresh/.
#
# Three checkpoints in this round:
#   1. baab-next-1b-pretrain-2k         -> run8_1b/final
#   2. baab-next-1b-pretrain-4k         -> run8_1b_cpt4k/step-00008000  (current published)
#   3. baab-next-1b-pretrain-4k-v2      -> run8_1b_cpt4k/step-00010000  (new candidate)
set -euo pipefail
cd "$(dirname "$0")/.."

OUT_DIR=outputs_fresh
mkdir -p "$OUT_DIR"

declare -a JOBS=(
  "../checkpoints/run8_1b/final|BaaB Next 1B (Pretrain 2K)|baab-next-1b-pretrain-2k.jsonl"
  "../checkpoints/run8_1b_cpt4k/step-00008000|BaaB Next 1B (Pretrain 4K)|baab-next-1b-pretrain-4k.jsonl"
  "../checkpoints/run8_1b_cpt4k/step-00010000|BaaB Next 1B (Pretrain 4K v2)|baab-next-1b-pretrain-4k-v2.jsonl"
)

for spec in "${JOBS[@]}"; do
  IFS='|' read -r ckpt name fname <<< "$spec"
  out="$OUT_DIR/$fname"
  if [[ -f "$out" ]] && [[ $(wc -l < "$out") -eq 450 ]]; then
    echo "[skip] $name -> $out (already 450 rows)"
    continue
  fi
  echo "=== $name -> $out ==="
  ../venv/bin/python run_eval_litgpt.py \
    --checkpoint "$ckpt" \
    --model-name "$name" \
    --tasks-dir tasks \
    --output "$out"
done
echo "DONE."
