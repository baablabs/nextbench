#!/usr/bin/env python3
"""Propose specific tasks to retire from the v0.1 corpus.

Combines two signals:
  1. Saturation — tasks where every model in the 12-model panel scores 4/4.
     These contribute zero to leaderboard signal.
  2. Redundancy — tasks in size>=4 subcategory clusters with high prompt
     Jaccard similarity. From each redundant cluster, keep the highest-
     discriminating representative(s) and retire the rest.

The output is a deterministic retirement list — written to a JSON file you can
review before applying. No tasks are deleted by this script; it's read-only.

Usage:
  python scripts/propose_dedup.py                     # default: aim for ~50 redundant retirements
  python scripts/propose_dedup.py --target-redundant 70
  python scripts/propose_dedup.py --output dedup_proposal.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from grade import grade_one  # noqa: E402

OUTPUTS_DIR = ROOT / "outputs"
TASKS_DIR = ROOT / "tasks"
CAP_REPORT = ROOT / "outputs" / "_capability_per_subcategory.jsonl"


def variance(xs: list[int]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mean = sum(xs) / n
    return sum((x - mean) ** 2 for x in xs) / (n - 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-redundant", type=int, default=50,
                        help="Approximate target for redundant-cluster retirements")
    parser.add_argument("--output", default="dedup_proposal.json")
    args = parser.parse_args()

    # ─── Load current task corpus + pass/score per task across panel ───────
    tasks: dict[str, dict] = {}
    for path in TASKS_DIR.glob("*.jsonl"):
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            tasks[rec["task_id"]] = rec

    # task_id -> list[score per model]
    scores: dict[str, list[int]] = defaultdict(list)
    output_files = sorted(p for p in OUTPUTS_DIR.glob("*.jsonl")
                          if not p.name.startswith("_"))
    for f in output_files:
        for line in open(f):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            tid = rec["task_id"]
            # Re-grade with current checks (post-fix)
            if tid in tasks:
                rec_current = dict(rec)
                rec_current["checks"] = tasks[tid]["checks"]
                g = grade_one(rec_current)
            else:
                g = grade_one(rec)
            scores[tid].append(g["score"])

    # ─── Saturated set ──────────────────────────────────────────────────────
    saturated: set[str] = set()
    for tid, ss in scores.items():
        if ss and all(s == 4 for s in ss):
            saturated.add(tid)

    # ─── Cluster info from capability_analysis output ──────────────────────
    if not CAP_REPORT.exists():
        sys.exit(f"Missing {CAP_REPORT} — run scripts/capability_analysis.py first")
    clusters = []
    for line in open(CAP_REPORT):
        line = line.strip()
        if not line:
            continue
        clusters.append(json.loads(line))

    # Focus on highly-redundant clusters (size>=4, Jaccard>=0.50)
    redundant_clusters = [
        c for c in clusters
        if c.get("n_tasks", 0) >= 4 and c.get("mean_prompt_jaccard", 0) >= 0.50
    ]

    # ─── For each redundant cluster, score each task's signal ──────────────
    # Signal = variance of scores across panel (higher var = better discrimination)
    # Plus: prefer keeping tasks where avg score is mid-range (not 4/4, not 0/4)
    # Heuristic: lower variance + extreme avg = lower signal = retire first

    redundant_retire: list[str] = []
    cluster_decisions = []
    for cluster in redundant_clusters:
        cat = cluster["category"]
        subcat = cluster["subcategory"]
        cluster_task_ids = [
            tid for tid, rec in tasks.items()
            if rec.get("category") == cat and rec.get("subcategory") == subcat
        ]
        if len(cluster_task_ids) < 4:
            continue
        # Skip if all members are already saturated (handled separately)
        scored = []
        for tid in cluster_task_ids:
            ss = scores.get(tid, [])
            if not ss:
                continue
            avg = sum(ss) / len(ss)
            var = variance(ss)
            extremity = abs(avg - 2.0)  # 0=mid, 2=extreme
            # Lower signal score = retire first
            signal = var - extremity * 0.3
            scored.append((tid, signal, avg, var))
        # Sort by signal asc (lowest signal first)
        scored.sort(key=lambda x: x[1])
        # Retire ~50% of cluster (but always keep at least 2 representatives)
        n_keep = max(2, len(scored) // 2)
        retire = [s for s in scored[: len(scored) - n_keep]]
        for tid, signal, avg, var in retire:
            if tid not in saturated:  # don't double-count
                redundant_retire.append(tid)
        cluster_decisions.append({
            "category": cat,
            "subcategory": subcat,
            "size": len(cluster_task_ids),
            "keep_n": n_keep,
            "retire_n": len(scored) - n_keep,
            "kept": [s[0] for s in scored[len(scored) - n_keep:]],
            "retired": [s[0] for s in retire if s[0] not in saturated],
        })

    # Trim redundant_retire down to target if we exceeded
    if len(redundant_retire) > args.target_redundant * 1.3:
        # Sort by signal (already done within clusters); take the worst
        # For simplicity, keep top-N by appearance order (clusters are sorted by size desc)
        redundant_retire = redundant_retire[: args.target_redundant]

    # ─── Output ────────────────────────────────────────────────────────────
    proposal = {
        "saturated_retirements": sorted(saturated),
        "redundant_retirements": sorted(set(redundant_retire)),
        "cluster_decisions": cluster_decisions,
        "summary": {
            "total_tasks_current": len(tasks),
            "saturated_n": len(saturated),
            "redundant_n": len(set(redundant_retire)),
            "total_retire": len(saturated) + len(set(redundant_retire)),
            "remaining": len(tasks) - len(saturated) - len(set(redundant_retire)),
        },
    }

    out_path = Path(args.output)
    out_path.write_text(json.dumps(proposal, indent=2))

    s = proposal["summary"]
    print(f"Current corpus:        {s['total_tasks_current']} tasks")
    print(f"Retire (saturated):    {s['saturated_n']}")
    print(f"Retire (redundant):    {s['redundant_n']}")
    print(f"Total retiring:        {s['total_retire']}")
    print(f"Remaining after dedup: {s['remaining']}")
    print(f"\nDetailed proposal: {out_path}")

    print(f"\nSaturated by category:")
    by_cat: dict[str, int] = defaultdict(int)
    for tid in saturated:
        by_cat[tasks[tid].get("category", "?")] += 1
    for c, n in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"  {c:20s} {n}")

    print(f"\nRedundant retirements by cluster:")
    for cd in sorted(cluster_decisions, key=lambda c: -c["retire_n"]):
        if cd["retire_n"] > 0:
            print(f"  {cd['category']:18s} {cd['subcategory']:30s} "
                  f"size={cd['size']:2d} keep={cd['keep_n']} retire={cd['retire_n']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
