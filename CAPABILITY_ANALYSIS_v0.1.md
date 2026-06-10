# NextBench v0.1 — Capability Analysis

**Generated:** 2026-06-08
**Tasks analysed:** 409

## What this measures

355 tasks in NextBench v0.1 — but how many *distinct capabilities* is that?
This analysis answers the question directly, before any v0.2 expansion is planned.

Three signals are combined:

1. **Subcategory clustering** — tasks share a subcategory iff they probe the same named pattern (`react.copy`, `database.prisma_model`, etc.). One subcategory ≈ one capability bucket.
2. **Check signature** — tasks with identical sorted-lowered `must_contain` sets grade the same surface pattern.
3. **Prompt Jaccard similarity** — within a subcategory cluster, average pairwise Jaccard on prompt tokens. High value (≥0.50) means prompts differ only in entity/prop names, not capability.

## Headline numbers

| Metric | Value |
|---|---:|
| Total tasks | 409 |
| Distinct subcategory buckets (capabilities) | **240** |
| Capability density (subcategories / tasks) | **0.59** |
| Singleton subcategories (1 task each) | 197 (197 tasks) |
| Subcategories of size ≥4 (template-cloned) | 37 (196 tasks) |
| Highly redundant clusters (size≥4 AND Jaccard≥0.50) | 37 (196 tasks) |

**Interpretation:**

- NextBench v0.1 contains **409 tasks across 240 subcategory buckets** — a capability density of 0.59.
- **196 of 409 tasks (48%) live in highly redundant clusters** (size ≥4 with mean intra-cluster prompt Jaccard ≥ 0.50). These tasks are likely template-cloned variations of the same underlying capability and contribute to *coverage* but not *capability differentiation*.
- The effective capability count of NextBench v0.1 is closer to **240** than to 409.

## Cluster size distribution

How many subcategories contain N tasks each:

| Tasks per subcategory | # subcategories | Total tasks in this size |
|---:|---:|---:|
| 1 | 197 | 197 |
| 2 | 2 | 4 |
| 3 | 4 | 12 |
| 4 | 18 | 72 |
| 5 | 6 | 30 |
| 6 | 7 | 42 |
| 8 | 4 | 32 |
| 10 | 2 | 20 |

## Per-category capability density

Categories with **low density** (many tasks per subcategory) are template-heavy; categories with **high density** (≈1 task per subcategory) cover more distinct capabilities.

| Category | Tasks | Subcategories | Density | Clusters ≥4 | Tasks in clusters ≥4 |
|---|---:|---:|---:|---:|---:|
| `nextjs` | 62 | 27 | 0.44 | 7 | 40 |
| `react` | 52 | 32 | 0.62 | 6 | 26 |
| `api-routes` | 43 | 16 | 0.37 | 6 | 33 |
| `server-actions` | 42 | 10 | 0.24 | 6 | 38 |
| `database` | 34 | 17 | 0.50 | 3 | 18 |
| `hooks` | 27 | 27 | 1.00 | 0 | 0 |
| `typescript` | 27 | 17 | 0.63 | 2 | 12 |
| `utils` | 27 | 27 | 1.00 | 0 | 0 |
| `tailwind` | 26 | 16 | 0.62 | 3 | 13 |
| `auth` | 23 | 13 | 0.57 | 2 | 8 |
| `form` | 19 | 16 | 0.84 | 1 | 4 |
| `payments` | 19 | 14 | 0.74 | 1 | 4 |
| `middleware` | 8 | 8 | 1.00 | 0 | 0 |

## Top redundant clusters (v0.2 deduplication candidates)

Subcategories with **size ≥4 AND mean prompt Jaccard ≥ 0.50**. These are the strongest candidates for capability deduplication in v0.2 — keep one or two representatives per cluster, retire the rest.

| Category | Subcategory | Tasks | Mean prompt Jaccard | Distinct check signatures |
|---|---|---:|---:|---:|
| `server-actions` | `create_zod` | 10 | 0.87 | 10 |
| `database` | `prisma_model` | 10 | 0.60 | 1 |
| `api-routes` | `get_list` | 8 | 0.90 | 8 |
| `server-actions` | `update_zod` | 8 | 0.88 | 8 |
| `nextjs` | `dynamic_page` | 8 | 0.83 | 8 |
| `typescript` | `interface` | 8 | 0.78 | 1 |
| `api-routes` | `post_create` | 6 | 0.93 | 6 |
| `api-routes` | `get_single` | 6 | 0.91 | 6 |
| `server-actions` | `archive` | 6 | 0.87 | 6 |
| `server-actions` | `delete` | 6 | 0.87 | 6 |
| `nextjs` | `layout_metadata` | 6 | 0.85 | 1 |
| `nextjs` | `search_params` | 6 | 0.81 | 6 |
| `nextjs` | `loading` | 6 | 0.75 | 2 |
| `api-routes` | `auth_gated` | 5 | 0.89 | 1 |
| `nextjs` | `error_boundary` | 5 | 0.89 | 1 |
| `react` | `copy` | 5 | 0.85 | 1 |
| `nextjs` | `generate_metadata` | 5 | 0.75 | 5 |
| `react` | `card` | 5 | 0.69 | 1 |
| `tailwind` | `hero` | 5 | 0.67 | 1 |
| `payments` | `stripe_portal` | 4 | 1.00 | 1 |
| `tailwind` | `alert_variant` | 4 | 1.00 | 1 |
| `database` | `drizzle_schema` | 4 | 0.91 | 1 |
| `api-routes` | `rate_limit` | 4 | 0.87 | 1 |
| `server-actions` | `transaction` | 4 | 0.87 | 4 |
| `api-routes` | `webhook` | 4 | 0.87 | 4 |
| `auth` | `nextauth_config` | 4 | 0.87 | 4 |
| `server-actions` | `formdata` | 4 | 0.86 | 1 |
| `nextjs` | `not_found` | 4 | 0.86 | 1 |
| `tailwind` | `pricing_card` | 4 | 0.83 | 1 |
| `database` | `prisma_relations` | 4 | 0.83 | 4 |
| `form` | `use_form_status` | 4 | 0.82 | 4 |
| `react` | `counter` | 4 | 0.82 | 1 |
| `react` | `toggle` | 4 | 0.82 | 1 |
| `auth` | `protected_component` | 4 | 0.77 | 1 |
| `react` | `empty_state` | 4 | 0.67 | 1 |
| `react` | `skeleton` | 4 | 0.60 | 1 |
| `typescript` | `type_guard` | 4 | 0.52 | 4 |

## v0.2 implications

1. **Capability dedup before expansion.** Retire ~75% of the tasks in each high-redundancy cluster (keep 1–2 representative variants). Replaces template inflation with capability breadth.
2. **Headline target updated.** v0.2 target is no longer "355 → 1000 tasks" but "~250 → ~600 capabilities". The right metric to grow is *distinct subcategories*, not *task count*.
3. **Expansion priority.** Categories with the lowest subcategory density (`react`, `nextjs`, `server-actions`, `database`) need more *diverse* tasks, not more *similar* ones.
4. **Future task generation rule.** When generating candidate tasks for `candidates/`, no more than 2 tasks per subcategory unless each tests a meaningfully different sub-capability (different patterns, different check signatures).

## Reproduce

```
python nextbench/scripts/capability_analysis.py
```

Re-runs deterministically against the current `tasks/` directory.
