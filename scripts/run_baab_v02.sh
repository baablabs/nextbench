#!/usr/bin/env bash
# Run the 2 baab-next-1b checkpoints on the 172 new v0.2 task_ids via litgpt.
set -euo pipefail
cd "$(dirname "$0")/.."

TASK_IDS=new_task_ids_v02.txt
OUT_DIR=outputs_new
mkdir -p "$OUT_DIR"

# Pretrain 2K → ../checkpoints/run8_1b/final
out=$OUT_DIR/baab-next-1b-pretrain-2k.jsonl
if [[ ! -f "$out" ]]; then
  echo "=== BaaB Next 1B (Pretrain 2K) -> $out ==="
  ../venv/bin/python run_eval_litgpt.py \
    --checkpoint ../checkpoints/run8_1b/final \
    --model-name "BaaB Next 1B (Pretrain 2K)" \
    --tasks-dir tasks --task-ids "$TASK_IDS" --output "$out"
fi

# Pretrain 4K → ../checkpoints/run8_1b_cpt4k/step-00008000
out=$OUT_DIR/baab-next-1b-pretrain-4k.jsonl
if [[ ! -f "$out" ]]; then
  echo "=== BaaB Next 1B (Pretrain 4K) -> $out ==="
  ../venv/bin/python run_eval_litgpt.py \
    --checkpoint ../checkpoints/run8_1b_cpt4k/step-00008000 \
    --model-name "BaaB Next 1B (Pretrain 4K)" \
    --tasks-dir tasks --task-ids "$TASK_IDS" --output "$out"
fi
echo "DONE."
