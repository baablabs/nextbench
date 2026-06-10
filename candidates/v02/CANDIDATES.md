# NextBench v0.2 — Candidate Batch 001

**5 candidate tasks for v0.2.**
Generated through Stages 1–4 of the BaaB Labs Capability Generation Pipeline. Not yet promoted to the benchmark.

## Revisions applied 2026-06-08 (post-review)

Five external-review fixes applied to tighten the checks. Each fix narrowed the test to *capability markers*, not implementation specifics:

| Task | Change | Reason |
|---|---|---|
| 1. `middleware.auth_redirect` | Removed `jwt.verify` from `must_not_contain` | `jose`'s `jwtVerify` is a valid alternative; was catching legitimate solutions |
| 2. `nextjs.streaming_suspense` | Removed `Promise.all` and `await fetch` from `must_not_contain` | Both valid inside the child component; the substring check can't distinguish *where* they appear |
| 3. `nextjs.unstable_cache` | Replaced `must_contain: ["prisma.product", "findUnique", ...]` with `["return", "revalidate", "tags"]` | The capability is the cache wrap, not the specific Prisma method (`findUnique` vs `findFirst` vs `findUniqueOrThrow` are all legitimate) |
| 4. `react.optimistic_ui` | Removed `fetch(` from `must_not_contain` | Some teams legitimately fetch from the client instead of via server actions; product choice, not anti-pattern |
| 5. `server-actions.revalidate_after_mutation` | Removed `publishedAt` from `must_contain` | Capability is *mutate → invalidate → redirect*; the specific field name (`publishedAt` vs `status: 'published'`) is an implementation choice |

The shape underneath each fix: **check the capability, not the implementation**. Going forward this is a v0.2 generation rule.

## Why these 5

Each candidate fills a **distinct capability gap** identified in [CAPABILITY_ANALYSIS_v0.1.md](../../CAPABILITY_ANALYSIS_v0.1.md):

| # | task_id | Category | Why distinct from v0.1 |
|---|---|---|---|
| 1 | `middleware.auth_redirect.001` | `middleware` (empty in v0.1) | Fills the empty 13th category — canonical session-cookie route protection |
| 2 | `nextjs.streaming_suspense.001` | `nextjs` | v0.1 has `loading.tsx` file-convention tasks; this is inline `<Suspense>` + async server component (different mechanic) |
| 3 | `nextjs.unstable_cache.001` | `nextjs` | v0.1 has zero caching tasks — entire Next.js cache API surface uncovered |
| 4 | `react.optimistic_ui.001` | `react` | v0.1 has zero `useOptimistic` / React 19 server-action UX tasks |
| 5 | `server-actions.revalidate_after_mutation.001` | `server-actions` | v0.1 has 6 mutation subcategories (create_zod, update_zod, delete, archive, transaction, formdata) — none focus on the cache-invalidation tail; this is the missing piece |

None of the five are template clones of anything in v0.1. Each tests a distinct, idiomatic Next.js capability that real production apps use.

## Pipeline reminder

Each candidate passed Stages 1–4 below. Stages 5–7 happen if and only if the candidate is approved for inclusion.

1. **Capability sourcing** — Next.js / React docs citation
2. **Uniqueness pre-filter** — no overlap with the 188 existing subcategories
3. **Prompt + ideal output authored separately** (prevents check-prompt coupling)
4. **Check authoring** from the ideal output + documented anti-patterns
5. *(later)* Grader self-validation: ideal scores 4/4, broken output scores <4
6. *(later)* Discrimination pre-test against the 12-model panel — reject if all 12 score 4/4 or all 12 score 0/4
7. *(later)* Human (or delegated) review
8. *(later)* Provenance logging into the task's metadata block

---

## How to evaluate these candidates

If you're reviewing this (whether human or LLM), please answer for each task:

1. **Is the capability genuinely distinct** from anything in v0.1? (no template clones of existing tasks)
2. **Is the ideal output correct and idiomatic** Next.js / React 19 code?
3. **Are the `must_contain` patterns load-bearing** — do they only fire when the model produced the right pattern?
4. **Are the `must_not_contain` anti-patterns** real anti-patterns (would actually be wrong code), not arbitrary?
5. **Are `must_match_regex` patterns achievable** without being template-restrictive?
6. **Are the `[min_lines, max_lines]` bounds defensible** — narrow enough to enforce discipline, wide enough to allow stylistic variation?
7. **Would a strong code model reasonably pass, and a weak model reasonably fail?** (the discrimination test)

