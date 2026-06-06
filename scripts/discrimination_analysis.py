#!/usr/bin/env python3
"""Discrimination analysis for NextBench v0.1.

Re-grades the 12 cross-model battle outputs through the NextBench grader and
computes per-task discrimination statistics: which tasks separate models,
which are saturated (everyone aces them), and which are impossible (no one
passes). Output informs v0.2 curation — saturated and impossible tasks are
candidates for retirement or replacement.

Outputs:
  - nextbench/outputs/_discrimination_per_task.jsonl   (per-task stats)
  - nextbench/ANALYSIS_v0.1.md                         (human-readable report)

Usage:
  python nextbench/scripts/discrimination_analysis.py
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "nextbench"))
from grade import grade_one  # noqa: E402

LEGACY_OUTPUTS_DIR = ROOT / "eval" / "battle" / "outputs"
TASKS_DIR = ROOT / "nextbench" / "tasks"
PER_TASK_JSONL = ROOT / "nextbench" / "outputs" / "_discrimination_per_task.jsonl"
REPORT_PATH = ROOT / "nextbench" / "ANALYSIS_v0.1.md"

# 12-model discrimination panel: 10 distinct production model architectures
# + 2 BaaB Next checkpoints (Pretrain 2K, Pretrain 4K).  Intentionally excludes
# the BaaB CPT step-2K/4K/6K/10K and the Run 8 mid-training checkpoints so the
# panel isn't dominated by BaaB-flavored variants.
PANEL: dict[str, str] = {
    # External production models
    "codegemma:2b": "codegemma_2b_battle.jsonl",
    "codestral:22b": "codestral_22b_battle.jsonl",
    "deepseek-coder:1.3b": "deepseek-coder_13b_battle.jsonl",
    "granite-code:3b": "granite-code_3b_battle.jsonl",
    "granite-code:8b": "granite-code_8b_battle.jsonl",
    "qwen2.5-coder:1.5b": "qwen25-coder_15b_battle.jsonl",
    "qwen2.5-coder:3b": "qwen25-coder_3b_battle.jsonl",
    "qwen2.5-coder:7b": "qwen25-coder_7b_battle.jsonl",
    "qwen3-coder:30b": "qwen3-coder_30b_battle.jsonl",
    "starcoder2:3b": "starcoder2_3b_battle.jsonl",
    # BaaB Next checkpoints
    "BaaB Next 1B (Pretrain 2K)": "final_battle.jsonl",
    "BaaB Next 1B (Pretrain 4K)": "step-00008000_battle.jsonl",
}


def load_new_tasks_by_legacy_id() -> dict[str, dict]:
    index: dict[str, dict] = {}
    for path in sorted(TASKS_DIR.glob("*.jsonl")):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                task = json.loads(line)
                legacy = task.get("metadata", {}).get("legacy_id")
                if legacy:
                    index[legacy] = task
    return index


def join_and_grade(output_path: Path, task_index: dict[str, dict]) -> dict[str, dict]:
    """Return task_id -> grade dict for one model's outputs."""
    grades: dict[str, dict] = {}
    with open(output_path) as f:
        for line in f:
            legacy = json.loads(line)
            legacy_id = legacy.get("id")
            new_task = task_index.get(legacy_id)
            if not new_task:
                continue
            joined = {**new_task, "output": legacy.get("output", "")}
            grade = grade_one(joined)
            grades[new_task["task_id"]] = grade
    return grades


def classify(mean_score: float, std_score: float) -> str:
    """Bucket each task by discrimination quality.

    Thresholds calibrated against the actual std distribution of the 12-model
    panel on the 355 v0.1 tasks (max std observed: 1.19, p50: 0.47, p90: 0.69).

    - saturated:    everyone aces it; adds no ranking signal
    - impossible:   no one passes it; likely a broken check (or legit ceiling)
    - low_signal:   std < 0.40 — bottom-quartile dispersion, narrow info
    - mid_signal:   0.40 <= std < 0.70
    - high_signal:  std >= 0.70 — top-decile differentiator
    """
    if mean_score >= 3.95 and std_score <= 0.2:
        return "saturated"
    if mean_score <= 0.5 and std_score <= 0.5:
        return "impossible"
    if std_score < 0.40:
        return "low_signal"
    if std_score < 0.70:
        return "mid_signal"
    return "high_signal"


