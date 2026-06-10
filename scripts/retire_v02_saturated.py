#!/usr/bin/env python3
"""Retire the 7 saturated v0.2 tasks surfaced by the audit's discrimination pass.

These are tasks where every model in the 12-model panel scored 4/4. They
provide zero discrimination signal and should not consume corpus slots.

This applies the same retire-saturated rule we used in the v0.1 dedup pass
(see apply_dedup.py). Retired records are appended to retired_v01.jsonl
(reusing the same recovery log file across v0.1 and v0.2 retirements).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
RETIRED_LOG = ROOT / "retired_v01.jsonl"

SATURATED = {
    "api-routes.cron_signature.001",
    "form.rhf_zod_resolver.001",
    "performance.lazy_suspense.001",
    "react.controlled_select.001",
    "server-actions.audit_log.001",
    "server-actions.composed_actions.001",
    "typescript-advanced.discriminated_narrow.001",
}


def main() -> None:
    n_retired = 0
    with open(RETIRED_LOG, "a") as log:
        for fp in sorted(TASKS_DIR.glob("*.jsonl")):
            kept: list[dict] = []
            with open(fp) as f:
                for line in f:
                    if not line.strip():
                        continue
                    t = json.loads(line)
                    if t["task_id"] in SATURATED:
                        t.setdefault("metadata", {})["retired_in"] = "v0.2-audit"
                        t["metadata"]["retire_reason"] = "saturated post-v0.2-eval"
                        log.write(json.dumps(t, ensure_ascii=False) + "\n")
                        n_retired += 1
                    else:
                        kept.append(t)
            with open(fp, "w") as f:
                for t in kept:
                    f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"Retired {n_retired}/{len(SATURATED)} saturated tasks.")
    # Verify totals
    total = sum(1 for fp in TASKS_DIR.glob("*.jsonl") for _ in open(fp))
    print(f"Corpus now: {total} tasks")


if __name__ == "__main__":
    main()
