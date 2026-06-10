# NextBench v0.2 — Candidate Batch 002b (Caching + Streaming)

**8 candidate tasks.** Fills v0.1's most damning gap — *zero* coverage of `next/cache` and streaming primitives. Per the reviewer: *"caching and streaming are far less represented across existing coding benchmarks than middleware."* This batch is where we expect the strongest benchmark gains.

Pipeline: Stages 1–4 complete. Capability markers > implementation specifics throughout.

## The 8 capabilities

| # | task_id | Diff | Tests |
|---|---|---|---|
| 9 | `nextjs.revalidate_tag.001` | mid | `revalidateTag('products')` after a server-action mutation |
| 10 | `nextjs.fetch_no_store.001` | trivial | `cache: 'no-store'` (or `next: { revalidate: 0 }`) opt-out |
| 11 | `nextjs.fetch_revalidate_seconds.001` | trivial | `next: { revalidate: N }` time-bounded fetch caching |
| 12 | `nextjs.draft_mode.001` | mid | `draftMode().enable()` + redirect in preview route |
| 13 | `nextjs.react_cache.001` | hard | React `cache()` for request-scoped server-side memoization |
| 14 | `nextjs.parallel_suspense.001` | mid | Multiple `<Suspense>` boundaries rendering in parallel |
| 15 | `nextjs.error_boundary_recovery.001` | mid | `error.tsx` with `reset()` retry button |
| 16 | `react.use_promise.001` | hard | React 19 `use(promise)` for streaming a promise to a client component |

## Two key design decisions

**1. Task 10 and 11 are deliberately separated** because they test opposite intents — *don't cache at all* (`no-store`) vs *cache with a time bound* (`revalidate: N`). A model that knows one but not the other will discriminate. Most code models conflate them.

**2. Task 14 (`parallel_suspense`) is structurally distinct from batch 001's `streaming_suspense`** — that one tests *one* boundary around *one* component; this tests *multiple parallel* boundaries (the more common production pattern: dashboard with several independently-loading panels). The capability is "parallel streaming," which is what makes Suspense win against waterfall fetches.

## Review checklist (same as previous batches)

For each task: ACCEPT / REVISE / REJECT with specifics. Pipeline-validation already passed; this batch is the scaling test for the caching+streaming sub-domain.

---

# Task 9 — `nextjs.revalidate_tag.001`

**Capability.** Server action mutates the database (Prisma `delete`), then calls `revalidateTag('products')` to invalidate every `unstable_cache` entry tagged with that key.