A `REJECT` verdict on any of (1)–(7) should be specific: which check, why it's wrong, what would fix it.

---

# Task 1 — `middleware.auth_redirect.001`

**Capability.** Next.js middleware that protects routes by checking for a session cookie and redirecting unauthenticated requests to `/login`, preserving the originally requested path as a query parameter.

**Source.** [Next.js Middleware docs](https://nextjs.org/docs/app/building-your-application/routing/middleware) — canonical "protect a route" pattern.

**Why distinct.** `v0.1.auth.middleware` (n=3) tests NextAuth v5 helpers (`auth()` from `@/auth`). This task tests *generic* edge-runtime session-cookie middleware — no NextAuth, just `NextRequest.cookies` + `NextResponse.redirect`. Different API surface.

### Prompt

```typescript
// middleware.ts — protect /dashboard routes via session cookie
import { NextResponse, type NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const session = request.cookies.get('session')
```

### Ideal continuation (authored independently)

```typescript
  if (!session) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    url.searchParams.set('redirect', request.nextUrl.pathname)
    return NextResponse.redirect(url)
  }
  return NextResponse.next()
}

export const config = {
  matcher: '/dashboard/:path*',
}
```

### Checks

```json
{
  "static": {
    "must_contain": [
      "NextResponse.redirect",
      "NextResponse.next",
      "matcher",
      "dashboard"
    ],
    "must_not_contain": [
      "document.cookie",
      "useState",
      "import bcrypt"
    ],
    "must_match_regex": [
      "NextResponse\\.(redirect|next|rewrite)",
      "matcher\\s*:\\s*['\"`].*dashboard"
    ],
    "min_lines": 8,
    "max_lines": 22
  }
}
```

### Anti-pattern rationale (`must_not_contain`)

| Forbidden | Why it's wrong |
|---|---|
| `jwt.verify` | Edge runtime middleware can't use `node:crypto`; `jwt.verify` would crash on Vercel Edge. Verifying JWTs in middleware requires `jose` or `next-auth/jwt`. |
| `document.cookie` | No DOM in middleware — runs on the edge, before any client code. |
| `useState` | Middleware is not a React component; importing/calling `useState` is a category error. |
| `import bcrypt` | Pure Node module, breaks on edge runtime. |

### Difficulty: `mid`. Tags: `["typescript", "edge-runtime", "next-middleware"]`. file_path: `middleware.ts`.

---

# Task 2 — `nextjs.streaming_suspense.001`

**Capability.** Server-component page that wraps an async data-fetching child component in a `<Suspense>` boundary with a fallback, enabling streaming. Tests the model's understanding that the page itself stays synchronous while the slow child streams.

**Source.** [Loading UI and Streaming](https://nextjs.org/docs/app/building-your-application/routing/loading-ui-and-streaming) — `<Suspense>` patterns inside the App Router.

**Why distinct.** `v0.1.nextjs.loading` (n=6, sigs=1) tests the *file-convention* `loading.tsx`. This is inline `<Suspense>` + an async server component called as a child — different control flow, different mechanic.

### Prompt

```typescript
// app/dashboard/[userId]/page.tsx
import { Suspense } from 'react'

async function RecentActivity({ userId }: { userId: string }) {
  const res = await fetch(`https://api.example.com/users/${userId}/events`, {
    next: { revalidate: 60 },
  })
  const events: { id: string; message: string }[] = await res.json()
  return (
    <ul className="space-y-2">
      {events.map((e) => (
        <li key={e.id}>{e.message}</li>
      ))}
    </ul>
  )
}

