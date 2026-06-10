#!/usr/bin/env python3
"""Capability density analysis for NextBench v0.1.

Answers the question: "355 tasks — how many distinct capabilities is that?"

Three signals, none on its own definitive but together informative:

1. SUBCATEGORY CLUSTERING
   Tasks share a subcategory iff they probe the same named pattern
   (e.g. `react.copy`, `database.prisma_model`). Cluster sizes >= 4
   are flagged as high-template-density.

2. CHECK SIGNATURE
   Tasks with the same sorted-lowered `must_contain` set are grading
   identical surface patterns. If many tasks have the same signature,
   they reward the same underlying skill.

3. PROMPT JACCARD SIMILARITY
   Within each subcategory cluster, compute pairwise token-set Jaccard
   on the prompt. High mean (>= 0.7) means the prompts differ only in
   entity names / props (template variation), not capability.

Output:
  - nextbench/outputs/_capability_per_subcategory.jsonl (per-cluster stats)
  - nextbench/CAPABILITY_ANALYSIS_v0.1.md             (human-readable report)

Usage:
  python nextbench/scripts/capability_analysis.py
"""
from __future__ import annotations

import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TASKS_DIR = ROOT / "nextbench" / "tasks"
OUT_JSONL = ROOT / "nextbench" / "outputs" / "_capability_per_subcategory.jsonl"
REPORT = ROOT / "nextbench" / "CAPABILITY_ANALYSIS_v0.1.md"

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def tokens(text: str) -> set[str]:
    return {t.lower() for t in TOKEN_RE.findall(text)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def mean_pairwise_jaccard(prompts: list[str]) -> float:
    """Average Jaccard over all unordered pairs in a cluster."""
    token_sets = [tokens(p) for p in prompts]
    if len(token_sets) < 2:
        return 1.0  # singleton: trivially "identical"
    pairs = []
    for i in range(len(token_sets)):
        for j in range(i + 1, len(token_sets)):
            pairs.append(jaccard(token_sets[i], token_sets[j]))
    return statistics.mean(pairs) if pairs else 1.0


def check_signature(task: dict) -> str:
    """A coarse fingerprint of what the static check grades."""
    static = task.get("checks", {}).get("static", {}) or {}
    mc = tuple(sorted(s.lower() for s in (static.get("must_contain") or [])))
    return "|".join(mc)


def main():
    # Load all tasks.
    tasks: list[dict] = []
    for p in sorted(TASKS_DIR.glob("*.jsonl")):
        with open(p) as f:
            for line in f:
                line = line.strip()
                if line:
                    tasks.append(json.loads(line))
    print(f"Loaded {len(tasks)} tasks")

    # ── 1. Subcategory clusters ──────────────────────────────────────────
    by_subcat: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for t in tasks:
        by_subcat[(t["category"], t["subcategory"])].append(t)

    n_subcats = len(by_subcat)
    print(f"Distinct (category, subcategory) buckets: {n_subcats}")
    print(f"Capability density: {n_subcats / len(tasks):.3f}  ({n_subcats} buckets / {len(tasks)} tasks)")

    # Cluster-size histogram
    size_hist: dict[int, int] = defaultdict(int)
    for cluster in by_subcat.values():
        size_hist[len(cluster)] += 1
    print(f"\nSubcategory cluster sizes:")
    for size in sorted(size_hist):
        n_clusters = size_hist[size]
        n_tasks_in_size = size * n_clusters
        print(f"  size {size}: {n_clusters} subcategories ({n_tasks_in_size} tasks)")

    # Singletons vs clusters of >= 4
    singletons = sum(1 for c in by_subcat.values() if len(c) == 1)
    clusters_ge4 = sum(1 for c in by_subcat.values() if len(c) >= 4)
    tasks_in_singletons = sum(len(c) for c in by_subcat.values() if len(c) == 1)
    tasks_in_clusters_ge4 = sum(len(c) for c in by_subcat.values() if len(c) >= 4)
    print(f"\nSingleton subcategories: {singletons}  ({tasks_in_singletons} tasks)")
    print(f"Subcategories of size >=4: {clusters_ge4}  ({tasks_in_clusters_ge4} tasks)")

    # ── 2. Per-cluster details: prompt similarity + check signatures ────
    per_subcat: list[dict] = []
    for (cat, sub), cluster in sorted(by_subcat.items()):
        prompts = [t["prompt"] for t in cluster]
        sims = mean_pairwise_jaccard(prompts) if len(cluster) >= 2 else None
        sigs = {check_signature(t) for t in cluster}
        per_subcat.append({
            "category": cat,
            "subcategory": sub,
            "n_tasks": len(cluster),
            "mean_prompt_jaccard": round(sims, 3) if sims is not None else None,
            "distinct_check_signatures": len(sigs),
            "task_ids": [t["task_id"] for t in cluster],
        })

    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSONL, "w") as f:
        for r in per_subcat:
            f.write(json.dumps(r) + "\n")
    print(f"\nWrote per-subcategory stats -> {OUT_JSONL.relative_to(ROOT)}")

    # ── 3. Capability buckets per category ──────────────────────────────
    by_category_buckets: dict[str, dict] = defaultdict(lambda: {"tasks": 0, "subcats": 0, "high_density_subcats": 0, "high_density_tasks": 0})
    for (cat, sub), cluster in by_subcat.items():
        by_category_buckets[cat]["tasks"] += len(cluster)
        by_category_buckets[cat]["subcats"] += 1
        if len(cluster) >= 4:
            by_category_buckets[cat]["high_density_subcats"] += 1
            by_category_buckets[cat]["high_density_tasks"] += len(cluster)
    print(f"\nPer-category capability density:")
    for cat in sorted(by_category_buckets, key=lambda c: -by_category_buckets[c]["tasks"]):
        d = by_category_buckets[cat]
        density = d["subcats"] / d["tasks"] if d["tasks"] else 0
        print(f"  {cat:18s} tasks={d['tasks']:>3d}  subcats={d['subcats']:>3d}  density={density:.2f}  clusters>=4: {d['high_density_subcats']} ({d['high_density_tasks']} tasks)")

    # ── 4. Top "redundant" clusters (size + similarity) ─────────────────
    redundant = [
        r for r in per_subcat
        if r["n_tasks"] >= 4 and (r["mean_prompt_jaccard"] or 0) >= 0.50
    ]
    redundant.sort(key=lambda r: (-r["n_tasks"], -(r["mean_prompt_jaccard"] or 0)))
    print(f"\nHighly redundant subcategory clusters (size>=4 AND prompt Jaccard>=0.50):")
    print(f"  {len(redundant)} clusters covering {sum(r['n_tasks'] for r in redundant)} tasks")
    for r in redundant[:20]:
        print(f"    {r['category']:18s} {r['subcategory']:30s}  n={r['n_tasks']:>2d}  jaccard={r['mean_prompt_jaccard']:.2f}  sigs={r['distinct_check_signatures']}")

    # ── 5. Markdown report ──────────────────────────────────────────────
    write_report(
        n_tasks=len(tasks),
        n_subcats=n_subcats,
        size_hist=size_hist,
        singletons=singletons,
        tasks_in_singletons=tasks_in_singletons,
        clusters_ge4=clusters_ge4,
        tasks_in_clusters_ge4=tasks_in_clusters_ge4,
        by_category_buckets=by_category_buckets,
        redundant=redundant,
        per_subcat=per_subcat,
    )
    print(f"\nWrote report -> {REPORT.relative_to(ROOT)}")


