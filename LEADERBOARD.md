# NextBench Leaderboard

**Benchmark:** NextBench v0.2 (443 completion tasks, 16 categories)
**Settings:** `temperature=0.0`, `top_k=1`, `max_tokens=500`, `num_ctx=4096`, `raw=true` (bypass chat template)
**Last updated:** 2026-06-10

Scoring rubric: each task is graded against `checks.static.*` for four binary signals — `pattern_hit`, `no_forbidden`, `regex_hit`, `length_ok`. Max score per task = 4. Total max = 4 × 443 = **1772**.

To reproduce any row: `python run_eval.py --backend <backend> --model <model>` followed by `python grade.py --input outputs/<model>.jsonl`. The `outputs/` directory holds raw model outputs from a single full eval pass on the v0.2 corpus.

---

## Headline ranking

| Rank | Model | Params | Score | % |
|---:|---|---:|---:|---:|
| 1 | qwen3-coder:30b (MoE) | 30B | 1571 / 1772 | **88.7%** |
| 2 | codestral:22b | 22B | 1494 / 1772 | 84.3% |
| **3** | 🌟 **BaaB Next 1B (Pretrain 2K)** | **1B** | **1492 / 1772** | **84.2%** |
| 4 | qwen2.5-coder:7b | 7B | 1490 / 1772 | 84.1% |
| 5 | BaaB Next 1B (Pretrain 4K) | 1B | 1472 / 1772 | 83.1% |
| 6 | qwen2.5-coder:3b | 3B | 1463 / 1772 | 82.6% |
| 7 | codegemma:2b | 2B | 1398 / 1772 | 78.9% |
| 8 | qwen2.5-coder:1.5b | 1.5B | 1383 / 1772 | 78.1% |
| 9 | granite-code:8b | 8B | 1341 / 1772 | 75.7% |
| 10 | starcoder2:3b | 3B | 1327 / 1772 | 74.9% |
| 11 | granite-code:3b | 3B | 1303 / 1772 | 73.5% |
| 12 | deepseek-coder:1.3b | 1.3B | 1140 / 1772 | 64.3% |

Scores rounded to 1 decimal for the public leaderboard. Full-precision results live in [outputs/](outputs/).

**Headline:** The top 3 sit inside a 0.22pp band — codestral 22B at 84.3%, BaaB Next 1B at 84.2%, qwen2.5-coder 7B at 84.1%. Statistically indistinguishable, with a 22× parameter ratio between the leader and the 1B specialist. The next coherent step is the supervised fine-tuned BaaB Next, which will close the pattern_hit gap to the 30B leader.

**Note on Pretrain 4K:** `BaaB Next 1B (Pretrain 4K)` corresponds to the CPT step-00008000 checkpoint. It scores 1.1pp below Pretrain 2K on the short-form NextBench corpus but is the production base for any application that needs >2K context (see the long-context suite, published separately).

---

## v0.1 → v0.2 movement

The v0.2 corpus extends the v0.1 corpus from 355 → 443 tasks, retires the tasks the v0.1 panel saturated, and adds three new categories: `testing`, `performance`, and `typescript-advanced`. Headline movement is therefore not directly comparable — v0.2 is a harder corpus by construction.

| Model | v0.1 (355) | v0.2 (443) | Δ |
|---|---:|---:|---:|
| qwen3-coder:30b | 93.1% | 88.7% | -4.4pp |
| codestral:22b | 90.0% | 84.3% | -5.7pp |
| BaaB Next 1B (Pretrain 2K) | 91.4% | 84.2% | -7.2pp |
| qwen2.5-coder:7b | 89.2% | 84.1% | -5.1pp |
| BaaB Next 1B (Pretrain 4K) | 90.1% | 83.1% | -7.0pp |
| qwen2.5-coder:3b | 88.5% | 82.6% | -5.9pp |

