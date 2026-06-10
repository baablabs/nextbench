#!/usr/bin/env python3
"""Upload NextBench to Hugging Face Hub as a dataset.

Pushes the entire nextbench/ directory to `baablabs/nextbench` on HF Hub so
that `datasets.load_dataset("baablabs/nextbench")` works for end users.

Prerequisites:
  1. pip install -U huggingface_hub
  2. huggingface-cli login    (one-time, opens browser)
     OR export HF_TOKEN=hf_...
  3. The org `baablabs` must exist on HF Hub. Create it at:
     https://huggingface.co/organizations/new
     (Free. Match the GitHub org name exactly.)

Usage:
  # Dry run — list what would be uploaded:
  python nextbench/scripts/upload_to_hf.py --dry-run

  # Real upload:
  python nextbench/scripts/upload_to_hf.py

  # Upload to a different repo (e.g. personal namespace for testing):
  python nextbench/scripts/upload_to_hf.py --repo-id YOUR_USERNAME/nextbench

What gets uploaded:
  - README.md (with HF dataset card frontmatter — `load_dataset` reads this)
  - LICENSE
  - LEADERBOARD.md, REPORT.md, STATUS.md, ANALYSIS_v0.1.md, CAPABILITY_ANALYSIS_v0.1.md
    (visible in dataset card / repo browser)
  - tasks/ (the JSONL data files — these become splits)
  - outputs/ (canonical v0.2 model outputs — useful for re-verification)
  - outputs_v01/ (historical v0.1 outputs preserved for reference)
  - run_eval.py, run_eval_litgpt.py, grade.py, scripts/ (reproducibility)
  - audit_report_v02*.json, retired_v01.jsonl (transparency artifacts)

What does NOT get uploaded:
  - .git/, __pycache__/, .DS_Store, anything matched by .gitignore
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # nextbench/
DEFAULT_REPO_ID = "baablabs/nextbench"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID, help=f"HF repo id (default: {DEFAULT_REPO_ID})")
    parser.add_argument("--dry-run", action="store_true", help="List what would upload without pushing")
    parser.add_argument("--commit-message", default="Upload NextBench v0.2")
    args = parser.parse_args()

    try:
        from huggingface_hub import HfApi, create_repo
    except ImportError:
        sys.exit(
            "Missing dependency. Install with:\n"
            "  pip install -U huggingface_hub"
        )

    api = HfApi()

    # Verify auth.
    try:
        whoami = api.whoami()
        print(f"Authenticated as: {whoami.get('name', '?')}")
    except Exception as e:
        sys.exit(
            f"HF Hub auth failed: {e}\n\n"
            "Run one of:\n"
            "  huggingface-cli login        (interactive, recommended)\n"
            "  export HF_TOKEN=hf_...        (env var)"
        )

    # Inventory what we're about to push.
    files: list[Path] = []
    for p in sorted(ROOT.rglob("*")):
        if p.is_dir():
            continue
        rel = p.relative_to(ROOT)
        parts = rel.parts
        if any(part.startswith(".") for part in parts):
            continue
        if "__pycache__" in parts:
            continue
        if parts[0] == "outputs" and parts[-1].startswith("_scratch_"):
            continue
        files.append(rel)

    total_bytes = sum((ROOT / f).stat().st_size for f in files)
    print(f"\nWill upload {len(files)} files ({total_bytes/1024:.1f} KB total) to dataset `{args.repo_id}`:\n")
    for f in files:
        size_kb = (ROOT / f).stat().st_size / 1024
        print(f"  {size_kb:8.1f} KB   {f}")

    if args.dry_run:
        print("\n--dry-run set — exiting without upload.")
        return

    # Ensure repo exists. create_repo is idempotent with exist_ok=True.
    print(f"\nEnsuring dataset repo `{args.repo_id}` exists...")
    create_repo(repo_id=args.repo_id, repo_type="dataset", exist_ok=True)

    # Upload the folder.
    print(f"Uploading {ROOT} -> {args.repo_id}...")
    api.upload_folder(
        folder_path=str(ROOT),
        repo_id=args.repo_id,
        repo_type="dataset",
        commit_message=args.commit_message,
        ignore_patterns=[".git/*", "__pycache__/*", ".DS_Store", "outputs/_scratch_*", "*.bak", "*.pyc"],
    )

    print(f"\nDone. View at: https://huggingface.co/datasets/{args.repo_id}")
    print(f"Load with: load_dataset({args.repo_id!r})")


if __name__ == "__main__":
    main()
