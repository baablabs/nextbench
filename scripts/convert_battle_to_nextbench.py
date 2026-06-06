#!/usr/bin/env python3
"""Convert the 355-prompt battle suite into NextBench v0.1 JSONL.

Reads:  eval/battle/battle_prompts.json  (single JSON array, legacy schema)
Writes: nextbench/tasks/<category>.jsonl (one file per category, schema v1.0)

Source-of-truth migrator. Deterministic. Re-runnable. If the source data
or schema decisions change, edit this script and re-run; do NOT hand-edit
the generated JSONL files.

Locked decisions (see RELEASE.md "Phase 1 — NextBench"):
  - One benchmark, multiple task_types. All 355 source tasks are completion.
  - Categories renamed: server-action -> server-actions, route-handler -> api-routes.
  - 13th category 'middleware' added (empty in v0.1, populated during expansion).
  - JSONL not JSON array.
  - schema_version 1.0, benchmark_version 0.1.
  - HF Hub layout: tasks/<category>.jsonl.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE = ROOT / "eval" / "battle" / "battle_prompts.json"
OUT_DIR = ROOT / "nextbench" / "tasks"

SCHEMA_VERSION = "1.0"
BENCHMARK_VERSION = "0.1"
SOURCE_TAG = "baab-battle-v1"
LICENSE = "MIT"
CREATED = "2026-05-09"

# Source category -> NextBench category (renames only).
CATEGORY_RENAME = {
    "server-action": "server-actions",
    "route-handler": "api-routes",
}

# Final NextBench v0.1 categories. Order matters for stable output listing.
NEXTBENCH_CATEGORIES = [
    "react",
    "hooks",
    "nextjs",
    "server-actions",
    "api-routes",
    "form",
    "tailwind",
    "typescript",
    "auth",
    "payments",
    "database",
    "utils",
    "middleware",  # empty in v0.1
]


def parse_id(legacy_id: str) -> tuple[str, str, str]:
    """Split legacy id "<cat>_<subcat>_<NNN>" into (category, subcategory, num)."""
    parts = legacy_id.split("_")
    if len(parts) >= 3 and parts[-1].isdigit():
        num = parts[-1]
        # Category may itself contain hyphens (server-action, route-handler).
        # Everything after the first underscore and before the trailing number
        # is subcategory; the source category field is the source of truth.
        subcategory = "_".join(parts[1:-1])
    else:
        num = "000"
        subcategory = "misc"
    return parts[0], subcategory, num


def extract_component_name(prompt: str) -> str | None:
    """Pull the function/component name from `export default function Foo(`."""
    m = re.search(r"export\s+default\s+(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)", prompt)
    if m:
        return m.group(1)
    m = re.search(r"export\s+(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)", prompt)
    if m:
        return m.group(1)
    return None


def infer_file_path(category: str, subcategory: str, prompt: str) -> str:
    """Best-effort file path for the prompt's destination file in a Next.js project."""
    name = extract_component_name(prompt)

    if category == "react":
        return f"components/{name or 'Component'}.tsx"

    if category == "hooks":
        hook_name = subcategory if subcategory.startswith("use") else (name or "useHook")
        return f"hooks/{hook_name}.ts"

    if category == "nextjs":
        nextjs_paths = {
            "home_page": "app/page.tsx",
            "dynamic_page": "app/[slug]/page.tsx",
            "protected_page": "app/(protected)/page.tsx",
            "layout_metadata": "app/layout.tsx",
            "loading": "app/loading.tsx",
            "error_boundary": "app/error.tsx",
            "not_found": "app/not-found.tsx",
            "og_image": "app/opengraph-image.tsx",
            "parallel_routes": "app/@modal/[id]/page.tsx",
            "intercepting_route": "app/(.)photo/[id]/page.tsx",
            "generate_metadata": "app/page.tsx",
            "search_params": "app/page.tsx",
            "robots_route": "app/robots.ts",
            "sitemap_route": "app/sitemap.ts",
        }
        return nextjs_paths.get(subcategory, "app/page.tsx")

    if category == "server-actions":
        return "app/actions.ts"

    if category == "api-routes":
        # Most route handlers are app/api/<resource>/route.ts; default to that shape.
        return "app/api/route.ts"

    if category == "form":
        return f"components/{name or 'Form'}.tsx"

    if category == "tailwind":
        return f"components/{name or 'Section'}.tsx"

    if category == "typescript":
        return "types.ts"

    if category == "auth":
        auth_paths = {
            "nextauth_config": "app/api/auth/[...nextauth]/route.ts",
            "middleware": "middleware.ts",
            "credentials_provider": "lib/auth.ts",
            "magic_link_provider": "lib/auth.ts",
            "jwt_callback": "lib/auth.ts",
            "session_callback": "lib/auth.ts",
            "handlers_reexport": "app/api/auth/[...nextauth]/route.ts",
            "signin_page": "app/(auth)/signin/page.tsx",
            "signup_action": "app/actions.ts",
            "protected_component": f"components/{name or 'Protected'}.tsx",
            "role_guard": f"components/{name or 'RoleGuard'}.tsx",
        }
        return auth_paths.get(subcategory, "lib/auth.ts")

    if category == "payments":
        if "stripe" in subcategory:
            if "webhook" in subcategory:
                return "app/api/stripe/webhook/route.ts"
            return "app/api/stripe/route.ts"
        if "razorpay" in subcategory:
            return "app/api/razorpay/route.ts"
        if "paddle" in subcategory:
            return "app/api/paddle/route.ts"
        if "lemonsqueezy" in subcategory:
            return "app/api/lemonsqueezy/route.ts"
        if "dodo" in subcategory:
            return "app/api/dodo/route.ts"
        if "cashfree" in subcategory:
            return "app/api/cashfree/route.ts"
        return f"components/{name or 'Checkout'}.tsx"

    if category == "database":
        if "prisma_model" in subcategory or "prisma_relations" in subcategory or "drizzle_schema" in subcategory:
            return "prisma/schema.prisma" if "prisma" in subcategory else "db/schema.ts"
        return "lib/db.ts"

    if category == "utils":
        return "lib/utils.ts"

    if category == "middleware":
        return "middleware.ts"

    return "app/page.tsx"