def write_report(*, n_tasks, n_subcats, size_hist, singletons, tasks_in_singletons,
                 clusters_ge4, tasks_in_clusters_ge4, by_category_buckets,
                 redundant, per_subcat):
    L: list[str] = []
    A = L.append
    A("# NextBench v0.1 — Capability Analysis")
    A("")
    A("**Generated:** 2026-06-08")
    A(f"**Tasks analysed:** {n_tasks}")
    A("")
    A("## What this measures")
    A("")
    A("355 tasks in NextBench v0.1 — but how many *distinct capabilities* is that?")
    A("This analysis answers the question directly, before any v0.2 expansion is planned.")
    A("")
    A("Three signals are combined:")
    A("")
    A("1. **Subcategory clustering** — tasks share a subcategory iff they probe the same named pattern (`react.copy`, `database.prisma_model`, etc.). One subcategory ≈ one capability bucket.")
    A("2. **Check signature** — tasks with identical sorted-lowered `must_contain` sets grade the same surface pattern.")
    A("3. **Prompt Jaccard similarity** — within a subcategory cluster, average pairwise Jaccard on prompt tokens. High value (≥0.50) means prompts differ only in entity/prop names, not capability.")
    A("")
    A("## Headline numbers")
    A("")
    n_redundant_tasks = sum(r["n_tasks"] for r in redundant)
    capability_density = n_subcats / n_tasks
    A("| Metric | Value |")
    A("|---|---:|")
    A(f"| Total tasks | {n_tasks} |")
    A(f"| Distinct subcategory buckets (capabilities) | **{n_subcats}** |")
    A(f"| Capability density (subcategories / tasks) | **{capability_density:.2f}** |")
    A(f"| Singleton subcategories (1 task each) | {singletons} ({tasks_in_singletons} tasks) |")
    A(f"| Subcategories of size ≥4 (template-cloned) | {clusters_ge4} ({tasks_in_clusters_ge4} tasks) |")
    A(f"| Highly redundant clusters (size≥4 AND Jaccard≥0.50) | {len(redundant)} ({n_redundant_tasks} tasks) |")
    A("")

    interpretation_lines = []
    interpretation_lines.append(
        f"NextBench v0.1 contains **{n_tasks} tasks across {n_subcats} subcategory buckets** — "
        f"a capability density of {capability_density:.2f}."
    )
    if n_redundant_tasks > 30:
        interpretation_lines.append(
            f"**{n_redundant_tasks} of {n_tasks} tasks ({100*n_redundant_tasks/n_tasks:.0f}%) live in highly redundant clusters** "
            f"(size ≥4 with mean intra-cluster prompt Jaccard ≥ 0.50). These tasks are likely template-cloned "
            f"variations of the same underlying capability and contribute to *coverage* but not *capability differentiation*."
        )
    interpretation_lines.append(
        f"The effective capability count of NextBench v0.1 is closer to **{n_subcats}** than to {n_tasks}."
    )
    A("**Interpretation:**")
    A("")
    for ln in interpretation_lines:
        A(f"- {ln}")
    A("")

    A("## Cluster size distribution")
    A("")
    A("How many subcategories contain N tasks each:")
    A("")
    A("| Tasks per subcategory | # subcategories | Total tasks in this size |")
    A("|---:|---:|---:|")
    for size in sorted(size_hist):
        n_clusters = size_hist[size]
        n_tasks_in_size = size * n_clusters
        A(f"| {size} | {n_clusters} | {n_tasks_in_size} |")
    A("")

    A("## Per-category capability density")
    A("")
    A("Categories with **low density** (many tasks per subcategory) are template-heavy; categories with **high density** (≈1 task per subcategory) cover more distinct capabilities.")
    A("")
    A("| Category | Tasks | Subcategories | Density | Clusters ≥4 | Tasks in clusters ≥4 |")
    A("|---|---:|---:|---:|---:|---:|")
    for cat in sorted(by_category_buckets, key=lambda c: -by_category_buckets[c]["tasks"]):
        d = by_category_buckets[cat]
        density = d["subcats"] / d["tasks"] if d["tasks"] else 0
        A(f"| `{cat}` | {d['tasks']} | {d['subcats']} | {density:.2f} | {d['high_density_subcats']} | {d['high_density_tasks']} |")
    A("")

    A("## Top redundant clusters (v0.2 deduplication candidates)")
    A("")
    A("Subcategories with **size ≥4 AND mean prompt Jaccard ≥ 0.50**. These are the strongest candidates for capability deduplication in v0.2 — keep one or two representatives per cluster, retire the rest.")
    A("")
    A("| Category | Subcategory | Tasks | Mean prompt Jaccard | Distinct check signatures |")
    A("|---|---|---:|---:|---:|")
    for r in redundant:
        A(f"| `{r['category']}` | `{r['subcategory']}` | {r['n_tasks']} | {r['mean_prompt_jaccard']:.2f} | {r['distinct_check_signatures']} |")
    A("")

    A("## v0.2 implications")
    A("")
    A("1. **Capability dedup before expansion.** Retire ~75% of the tasks in each high-redundancy cluster (keep 1–2 representative variants). Replaces template inflation with capability breadth.")
    A("2. **Headline target updated.** v0.2 target is no longer \"355 → 1000 tasks\" but \"~250 → ~600 capabilities\". The right metric to grow is *distinct subcategories*, not *task count*.")
    A("3. **Expansion priority.** Categories with the lowest subcategory density (`react`, `nextjs`, `server-actions`, `database`) need more *diverse* tasks, not more *similar* ones.")
    A("4. **Future task generation rule.** When generating candidate tasks for `candidates/`, no more than 2 tasks per subcategory unless each tests a meaningfully different sub-capability (different patterns, different check signatures).")
    A("")
    A("## Reproduce")
    A("")
    A("```")
    A("python nextbench/scripts/capability_analysis.py")
    A("```")
    A("")
    A("Re-runs deterministically against the current `tasks/` directory.")
    A("")

    REPORT.write_text("\n".join(L))


if __name__ == "__main__":
    main()
