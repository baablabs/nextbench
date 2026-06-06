# NextBench v0.1 — Benchmark Report

**The benchmark for modern Next.js code generation and completion.**

NextBench measures how well language models complete real-world Next.js / React / TypeScript code. Every task is an autocomplete prompt — a partial file with the cursor at the end — graded against deterministic checks. No LLM judge, no subjectivity, full reproducibility.

- **355 tasks** across 13 categories
- **12-model benchmark panel** spanning 1.3B to 30B parameters
- **Deterministic scoring** — 4 binary signals per task, 1420 max points
- **MIT licensed** — tasks, tooling, and outputs

Maintained by [BaaB Labs](https://baablabs.com). Benchmark-first: contributions from any lab welcome.

---

## Headline ranking

12 models evaluated under matched settings (`temperature=0.0`, `top_k=1`, `max_tokens=500`, `num_ctx=4096`, raw completion — no chat template).

| Rank | Model | Params | Score | % |
|---:|---|---:|---:|---:|
| 1 | qwen3-coder:30b (MoE) | 30B | 1322 / 1420 | **93.1%** |
| **2** | **BaaB Next 1B (Pretrain 2K)** | **1B** | **1298 / 1420** | **91.4%** |
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

**Observations:**

- A 1B specialist (BaaB Next, trained from scratch on a Next.js corpus) ranks #2 — beating every production code model under 30B parameters.
- The 30B model holds a 1.7pp lead over the 1B specialist. The 22B general code model trails the 1B specialist by 1.4pp.
- Under-3B general code models cluster at 73–85%. The threshold for "fluent in modern Next.js completion" sits around 85% on this suite.

---

## What NextBench tests

13 categories, 355 tasks. Each task is a partial Next.js / TypeScript file ending mid-function; the model must complete it.

| Category | Tasks | Probes |
|---|---:|---|
| `react` | 39 | Client components, hooks usage, event handlers, common UI primitives |
| `hooks` | 27 | Custom hooks — `useDebounce`, `useLocalStorage`, `useClickOutside`, etc. |
| `nextjs` | 48 | App Router primitives — pages, layouts, metadata, error/loading, OG images, sitemap |
| `server-actions` | 38 | Server actions for CRUD, Zod-validated mutations, FormData, transactions |
| `api-routes` | 36 | Route handlers — GET/POST/PATCH/DELETE, auth-gated, webhooks, rate limiting |
| `form` | 19 | Controlled forms, React Hook Form, `useFormStatus` |
| `tailwind` | 26 | UI sections — heroes, pricing, navbars, dashboards |
| `typescript` | 27 | Utility types, type guards, branded ids, discriminated unions, inference |
| `auth` | 21 | NextAuth v5 — providers, callbacks, middleware, protected pages, role guards |
| `payments` | 19 | Stripe, Razorpay, Paddle, Lemon Squeezy, Dodo, Cashfree |
| `database` | 28 | Prisma & Drizzle — schemas, queries, relations, transactions, pagination |
| `utils` | 27 | Pure helpers — `cn`, `debounce`, `formatCurrency`, `slugify`, `safeJsonParse` |
| `middleware` | 0 | Reserved for v0.2 |
| **Total** | **355** | |

Tasks span three difficulty tiers: **63 trivial / 238 mid / 54 hard**.

---

## How tasks are scored

Each task ships with `checks.static`:

| Signal | Definition |
|---|---|
| `pattern_hit` | Every `must_contain` substring appears in the model output (case-insensitive). |
| `no_forbidden` | No `must_not_contain` substring appears. |
| `regex_hit` | Every `must_match_regex` pattern matches (case-insensitive, multiline). |
| `length_ok` | Output line count within `[min_lines, max_lines]`. Tight upper bounds (≤6) enforce both ends. |

Score per task: 0–4. Suite total: 4 × 355 = **1420**.

Two further check slots are reserved in the schema (`checks.execution` for TypeScript compile + light runtime tests; `checks.judge` for human-reviewed rubrics). Both are `null` in v0.1 and ignored by the grader. They'll be populated in v0.2 / v1.0 without schema break.

**No LLM judge in v0.1.** Reproducibility was the design priority. LLM-judged scores invite the question "which judge, which temperature, which model" — questions that have no good answer when the goal is a benchmark anyone can re-run on a laptop in five minutes.

---

## Design choices

**Completion-shaped, not chat-shaped.** Every task is a prefix the model must continue. This matches how Next.js development actually happens — in an IDE, mid-file, with a cursor. Tasks include `file_path` (where the file would live in a Next.js project) and `context.cursor_position` so future infill task types slot in cleanly.

**One benchmark, multiple task types.** Schema includes `task_type: "completion" | "infill" | "instruction" | "agent"`. v0.1 is completion-only; v0.2 will add `infill` and a small `instruction` subset. One leaderboard, multiple ways of measuring.

**Static checks first, execution next.** Static substring/regex checks catch the patterns that matter for Next.js code (correct imports, correct API calls, correct directives like `'use client'`). They're cheap, deterministic, and run in milliseconds. v0.2 will add execution checks for a curated subset where running the code adds signal beyond pattern matching.

**Subcategories + tags.** Every task carries `category`, `subcategory`, and a `tags` array. This enables slicing like "best `client-component` score" or "best `prisma` score" that single-category benchmarks can't produce.

**Two layers of versioning.** `schema_version` (per record) and `benchmark_version` (per task-set release) move independently. v0.1 → v0.2 grows the task set without breaking the schema.

---

## Self-audit: discrimination analysis

A benchmark that gives every model the same score doesn't rank anything. We measured how well each NextBench task differentiates between models in the 12-model panel.

**Method:** for each task, we computed the standard deviation of scores across the panel. Tasks with std ≤ 0.2 (and mean ≥ 3.95) are *saturated* — every model aces them. Tasks where no model passes are *impossible*. Tasks with high std are *high-signal* — they define the leaderboard.

**Result:**

| Bucket | Tasks | % of suite |
|---|---:|---:|
| Saturated (zero ranking signal) | 26 | 7.3% |
| Low signal (std < 0.4) | 86 | 24.2% |
| Mid signal (0.4 ≤ std < 0.7) | 209 | 58.9% |
| High signal (std ≥ 0.7) | 34 | 9.6% |
| Impossible (no model passes) | 0 | 0.0% |

**Interpretation:**

- **Zero impossible tasks.** No checks are broken; no task is structurally unfair.
- **68.5% of the suite (mid + high signal) carries meaningful ranking signal.** Healthy for a v0.1.
- **34 high-signal tasks (9.6%) drive most leaderboard separation.** v0.2 will replicate these patterns at scale.
- **26 saturated tasks (7.3%) add no separation power.** They're candidates for retirement or for tightening checks in v0.2.

**Per-category discrimination:**

| Category | High signal | High-signal rate |
|---|---:|---:|
| `api-routes` | 9 of 36 | 25.0% |
| `auth` | 7 of 21 | 33.3% |
| `form` | 6 of 19 | 31.6% |
| `payments` | 6 of 19 | 31.6% |
| `hooks` | 4 of 27 | 14.8% |
| `react` | 1 of 39 | 2.6% |
| `server-actions` | 1 of 38 | 2.6% |
| `nextjs` | 0 of 48 | 0.0% |
| `typescript` | 0 of 27 | 0.0% |
| `database` | 0 of 28 | 0.0% |
| `utils` | 0 of 27 | 0.0% |
| `tailwind` | 0 of 26 | 0.0% |

**`auth`, `form`, `payments`, `api-routes` are NextBench's discriminating spine** — these categories separate production code models most sharply. `nextjs`, `typescript`, `database`, `utils`, `tailwind` cover well but produce broad agreement among production-grade models; they need harder examples in v0.2.

This analysis informs the v0.2 expansion plan, not v0.1 ranking.

Full per-task statistics: [outputs/_discrimination_per_task.jsonl](outputs/_discrimination_per_task.jsonl). Methodology and named lists: [ANALYSIS_v0.1.md](ANALYSIS_v0.1.md). Reproducible: `python scripts/discrimination_analysis.py`.

---

## What's next

| Version | Target | Notes |
|---|---|---|
| **v0.1** (now) | 355 tasks, completion-only | Current. The base benchmark — published, scoreable, MIT. |
| **v0.2** | ~600 tasks | Coverage expansion focused on under-discriminating categories (typescript, tailwind, database, utils, nextjs). Adds the first `infill` tasks. Retires the 26 saturated v0.1 tasks. |
| **v1.0** | ~1000–1500 tasks | Adds `execution` checks for ~30% of tasks (TypeScript compile + light runtime). First `instruction` task type. |

Expansion is curation-driven, not generation-driven: candidate tasks are reviewed and discrimination-tested before promotion. Throughput target is quality over quantity.

---

## How to submit a result

1. Run the eval against your model:
   ```
   python run_eval.py --backend ollama --model <your-model>
   # or
   OPENAI_API_KEY=... python run_eval.py --backend openai --model <your-model>
   ```
2. Grade the output:
   ```
   python grade.py --input outputs/<your-model>.jsonl
   ```
3. Open a PR adding your row to [LEADERBOARD.md](LEADERBOARD.md), include the output JSONL at `submissions/<your-model>.jsonl`. The submission must reproduce when re-graded.

**Requirements:** deterministic settings (`temperature=0.0`, `top_k=1`), a reproducible model identifier, output JSONL containing the original task fields plus `output` and `settings`.

---

## Reproducing this report

Every number in this document is reproducible:

```
# Leaderboard:                python grade.py --input outputs/*.jsonl --compare
# Discrimination analysis:    python scripts/discrimination_analysis.py
# Parity (vs legacy grader):  python scripts/smoke_test_parity.py
```

Per-model outputs, grader, runner, and analysis scripts all live in this repo. No hidden infrastructure.

---

## Provenance

NextBench v0.1 is the public release of a 355-prompt internal evaluation suite originally built and run by BaaB Labs on 2026-05-09 to evaluate the BaaB Next 1B base model against 10 production code models.

The schema was migrated to v1.0 (JSONL, nested `checks` blocks, completion-context fields, tags, task types) and parity-verified: re-grading the original BaaB Next 1B outputs through the new grader produces identical scores at every level — overall (91.4%), per category, per signal. The legacy 355-prompt suite is therefore *the same benchmark* as NextBench v0.1, just in a public, schema-versioned, HF-Hub-distributable form.

---

## License & citation

MIT licensed (tasks + tooling). Use freely, including in commercial training and evaluation.

```bibtex
@misc{nextbench2026,
  title         = {NextBench: A Benchmark for Next.js Code Completion},
  author        = {BaaB Labs},
  year          = {2026},
  howpublished  = {\url{https://github.com/baablabs/nextbench}},
}
```

---

**BaaB Labs** — [baablabs.com](https://baablabs.com)