export default function Dashboard({ params }: { params: { userId: string } }) {
```

### Ideal continuation

```typescript
  return (
    <main className="p-6">
      <h1 className="text-2xl font-semibold mb-4">Dashboard</h1>
      <Suspense fallback={<p className="text-zinc-500">Loading activity…</p>}>
        <RecentActivity userId={params.userId} />
      </Suspense>
    </main>
  )
}
```

### Checks

```json
{
  "static": {
    "must_contain": [
      "<Suspense",
      "fallback",
      "RecentActivity",
      "params.userId"
    ],
    "must_not_contain": [
      "useState",
      "useEffect",
      "'use client'"
    ],
    "must_match_regex": [
      "<Suspense[^>]*fallback",
      "<RecentActivity\\s+userId"
    ],
    "min_lines": 5,
    "max_lines": 18
  }
}
```

### Anti-pattern rationale

| Forbidden | Why it's wrong |
|---|---|
| `useState` | Server component; `useState` would force `'use client'`, defeating streaming. |
| `useEffect` | Same. Server components don't have effects. |
| `'use client'` | Page must stay a server component for streaming to work; otherwise the whole tree turns client and Suspense fallback never shows on initial paint. |
| `await fetch` | Awaiting in the page (not in `RecentActivity`) blocks the whole render — defeats the entire reason to use Suspense. |
| `Promise.all` | Indicates over-engineering — the page should pass the prop and let the child do the fetching. |

### Difficulty: `mid`. Tags: `["typescript", "server-component", "streaming", "suspense"]`. file_path: `app/dashboard/[userId]/page.tsx`.

---

# Task 3 — `nextjs.unstable_cache.001`

**Capability.** Wrapping a database fetcher in `unstable_cache` with named cache key, `revalidate` interval, and `tags` for on-demand invalidation. Tests the model's knowledge of Next.js's primary server-side cache API.

**Source.** [`unstable_cache` API reference](https://nextjs.org/docs/app/api-reference/functions/unstable_cache).

**Why distinct.** v0.1 has **zero** caching tasks. Entire `next/cache` API surface (`unstable_cache`, `revalidatePath`, `revalidateTag`, `cache` from React) is uncovered.

### Prompt

```typescript
// lib/getProductBySlug.ts — fetch product with Next.js cache layer
import { unstable_cache } from 'next/cache'
import { prisma } from './prisma'

