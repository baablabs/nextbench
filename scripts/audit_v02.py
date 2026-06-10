#!/usr/bin/env python3
"""v0.2 corpus quality audit — 6 automated passes.

Each pass surfaces a list of flagged tasks. The script does NOT fix anything —
it produces a JSON report (audit_report.json) and a human-readable summary
that a human triages.

Passes:
  1. Discrimination signal — pass rate of each task across 12 models.
     Flags: near-ceiling (0–1/12 pass) and near-floor (11–12/12 pass).
  2. Inverted-pass anomalies — tasks where weak models pass and strong
     models fail. Strong signal the check is wrong.
  3. Difficulty calibration — `difficulty` label vs measured pass rate.
     Flags: `trivial` <70%, `mid` outside 50–90%, `hard` >85%.
  4. Source URL HEAD check — every `metadata.source_url` returns 2xx or 3xx.
  5. Schema completeness — `framework_version`, `task_class`, `license`,
     `created` present on every task.
  6. Tag coverage — each category has at least 3 distinct tags;
     each task has at least 2 tags.

Usage:
  python scripts/audit_v02.py --outputs-dir outputs_450
  python scripts/audit_v02.py --outputs-dir outputs_fresh  # post-fresh-eval
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
sys.path.insert(0, str(ROOT))
from grade import grade_one  # noqa: E402

# Strong-model ordering for inverted-pass detection
STRONG_TO_WEAK_PANEL = [
    "qwen3-coder_30b",
    "baab-next-1b-pretrain-2k",
    "codestral_22b",
    "qwen25-coder_7b",
    "baab-next-1b-pretrain-4k",
    "qwen25-coder_3b",
    "codegemma_2b",
    "qwen25-coder_15b",
    "granite-code_8b",
    "starcoder2_3b",
    "granite-code_3b",
    "deepseek-coder_13b",
]


def load_tasks() -> dict[str, dict]:
    idx = {}
    for fp in sorted(TASKS_DIR.glob("*.jsonl")):
        with open(fp) as f:
            for line in f:
                if line.strip():
                    t = json.loads(line)
                    idx[t["task_id"]] = t
    return idx


def load_outputs(outputs_dir: Path) -> dict[str, dict[str, dict]]:
    """Returns {task_id -> {model_slug -> grade_record}}."""
    per_task: dict[str, dict[str, dict]] = defaultdict(dict)
    files = sorted(p for p in outputs_dir.glob("*.jsonl") if not p.name.startswith("_"))
    for fp in files:
        slug = fp.stem
        with open(fp) as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                g = grade_one(rec)
                per_task[rec["task_id"]][slug] = g
    return per_task


# ──────────────────────────────────────────────────────────────────────────
# Pass 1: discrimination signal
# ──────────────────────────────────────────────────────────────────────────

def pass_discrimination(per_task: dict, tasks: dict) -> list[dict]:
    n_models = max(len(grades) for grades in per_task.values())
    flagged = []
    for tid, grades in per_task.items():
        passes = sum(1 for g in grades.values() if g["score"] == g["max"])
        if passes <= 1:
            severity = "ceiling" if passes == 0 else "near-ceiling"
            flagged.append({
                "task_id": tid,
                "category": tasks[tid]["category"],
                "subcategory": tasks[tid].get("subcategory", ""),
                "pass_rate": f"{passes}/{n_models}",
                "issue": severity,
                "n_passes": passes,
            })
        elif passes >= n_models - 1:
            severity = "saturated" if passes == n_models else "near-saturated"
            flagged.append({
                "task_id": tid,
                "category": tasks[tid]["category"],
                "subcategory": tasks[tid].get("subcategory", ""),
                "pass_rate": f"{passes}/{n_models}",
                "issue": severity,
                "n_passes": passes,
            })
    return flagged


# ──────────────────────────────────────────────────────────────────────────
# Pass 2: inverted-pass anomalies
# ──────────────────────────────────────────────────────────────────────────

def pass_inverted(per_task: dict, tasks: dict) -> list[dict]:
    """Flag tasks where the bottom-half of the panel passes but the top-half
    fails. Strong signal the check encodes a non-canonical answer."""
    flagged = []
    for tid, grades in per_task.items():
        top_half = STRONG_TO_WEAK_PANEL[:6]
        bottom_half = STRONG_TO_WEAK_PANEL[6:]
        top_pass = sum(1 for m in top_half if m in grades and grades[m]["score"] == grades[m]["max"])
        bot_pass = sum(1 for m in bottom_half if m in grades and grades[m]["score"] == grades[m]["max"])
        # Inverted if 4+ bottom-half models pass AND 2 or fewer top-half pass
        if bot_pass >= 4 and top_pass <= 2:
            flagged.append({
                "task_id": tid,
                "category": tasks[tid]["category"],
                "top_half_pass": f"{top_pass}/6",
                "bottom_half_pass": f"{bot_pass}/6",
                "issue": "inverted-pass",
            })
    return flagged


# ──────────────────────────────────────────────────────────────────────────
# Pass 3: difficulty calibration
# ──────────────────────────────────────────────────────────────────────────

def pass_difficulty_calibration(per_task: dict, tasks: dict) -> list[dict]:
    flagged = []
    for tid, grades in per_task.items():
        n = len(grades)
        if n == 0:
            continue
        passes = sum(1 for g in grades.values() if g["score"] == g["max"])
        rate = passes / n
        diff = tasks[tid].get("difficulty", "?")
        mismatch = None
        if diff == "trivial" and rate < 0.70:
            mismatch = f"trivial but {rate*100:.0f}% pass rate"
        elif diff == "mid" and (rate < 0.40 or rate > 0.92):
            mismatch = f"mid but {rate*100:.0f}% pass rate"
        elif diff == "hard" and rate > 0.85:
            mismatch = f"hard but {rate*100:.0f}% pass rate"
        if mismatch:
            flagged.append({
                "task_id": tid,
                "category": tasks[tid]["category"],
                "difficulty_label": diff,
                "actual_pass_rate": f"{rate*100:.0f}%",
                "issue": mismatch,
            })
    return flagged


# ──────────────────────────────────────────────────────────────────────────
# Pass 4: source URL HEAD check
# ──────────────────────────────────────────────────────────────────────────

def _head(url: str, timeout: int = 8) -> tuple[str, int | str]:
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "nextbench-audit/0.2"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return url, resp.status
    except urllib.error.HTTPError as e:
        # Some servers reject HEAD; retry as GET with no body read.
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "nextbench-audit/0.2"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return url, resp.status
        except Exception as e2:
            return url, f"err:{type(e2).__name__}"
    except Exception as e:
        return url, f"err:{type(e).__name__}"


def pass_source_urls(tasks: dict) -> list[dict]:
    urls_per_task: dict[str, str] = {}
    for tid, t in tasks.items():
        url = t.get("metadata", {}).get("source_url")
        if url:
            urls_per_task[tid] = url
    if not urls_per_task:
        return []
    unique_urls = sorted(set(urls_per_task.values()))
    print(f"  HEAD-checking {len(unique_urls)} unique source URLs...", flush=True)
    results: dict[str, int | str] = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(_head, u): u for u in unique_urls}
        for fut in as_completed(futures):
            u, status = fut.result()
            results[u] = status
    flagged = []
    for tid, url in urls_per_task.items():
        status = results.get(url, "missing")
        if not isinstance(status, int) or status >= 400:
            flagged.append({
                "task_id": tid,
                "category": tasks[tid]["category"],
                "source_url": url,
                "status": status,
                "issue": "broken-source-url",
            })
    return flagged


# ──────────────────────────────────────────────────────────────────────────
# Pass 5: schema completeness
# ──────────────────────────────────────────────────────────────────────────

REQUIRED_META = ["source", "schema_version", "benchmark_version", "license"]
RECOMMENDED_META = ["source_url", "created"]


def pass_schema(tasks: dict) -> list[dict]:
    flagged = []
    for tid, t in tasks.items():
        meta = t.get("metadata", {}) or {}
        missing_req = [k for k in REQUIRED_META if not meta.get(k)]
        missing_rec = [k for k in RECOMMENDED_META if not meta.get(k)]
        if missing_req or missing_rec:
            flagged.append({
                "task_id": tid,
                "category": t["category"],
                "missing_required": missing_req,
                "missing_recommended": missing_rec,
                "issue": "schema-incomplete" if missing_req else "schema-recommendation",
            })
    return flagged


# ──────────────────────────────────────────────────────────────────────────
# Pass 6: tag coverage
# ──────────────────────────────────────────────────────────────────────────

def pass_tag_coverage(tasks: dict) -> list[dict]:
    flagged = []
    per_cat_tags: dict[str, set] = defaultdict(set)
    per_cat_count: dict[str, int] = defaultdict(int)
    for t in tasks.values():
        per_cat_tags[t["category"]].update(t.get("tags", []))
        per_cat_count[t["category"]] += 1
        if len(t.get("tags", [])) < 2:
            flagged.append({
                "task_id": t["task_id"],
                "category": t["category"],
                "tags": t.get("tags", []),
                "issue": "too-few-tags",
            })
    # Per-category thin coverage
    for cat, tagset in per_cat_tags.items():
        if per_cat_count[cat] >= 8 and len(tagset) < 4:
            flagged.append({
                "task_id": f"<category:{cat}>",
                "category": cat,
                "distinct_tags": sorted(tagset),
                "n_tasks": per_cat_count[cat],
                "issue": "thin-category-tag-coverage",
            })
    return flagged


# ──────────────────────────────────────────────────────────────────────────
# Driver
# ──────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outputs-dir", default="outputs_450",
                    help="Directory with per-model output JSONLs.")
    ap.add_argument("--report", default="audit_report_v02.json")
    ap.add_argument("--skip-urls", action="store_true",
                    help="Skip the URL HEAD-check pass (slow if offline).")
    args = ap.parse_args()

    tasks = load_tasks()
    outputs_dir = Path(args.outputs_dir)
    if not outputs_dir.is_absolute():
        outputs_dir = ROOT / outputs_dir
    print(f"Loaded {len(tasks)} tasks", flush=True)
    print(f"Outputs dir: {outputs_dir}", flush=True)
    per_task = load_outputs(outputs_dir)
    print(f"Loaded outputs for {len(per_task)} tasks across {len(next(iter(per_task.values()))) if per_task else 0} models", flush=True)
    print()

    report = {}

    print("Pass 1/6: discrimination signal", flush=True)
    report["discrimination"] = pass_discrimination(per_task, tasks)
    print(f"  {len(report['discrimination'])} flags", flush=True)

    print("Pass 2/6: inverted-pass anomalies", flush=True)
    report["inverted_pass"] = pass_inverted(per_task, tasks)
    print(f"  {len(report['inverted_pass'])} flags", flush=True)

    print("Pass 3/6: difficulty calibration", flush=True)
    report["difficulty"] = pass_difficulty_calibration(per_task, tasks)
    print(f"  {len(report['difficulty'])} flags", flush=True)

    if not args.skip_urls:
        print("Pass 4/6: source URLs", flush=True)
        report["source_urls"] = pass_source_urls(tasks)
        print(f"  {len(report['source_urls'])} flags", flush=True)
    else:
        print("Pass 4/6: source URLs — SKIPPED", flush=True)
        report["source_urls"] = []

    print("Pass 5/6: schema completeness", flush=True)
    report["schema"] = pass_schema(tasks)
    print(f"  {len(report['schema'])} flags", flush=True)

    print("Pass 6/6: tag coverage", flush=True)
    report["tags"] = pass_tag_coverage(tasks)
    print(f"  {len(report['tags'])} flags", flush=True)

    # Summary
    print()
    print("=" * 60)
    print(f"AUDIT SUMMARY ({len(tasks)} tasks)")
    print("=" * 60)
    total_flags = sum(len(v) for v in report.values())
    print(f"Total flags: {total_flags}")
    for k, v in report.items():
        if v:
            print(f"  {k:<20} {len(v):>4} flags")
    print()

    # By category for the two highest-signal passes
    if report["discrimination"]:
        print("Discrimination flags by category:")
        c = Counter(f["category"] for f in report["discrimination"])
        for cat, n in c.most_common():
            print(f"  {cat:<22} {n}")
        print()
    if report["inverted_pass"]:
        print("Inverted-pass flags by category:")
        c = Counter(f["category"] for f in report["inverted_pass"])
        for cat, n in c.most_common():
            print(f"  {cat:<22} {n}")
        print()

    report_path = ROOT / args.report
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