**Source.** [`revalidateTag` API reference](https://nextjs.org/docs/app/api-reference/functions/revalidateTag).

**Why distinct.** v0.1 has zero `revalidateTag` tasks. Pairs naturally with batch 001's `unstable_cache` (both use the `'products'` tag — the model can grasp tag-based invalidation as a system).

### Prompt

```typescript
// app/admin/products/actions.ts
'use server'
import { revalidateTag } from 'next/cache'
import { prisma } from '@/lib/prisma'

export async function deleteProduct(id: string) {
```

### Ideal continuation

```typescript
  await prisma.product.delete({ where: { id } })
  revalidateTag('products')
  return { success: true }
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["prisma.product", "revalidateTag", "products"],
    "must_not_contain": ["useState", "useEffect", "fetch(", "window.location", "router.push"],
    "must_match_regex": ["revalidateTag\\s*\\(", "prisma\\.product\\.(delete|deleteMany)"],
    "min_lines": 3,
    "max_lines": 10
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `useState`, `useEffect` | Server action; React hooks unavailable. |
| `fetch(` | Action should mutate the DB directly, not call its own API. |
| `window.location`, `router.push` | Server-side; no DOM and no client router. |

Difficulty: `mid`. Tags: `["typescript", "server-action", "next-cache", "prisma"]`. file_path: `app/admin/products/actions.ts`.

---

# Task 10 — `nextjs.fetch_no_store.001`

**Capability.** Opt out of Next.js fetch caching with `cache: 'no-store'` (or the equivalent `next: { revalidate: 0 }`) — for endpoints whose freshness must beat caching.

**Source.** [Next.js Caching docs](https://nextjs.org/docs/app/building-your-application/caching).

**Why distinct.** v0.1 has zero fetch-caching tasks. Tests whether the model knows the explicit cache opt-out idiom.

### Prompt

```typescript
// app/dashboard/page.tsx — must always show fresh stats, never cached
async function getStats() {
  const res = await fetch('https://api.example.com/stats', {
```

### Ideal continuation

```typescript
    cache: 'no-store',
  })
  return res.json()
}

export default async function Dashboard() {
  const stats = await getStats()
  return (
    <main className="p-6">
      <h1>Stats</h1>
      <pre>{JSON.stringify(stats, null, 2)}</pre>
    </main>
  )
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["res.json"],
    "must_not_contain": ["localStorage", "useEffect"],
    "must_match_regex": ["(cache\\s*:\\s*['\"`]no-store|revalidate\\s*:\\s*0)"],
    "min_lines": 3,
    "max_lines": 18
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `Date.now()` | Manual cache-busting via query-string timestamps is the anti-pattern the framework primitive replaces. |
| `localStorage`, `useEffect` | Wrong runtime / wrong pattern for a server component fetcher. |

The regex accepts **both** valid idioms — `cache: 'no-store'` (preferred) *and* `next: { revalidate: 0 }` (equivalent). The capability is "explicit no-cache directive," not the specific spelling.

Difficulty: `trivial`. Tags: `["typescript", "server-component", "next-cache"]`. file_path: `app/dashboard/page.tsx`.

---

# Task 11 — `nextjs.fetch_revalidate_seconds.001`

**Capability.** Time-bounded fetch caching via `next: { revalidate: N }` — for endpoints whose data is acceptable to serve stale for up to N seconds.

**Source.** [Next.js fetch options](https://nextjs.org/docs/app/api-reference/functions/fetch).

**Why distinct from #10.** Opposite intent: #10 disables caching entirely; #11 enables it with a TTL. A model that conflates them will fail one of the two.

### Prompt

```typescript
// lib/getExchangeRates.ts — exchange rates refresh every 5 minutes
export async function getExchangeRates() {
  const res = await fetch('https://api.example.com/rates', {
```

### Ideal continuation

```typescript
    next: { revalidate: 300 },
  })
  return res.json()
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["next", "revalidate", "res.json"],
    "must_not_contain": ["Date.now()", "localStorage", "useEffect", "no-store"],
    "must_match_regex": ["next\\s*:\\s*\\{[^}]*revalidate\\s*:\\s*\\d+"],
    "min_lines": 2,
    "max_lines": 10
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `no-store` | Capability is *time-bounded caching*; `no-store` is the opposite intent — gets credit on Task 10 instead. |
| `Date.now()` | Manual cache-busting defeats the framework's TTL. |
| `localStorage`, `useEffect` | Wrong runtime. |

Difficulty: `trivial`. Tags: `["typescript", "server-component", "next-cache"]`. file_path: `lib/getExchangeRates.ts`.

---

# Task 12 — `nextjs.draft_mode.001`

**Capability.** Preview-mode route handler that validates a secret query param, enables draft mode via `draftMode().enable()`, then redirects into the post page so subsequent fetches see uncached drafts.

**Source.** [`draftMode` API reference](https://nextjs.org/docs/app/api-reference/functions/draftMode).

**Why distinct.** v0.1 has zero preview-mode tasks. Real CMS pattern.

### Prompt

```typescript
// app/api/preview/route.ts
import { draftMode } from 'next/headers'
import { redirect } from 'next/navigation'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const secret = searchParams.get('secret')
  const slug = searchParams.get('slug')

  if (secret !== process.env.PREVIEW_SECRET || !slug) {
    return new Response('Invalid', { status: 401 })
  }
```

### Ideal continuation

```typescript
  (await draftMode()).enable()
  redirect(`/posts/${slug}`)
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["draftMode", ".enable", "redirect", "slug"],
    "must_not_contain": ["useState", "fetch(", "useRouter", "window.location"],
    "must_match_regex": ["draftMode\\s*\\(", "redirect\\s*\\(\\s*[`'\"]"],
    "min_lines": 2,
    "max_lines": 8
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `useRouter`, `window.location` | Route handler context; no client router or DOM. |
| `useState` | Not React. |
| `fetch(` | Handler should enable preview and redirect; no remote call needed. |

Difficulty: `mid`. Tags: `["typescript", "route-handler", "next-cache", "preview"]`. file_path: `app/api/preview/route.ts`.

---

# Task 13 — `nextjs.react_cache.001`

**Capability.** Wrap a database-query fn in React's `cache()` so calls within the same request share a single execution (request-scoped memoization). The canonical pattern for "fetch the current user once per request."

**Source.** [React `cache()` reference](https://react.dev/reference/react/cache); [Next.js memoization docs](https://nextjs.org/docs/app/building-your-application/caching#react-cache-function).

**Why distinct.** Different mechanism from `unstable_cache` (cross-request, with TTL/tags) — `cache()` is intra-request only. Tests whether the model knows the distinction.

### Prompt

```typescript
// lib/getCurrentUser.ts — request-scoped memoization
import { cache } from 'react'
import { cookies } from 'next/headers'
import { prisma } from './prisma'

export const getCurrentUser = cache(async () => {
```

### Ideal continuation

```typescript
  const sessionId = (await cookies()).get('session')?.value
  if (!sessionId) return null
  return prisma.user.findUnique({
    where: { sessionToken: sessionId },
  })
})
```

### Checks

```json
{
  "static": {
    "must_contain": ["cookies", "prisma", "return"],
    "must_not_contain": ["useState", "useEffect", "fetch(", "localStorage"],
    "must_match_regex": ["return", "\\}\\s*\\)"],
    "min_lines": 4,
    "max_lines": 14
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `useState`, `useEffect` | Server-side function; not React UI code. |
| `fetch(` | The function reads from Prisma (per the prompt's imports), not remote. |
| `localStorage` | Wrong runtime. |

The trailing `\}\s*\)` regex enforces correct closure of the `cache(...)` wrapper — a common failure mode for weaker models on nested function wrappers.

Difficulty: `hard`. Tags: `["typescript", "server-component", "react-19", "next-cache", "prisma"]`. file_path: `lib/getCurrentUser.ts`.

---

# Task 14 — `nextjs.parallel_suspense.001`

**Capability.** Multiple `<Suspense>` boundaries inside a single page, each wrapping a different async server component, each with its own fallback. The production pattern for dashboards with several independently-loading panels.

**Source.** [Streaming with Suspense](https://nextjs.org/docs/app/building-your-application/routing/loading-ui-and-streaming#streaming-with-suspense).

**Why distinct from batch 001's `streaming_suspense`.** That tests *one* boundary around *one* component. This tests *parallel* streaming — the capability that makes Suspense actually win against waterfalls.

### Prompt

```typescript
// app/dashboard/page.tsx — parallel-streamed dashboard
import { Suspense } from 'react'
import { UserProfile } from './UserProfile'
import { RecentOrders } from './RecentOrders'
import { Recommendations } from './Recommendations'

export default function Dashboard() {
```

### Ideal continuation

```typescript
  return (
    <main className="p-6 grid grid-cols-3 gap-6">
      <Suspense fallback={<p>Loading profile…</p>}>
        <UserProfile />
      </Suspense>
      <Suspense fallback={<p>Loading orders…</p>}>
        <RecentOrders />
      </Suspense>
      <Suspense fallback={<p>Loading recommendations…</p>}>
        <Recommendations />
      </Suspense>
    </main>
  )
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["<Suspense", "fallback", "UserProfile", "RecentOrders", "Recommendations"],
    "must_not_contain": ["useState", "useEffect", "'use client'"],
    "must_match_regex": ["<Suspense[^>]*fallback", "<Suspense[\\s\\S]*<Suspense"],
    "min_lines": 8,
    "max_lines": 28
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `useState`, `useEffect`, `'use client'` | Page must stay a server component for streaming to work. |

The second regex (`<Suspense[\s\S]*<Suspense`) is the *parallel* capability marker — the page must contain at least two `<Suspense>` boundaries, which is the distinguishing feature versus the batch-001 single-boundary task.

Difficulty: `mid`. Tags: `["typescript", "server-component", "streaming", "suspense"]`. file_path: `app/dashboard/page.tsx`.

---

# Task 15 — `nextjs.error_boundary_recovery.001`

**Capability.** App Router `error.tsx` — a client component that receives `error` + `reset` props, logs the error, and renders a "Try again" button that calls `reset()` to re-attempt the failed segment without a full page reload.

**Source.** [Error Handling docs](https://nextjs.org/docs/app/building-your-application/routing/error-handling).

**Why distinct.** v0.1 has an `error_boundary` subcategory (n=5) but those test the file existence + `'use client'` directive. This tests the *recovery* capability via `reset()` — different mechanic.

### Prompt

```typescript
// app/dashboard/error.tsx
'use client'
import { useEffect } from 'react'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])
```

### Ideal continuation

```typescript
  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold mb-2">Something went wrong</h2>
      <p className="text-zinc-500 mb-4">{error.message}</p>
      <button
        onClick={() => reset()}
        className="px-3 py-1.5 rounded border"
      >
        Try again
      </button>
    </div>
  )
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["reset", "error.message", "onClick", "<button"],
    "must_not_contain": ["window.location.reload", "router.push", "fetch("],
    "must_match_regex": ["reset\\s*\\(", "onClick"],
    "min_lines": 5,
    "max_lines": 22
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `window.location.reload` | Defeats the segment-scoped recovery the App Router gives for free — the entire point of `reset()` is *not* doing a full page reload. |
| `router.push` | Navigating away discards the error context instead of recovering from it. |
| `fetch(` | Recovery is local; no remote call needed. |

Difficulty: `mid`. Tags: `["typescript", "client-component", "error-handling", "react-hook", "event-handler"]`. file_path: `app/dashboard/error.tsx`.

---

# Task 16 — `react.use_promise.001`

**Capability.** Read a server-passed promise inside a client component using React 19's `use(promise)` hook — the Suspense-aware unwrap, contrast with `await` (server-only) and `.then()` (legacy).

**Source.** [`use` API reference](https://react.dev/reference/react/use).

**Why distinct.** v0.1 has zero `use(promise)` tasks. The pattern unlocks the "pass a promise from server to client and let Suspense handle the wait" architecture that's the React 19 way of doing client streaming.

### Prompt

```typescript
'use client'
import { use } from 'react'

type UserProps = {
  userPromise: Promise<{ id: string; name: string; email: string }>
}

export function UserCard({ userPromise }: UserProps) {
```

### Ideal continuation

```typescript
  const user = use(userPromise)
  return (
    <article className="border rounded p-4">
      <h2 className="text-lg font-medium">{user.name}</h2>
      <p className="text-sm text-zinc-500">{user.email}</p>
    </article>
  )
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["use(userPromise)", "user.name", "user.email"],
    "must_not_contain": ["useState", "useEffect", "await", ".then("],
    "must_match_regex": ["use\\s*\\(\\s*userPromise"],
    "min_lines": 4,
    "max_lines": 14
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `await` | Client components can't `await` top-level; the whole point of `use()` is the Suspense-aware unwrap. |
| `.then(` | Old promise-handling pattern. `use()` IS the new pattern. |
| `useState`, `useEffect` | Suggest the model is fetching client-side instead of consuming a server-passed promise — wrong architectural intent. |

Difficulty: `hard`. Tags: `["typescript", "client-component", "react-19", "react-hook", "suspense"]`. file_path: `components/UserCard.tsx`.

---

## After this batch

If 7–8 promote with minor fixes, batch 002c (react-19 + edge, 7 tasks) goes next.

The full v0.2 roadmap is in [ROADMAP.md](ROADMAP.md). Six batches total. After 002b: ~21 capabilities locked, 29 to go.
