#!/usr/bin/env python3
"""Check for capability duplication in the v0.2 registry.

Prevents accidentally re-doing the same capability across batches as the
benchmark scales toward 50+ capabilities. Run before adding a new capability
to capabilities.jsonl.

Usage:
  # Audit the existing registry
  python check_capability_dup.py

  # Check whether a proposed capability collides with existing
  python check_capability_dup.py --propose middleware.auth_redirect
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "capabilities.jsonl"


def load_registry() -> list[dict]:
    if not REGISTRY.exists():
        sys.exit(f"Missing registry at {REGISTRY}")
    return [json.loads(line) for line in REGISTRY.open() if line.strip()]


def audit(records: list[dict]) -> int:
    """Return number of issues found."""
    issues = 0
    ids = [r["capability_id"] for r in records]
    dups = [cid for cid, n in Counter(ids).items() if n > 1]
    if dups:
        print("DUPLICATE capability_ids:")
        for d in dups:
            print(f"  - {d}")
        issues += len(dups)

    print(f"\nRegistry: {len(records)} capabilities")
    by_status = Counter(r["status"] for r in records)
    print(f"  by status:")
    for s, n in by_status.most_common():
        print(f"    {s:12s} {n}")

    by_batch = Counter(r["batch"] for r in records)
    print(f"  by batch:")
    for b, n in sorted(by_batch.items()):
        print(f"    {b:6s} {n}")

    by_category = Counter(r["category"] for r in records)
    print(f"  by category:")
    for c, n in by_category.most_common():
        print(f"    {c:18s} {n}")

    return issues


def propose(records: list[dict], candidate: str) -> int:
    """Check if a proposed capability_id collides with existing.

    Soft-collision = same prefix (category.subcat) regardless of suffix variant.
    """
    existing = {r["capability_id"] for r in records}
    if candidate in existing:
        print(f"COLLISION (exact): `{candidate}` already in registry")
        match = next(r for r in records if r["capability_id"] == candidate)
        print(f"  batch:  {match['batch']}")
        print(f"  status: {match['status']}")
        return 1
    # Soft collision: same category, similar subcategory
    cat = candidate.split(".")[0]
    sub = candidate.split(".")[-1] if "." in candidate else ""
    soft = [r for r in records if r["category"] == cat and sub in r["capability_id"].lower()]
    if soft:
        print(f"SOFT COLLISIONS (review):")
        for r in soft:
            print(f"  - {r['capability_id']:50s} ({r['batch']} / {r['status']})")
    else:
        print(f"OK: `{candidate}` has no collisions in registry.")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--propose", help="Check a proposed capability_id for collisions")
    args = parser.parse_args()

    records = load_registry()
    if args.propose:
        sys.exit(propose(records, args.propose))
    else:
        sys.exit(audit(records))


if __name__ == "__main__":
    main()
