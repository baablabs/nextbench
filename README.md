---
license: mit
language:
  - en
  - code
tags:
  - code-generation
  - code-completion
  - next-js
  - react
  - typescript
  - benchmark
  - evaluation
size_categories:
  - n<1K
task_categories:
  - text-generation
pretty_name: NextBench
configs:
  - config_name: default
    data_files:
      - split: react
        path: tasks/react.jsonl
      - split: hooks
        path: tasks/hooks.jsonl
      - split: nextjs
        path: tasks/nextjs.jsonl
      - split: server_actions
        path: tasks/server-actions.jsonl
      - split: api_routes
        path: tasks/api-routes.jsonl
      - split: form
        path: tasks/form.jsonl
      - split: tailwind
        path: tasks/tailwind.jsonl
      - split: typescript
        path: tasks/typescript.jsonl
      - split: auth
        path: tasks/auth.jsonl
      - split: payments
        path: tasks/payments.jsonl
      - split: database
        path: tasks/database.jsonl
      - split: utils
        path: tasks/utils.jsonl
dataset_info:
  features:
    - name: task_id
      dtype: string
    - name: task_type
      dtype: string
    - name: category
      dtype: string
    - name: subcategory
      dtype: string
    - name: difficulty
      dtype: string
    - name: tags
      sequence: string
    - name: file_path
      dtype: string
    - name: prompt
      dtype: string
    - name: context
      struct:
        - name: prefix
          dtype: string
        - name: cursor_position
          dtype: int64
        - name: suffix
          dtype: string
    - name: checks
      struct:
        - name: static
          struct:
            - name: must_contain
              sequence: string
            - name: must_not_contain
              sequence: string
            - name: must_match_regex
              sequence: string
            - name: min_lines
              dtype: int64
            - name: max_lines
              dtype: int64
        - name: execution
          dtype: string
        - name: judge
          dtype: string
    - name: metadata
      struct:
        - name: source
          dtype: string
        - name: schema_version
          dtype: string
        - name: benchmark_version
          dtype: string
        - name: license
          dtype: string
        - name: created
          dtype: string
        - name: legacy_id
          dtype: string
        - name: judge_brief
          dtype: string
---

# NextBench

**The benchmark for modern Next.js code generation and completion.**

NextBench measures how well a language model can complete real-world Next.js / React / TypeScript code. Every task is an autocomplete prompt — a partial file with the cursor at the end — graded against deterministic checks: must-contain patterns, forbidden patterns, regex matches, and output length.

- **355 tasks** across 13 categories (v0.1)
- **Deterministic scoring** — no LLM judge, no subjectivity, full reproducibility
- **Completion-shaped** — tasks model what real Next.js development looks like inside an IDE
- **Open source** — MIT-licensed tasks and tooling