def main():
    task_index = load_new_tasks_by_legacy_id()
    print(f"Loaded {len(task_index)} new-schema tasks")

    # Grade every panel model on every task.
    model_grades: dict[str, dict[str, dict]] = {}
    for model, fname in PANEL.items():
        path = LEGACY_OUTPUTS_DIR / fname
        if not path.exists():
            print(f"  MISSING: {model} -> {fname}")
            continue
        model_grades[model] = join_and_grade(path, task_index)
        print(f"  graded {len(model_grades[model])} tasks for {model}")

    n_panel = len(model_grades)
    print(f"\nPanel size: {n_panel} models")

    # Build per-task statistics.
    per_task: list[dict] = []
    for task_id in sorted({tid for g in model_grades.values() for tid in g}):
        scores = [model_grades[m].get(task_id, {}).get("score") for m in model_grades]
        scores = [s for s in scores if s is not None]
        if len(scores) < n_panel:
            # Skip tasks missing from any model output.
            continue
        # Pull task metadata from any model's grade (all identical).
        any_grade = next(g[task_id] for g in model_grades.values() if task_id in g)
        mean = statistics.mean(scores)
        std = statistics.pstdev(scores) if len(scores) > 1 else 0.0
        spread = max(scores) - min(scores)
        bucket = classify(mean, std)

        per_task.append({
            "task_id": task_id,
            "category": any_grade["category"],
            "subcategory": any_grade["subcategory"],
            "difficulty": any_grade["difficulty"],
            "tags": any_grade["tags"],
            "panel_size": len(scores),
            "mean_score": round(mean, 3),
            "std_score": round(std, 3),
            "min_score": min(scores),
            "max_score": max(scores),
            "spread": spread,
            "score_distribution": {
                str(k): scores.count(k) for k in (0, 1, 2, 3, 4)
            },
            "bucket": bucket,
        })

    # Write per-task JSONL.
    PER_TASK_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(PER_TASK_JSONL, "w") as f:
        for r in per_task:
            f.write(json.dumps(r) + "\n")
    print(f"\nWrote {len(per_task)} per-task records to {PER_TASK_JSONL.relative_to(ROOT)}")

    # Aggregate stats.
    by_bucket: dict[str, list[dict]] = defaultdict(list)
    for r in per_task:
        by_bucket[r["bucket"]].append(r)

    bucket_order = ["saturated", "low_signal", "impossible", "mid_signal", "high_signal"]
    print(f"\nBucket distribution:")
    for b in bucket_order:
        n = len(by_bucket.get(b, []))
        pct = 100 * n / len(per_task) if per_task else 0
        print(f"  {b:14s} {n:4d}  ({pct:5.1f}%)")

    # By category × bucket
    by_cat_bucket: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    cat_totals: dict[str, int] = defaultdict(int)
    for r in per_task:
        by_cat_bucket[r["category"]][r["bucket"]] += 1
        cat_totals[r["category"]] += 1

    print(f"\nPer-category bucket counts:")
    header = f"  {'category':18s}  {'tot':>4s}  " + "  ".join(f"{b:>10s}" for b in bucket_order)
    print(header)
    for cat in sorted(cat_totals, key=lambda c: -cat_totals[c]):
        row = [f"{cat_totals[cat]:>4d}"]
        for b in bucket_order:
            row.append(f"{by_cat_bucket[cat].get(b, 0):>10d}")
        print(f"  {cat:18s}  " + "  ".join(row))

    # Write the markdown report.
    write_report(per_task, by_bucket, by_cat_bucket, cat_totals, bucket_order, n_panel, list(model_grades.keys()))
    print(f"\nWrote report -> {REPORT_PATH.relative_to(ROOT)}")


