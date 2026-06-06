# NextBench v0.1 — Discrimination Analysis

**Generated:** 2026-06-06
**Panel:** 12 models (10 external production code models + 2 BaaB Next checkpoints)
**Tasks analysed:** 355 of 355

## Purpose

For each task, this analysis asks: **does the task separate models, or do all models score the same?**
Tasks where every model scores 4/4 add no ranking signal; tasks where every model scores 0/4 are either
impossible or have a broken check. Both are candidates for retirement or replacement in v0.2.

Each task is classified by the standard deviation of its scores across the 12-model panel:

| Bucket | Condition | Meaning |
|---|---|---|
| `saturated` | mean ≥ 3.95 AND std ≤ 0.2 | Every model aces it. Zero ranking signal. |
| `impossible` | mean ≤ 0.5 AND std ≤ 0.5 | No model passes. Likely a broken check or unfair task. |
| `low_signal` | std < 0.40 | Bottom-quartile dispersion; narrow info. |
| `mid_signal` | 0.40 ≤ std < 0.70 | Healthy differentiation. |
| `high_signal` | std ≥ 0.70 | Top-decile differentiator — keep, replicate the pattern. |

Thresholds calibrated against the actual std distribution of the 12-model panel on the 355 v0.1 tasks (p25=0.37, p50=0.47, p90=0.69, max=1.19).

## Panel

- `codegemma:2b`
- `codestral:22b`
- `deepseek-coder:1.3b`
- `granite-code:3b`
- `granite-code:8b`
- `qwen2.5-coder:1.5b`
- `qwen2.5-coder:3b`
- `qwen2.5-coder:7b`
- `qwen3-coder:30b`
- `starcoder2:3b`
- `BaaB Next 1B (Pretrain 2K)`
- `BaaB Next 1B (Pretrain 4K)`

## Bucket distribution

| Bucket | Tasks | % of suite |
|---|---:|---:|
| `saturated` | 26 | 7.3% |
| `low_signal` | 86 | 24.2% |
| `impossible` | 0 | 0.0% |
| `mid_signal` | 209 | 58.9% |
| `high_signal` | 34 | 9.6% |

### Headline

- **243 tasks (68.5%)** carry real ranking signal (mid + high).
- **26 tasks (7.3%)** are saturated — every panel model scores 4/4. Candidates for retirement.
- **0 tasks (0.0%)** are impossible — no panel model passes. Audit before v0.2 (broken check vs legitimate ceiling).
- **86 tasks (24.2%)** are low-signal (narrow band, std < 0.5).

## Per-category breakdown

Counts of how many tasks in each category fall into each bucket. Categories with many `saturated` or `low_signal` tasks are the ones to thicken with harder examples in v0.2; categories already heavy in `mid_signal` / `high_signal` are doing their job.

| Category | Total | `saturated` | `low_signal` | `impossible` | `mid_signal` | `high_signal` |
|---|---:|---:|---:|---:|---:|---:|
| nextjs | 48 | 5 | 16 | 0 | 27 | 0 |
| react | 39 | 6 | 13 | 0 | 19 | 1 |
| server-actions | 38 | 0 | 5 | 0 | 32 | 1 |
| api-routes | 36 | 0 | 5 | 0 | 22 | 9 |
| database | 28 | 2 | 6 | 0 | 20 | 0 |
| hooks | 27 | 2 | 8 | 0 | 13 | 4 |
| typescript | 27 | 4 | 11 | 0 | 12 | 0 |
| utils | 27 | 5 | 7 | 0 | 15 | 0 |
| tailwind | 26 | 1 | 6 | 0 | 19 | 0 |
| auth | 21 | 0 | 4 | 0 | 10 | 7 |
| form | 19 | 1 | 1 | 0 | 11 | 6 |
| payments | 19 | 0 | 4 | 0 | 9 | 6 |

## Saturated tasks (zero ranking signal)

All 26 listed below. Every panel model scored 4/4.