def infer_tags(category: str, subcategory: str, prompt: str, must_contain: list[str]) -> list[str]:
    """Conservative tag derivation. Only add tags clearly evidenced by the source."""
    tags: list[str] = []
    mc_lower = [s.lower() for s in must_contain]
    prompt_lower = prompt.lower()

    # Universal — every prompt is TS/TSX in v0.1.
    tags.append("typescript")

    if "'use client'" in prompt or '"use client"' in prompt:
        tags.append("client-component")
    elif category in {"nextjs", "server-actions", "api-routes", "middleware"} and "use client" not in prompt_lower:
        tags.append("server-component")

    if "'use server'" in prompt or '"use server"' in prompt or category == "server-actions":
        tags.append("server-action")

    # React hooks usage (any built-in or custom hook starting with 'use').
    if re.search(r"\buse[A-Z]\w+", prompt) or any(re.match(r"use[A-Z]", s) for s in must_contain):
        tags.append("react-hook")

    if any(h in prompt_lower or h in mc_lower for h in ("onclick", "onchange", "onsubmit", "onkeydown", "onmouseenter")):
        tags.append("event-handler")

    if category == "tailwind" or re.search(r'className="[^"]*\b(bg-|text-|p-|m-|h-|w-|flex|grid|rounded)', prompt):
        tags.append("tailwind")

    if "z.object" in prompt or "z.object" in " ".join(must_contain) or "from 'zod'" in prompt:
        tags.append("zod")

    if "useform" in prompt_lower or "react-hook-form" in prompt_lower:
        tags.append("react-hook-form")

    if "prisma" in prompt_lower or "prisma" in subcategory:
        tags.append("prisma")
    if "drizzle" in prompt_lower or "drizzle" in subcategory:
        tags.append("drizzle")

    if "nextauth" in prompt_lower or "next-auth" in prompt_lower:
        tags.append("nextauth")

    if "stripe" in subcategory or "stripe" in prompt_lower:
        tags.append("stripe")
    if "razorpay" in subcategory:
        tags.append("razorpay")
    if "paddle" in subcategory:
        tags.append("paddle")

    if "formdata" in prompt_lower or "formdata" in mc_lower:
        tags.append("formdata")

    # Dedupe preserving order.
    seen = set()
    out = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def convert_one(legacy: dict) -> dict:
    legacy_cat = legacy["category"]
    nextbench_cat = CATEGORY_RENAME.get(legacy_cat, legacy_cat)
    _, subcategory, num = parse_id(legacy["id"])
    task_id = f"{nextbench_cat}.{subcategory}.{num}"

    prompt = legacy["prompt"]
    must_contain = legacy.get("must_contain", []) or []
    must_not_contain = legacy.get("must_not_contain", []) or []
    must_match_regex = legacy.get("must_match_regex", []) or []

    return {
        "task_id": task_id,
        "task_type": "completion",
        "category": nextbench_cat,
        "subcategory": subcategory,
        "difficulty": legacy["difficulty"],
        "tags": infer_tags(nextbench_cat, subcategory, prompt, must_contain),
        "file_path": infer_file_path(nextbench_cat, subcategory, prompt),
        "prompt": prompt,
        "context": {
            "prefix": prompt,
            "cursor_position": len(prompt),
            "suffix": "",
        },
        "checks": {
            "static": {
                "must_contain": must_contain,
                "must_not_contain": must_not_contain,
                "must_match_regex": must_match_regex,
                "min_lines": legacy.get("min_lines", 0),
                "max_lines": legacy.get("max_lines", 9999),
            },
            "execution": None,
            "judge": None,
        },
        "metadata": {
            "source": SOURCE_TAG,
            "schema_version": SCHEMA_VERSION,
            "benchmark_version": BENCHMARK_VERSION,
            "license": LICENSE,
            "created": CREATED,
            "legacy_id": legacy["id"],
            "judge_brief": legacy.get("judge_brief", ""),
        },
    }


def main():
    source = json.load(open(SOURCE))
    print(f"Read {len(source)} legacy tasks from {SOURCE.relative_to(ROOT)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    by_category: dict[str, list[dict]] = defaultdict(list)
    for legacy in source:
        new = convert_one(legacy)
        by_category[new["category"]].append(new)

    # Sort within category for deterministic output.
    for cat in by_category:
        by_category[cat].sort(key=lambda t: t["task_id"])

    # Write a JSONL per category, including empty middleware.jsonl.
    totals: dict[str, int] = {}
    for cat in NEXTBENCH_CATEGORIES:
        out_path = OUT_DIR / f"{cat}.jsonl"
        tasks = by_category.get(cat, [])
        with open(out_path, "w") as f:
            for t in tasks:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")
        totals[cat] = len(tasks)
        print(f"  {cat:18s} {len(tasks):4d} tasks  -> {out_path.relative_to(ROOT)}")

    grand = sum(totals.values())
    print(f"\nWrote {grand} tasks across {len(NEXTBENCH_CATEGORIES)} categories.")
    if grand != len(source):
        raise SystemExit(f"FATAL: total mismatch ({grand} written vs {len(source)} source).")


if __name__ == "__main__":
    main()