NextBench is maintained by [BaaB Labs](https://huggingface.co/baablabs) but is benchmark-first: model entries from any lab are welcome.

---

## Quick start

```bash
git clone https://github.com/baablabs/nextbench
cd nextbench

# Evaluate any Ollama-hosted model:
python run_eval.py --backend ollama --model qwen2.5-coder:7b

# Or any OpenAI-compatible API:
OPENAI_API_KEY=sk-... python run_eval.py \
    --backend openai --model gpt-4o-mini

# Grade and view the leaderboard-style report:
python grade.py --input outputs/qwen2.5-coder_7b.jsonl
```

Output:

```
OVERALL: 1267/1420 = 89.23%

By category:
   105/ 108   97.2%   hooks
   138/ 144   95.8%   api-routes
   ...
```

---

## Load from Hugging Face

```python
from datasets import load_dataset

# Load every category as a separate split:
ds = load_dataset("baablabs/nextbench")
print(ds)
# DatasetDict with splits: react, hooks, nextjs, server_actions, api_routes,
#                          form, tailwind, typescript, auth, payments,
#                          database, utils
# (middleware category is reserved for v0.2; not loadable until populated)

# Load a single category:
react_tasks = load_dataset("baablabs/nextbench", split="react")
api_routes = load_dataset("baablabs/nextbench", split="api_routes")
server_actions = load_dataset("baablabs/nextbench", split="server_actions")
```

**Split naming note:** HF Datasets split names can't contain hyphens, so `server-actions` and `api-routes` (as they appear in the `category` field) map to `server_actions` and `api_routes` as split names. The raw JSONL files keep their canonical hyphenated names.

---

## Task schema (v1.0)

```jsonl
{
  "task_id": "react.copy_button.001",
  "task_type": "completion",
  "category": "react",
  "subcategory": "copy_button",
  "difficulty": "trivial",
  "tags": ["typescript", "client-component", "react-hook", "event-handler"],
  "file_path": "components/CopyButton.tsx",
  "prompt": "'use client'\nimport { useState } from 'react'\n\nexport default function CopyButton({ text }: { text: string }) {",
  "context": {
    "prefix": "<same as prompt for v0.1>",
    "cursor_position": 142,
    "suffix": ""
  },
  "checks": {
    "static": {
      "must_contain": ["useState", "clipboard", "onClick"],
      "must_not_contain": [],
      "must_match_regex": [],
      "min_lines": 4,
      "max_lines": 18
    },
    "execution": null,
    "judge": null
  },
  "metadata": {
    "source": "baab-battle-v1",
    "schema_version": "1.0",
    "benchmark_version": "0.1",
    "license": "MIT"
  }
}
```

**Schema future-proofing:** `checks.execution` (TypeScript compile + light runtime tests) and `checks.judge` (optional rubric) slots exist now but are `null` in v0.1. They'll be populated in v0.2 / v1.0 without breaking the schema.

**Task types:** `completion` (v0.1, autocomplete from a prefix) → future `infill`, `instruction`, `agent`. One benchmark, multiple task types.

---

## Categories (v0.1)

| Category | Tasks | Description |
|---|---:|---|
| `react` | 39 | Client components, hooks usage, event handlers, common UI primitives |
| `hooks` | 27 | Custom hooks (`useDebounce`, `useLocalStorage`, `useClickOutside`, …) |
| `nextjs` | 48 | App Router primitives — pages, layouts, metadata, error/loading, OG images, sitemap, robots |
| `server-actions` | 38 | Server actions for CRUD, Zod-validated mutations, FormData handling, transactions |
| `api-routes` | 36 | Route handlers — GET/POST/PATCH/DELETE, auth-gated, webhooks, rate limiting |
| `form` | 19 | Controlled forms, React Hook Form integration, useFormStatus patterns |
| `tailwind` | 26 | UI sections — heroes, pricing cards, navbars, dashboards, feature grids |
| `typescript` | 27 | Utility types, type guards, branded ids, discriminated unions, inference helpers |
| `auth` | 21 | NextAuth v5 — providers, callbacks, middleware, protected pages, role guards |
| `payments` | 19 | Stripe, Razorpay, Paddle, Lemon Squeezy, Dodo, Cashfree |
| `database` | 28 | Prisma & Drizzle — schemas, queries, relations, transactions, pagination |
| `utils` | 27 | Pure helpers — `cn`, `debounce`, `formatCurrency`, `slugify`, `safeJsonParse`, … |
| `middleware` | 0 | Empty in v0.1; populated during expansion |
| **Total** | **355** | |

---

## Scoring

Each task is scored 0-4 on four binary signals against `checks.static`:

| Signal | Definition |
|---|---|
| `pattern_hit` | Every `must_contain` substring appears in the output (case-insensitive). |
| `no_forbidden` | No `must_not_contain` substring appears. |
| `regex_hit` | Every `must_match_regex` pattern matches the output (case-insensitive, multiline). |
| `length_ok` | Output line count is within `[min_lines, max_lines]`. For tight bounds (`max_lines ≤ 6`) both bounds are enforced; otherwise only the lower bound. |

Aggregate score = sum across all tasks / `(4 × N_tasks)`. NextBench v0.1 max = `4 × 355 = 1420`.

`checks.execution` and `checks.judge` slots are reserved for future versions; v0.1 grader ignores them.

---

## Submitting a result

1. Run `python run_eval.py --backend <backend> --model <your-model>` (or implement your own backend — see [run_eval.py](run_eval.py)).
2. Grade with `python grade.py --input outputs/<your-model>.jsonl`.
3. Open a PR adding your row to [LEADERBOARD.md](LEADERBOARD.md) and including the output JSONL at `submissions/<your-model>.jsonl`. The submission must reproduce when re-graded.

**Requirements:**

- Deterministic settings (`temperature=0.0`, `top_k=1`). Sampled scores are rejected.
- A reproducible model id (Ollama tag, HF repo, or API model id).
- Output JSONL must include the original task fields plus `output` and `settings`.

---

## Versioning

| Version | Tasks | Status |
|---|---:|---|
| v0.1 | 355 | Current — completion-only |
| v0.2 (planned) | ~1000 | Expansion focused on coverage (data tables, charts, file upload, animations, real-time, i18n, search, RAG). |
| v1.0 (planned) | ~2500 | Multi-task-type — adds infill and instruction tasks. Optional `execution` checks for a subset (TypeScript compile + light runtime). |

Schema is independent of benchmark version: `schema_version` only bumps if the per-record structure changes. `benchmark_version` bumps with each task-set release.

---

## License

- Tasks: **MIT** (use freely, including in commercial training and evaluation).
- Tooling (`run_eval.py`, `grade.py`, scripts): **MIT**.

---

## Citation

```bibtex
@misc{nextbench2026,
  title         = {NextBench: A Benchmark for Next.js Code Completion},
  author        = {BaaB Labs},
  year          = {2026},
  howpublished  = {\url{https://github.com/baablabs/nextbench}},
}
```

---

## Related

- **BaaB Next** — the model family this benchmark grew out of. Current best: `baab-next-1b-pretrain-4k`.
- **BaaB Playground** — interactive completion playground (Phase 2).
- **BaaB for VS Code** — editor extension (Phase 3).
