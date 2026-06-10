#!/usr/bin/env python3
"""Fix the tight-max_lines class bug surfaced by the v0.2 audit.

The grader enforces BOTH min_lines and max_lines when max_lines <= 6
(TIGHT_MAX_THRESHOLD). For short utility tasks we set max_lines at 2/4/5,
which is correct for a JUST-the-function answer.

But at max_tokens=500 (the canonical leaderboard setting), strong models
naturally continue past the target function and write additional helpers.
They produce a CORRECT primary implementation followed by extra content.
The tight max_lines window then penalizes them while weak models that
stop early get full credit. Inversion.

Fix: for every tight-max task in this list (surfaced by the audit), raise
max_lines to 30. That keeps the min_lines floor (catches one-line stubs)
and a 30-line ceiling (catches truly runaway 80+ line continuations) but
drops the grader out of the TIGHT_MAX_THRESHOLD regime so trailing content
is acceptable.

We also fix the noop typo: must_contain ['() => '] requires a trailing
space and fails on the common '() => {}' completion.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"

# Surfaced by audit_v02.py — tasks where >=3 strong models fail solely on
# length_ok. Pattern: short utility helpers with max_lines <= 6.
TIGHT_TASKS = {
    "auth.handlers_reexport.005",
    "typescript.awaited_simple.018",
    "typescript.branded_id.027",
    "typescript.extract_array_element.024",
    "typescript.function_return.026",
    "typescript.infer_values.019",
    "typescript.non_nullable.015",
    "utils.assert_unreachable.027",
    "utils.capitalize.020",
    "utils.clamp.009",
    "utils.cn.012",
    "utils.is_browser.014",
    "utils.noop.023",
    "utils.sleep.011",
}

# Per-task `must_contain` token fixes (the noop typo + similar trailing-space
# pattern bugs).
PATTERN_FIXES = {
    "utils.noop.023": {
        # '() => ' with trailing space fails on '() => {}'. Drop trailing space.
        "replace_must_contain": {"() => ": "() =>"},
    },
}

NEW_MAX_LINES = 30


def apply_tight_max(task: dict) -> bool:
    s = task["checks"]["static"]
    current = s.get("max_lines")
    if current is not None and current <= 6:
        s["max_lines"] = NEW_MAX_LINES
        return True
    return False


def apply_pattern_fix(task: dict, fix: dict) -> bool:
    s = task["checks"]["static"]
    mc = s.get("must_contain", [])
    changed = False
    if "replace_must_contain" in fix:
        for old, new in fix["replace_must_contain"].items():
            for i, tok in enumerate(mc):
                if tok == old:
                    mc[i] = new
                    changed = True
    return changed


def main() -> None:
    n_tight = 0
    n_pattern = 0
    files_touched = 0

    for fp in sorted(TASKS_DIR.glob("*.jsonl")):
        rows = []
        touched = False
        with open(fp) as f:
            for line in f:
                if not line.strip():
                    continue
                t = json.loads(line)
                tid = t["task_id"]
                if tid in TIGHT_TASKS:
                    if apply_tight_max(t):
                        n_tight += 1
                        touched = True
                if tid in PATTERN_FIXES:
                    if apply_pattern_fix(t, PATTERN_FIXES[tid]):
                        n_pattern += 1
                        touched = True
                rows.append(t)

        if touched:
            files_touched += 1
            with open(fp, "w") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"tight max_lines fixes: {n_tight}/{len(TIGHT_TASKS)}")
    print(f"pattern fixes:         {n_pattern}/{len(PATTERN_FIXES)}")
    print(f"files touched:         {files_touched}")


if __name__ == "__main__":
    main()