def write_report(per_task, by_bucket, by_cat_bucket, cat_totals, bucket_order, n_panel, panel_models):
    lines = []
    lines.append("# NextBench v0.1 — Discrimination Analysis")
    lines.append("")
    lines.append(f"**Generated:** 2026-06-06")
    lines.append(f"**Panel:** {n_panel} models (10 external production code models + 2 BaaB Next checkpoints)")
    lines.append(f"**Tasks analysed:** {len(per_task)} of 355")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("For each task, this analysis asks: **does the task separate models, or do all models score the same?**")
    lines.append("Tasks where every model scores 4/4 add no ranking signal; tasks where every model scores 0/4 are either")
    lines.append("impossible or have a broken check. Both are candidates for retirement or replacement in v0.2.")
    lines.append("")
    lines.append("Each task is classified by the standard deviation of its scores across the 12-model panel:")
    lines.append("")
    lines.append("| Bucket | Condition | Meaning |")
    lines.append("|---|---|---|")
    lines.append("| `saturated` | mean ≥ 3.95 AND std ≤ 0.2 | Every model aces it. Zero ranking signal. |")
    lines.append("| `impossible` | mean ≤ 0.5 AND std ≤ 0.5 | No model passes. Likely a broken check or unfair task. |")
    lines.append("| `low_signal` | std < 0.40 | Bottom-quartile dispersion; narrow info. |")
    lines.append("| `mid_signal` | 0.40 ≤ std < 0.70 | Healthy differentiation. |")
    lines.append("| `high_signal` | std ≥ 0.70 | Top-decile differentiator — keep, replicate the pattern. |")
    lines.append("")
    lines.append("Thresholds calibrated against the actual std distribution of the 12-model panel on the 355 v0.1 tasks (p25=0.37, p50=0.47, p90=0.69, max=1.19).")
    lines.append("")
    lines.append("## Panel")
    lines.append("")
    for m in panel_models:
        lines.append(f"- `{m}`")
    lines.append("")
    lines.append("## Bucket distribution")
    lines.append("")
    lines.append("| Bucket | Tasks | % of suite |")
    lines.append("|---|---:|---:|")
    for b in bucket_order:
        n = len(by_bucket.get(b, []))
        pct = 100 * n / len(per_task) if per_task else 0
        lines.append(f"| `{b}` | {n} | {pct:.1f}% |")
    lines.append("")

    sat = len(by_bucket.get("saturated", []))
    imp = len(by_bucket.get("impossible", []))
    low = len(by_bucket.get("low_signal", []))
    mid = len(by_bucket.get("mid_signal", []))
    high = len(by_bucket.get("high_signal", []))
    keeper = mid + high
    keeper_pct = 100 * keeper / len(per_task) if per_task else 0

    lines.append("### Headline")
    lines.append("")
    lines.append(f"- **{keeper} tasks ({keeper_pct:.1f}%)** carry real ranking signal (mid + high).")
    lines.append(f"- **{sat} tasks ({100*sat/len(per_task):.1f}%)** are saturated — every panel model scores 4/4. Candidates for retirement.")
    lines.append(f"- **{imp} tasks ({100*imp/len(per_task):.1f}%)** are impossible — no panel model passes. Audit before v0.2 (broken check vs legitimate ceiling).")
    lines.append(f"- **{low} tasks ({100*low/len(per_task):.1f}%)** are low-signal (narrow band, std < 0.5).")
    lines.append("")
    lines.append("## Per-category breakdown")
    lines.append("")
    lines.append("Counts of how many tasks in each category fall into each bucket. Categories with many `saturated` or `low_signal` tasks are the ones to thicken with harder examples in v0.2; categories already heavy in `mid_signal` / `high_signal` are doing their job.")
    lines.append("")
    header_cells = ["Category", "Total"] + [f"`{b}`" for b in bucket_order]
    lines.append("| " + " | ".join(header_cells) + " |")
    lines.append("|" + "|".join(["---"] + ["---:"] * (len(header_cells) - 1)) + "|")
    for cat in sorted(cat_totals, key=lambda c: -cat_totals[c]):
        cells = [cat, str(cat_totals[cat])] + [str(by_cat_bucket[cat].get(b, 0)) for b in bucket_order]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    # Saturated tasks listing
    lines.append("## Saturated tasks (zero ranking signal)")
    lines.append("")
    sat_tasks = sorted(by_bucket.get("saturated", []), key=lambda r: r["task_id"])
    if not sat_tasks:
        lines.append("_None._")
    else:
        lines.append(f"All {len(sat_tasks)} listed below. Every panel model scored 4/4.")
        lines.append("")
        lines.append("| task_id | category | difficulty |")
        lines.append("|---|---|---|")
        for r in sat_tasks:
            lines.append(f"| `{r['task_id']}` | {r['category']} | {r['difficulty']} |")
    lines.append("")

    # Impossible tasks listing
    lines.append("## Impossible tasks (no panel model passes)")
    lines.append("")
    imp_tasks = sorted(by_bucket.get("impossible", []), key=lambda r: r["task_id"])
    if not imp_tasks:
        lines.append("_None._")
    else:
        lines.append(f"All {len(imp_tasks)} listed. **Audit each one before v0.2:** is the check unfair, or is the task a legitimate ceiling (e.g. a pattern none of these models has been trained on)?")
        lines.append("")
        lines.append("| task_id | category | difficulty | mean | max |")
        lines.append("|---|---|---|---:|---:|")
        for r in imp_tasks:
            lines.append(f"| `{r['task_id']}` | {r['category']} | {r['difficulty']} | {r['mean_score']} | {r['max_score']} |")
    lines.append("")

    # Top 20 highest-signal tasks
    high_tasks = sorted(by_bucket.get("high_signal", []), key=lambda r: -r["std_score"])
    lines.append(f"## Top 20 highest-discrimination tasks (gold)")
    lines.append("")
    lines.append("These tasks differentiate models the most. They define the shape of the leaderboard. v0.2 should replicate the *patterns* underneath them.")
    lines.append("")
    lines.append("| task_id | category | difficulty | mean | std | spread |")
    lines.append("|---|---|---|---:|---:|---:|")
    for r in high_tasks[:20]:
        lines.append(f"| `{r['task_id']}` | {r['category']} | {r['difficulty']} | {r['mean_score']} | {r['std_score']} | {r['spread']} |")
    lines.append("")

    # Findings & recommendations
    lines.append("## Findings & recommendations for v0.2")
    lines.append("")
    lines.append("1. **Retirement candidates:** the saturated tasks above contribute nothing to model ranking. Either retire them or rewrite their checks to demand more (tighter `must_match_regex`, additional `must_contain`).")
    lines.append("2. **Audit impossible tasks:** if the check is broken, fix it. If the model class is the issue, document it and keep — these become aspirational benchmarks for next-gen models.")
    lines.append("3. **Categories light on signal:** any category with >50% saturated+low_signal tasks needs new harder prompts in v0.2.")
    lines.append("4. **Replicate the gold patterns:** the top-20 high-signal tasks above show what *kinds* of prompts produce differentiation. New v0.2 tasks should be designed in those shapes — not random Claude-generated prompts.")
    lines.append("5. **Coverage rebalancing:** combine this report with the category totals when planning v0.2's ~245 new tasks. Add to under-discriminating categories, not just under-represented ones.")
    lines.append("")
    lines.append("## Reproduce")
    lines.append("")
    lines.append("```")
    lines.append("python nextbench/scripts/discrimination_analysis.py")
    lines.append("```")
    lines.append("")
    lines.append("Re-runs deterministically. Re-grades the legacy battle outputs via the NextBench grader — no model inference required.")
    lines.append("")

    REPORT_PATH.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