Every model loses ground on v0.2 because the new categories (typescript-advanced, performance, testing) are deliberately harder and the saturated tasks that propped up v0.1 scores are gone. BaaB Next loses the most because its training data didn't cover the three new categories. Future model versions will be evaluated against the v0.2 corpus from the start.

---

## Per-category breakdown — BaaB Next 1B (Pretrain 2K)

| Category | Tasks | Score | % |
|---|---:|---:|---:|
| hooks | 25 | 97 / 100 | 97.0% |
| payments | 18 | 66 / 72 | 91.7% |
| react | 57 | 201 / 228 | 88.2% |
| server-actions | 52 | 181 / 208 | 87.0% |
| form | 23 | 80 / 92 | 87.0% |
| tailwind | 25 | 86 / 100 | 86.0% |
| nextjs | 52 | 177 / 208 | 85.1% |
| auth | 29 | 98 / 116 | 84.5% |
| typescript | 23 | 77 / 92 | 83.7% |
| api-routes | 37 | 122 / 148 | 82.4% |
| utils | 22 | 72 / 88 | 81.8% |
| performance | 9 | 28 / 36 | 77.8% |
| database | 32 | 97 / 128 | 75.8% |
| middleware | 20 | 59 / 80 | 73.8% |
| testing | 12 | 33 / 48 | 68.8% |
| typescript-advanced | 7 | 18 / 28 | 64.3% |

Categories new in v0.2 (testing, performance, typescript-advanced) are the bottom three on the BaaB Next sheet — expected, since they fall outside the bulk of the pretraining corpus. The pattern is consistent across all five top-tier models (qwen3-coder leads the new categories too).

---

## Internal ablation — BaaB Next 1B (Pretrain 4K v2)

A third BaaB Next checkpoint was evaluated as part of v0.2 development but is **not on the public leaderboard**: `baab-next-1b-pretrain-4k-v2` = `run8_1b_cpt4k/step-00010000`. It scored **82.9%** — 0.2pp below Pretrain 4K (step-00008000), suggesting the additional 2K CPT steps marginally degraded short-form completion quality while continuing to adapt to longer contexts. The current published 4K checkpoint (step-00008000) remains the recommended production base.

---

## Corpus signals

- **Top-3 within 0.22pp** — codestral 22B (84.31%), BaaB Next 1B (84.20%), qwen2.5-coder 7B (84.09%). Within statistical noise. Inverted-pass scan and tight-max-lines fixes leveled the playing field across the cluster.
- **0 saturated tasks** in v0.2 — every task that 12/12 models passed has been retired.
- **Discrimination spread** — bottom-quartile model at 64%, top-quartile at 84%+, leader at 88.7%. ~24pp dynamic range across the 12-model panel.

---

## How v0.2 was assembled

| Source | Tasks |
|---|---:|
| v0.1 corpus, retained | 278 |
| Retired in v0.1 dedup (saturated / redundant) | -77 |
| Generated this release (batches 002d–f, 003a–k) | +172 |
| Retired post-audit (saturated post-fix) | -7 |
| Retired post-audit (broken / brittle, never reached eval) | 0 |
| **v0.2 total** | **443** |

Retired tasks remain logged in `retired_v01.jsonl` for recovery and audit.

---

## Post-release notes (this version)

41 panel-impossible tasks were fixed during the v0.2 release cycle ([scripts/fix_v02_panel_brittleness.py](scripts/fix_v02_panel_brittleness.py)): brittleness fixes for arbitrary names and second-function expectations. A second pass found 14 tasks where tight `max_lines` (≤6) was penalising strong models that complete the target function then keep generating ([scripts/fix_v02_tight_max_lines.py](scripts/fix_v02_tight_max_lines.py)) — those tasks now use `max_lines=30`, dropping out of the grader's `TIGHT_MAX_THRESHOLD` regime. 7 tasks that became saturated post-fix were retired ([scripts/retire_v02_saturated.py](scripts/retire_v02_saturated.py)).
