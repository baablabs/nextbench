# NextBench Leaderboard

**Benchmark:** NextBench v0.1 (355 completion tasks, 13 categories)
**Settings:** `temperature=0.0`, `top_k=1`, `max_tokens=500`, `num_ctx=4096`, `raw=true` (bypass chat template)
**Last updated:** 2026-06-06

Scoring rubric: each task is graded against `checks.static.*` for four binary signals — `pattern_hit`, `no_forbidden`, `regex_hit`, `length_ok`. Max score per task = 4. Total max = 4 × 355 = **1420**.

To reproduce any row in this table: `python run_eval.py --backend <backend> --model <model>` followed by `python grade.py --input outputs/<model>.jsonl`.

---

## Headline ranking

| Rank | Model | Params | Score | % |
|---:|---|---:|---:|---:|
| 1 | qwen3-coder:30b (MoE) | 30B | 1322 / 1420 | **93.1%** |
| **2** | 🌟 **BaaB Next 1B (Pretrain 2K)** | **1B** | **1298 / 1420** | **91.4%** |
| 3 | BaaB Next 1B (Pretrain 4K) | 1B | 1280 / 1420 | 90.1% |
| 4 | codestral:22b | 22B | 1278 / 1420 | 90.0% |
| 5 | qwen2.5-coder:7b | 7B | 1267 / 1420 | 89.2% |
| 6 | qwen2.5-coder:3b | 3B | 1257 / 1420 | 88.5% |
| 7 | codegemma:2b | 2B | 1213 / 1420 | 85.4% |
| 8 | qwen2.5-coder:1.5b | 1.5B | 1212 / 1420 | 85.4% |
| 9 | starcoder2:3b | 3B | 1190 / 1420 | 83.8% |
| 10 | granite-code:8b | 8B | 1180 / 1420 | 83.1% |
| 11 | granite-code:3b | 3B | 1170 / 1420 | 82.4% |
| 12 | deepseek-coder:1.3b | 1.3B | 1036 / 1420 | 73.0% |

Scores rounded to 1 decimal for the public leaderboard. Full-precision results live in [outputs/](outputs/).

**Note:** `BaaB Next 1B (Pretrain 4K)` corresponds to the CPT step-00008000 checkpoint, chosen as the production 4K base because it offers the best balance of short-eval retention (-1.3pp vs Pretrain 2K) and long-context lift (+23.4pp on the long-context suite, published separately).

---

## Per-category breakdown — BaaB Next 1B (Pretrain 2K)

| Category | Score | % |
|---|---:|---:|
| hooks | 105 / 108 | 97.2% |
| api-routes | 138 / 144 | 95.8% |
| form | 72 / 76 | 94.7% |
| auth | 79 / 84 | 94.0% |
| server-actions | 142 / 152 | 93.4% |
| nextjs | 179 / 192 | 93.2% |
| react | 144 / 156 | 92.3% |
| payments | 70 / 76 | 92.1% |
| tailwind | 90 / 104 | 86.5% |
| typescript | 93 / 108 | 86.1% |
| utils | 92 / 108 | 85.2% |
| database | 94 / 112 | 83.9% |
| **middleware** | **0 / 0** | **— (reserved, populated in v0.2)** |

---

## Signal breakdown — BaaB Next 1B (Pretrain 2K)

| Signal | Pass rate |
|---|---:|
| `pattern_hit` (every must_contain present) | 256 / 355 — 72.1% |
| `no_forbidden` (no must_not_contain present) | 350 / 355 — 98.6% |
| `regex_hit` (every must_match_regex matches) | 354 / 355 — 99.7% |
| `length_ok` (output line count in window) | 338 / 355 — 95.2% |

`pattern_hit` is the dominant signal — it captures whether the model produced the required API calls, imports, and identifiers. The other three signals approach ceiling.

---

## How to submit a result

1. Run `python run_eval.py --backend <backend> --model <your-model>` against this commit's `tasks/`.
2. Grade with `python grade.py --input outputs/<your-model>.jsonl`.
3. Open a PR adding your row to this table, including the output JSONL in `submissions/<your-model>.jsonl`. The output file must reproduce when re-graded.

**Required for inclusion:**

- Deterministic settings (`temperature=0.0`, `top_k=1`). Sampled scores will be rejected.
- Output file with one record per task, in NextBench v0.1 record format (`task_id` + `output` + `settings`).
- A reproducible model id (Ollama tag, HF repo, or model API id).

**Versioning:** When the task set changes (v0.1 → v0.2 → v1.0), prior scores are preserved in `LEADERBOARD_v0.1.md`. Current `LEADERBOARD.md` always tracks the latest task set.

---

## Provenance

The 355 tasks in NextBench v0.1 are the publicly-released form of the BaaB Labs internal 355-prompt battle suite, originally built and evaluated 2026-05-09. Schema migration to v1.0 was verified to produce identical per-task and aggregate scores against the original grader.

- Source tag: `baab-battle-v1`
- Migrator (source-of-truth): [scripts/convert_battle_to_nextbench.py](scripts/convert_battle_to_nextbench.py)
- Parity check: [scripts/smoke_test_parity.py](scripts/smoke_test_parity.py)
