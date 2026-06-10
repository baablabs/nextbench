# NextBench v0.2 — Candidate Batch 002a (Middleware)

**8 candidate tasks.** Fills the empty `middleware` category. Each task probes a distinct Next.js middleware capability with no template-cloned variants.

Pipeline: Stages 1–4 complete (sourcing, uniqueness, prompt + ideal authored separately, capability-focused checks). Stages 5–7 (grader self-validation, discrimination pre-test, review) pending.

## Revisions applied 2026-06-08 (post-review, 7 ACCEPT + 1 REVISE)

| Task | Change | Reason |
|---|---|---|
| 1. `locale_redirect` | Regex tightened: `NextResponse\.redirect` only (no `rewrite`) | Locale routing is specifically a redirect capability; rewrite would silently pass |
| 2. `bot_block` | Difficulty `trivial` → `mid` | UA parsing + matcher export is above the v0.1 `trivial` floor |
| 4. `rate_limit_ip` | Removed `buckets` from `must_contain` | Capability is rate limiting, not a JS Map store; edge memory is ephemeral |
| 8. `session_refresh` | Added `sameSite` to `must_contain` | `SameSite` is part of the cookie-security capability, not optional polish |

## Why these 8 in this order

| # | task_id | Capability | Why this slot |
|---|---|---|---|
| 1 | `middleware.locale_redirect.001` | i18n routing via `Accept-Language` | Most common middleware pattern after auth |
| 2 | `middleware.bot_block.001` | User-Agent based access control | Real production skill, distinct from auth flow |
| 3 | `middleware.csrf_token.001` | CSRF cookie/header validation | Security pattern that strong models know cleanly |
| 4 | `middleware.rate_limit_ip.001` | IP-based rate limit + `Retry-After` | Forces edge-runtime-compatible state management |
| 5 | `middleware.maintenance_mode.001` | env-flag-gated 503 | Tests `process.env` access in edge + matcher exclusions |
| 6 | `middleware.subdomain_routing.001` | host-based rewrite (not redirect) | Tests the rewrite-vs-redirect distinction explicitly |
| 7 | `middleware.api_key_validation.001` | header validation against env | Tests env-secret comparison + 401 response |
| 8 | `middleware.session_refresh.001` | re-set session cookie with `httpOnly` + `maxAge` | Tests cookie security flags on response side |

## Review checklist (same as batch 001)

For each task, please answer:

1. **Capability uniqueness:** Genuinely distinct, no template clone?
2. **Ideal output correctness:** Idiomatic Next.js 14/15 middleware?
3. **Check rigor:** Do `must_contain` / `must_not_contain` / `must_match_regex` grade the right thing?
4. **Anti-pattern validity:** Are forbidden patterns genuinely wrong, not stylistic?
5. **Discrimination plausibility:** Strong model passes, weak model fails?

ACCEPT / REVISE (specific changes) / REJECT (specific reason).

---

# Task 1 — `middleware.locale_redirect.001`

**Capability.** Inspect the `Accept-Language` header on incoming requests, pick a supported locale, redirect to `/<locale>/...` if the URL doesn't already include one.

