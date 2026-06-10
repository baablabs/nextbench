#!/usr/bin/env python3
"""Surgical fix for v0.1 tasks with brittle must_contain tokens.

These tasks were surfaced by scan_universal_failures.py — each has a single
must_contain token that no model across the 12-model panel has ever hit.
The fix is conservative: drop the broken token, leave the rest of the check
intact. Capability remains; the false-failure-floor is removed.

Each fix here has a documented justification (see SUSPECTS below).

Usage:
  python fix_v01_bugs.py --dry-run   # show what would change
  python fix_v01_bugs.py             # apply the fixes
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"

# task_id -> {"drop": [must_contain tokens to remove], "reason": "..."}
SUSPECTS: dict[str, dict] = {
    "auth.magic_link_provider.020": {
        "drop": ["EmailProvider"],
        "reason": "EmailProvider is in the prompt's import; model wouldn't re-emit it in the completion. Prompt-only token bug.",
    },
    "auth.nextauth_config.003": {
        "drop": ["process.env.DISCORD_ID", "process.env.DISCORD_SECRET"],
        "reason": "NextAuth v5 convention is AUTH_DISCORD_ID / AUTH_DISCORD_SECRET. Bulk-generator used old/wrong env var names.",
    },
    "database.prisma_aggregate.028": {
        "drop": ["$queryRaw"],
        "reason": "Capability is 'monthly aggregate via Prisma' — typed groupBy/aggregate is more idiomatic than dropping to $queryRaw. Models correctly avoid raw SQL.",
    },
    "nextjs.loading.018": {
        "drop": ["animate-pulse"],
        "reason": "animate-pulse is one of many skeleton-loader styles. Models use animate-shimmer, bg-gradient, custom CSS, etc. Capability is 'render a loading state', not 'use this exact Tailwind class'.",
    },
    "nextjs.loading.020": {
        "drop": ["animate-pulse"],
        "reason": "Same as nextjs.loading.018 — over-specific Tailwind class requirement.",
    },
    "server-actions.transaction.036": {
        "drop": ["prisma.lineItem"],
        "reason": "Model name 'lineItem' is the bulk-generator's guess. Models infer different names like 'invoiceItem', 'lineItems'. Capability ($transaction over related models) is still enforced.",
    },
    "server-actions.transaction.038": {
        "drop": ["prisma.member"],
        "reason": "Same as transaction.036 — model name dependency. Models use 'workspaceMember', 'user', etc.",
    },
    "typescript.result_type.020": {
        "drop": ["ok: true", "ok: false"],
        "reason": "Discriminated unions can use {ok: true/false}, {success: true/false}, {kind: 'ok'/'err'}, or interface-based Ok<T>/Err<E>. Capability is 'tagged union for Result', not a specific tag name.",
    },
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    fixed_count = 0
    untouched_files: set[str] = set()
    files_modified: dict[str, list[str]] = {}

    for cat_file in sorted(TASKS_DIR.glob("*.jsonl")):
        records = [json.loads(line) for line in open(cat_file) if line.strip()]
        modified = False
        for rec in records:
            if rec["task_id"] in SUSPECTS:
                fix = SUSPECTS[rec["task_id"]]
                static = rec["checks"]["static"]
                original = list(static.get("must_contain", []))
                new = [t for t in original if t not in fix["drop"]]
                if original != new:
                    static["must_contain"] = new
                    modified = True
                    fixed_count += 1
                    files_modified.setdefault(cat_file.name, []).append(
                        f"  {rec['task_id']}: dropped {fix['drop']}"
                    )

        if modified and not args.dry_run:
            with open(cat_file, "w") as f:
                for rec in records:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        elif not modified:
            untouched_files.add(cat_file.name)

    print(f"Tasks fixed: {fixed_count}/{len(SUSPECTS)}")
    for fname, fixes in files_modified.items():
        print(f"\n{fname}:")
        for f in fixes:
            print(f)

    if args.dry_run:
        print("\n[dry-run] no files written. Re-run without --dry-run to apply.")

    missing = set(SUSPECTS.keys()) - {
        line.split(":")[0].strip()
        for fixes in files_modified.values()
        for line in fixes
    }
    if missing:
        print(f"\nWARNING: {len(missing)} suspect task_ids were not found in tasks/:")
        for tid in missing:
            print(f"  {tid}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
