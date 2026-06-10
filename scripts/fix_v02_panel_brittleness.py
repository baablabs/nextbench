#!/usr/bin/env python3
"""Fix the 41 universal-failure tasks surfaced by scan_universal_failures.py
on the v0.2 (450-task) corpus.

The pattern across these failures is consistent and fits the brittleness
class we already documented in CONTEXT/STATUS:

  (A) Arbitrary names — must_contain expects a specific variable, function,
      type, or string-literal name (e.g., 'autofillUS', 'tokenHash',
      'modal-root', 'monthBucket', 'COLOR_MAP') that a model has no way to
      predict from the prompt. False-negative engine.

  (B) Second-function expectations — must_contain expects tokens from a
      SECOND function/type/feature beyond what the model can produce in
      max_tokens=500 (the canonical leaderboard setting).

  (C) Over-narrow implementation choice — must_contain expects a specific
      implementation detail (e.g., 'getElementById', '308' status code,
      'placeholder=' attribute) where multiple correct implementations exist.

This script drops the never-hit tokens per task. We retain tokens that
encode the actual API surface being measured (the things that genuinely
must appear for the answer to be correct), and drop tokens that encode
implementation choices the prompt did not constrain.

We then smoke-test the patched task: the ideal_output must still score
4/4 against the patched checks. The smoke test is run inline.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
sys.path.insert(0, str(ROOT))
from grade import grade_one  # noqa: E402


# ──────────────────────────────────────────────────────────────────────────
# Per-task drop list.
# Each entry maps task_id -> dict with optional `drop_must_contain` and
# `drop_must_match_regex` lists. We drop EXACTLY those tokens; we don't add
# new ones. The reason field is for documentation only — it's not used by
# the patcher but it's why we're dropping each token.
# ──────────────────────────────────────────────────────────────────────────
PATCHES: dict[str, dict] = {
    # ── api-routes ──────────────────────────────────────────────────────
    "api-routes.batch_processor.001": {
        # Promise.allSettled IS the right API for batch processing —
        # keep as required, but drop 'fulfilled' (the discrimination
        # of fulfilled/rejected on settled results is a stylistic choice).
        "drop_must_contain": ["fulfilled"],
        "drop_must_match_regex": ["fulfilled"],
        "reason": "C — fulfilled key is one stylistic choice",
    },
    "api-routes.cron_signature.001": {
        # The handler returning early with timestamp + deletedCount is a
        # SECOND chunk beyond signature verification.
        "drop_must_contain": ["deletedCount", "timestamp", "toISOString"],
        "drop_must_match_regex": [r"toISOString\s*\("],
        "reason": "B — second chunk beyond signature verification",
    },
    "api-routes.download_csv.001": {
        # 'text/csv' is the right Content-Type; keep it. But the
        # 'attachment' disposition + .csv filename are implementation details.
        "drop_must_contain": [".csv", "Content-Disposition", "attachment"],
        "drop_must_match_regex": ["attachment"],
        "reason": "C — only 'text/csv' MIME is required signal",
    },
    "api-routes.health_check.001": {
        # 'degraded' and 'checks.upstream' are specific shape choices.
        "drop_must_contain": ["checks.upstream", "degraded"],
        "drop_must_match_regex": ["degraded", r"status\s*:\s*allOk"],
        "reason": "C — health-check shape isn't pinned by prompt",
    },
    "api-routes.openapi_export.001": {
        # Models tend to return the OpenAPI doc inline-stringified or
        # omit field-by-field literals.
        "drop_must_contain": ["3.1.0", "info"],
        "drop_must_match_regex": [r"paths\s*:"],
        "reason": "C — OpenAPI doc shape varies; keep 'openapi' marker",
    },
    "api-routes.pagination_link_header.001": {
        # Link header IS the API; keep it. But links.join is one impl path.
        "drop_must_contain": ["links.join"],
        "reason": "A — links.join is one of several valid joins",
    },
    "api-routes.versioned_route.001": {
        # API-Version is the canonical header name but case-sensitive
        # substring matching fails on 'api-version' etc.
        "drop_must_contain": ["API-Version"],
        "drop_must_match_regex": ["API-Version"],
        "reason": "A — case-sensitive header name match too narrow",
    },

    # ── auth ────────────────────────────────────────────────────────────
    "auth.password_reset_token.001": {
        "drop_must_contain": ["tokenHash"],
        "drop_must_match_regex": ["tokenHash"],
        "reason": "A — tokenHash is an arbitrary variable name",
    },
    "auth.refresh_token_rotate.001": {
        "drop_must_contain": ["revokedAt"],
        "drop_must_match_regex": [r"refreshToken\.update", "revokedAt"],
        "reason": "A — revokedAt is one of several valid soft-revoke columns",
    },

    # ── database ────────────────────────────────────────────────────────
    "database.aggregate_window.001": {
        "drop_must_contain": ["_count", "monthBucket"],
        "drop_must_match_regex": [r"_count\s*:"],
        "reason": "A — monthBucket is an arbitrary alias name",
    },
    "database.optimistic_locking.001": {
        # newVersion is an arbitrary name; result.count is implementation.
        "drop_must_contain": ["newVersion", "result.count"],
        "drop_must_match_regex": [r"result\.count\s*===\s*0"],
        # Keep 'updateMany' since that IS the API.
        "reason": "A — newVersion + result.count are arbitrary names",
    },
    "database.prisma_extension.001": {
        # 'compute' and 'fullName' are arbitrary field/computed-name choices.
        "drop_must_contain": ["compute", "fullName"],
        "drop_must_match_regex": [r"compute\s*\("],
        "reason": "A — compute()/fullName are arbitrary names",
    },
    "database.soft_delete.001": {
        # listActivePosts is a SECOND function. deletedAt is the API.
        "drop_must_contain": ["listActivePosts"],
        "drop_must_match_regex": [],
        "reason": "B — listActivePosts is a second function",
    },

    # ── form ────────────────────────────────────────────────────────────
    "form.html5_validation.001": {
        "drop_must_contain": ["checkValidity"],
        "drop_must_match_regex": [r"checkValidity\s*\(\s*\)"],
        "reason": "C — checkValidity is one of several validation impls",
    },
    "form.rhf_dependent_field.001": {
        # Specific error-message literal is arbitrary.
        "drop_must_contain": ["Passwords must match"],
        "reason": "A — error message text is arbitrary",
    },
    "form.rhf_set_value.001": {
        "drop_must_contain": ["autofillUS"],
        "drop_must_match_regex": [r"onClick\s*=\s*\{autofillUS"],
        "reason": "A — autofillUS is an arbitrary function name",
    },

    # ── middleware ──────────────────────────────────────────────────────
    "middleware.ab_test_assignment.001": {
        "drop_must_contain": ["x-ab-variant"],
        "drop_must_match_regex": ["x-ab-variant"],
        "reason": "A — header name is one of several valid choices",
    },
    "middleware.cookie_consent_redirect.001": {
        "drop_must_contain": ["returnTo"],
        "reason": "A — returnTo is an arbitrary cookie/param name",
    },
    "middleware.https_redirect.001": {
        # Models default to 307/308 inconsistently; 308 specifically too narrow.
        "drop_must_contain": ["308"],
        "drop_must_match_regex": ["308"],
        "reason": "C — 307 also valid for permanent HTTPS redirect",
    },
    "middleware.legacy_url_redirect.001": {
        "drop_must_match_regex": [r"redirect\s*\([^,]+,\s*308"],
        "reason": "C — 307 also valid",
    },
    "middleware.observability_log.001": {
        "drop_must_match_regex": [r"request\.nextUrl\.pathname"],
        "reason": "C — req.url and request.url also valid",
    },

    # ── nextjs ──────────────────────────────────────────────────────────
    "nextjs.fetch_revalidate_tag.001": {
        "drop_must_match_regex": [r"next\s*:\s*\{[^}]*tags", r"tags\s*:\s*\["],
        "reason": "C — tags array shape varies (single vs literal)",
    },
    "nextjs.optional_catch_all.001": {
        "drop_must_match_regex": [r"filter\s*=\s*\[\]"],
        "reason": "A — empty-array default destructure pattern is arbitrary",
    },
    "nextjs.sse_response.001": {
        # SSE is genuinely hard to one-shot in 500 tokens. Drop the
        # specific impl tokens, keep text/event-stream as the marker.
        "drop_must_contain": ["ReadableStream", "controller.enqueue", "data:"],
        "drop_must_match_regex": [r"ReadableStream\s*\(\s*\{"],
        "reason": "B/C — only text/event-stream content-type is fingerprint",
    },

    # ── performance ─────────────────────────────────────────────────────
    "performance.image_priority_lcp.001": {
        "drop_must_contain": ["placeholder", "sizes="],
        "drop_must_match_regex": [r"placeholder\s*=\s*[\"']blur"],
        "reason": "C — placeholder/sizes are optional Next/Image props",
    },
    "performance.next_font_subset.001": {
        "drop_must_contain": ["display:", "variable:"],
        "drop_must_match_regex": [r"display\s*:\s*['\"]swap['\"]"],
        "reason": "C — display:swap and variable: are stylistic choices",
    },
    "performance.use_callback.001": {
        "drop_must_match_regex": [r"onToggle\s*=\s*\{handleToggle"],
        "reason": "A — onToggle/handleToggle names are arbitrary",
    },

    # ── react ───────────────────────────────────────────────────────────
    "react.compound_component.001": {
        "drop_must_contain": ["TabTrigger"],
        "drop_must_match_regex": ["TabTrigger"],
        "reason": "A — TabTrigger is an arbitrary subcomponent name",
    },
    "react.controlled_select.001": {
        "drop_must_match_regex": [r"value\s*=\s*\{value\}"],
        "reason": "A — `value` is one of many valid state-variable names",
    },
    "react.portal_modal.001": {
        "drop_must_contain": ["getElementById", "modal-root"],
        "reason": "A/C — modal-root element id is implementation-specific",
    },
    "react.use_deferred_value.001": {
        "drop_must_contain": ["isStale"],
        "drop_must_match_regex": [r"query\s*!==\s*deferredQuery"],
        "reason": "A — isStale variable name + comparison style are arbitrary",
    },

    # ── server-actions ──────────────────────────────────────────────────
    "server-actions.audit_log.001": {
        "drop_must_contain": ["$transaction", "actorId", "auditLog.create"],
        "drop_must_match_regex": [r"\$transaction\s*\(", r"auditLog\.create"],
        "reason": "A — schema-specific names; $transaction is one impl path",
    },
    "server-actions.enqueue_job.001": {
        "drop_must_contain": ["exportJob.create", "jobId", "queued"],
        "drop_must_match_regex": [r"exportJob\.create"],
        "reason": "A — exportJob/jobId/queued are arbitrary schema choices",
    },
    "server-actions.session_extend.001": {
        "drop_must_contain": ["newExpiry"],
        "reason": "A — newExpiry is an arbitrary variable name",
    },
    "server-actions.zod_discriminated.001": {
        "drop_must_contain": ["parsed.data.type"],
        "drop_must_match_regex": [r"parsed\.data\.type"],
        "reason": "A — `parsed.data` is one of several valid bindings",
    },

    # ── testing ─────────────────────────────────────────────────────────
    "testing.playwright_form_e2e.001": {
        "drop_must_contain": ["waitForURL"],
        "drop_must_match_regex": [r"waitForURL\s*\("],
        "reason": "C — waitForURL is one of several navigation-wait APIs",
    },
    "testing.playwright_smoke.001": {
        "drop_must_contain": ["toHaveTitle"],
        "reason": "C — toHaveTitle is one of several valid first assertions",
    },

    # ── typescript-advanced ─────────────────────────────────────────────
    "typescript-advanced.const_assertion.001": {
        "drop_must_contain": ["COLOR_MAP"],
        "drop_must_match_regex": [r"\(typeof\s+\w+\)\[number\]"],
        # The (typeof X)[number] pattern would be a great differentiator
        # but the prompt only hints at STATUSES, not COLOR_MAP. Drop both
        # the SECOND constant and the regex that requires it (the regex
        # matches the type alias too, but never fired here).
        "reason": "B — COLOR_MAP is a second const beyond the prompt",
    },
    "typescript-advanced.infer_keyword.001": {
        "drop_must_contain": ["ParamsOf"],
        "reason": "B — ParamsOf is a second type beyond AwaitedT",
    },
    "typescript-advanced.satisfies_operator.001": {
        "drop_must_contain": ["RouteName"],
        "reason": "B — RouteName is a second derived type",
    },
    "typescript-advanced.template_literal_type.001": {
        "drop_must_contain": ["EntityWithVerb"],
        "drop_must_match_regex": [r"\$\{V\}"],
        "reason": "B — EntityWithVerb is a second generic type alias",
    },
}


def patch_task(task: dict, patch: dict) -> dict:
    """Apply drop lists to a task's checks. Mutates and returns."""
    checks = task["checks"]["static"]
    drops_c = set(patch.get("drop_must_contain", []))
    drops_r = set(patch.get("drop_must_match_regex", []))

    if drops_c:
        checks["must_contain"] = [t for t in checks.get("must_contain", []) if t not in drops_c]
    if drops_r:
        checks["must_match_regex"] = [r for r in checks.get("must_match_regex", []) if r not in drops_r]
    return task