**Source.** [Next.js i18n routing docs](https://nextjs.org/docs/app/building-your-application/routing/internationalization).

**Why distinct.** No v0.1 task touches `Accept-Language` or locale-based middleware. Different mechanism from any auth/protection pattern.

### Prompt

```typescript
// middleware.ts — locale-aware routing via Accept-Language header
import { NextResponse, type NextRequest } from 'next/server'

const SUPPORTED_LOCALES = ['en', 'es', 'fr', 'de'] as const
const DEFAULT_LOCALE = 'en'

function pickLocale(acceptLanguage: string | null): string {
  if (!acceptLanguage) return DEFAULT_LOCALE
  for (const part of acceptLanguage.split(',')) {
    const tag = part.split(';')[0].trim().slice(0, 2)
    if (SUPPORTED_LOCALES.includes(tag as typeof SUPPORTED_LOCALES[number])) return tag
  }
  return DEFAULT_LOCALE
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  if (SUPPORTED_LOCALES.some((l) => pathname.startsWith(`/${l}/`) || pathname === `/${l}`)) {
    return NextResponse.next()
  }
```

### Ideal continuation

```typescript
  const locale = pickLocale(request.headers.get('accept-language'))
  const url = request.nextUrl.clone()
  url.pathname = `/${locale}${pathname}`
  return NextResponse.redirect(url)
}

export const config = {
  matcher: ['/((?!_next|api|.*\\..*).*)'],
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["NextResponse.redirect", "accept-language", "matcher"],
    "must_not_contain": ["document.cookie", "useState", "localStorage"],
    "must_match_regex": ["NextResponse\\.redirect", "matcher\\s*:"],
    "min_lines": 5,
    "max_lines": 18
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `document.cookie` | No DOM in edge middleware. |
| `useState` | Not a React component. |
| `localStorage` | No DOM. |

Difficulty: `mid`. Tags: `["typescript", "edge-runtime", "next-middleware", "i18n"]`. file_path: `middleware.ts`.

---

# Task 2 — `middleware.bot_block.001`

**Capability.** Parse `User-Agent`, deny known bot patterns with HTTP 403 on a scoped path.

**Source.** Standard middleware pattern; documented in middleware-cookbook style guides.

**Why distinct.** No v0.1 task touches `User-Agent` parsing. Different mechanism from any cookie/auth check.

### Prompt

```typescript
// middleware.ts — block known bot/crawler user agents from /admin
import { NextResponse, type NextRequest } from 'next/server'

const BOT_PATTERNS = /bot|crawl|spider|scraper|wget|curl/i

export function middleware(request: NextRequest) {
  const userAgent = request.headers.get('user-agent') || ''
```

### Ideal continuation

```typescript
  if (BOT_PATTERNS.test(userAgent)) {
    return new NextResponse('Forbidden', { status: 403 })
  }
  return NextResponse.next()
}

export const config = {
  matcher: '/admin/:path*',
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["BOT_PATTERNS", "403", "matcher", "admin"],
    "must_not_contain": ["document.cookie", "useState", "fetch("],
    "must_match_regex": ["403", "matcher\\s*:\\s*['\"`].*admin"],
    "min_lines": 4,
    "max_lines": 16
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `document.cookie` | No DOM. |
| `useState` | Not a component. |
| `fetch(` | Middleware should fail fast on UA check, not remote-validate. |

Difficulty: `mid`. Tags: `["typescript", "edge-runtime", "next-middleware"]`. file_path: `middleware.ts`.

---

# Task 3 — `middleware.csrf_token.001`

**Capability.** On unsafe HTTP methods, compare a token from a cookie against one from a custom header; reject mismatches with 403.

**Source.** [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html) — "double-submit cookie" pattern.

**Why distinct.** No v0.1 task touches CSRF or method-conditional middleware logic. Distinct security capability.

### Prompt

```typescript
// middleware.ts — CSRF protection for POST/PUT/PATCH/DELETE
import { NextResponse, type NextRequest } from 'next/server'

const UNSAFE_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']

export function middleware(request: NextRequest) {
  if (!UNSAFE_METHODS.includes(request.method)) {
    return NextResponse.next()
  }
```

### Ideal continuation

```typescript
  const cookieToken = request.cookies.get('csrf-token')?.value
  const headerToken = request.headers.get('x-csrf-token')
  if (!cookieToken || !headerToken || cookieToken !== headerToken) {
    return new NextResponse('Invalid CSRF token', { status: 403 })
  }
  return NextResponse.next()
}

export const config = {
  matcher: '/api/:path*',
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["csrf-token", "x-csrf-token", "403", "matcher"],
    "must_not_contain": ["document.cookie", "useState", "localStorage"],
    "must_match_regex": ["403|Forbidden|Invalid", "matcher\\s*:"],
    "min_lines": 5,
    "max_lines": 18
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `document.cookie` | No DOM; cookie access is via `request.cookies`. |
| `useState` | Not a component. |
| `localStorage` | No DOM. |

Difficulty: `mid`. Tags: `["typescript", "edge-runtime", "next-middleware", "security"]`. file_path: `middleware.ts`.

---

# Task 4 — `middleware.rate_limit_ip.001`

**Capability.** Track requests per client IP in an in-memory `Map` bucket; respond with 429 + `Retry-After` header when the limit is exceeded; reset on window expiry.

**Source.** [`Retry-After` header (MDN)](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Retry-After); standard rate-limit pattern.

**Why distinct.** No v0.1 task touches rate limiting or response-header construction. Distinct from any auth/CSRF check.

### Prompt

```typescript
// middleware.ts — naive in-memory rate limiter for /api routes
import { NextResponse, type NextRequest } from 'next/server'

const RATE_LIMIT = 10
const WINDOW_MS = 60_000
const buckets = new Map<string, { count: number; expiresAt: number }>()

function getClientIp(request: NextRequest): string {
  return request.headers.get('x-forwarded-for')?.split(',')[0].trim() ?? 'unknown'
}

export function middleware(request: NextRequest) {
  const ip = getClientIp(request)
  const now = Date.now()
  const bucket = buckets.get(ip)
```

### Ideal continuation

```typescript
  if (!bucket || bucket.expiresAt < now) {
    buckets.set(ip, { count: 1, expiresAt: now + WINDOW_MS })
    return NextResponse.next()
  }
  if (bucket.count >= RATE_LIMIT) {
    return new NextResponse('Too Many Requests', {
      status: 429,
      headers: { 'Retry-After': String(Math.ceil((bucket.expiresAt - now) / 1000)) },
    })
  }
  bucket.count++
  return NextResponse.next()
}

export const config = {
  matcher: '/api/:path*',
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["429", "Retry-After", "matcher"],
    "must_not_contain": ["useState", "document.cookie", "fetch("],
    "must_match_regex": ["429", "matcher\\s*:\\s*['\"`].*api"],
    "min_lines": 8,
    "max_lines": 24
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `useState` | Not a component. |
| `document.cookie` | No DOM. |
| `fetch(` | Middleware should rate-limit locally, not phone home. |

Difficulty: `hard`. Tags: `["typescript", "edge-runtime", "next-middleware", "rate-limit"]`. file_path: `middleware.ts`.

---

# Task 5 — `middleware.maintenance_mode.001`

**Capability.** Read `MAINTENANCE_MODE` env var; when enabled, rewrite all traffic to `/maintenance` with 503 status, allow `/maintenance` itself and exclude `_next` / `/api/health` via matcher.

**Source.** Standard ops pattern; documented in Vercel maintenance-mode guides.

**Why distinct.** No v0.1 task touches `process.env` reads, 503 responses, or rewrite-with-status. Distinct from redirect-based patterns.

### Prompt

```typescript
// middleware.ts — global maintenance mode toggle via env var
import { NextResponse, type NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  if (process.env.MAINTENANCE_MODE !== 'true') {
    return NextResponse.next()
  }
```

### Ideal continuation

```typescript
  if (request.nextUrl.pathname.startsWith('/maintenance')) {
    return NextResponse.next()
  }
  const url = request.nextUrl.clone()
  url.pathname = '/maintenance'
  return NextResponse.rewrite(url, { status: 503 })
}

export const config = {
  matcher: '/((?!_next|api/health).*)',
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["503", "maintenance", "NextResponse.rewrite", "matcher"],
    "must_not_contain": ["useState", "document.cookie", "fetch("],
    "must_match_regex": ["503", "NextResponse\\.(rewrite|redirect)"],
    "min_lines": 5,
    "max_lines": 18
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `useState` | Not a component. |
| `document.cookie` | No DOM. |
| `fetch(` | Maintenance check is local, not remote. |

Difficulty: `mid`. Tags: `["typescript", "edge-runtime", "next-middleware", "ops"]`. file_path: `middleware.ts`.

---

# Task 6 — `middleware.subdomain_routing.001`

**Capability.** Read `host` header, extract subdomain, rewrite (not redirect) the path to a tenant-scoped internal route. Pass through root / `www` requests untouched.

**Source.** [Vercel multi-tenant routing example](https://vercel.com/templates/next.js/platforms-starter-kit).

**Why distinct.** No v0.1 task touches `host` header, multi-tenancy, or rewrite-vs-redirect distinction. Tests an explicit decision: `rewrite` (URL stays) vs `redirect` (URL changes).

### Prompt

```typescript
// middleware.ts — multi-tenant subdomain routing
import { NextResponse, type NextRequest } from 'next/server'

const ROOT_DOMAIN = 'example.com'

export function middleware(request: NextRequest) {
  const host = request.headers.get('host') ?? ''
  const subdomain = host.replace(`.${ROOT_DOMAIN}`, '').split(':')[0]
```

### Ideal continuation

```typescript
  if (subdomain === host || subdomain === 'www') {
    return NextResponse.next()
  }
  const url = request.nextUrl.clone()
  url.pathname = `/_tenant/${subdomain}${url.pathname}`
  return NextResponse.rewrite(url)
}

export const config = {
  matcher: '/((?!_next|api).*)',
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["NextResponse.rewrite", "subdomain", "_tenant", "matcher"],
    "must_not_contain": ["NextResponse.redirect", "useState", "document.cookie"],
    "must_match_regex": ["NextResponse\\.rewrite", "matcher\\s*:"],
    "min_lines": 5,
    "max_lines": 18
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `NextResponse.redirect` | Multi-tenant routing must *rewrite* — redirect would change the URL bar and break the subdomain UX. This is the capability test. |
| `useState`, `document.cookie` | Not a component / no DOM. |

Difficulty: `mid`. Tags: `["typescript", "edge-runtime", "next-middleware", "multi-tenant"]`. file_path: `middleware.ts`.

---

# Task 7 — `middleware.api_key_validation.001`

**Capability.** Compare a request header against an env secret; return 401 if missing or mismatched; scope to `/api/internal/*` via matcher.

**Source.** Standard API key gating pattern.

**Why distinct.** No v0.1 task touches header-vs-env-var comparison. Distinct from CSRF (different threat model: server-to-server, not browser).

### Prompt

```typescript
// middleware.ts — protect /api/internal/* with API key header
import { NextResponse, type NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const apiKey = request.headers.get('x-api-key')
```

### Ideal continuation

```typescript
  if (!apiKey || apiKey !== process.env.INTERNAL_API_KEY) {
    return new NextResponse('Unauthorized', { status: 401 })
  }
  return NextResponse.next()
}

export const config = {
  matcher: '/api/internal/:path*',
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["process.env", "401", "matcher", "internal"],
    "must_not_contain": ["useState", "document.cookie", "localStorage"],
    "must_match_regex": ["401|Unauthorized", "matcher\\s*:\\s*['\"`].*internal"],
    "min_lines": 4,
    "max_lines": 14
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `useState`, `document.cookie`, `localStorage` | Not a component / no DOM. |

Difficulty: `trivial`. Tags: `["typescript", "edge-runtime", "next-middleware", "api-key"]`. file_path: `middleware.ts`.

---

# Task 8 — `middleware.session_refresh.001`

**Capability.** When a session cookie is present, re-set it on the outgoing response with `httpOnly`, `secure`, `sameSite`, and an extended `maxAge` — extending the session window on each request.

**Source.** Standard "rolling session" pattern; documented in NextAuth and Lucia session-management guides.

**Why distinct.** v0.1's `auth.middleware` (n=3) tests NextAuth-specific helpers. This is generic cookie-refresh logic on the *response* (response.cookies.set), which v0.1 never tests.

### Prompt

```typescript
// middleware.ts — refresh session cookie expiry on each request
import { NextResponse, type NextRequest } from 'next/server'

const SESSION_TTL_SECONDS = 60 * 60 * 24 * 7 // 7 days

export function middleware(request: NextRequest) {
  const session = request.cookies.get('session')
  if (!session) {
    return NextResponse.next()
  }
  const response = NextResponse.next()
```

### Ideal continuation

```typescript
  response.cookies.set('session', session.value, {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    maxAge: SESSION_TTL_SECONDS,
    path: '/',
  })
  return response
}

export const config = {
  matcher: '/((?!_next|api/auth).*)',
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["response.cookies.set", "httpOnly", "sameSite", "session.value", "matcher"],
    "must_not_contain": ["document.cookie", "useState", "localStorage"],
    "must_match_regex": ["(maxAge|expires)\\s*:", "httpOnly\\s*:\\s*true"],
    "min_lines": 6,
    "max_lines": 18
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `document.cookie` | Cookie writes go through `response.cookies.set`, not the DOM. |
| `useState`, `localStorage` | Not a component / no DOM. |

Difficulty: `mid`. Tags: `["typescript", "edge-runtime", "next-middleware", "auth"]`. file_path: `middleware.ts`.

---

## After this batch survives review

If 7–8 of these tasks promote with only minor fixes:
- ✅ Pipeline is validated for the remaining batches (002b–002f, 37 more capabilities).
- Generation continues per [ROADMAP.md](ROADMAP.md), one batch at a time, reviewer between each.

If ≥3 tasks need major rework or rejection:
- 🛑 Pipeline needs adjustment before scaling. Resolve in this batch first.