export const getProductBySlug = unstable_cache(
  async (slug: string) => {
```

### Ideal continuation

```typescript
    return prisma.product.findUnique({
      where: { slug },
      include: { variants: true },
    })
  },
  ['product-by-slug'],
  {
    revalidate: 3600,
    tags: ['products'],
  }
)
```

### Checks

```json
{
  "static": {
    "must_contain": [
      "return",
      "revalidate",
      "tags"
    ],
    "must_not_contain": [
      "fetch(",
      "useEffect",
      "Date.now()",
      "localStorage",
      "setInterval"
    ],
    "must_match_regex": [
      "tags\\s*:\\s*\\[",
      "revalidate\\s*:\\s*\\d+"
    ],
    "min_lines": 6,
    "max_lines": 16
  }
}
```

### Anti-pattern rationale

| Forbidden | Why it's wrong |
|---|---|
| `fetch(` | The function is documented to wrap a DB call (`prisma.product`); replacing with a remote fetch is a category swap, not a completion. |
| `useEffect` | This is a server-side function, not React. |
| `Date.now()` | Manual cache invalidation defeats the purpose of `unstable_cache`'s built-in `revalidate`/`tags`. |
| `localStorage` | No DOM on the server. |
| `setInterval` | Same — and would leak. |

### Difficulty: `mid`. Tags: `["typescript", "next-cache", "prisma", "server-component"]`. file_path: `lib/getProductBySlug.ts`.

---

# Task 4 — `react.optimistic_ui.001`

**Capability.** `useOptimistic` + `useTransition` to update UI before the server action completes — the canonical React 19 optimistic-UI pattern for like buttons, vote counters, and similar low-stakes mutations.

**Source.** [`useOptimistic` API reference](https://react.dev/reference/react/useOptimistic).

**Why distinct.** v0.1 has zero `useOptimistic` tasks. React 19 added this API specifically for the server-action UX, and it's the right answer when the question is "show the user immediate feedback for a server mutation."

### Prompt

```typescript
'use client'
import { useOptimistic, useTransition } from 'react'
import { likePost } from '@/app/actions'

type Post = { id: string; likes: number }

export default function LikeButton({ post }: { post: Post }) {
  const [optimisticPost, addOptimisticLike] = useOptimistic(
    post,
    (state, _increment: number) => ({ ...state, likes: state.likes + 1 })
  )
  const [isPending, startTransition] = useTransition()
```

### Ideal continuation

```typescript
  return (
    <button
      onClick={() => {
        startTransition(async () => {
          addOptimisticLike(1)
          await likePost(post.id)
        })
      }}
      disabled={isPending}
      className="px-3 py-1.5 rounded border"
    >
      {optimisticPost.likes} ♥
    </button>
  )
}
```

### Checks

```json
{
  "static": {
    "must_contain": [
      "startTransition",
      "addOptimisticLike",
      "likePost",
      "optimisticPost.likes",
      "onClick"
    ],
    "must_not_contain": [
      "useState",
      "useEffect",
      "setOptimistic"
    ],
    "must_match_regex": [
      "startTransition\\s*\\(\\s*async",
      "addOptimisticLike\\s*\\("
    ],
    "min_lines": 6,
    "max_lines": 22
  }
}
```

### Anti-pattern rationale

| Forbidden | Why it's wrong |
|---|---|
| `useState` | `useOptimistic` already provides the optimistic state — adding a parallel `useState` is the most common mistake on this pattern and produces races. |
| `useEffect` | The server-action call belongs in `startTransition`, not in an effect that fires after render. |
| `fetch(` | The model should call the server action (`likePost`), not a raw fetch. |
| `setOptimistic` | Common hallucination — there is no setOptimistic returned by `useOptimistic`. The setter is the second tuple element returned (here named `addOptimisticLike`). |

### Difficulty: `hard`. Tags: `["typescript", "client-component", "react-19", "react-hook", "server-action", "event-handler"]`. file_path: `components/LikeButton.tsx`.

---

# Task 5 — `server-actions.revalidate_after_mutation.001`

**Capability.** Server action that mutates the database via Prisma, then calls `revalidatePath` on the affected routes, then redirects. Tests the canonical "post-mutation cache invalidation" pattern that nearly every production server action needs.

**Source.** [`revalidatePath` API reference](https://nextjs.org/docs/app/api-reference/functions/revalidatePath).

**Why distinct.** v0.1's 6 server-action subcategories (`create_zod`, `update_zod`, `delete`, `archive`, `formdata`, `transaction`) all reward the DB mutation but none check that cache invalidation happens correctly afterward. This is the missing tail of the pattern.

### Prompt

```typescript
// app/posts/actions.ts
'use server'
import { z } from 'zod'
import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { prisma } from '@/lib/prisma'

const PublishSchema = z.object({
  id: z.string().cuid(),
})

export async function publishPost(formData: FormData) {
  const parsed = PublishSchema.safeParse({
    id: formData.get('id'),
  })
  if (!parsed.success) {
    return { error: 'Invalid input' }
  }
```

### Ideal continuation

```typescript
  const post = await prisma.post.update({
    where: { id: parsed.data.id },
    data: { publishedAt: new Date() },
  })

  revalidatePath('/posts')
  revalidatePath(`/posts/${post.slug}`)
  redirect(`/posts/${post.slug}`)
}
```

### Checks

```json
{
  "static": {
    "must_contain": [
      "prisma.post.update",
      "revalidatePath",
      "redirect"
    ],
    "must_not_contain": [
      "router.push",
      "window.location",
      "fetch(",
      "useState",
      "useRouter"
    ],
    "must_match_regex": [
      "revalidatePath\\s*\\(",
      "prisma\\.post\\.(update|upsert)"
    ],
    "min_lines": 5,
    "max_lines": 18
  }
}
```

### Anti-pattern rationale

| Forbidden | Why it's wrong |
|---|---|
| `router.push` | `useRouter` is client-side. Server actions can't access it. |
| `window.location` | No DOM on the server. |
| `fetch(` | Server action should not call out — it owns the DB write. |
| `useState`, `useRouter` | React hooks are not available in `'use server'` files. |

### Difficulty: `mid`. Tags: `["typescript", "server-action", "prisma", "zod", "next-cache"]`. file_path: `app/posts/actions.ts`.

---

# What I want from a review

Specifically, for each task, please answer:

- **Capability uniqueness:** Is this a genuinely distinct capability from anything in v0.1, or am I template-cloning?
- **Ideal output correctness:** Is the ideal continuation what a strong Next.js / React 19 dev would actually write?
- **Check rigor:** Do the `must_contain` / `must_not_contain` / `must_match_regex` actually grade the right thing? Anything missing or over-restrictive?
- **Anti-pattern validity:** Are the forbidden patterns genuinely wrong, or just stylistic disagreements?
- **Discrimination plausibility:** Would a strong code model (Claude, GPT-4, Qwen 30B) reasonably get this right, and a weak one (DeepSeek 1.3B, Granite 3B) reasonably get it wrong?

If any task should be rejected, please be specific — which check, why it's wrong, what would fix it.

If 5 candidates is fine, I'll generate the next batch (50 more) using the same pipeline.