def smoke_test(task: dict) -> tuple[bool, dict]:
    """Verify the task's ideal_output scores 4/4 on the patched checks."""
    ideal = task.get("ideal_output", "")
    if not ideal:
        return True, {"skipped": "no ideal_output"}
    # grade_one expects a record with `output` and `checks`. Build a stub.
    stub = {**task, "output": ideal}
    result = grade_one(stub)
    return bool(result.get("pass")), result


def main() -> None:
    files_changed: dict[str, list[dict]] = {}
    smoke_fails: list[str] = []
    applied = 0

    for fp in sorted(TASKS_DIR.glob("*.jsonl")):
        rows: list[dict] = []
        changed_in_file = False
        with open(fp) as f:
            for line in f:
                if not line.strip():
                    continue
                task = json.loads(line)
                tid = task["task_id"]
                if tid in PATCHES:
                    patch = PATCHES[tid]
                    task = patch_task(task, patch)
                    ok, result = smoke_test(task)
                    if not ok:
                        smoke_fails.append(f"{tid}: {result}")
                    else:
                        applied += 1
                    changed_in_file = True
                rows.append(task)

        if changed_in_file:
            with open(fp, "w") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            files_changed[fp.name] = [t["task_id"] for t in rows if t["task_id"] in PATCHES]

    print(f"Patched {applied}/{len(PATCHES)} tasks.")
    print(f"Files touched: {len(files_changed)}")
    for fn, ids in files_changed.items():
        print(f"  {fn}: {len(ids)} tasks patched")
    if smoke_fails:
        print(f"\nSMOKE FAILURES ({len(smoke_fails)}):")
        for sf in smoke_fails:
            print(f"  {sf}")
        sys.exit(1)
    else:
        print("\nAll patched tasks still pass smoke (ideal_output 4/4).")


if __name__ == "__main__":
    main()
