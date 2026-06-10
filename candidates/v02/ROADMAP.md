# NextBench v0.2 — Capability Roadmap

**Locked 2026-06-08.** Master plan for v0.2 generation. Source of truth for what gets built and what doesn't.

## v0.2 generation rule

> **1 capability = 1 canonical task.** Check the capability, not the implementation.

Every task in v0.2 grades a single distinct Next.js / React capability. No template-cloned entity variants. Checks reward the capability marker; implementation choices (specific Prisma method, specific UI library, specific field name) are not penalized.

## v0.2 targets

- **Distinct capabilities:** ~233 (v0.1's 188 + ~45 new)
- **Total tasks:** ~280 (after v0.1 dedup pass + batch 001 + batch 002)
- **Capability density:** ≥ 0.83

## Capability list (locked, post-review)

### Batch 001 — already generated (5 tasks)

Reviewed, revised, lock-pending final approval:

1. `middleware.auth_redirect` — protect routes via session cookie
2. `nextjs.streaming_suspense` — inline `<Suspense>` + async server component
3. `nextjs.unstable_cache` — `unstable_cache` with `revalidate` + `tags`
4. `react.optimistic_ui` — `useOptimistic` + `useTransition`
5. `server-actions.revalidate_after_mutation` — mutation → `revalidatePath` → `redirect`

### Batch 002a — middleware (8 tasks)

The empty-category-fill batch. Generated next.

1. `middleware.locale_redirect` — `Accept-Language` → `/[locale]`
2. `middleware.bot_block` — `User-Agent` parsing → 403
3. `middleware.csrf_token` — cookie/header CSRF validation on unsafe methods
4. `middleware.rate_limit_ip` — IP-based rate limit → 429 + `Retry-After`
5. `middleware.maintenance_mode` — env-flag-gated 503 rewrite
6. `middleware.subdomain_routing` — host header → rewrite to `/_tenant/<sub>`
7. `middleware.api_key_validation` — `x-api-key` env compare → 401
8. `middleware.session_refresh` — re-set session cookie on each request

### Batch 002b — caching + streaming (8 tasks)

The "biggest hole" batch per reviewer.

9. `nextjs.revalidate_tag` — server action calls `revalidateTag`
10. `nextjs.fetch_no_store` — `{ cache: 'no-store' }`
11. `nextjs.fetch_revalidate_seconds` — `next: { revalidate: 60 }`
12. `nextjs.draft_mode` — `draftMode().enable()`
13. `nextjs.react_cache` — `cache()` from React for request-scoped memo
14. `nextjs.parallel_suspense` — parallel `<Suspense>` boundaries
15. `nextjs.error_boundary_recovery` — `error.tsx` with `reset()`
16. `react.use_promise` — React 19 `use(promise)`

### Batch 002c — react-19 + edge (7 tasks)

17. `react.form_action` — `<form action={serverAction}>`
18. `react.use_form_state` — `useFormState` + server action
19. `react.action_state` — `useActionState` with typed error returns
20. `react.use_context_typed` — typed `useContext` provider + hook
21. `edge.runtime_export_const` — `export const runtime = 'edge'`
22. `edge.geo_response` — `x-vercel-ip-country` / `cf-ipcountry`
23. `edge.streaming_response` — `ReadableStream` in `Response`

### Batch 002d — server-actions + api-routes (8 tasks)

24. `server-actions.zod_field_errors` — `safeParse` → field-level errors
25. `server-actions.use_form_status_pending` — client uses `useFormStatus()`
26. `server-actions.cookies_set` — server action sets cookie via `cookies()`
27. `server-actions.headers_check` — reads incoming headers via `headers()`
28. `api-routes.streaming_response` — `ReadableStream` response body
29. `api-routes.form_data_parse` — `request.formData()` parsing
30. `api-routes.signed_url_redirect` — generate presigned URL → redirect
31. `api-routes.webhook_signature_verify` — HMAC signature check (generic, not Stripe-specific)

### Batch 002e — prisma + realtime (8 tasks)

32. `database.prisma_transaction` — `$transaction(async tx => …)`
33. `database.prisma_nested_create` — nested `create: { …children }`
34. `database.prisma_cursor_pagination` — `take` + `cursor`
35. `database.prisma_count_groupby` — `count` + `groupBy`
36. `auth.resource_owner` — verify `resource.userId === session.userId` before mutate
37. `nextjs.sse_response` — Server-Sent Events with `text/event-stream`
38. `react.use_websocket_hook` — client hook wrapping a WebSocket
39. `react.optimistic_chat` — `useOptimistic` over message list (distinct from #4's scalar pattern)

### Batch 002f — file/i18n/search (6 tasks)

40. `api-routes.file_upload_formdata` — `multipart/form-data` parsing (capability-only, no s3/uploadThing requirements)
41. `react.file_drop_zone` — drag-drop file input with `onDrop`
42. `nextjs.next_intl_setup` — `NextIntlClientProvider` in root layout (note: package-specific, may age)
43. `nextjs.locale_segment_param` — `[locale]` dynamic segment + `getTranslations`
44. `nextjs.search_params_zod` — Zod-validate `searchParams` with `safeParse`
45. `react.use_search_params_client` — client `useSearchParams()` for filters

## Roadmap adjustments — post-review 2026-06-08

| Change | Item | Reason |
|---|---|---|
| **REMOVE** | `database.prisma_raw_query` | `$queryRaw` isn't typically a capability — it's "I couldn't express this in Prisma." Benchmark should reward higher-level relations / transactions / aggregations first. |
| **ADD (replacing prisma_raw_query)** | `auth.resource_owner` | Real production skill — verify resource ownership before mutation. Distinct from v0.1's existing `auth.role_guard` (which tests role checking, not ownership). |
| **DEFER to v0.3 backlog** | `nextjs.not_found` | Modern Next.js error-handling surface beyond what `error.tsx` covers. Not urgent for v0.2. |

### Yellow-light guidance (apply during generation)

| Capability | Constraint |
|---|---|
| `api-routes.webhook_signature_verify` | Test generic HMAC signature verification, not Stripe docs memorization. No `stripe.webhooks.constructEvent` requirement. |
| `api-routes.file_upload_formdata` | Capability is `multipart/form-data` parsing. No `s3`, `uploadThing`, `vercel-blob` requirements. |
| `nextjs.next_intl_setup` | Framework-level i18n stronger than package-specific. May age faster as `next-intl` evolves. |

## v0.3 backlog

Tracked for future batches, not in v0.2 scope:

- `nextjs.not_found` — `notFound()` and `not-found.tsx` patterns
- Additional auth flows beyond ownership/roles
- More edge runtime patterns

## Why this roadmap, in one sentence

NextBench v0.1 was "the formalized internal eval." NextBench v0.2 is **the modern Next.js capability benchmark** — covering middleware, caching, streaming, React 19, edge runtime, server-action UX patterns, and resource-level authorization that the v0.1 entity-variant generator never reached.
