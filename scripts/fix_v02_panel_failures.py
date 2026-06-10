#!/usr/bin/env python3
"""Surgical fix for v0.2 tasks the model panel surfaced as broken.

Each suspect here was flagged by scan_universal_failures.py running against
outputs_v02/. Diagnosis was done by inspecting actual model outputs vs the
ideal. Fixes are minimal: prompt clarification or check relaxation, never
capability redesign.

Run AFTER scan_universal_failures.py confirms the issue, BEFORE re-eval.

Usage:
  python fix_v02_panel_failures.py --dry-run
  python fix_v02_panel_failures.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
V02_ONLY_DIR = ROOT / "tasks_v02_only"


def apply_fix(rec: dict) -> bool:
    """Return True if the record was modified."""
    tid = rec["task_id"]

    if tid == "api-routes.edge_runtime.001":
        # Prompt redesign: end prompt before the handler so the completion
        # naturally includes BOTH the runtime export AND the handler body.
        new_prompt = (
            "// app/api/ping/route.ts — lightweight health check; must run on edge runtime\n"
            "import { NextResponse } from 'next/server'\n\n"
        )
        new_ideal = (
            "export const runtime = 'edge'\n\n"
            "export async function GET() {\n"
            "  return NextResponse.json({\n"
            "    ok: true,\n"
            "    timestamp: Date.now(),\n"
            "    region: process.env.VERCEL_REGION ?? 'local',\n"
            "  })\n"
            "}"
        )
        rec["prompt"] = new_prompt
        rec["context"]["prefix"] = new_prompt
        rec["context"]["cursor_position"] = len(new_prompt)
        rec["ideal_output"] = new_ideal
        return True

    if tid == "api-routes.form_data_parse.001":
        # Add a file-purpose comment so the model has context for what to parse.
        new_prompt = (
            "// app/api/contact/route.ts — POST handler for the multipart contact form\n"
            "import { NextResponse } from 'next/server'\n\n"
            "export async function POST(request: Request) {"
        )
        rec["prompt"] = new_prompt
        rec["context"]["prefix"] = new_prompt
        rec["context"]["cursor_position"] = len(new_prompt)
        return True

    if tid == "api-routes.signed_url_redirect.001":
        # Models hit max_tokens before reaching the redirect line. Drop it from
        # must_contain — the security primitive (HMAC + timingSafeEqual, already
        # required) is the primary capability marker per the 002d reviewer note.
        static = rec["checks"]["static"]
        static["must_contain"] = [t for t in static["must_contain"] if t != "NextResponse.redirect"]
        return True

    if tid == "middleware.subdomain_routing.001":
        # `_tenant` is a specific path prefix this task happens to use; models
        # legitimately pick /tenants/, /site/, /${subdomain}, etc. Drop the
        # brittle token — NextResponse.rewrite (still required) is the
        # architectural primitive.
        static = rec["checks"]["static"]
        static["must_contain"] = [t for t in static["must_contain"] if t != "_tenant"]
        return True

    return False


def fix_dir(d: Path, dry_run: bool) -> dict[str, int]:
    """Apply fixes to every jsonl file in d. Return {filename: fix_count}."""
    counts: dict[str, int] = {}
    for jp in sorted(d.glob("*.jsonl")):
        records = [json.loads(line) for line in open(jp) if line.strip()]
        n = 0
        for rec in records:
            if apply_fix(rec):
                n += 1
        if n > 0:
            counts[jp.name] = n
            if not dry_run:
                with open(jp, "w") as f:
                    for rec in records:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(f"Fixing tasks/ (canonical corpus)...")
    c1 = fix_dir(TASKS_DIR, args.dry_run)
    for f, n in c1.items():
        print(f"  {f}: {n} fix(es)")

    print(f"\nFixing tasks_v02_only/ (eval mini-corpus)...")
    c2 = fix_dir(V02_ONLY_DIR, args.dry_run)
    for f, n in c2.items():
        print(f"  {f}: {n} fix(es)")

    total = sum(c1.values()) + sum(c2.values())
    print(f"\nTotal fixes: {total} (expected 8 = 4 fixes × 2 corpora)")

    if args.dry_run:
        print("[dry-run] no files written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