| task_id | category | difficulty |
|---|---|---|
| `database.prisma_pagination.021` | database | mid |
| `database.prisma_pagination.022` | database | mid |
| `form.rhf_signin.002` | form | hard |
| `hooks.useMounted.018` | hooks | trivial |
| `hooks.useToggle_tuple.001` | hooks | trivial |
| `nextjs.generate_metadata.037` | nextjs | mid |
| `nextjs.not_found.027` | nextjs | trivial |
| `nextjs.not_found.028` | nextjs | trivial |
| `nextjs.not_found.029` | nextjs | trivial |
| `nextjs.not_found.030` | nextjs | trivial |
| `react.copy.002` | react | trivial |
| `react.copy.003` | react | trivial |
| `react.copy.005` | react | trivial |
| `react.counter.006` | react | trivial |
| `react.counter.008` | react | trivial |
| `react.rating_stars.036` | react | mid |
| `tailwind.section_header.023` | tailwind | mid |
| `typescript.interface.002` | typescript | trivial |
| `typescript.interface.004` | typescript | trivial |
| `typescript.interface.007` | typescript | trivial |
| `typescript.interface.008` | typescript | trivial |
| `utils.debounce_fn.007` | utils | mid |
| `utils.format_bytes.001` | utils | trivial |
| `utils.safe_json_parse.008` | utils | trivial |
| `utils.shallow_equal.025` | utils | mid |
| `utils.slugify.003` | utils | trivial |

## Impossible tasks (no panel model passes)

_None._

## Top 20 highest-discrimination tasks (gold)

These tasks differentiate models the most. They define the shape of the leaderboard. v0.2 should replicate the *patterns* underneath them.

| task_id | category | difficulty | mean | std | spread |
|---|---|---|---:|---:|---:|
| `api-routes.webhook.022` | api-routes | hard | 2.917 | 1.187 | 3 |
| `auth.protected_component.007` | auth | mid | 3 | 1.0 | 2 |
| `auth.protected_component.009` | auth | mid | 3 | 1.0 | 2 |
| `auth.protected_component.006` | auth | mid | 3.083 | 0.954 | 2 |
| `form.use_form_status.007` | form | mid | 3.083 | 0.954 | 2 |
| `api-routes.webhook.021` | api-routes | hard | 3.333 | 0.943 | 3 |
| `api-routes.auth_gated.026` | api-routes | mid | 3.167 | 0.898 | 2 |
| `auth.protected_component.008` | auth | mid | 3.167 | 0.898 | 2 |
| `form.use_form_status.005` | form | mid | 3.167 | 0.898 | 2 |
| `api-routes.auth_gated.029` | api-routes | mid | 3.083 | 0.862 | 2 |
| `react.avatar.021` | react | mid | 2.917 | 0.862 | 2 |
| `hooks.useClickOutside.005` | hooks | mid | 3.667 | 0.85 | 3 |
| `form.use_form_status.006` | form | mid | 3.25 | 0.829 | 2 |
| `hooks.useLocalStorage.003` | hooks | mid | 3.75 | 0.829 | 3 |
| `api-routes.auth_gated.027` | api-routes | mid | 3.167 | 0.799 | 2 |
| `api-routes.auth_gated.028` | api-routes | mid | 3.167 | 0.799 | 2 |
| `form.multi_step.010` | form | hard | 3.167 | 0.799 | 2 |
| `payments.paddle_checkout.014` | payments | hard | 3.5 | 0.764 | 2 |
| `api-routes.auth_gated.025` | api-routes | mid | 3.583 | 0.759 | 2 |
| `api-routes.webhook.023` | api-routes | hard | 2.583 | 0.759 | 3 |

## Findings & recommendations for v0.2

1. **Retirement candidates:** the saturated tasks above contribute nothing to model ranking. Either retire them or rewrite their checks to demand more (tighter `must_match_regex`, additional `must_contain`).
2. **Audit impossible tasks:** if the check is broken, fix it. If the model class is the issue, document it and keep — these become aspirational benchmarks for next-gen models.
3. **Categories light on signal:** any category with >50% saturated+low_signal tasks needs new harder prompts in v0.2.
4. **Replicate the gold patterns:** the top-20 high-signal tasks above show what *kinds* of prompts produce differentiation. New v0.2 tasks should be designed in those shapes — not random Claude-generated prompts.
5. **Coverage rebalancing:** combine this report with the category totals when planning v0.2's ~245 new tasks. Add to under-discriminating categories, not just under-represented ones.

## Reproduce

```
python nextbench/scripts/discrimination_analysis.py
```

Re-runs deterministically. Re-grades the legacy battle outputs via the NextBench grader — no model inference required.
