# NextBench v0.2 — Candidate Batch 002e (Database + Auth + Realtime)

**12 candidate tasks** — first batch at the new 10-12 size. Three sub-clusters:
- **Database / Prisma** (6 tasks) — `$transaction`, nested write, cursor pagination, `groupBy`, `upsert`, connection-pool singleton
- **Authorization** (2 tasks) — resource ownership check, session-gated server component
- **Realtime / Streaming** (4 tasks) — SSE producer, WebSocket hook, optimistic chat list, EventSource consumer

Capability registry pre-check: zero collisions across batches 001/002a/002b/002c/002d. Four net-new capabilities (`prisma_upsert`, `connection_pool_singleton`, `session_check_redirect`, `use_event_source`) were added to the registry as part of the batch-size expansion — all `in_review`.

## The 12 capabilities

| # | task_id | Diff | Tests |
|---|---|---|---|
| 31 | `database.prisma_transaction.001` | hard | `$transaction([...])` atomic multi-write |
| 32 | `database.prisma_nested_create.001` | mid | Nested `create:` inside `tags:` block |
| 33 | `database.prisma_cursor_pagination.001` | mid | `cursor` + `take` + `skip: 1` (NOT OFFSET) |
| 34 | `database.prisma_count_groupby.001` | mid | `groupBy` + `_count` aggregation |
| 35 | `database.prisma_upsert.001` | mid | Atomic `upsert` with create + update blocks |
| 36 | `database.connection_pool_singleton.001` | mid | `globalThis` Prisma singleton for Next.js dev |
| 37 | `auth.resource_owner.001` | hard | OWASP BOLA — `authorId !== user.id` before mutation |
| 38 | `auth.session_check_redirect.001` | mid | Server-component `if (!user) redirect('/login')` |
| 39 | `nextjs.sse_response.001` | hard | `ReadableStream` + `text/event-stream` + `data:` lines |
| 40 | `react.use_websocket_hook.001` | hard | `new WebSocket` + useEffect cleanup |
| 41 | `react.optimistic_chat.001` | hard | `useOptimistic` over a list with `pending` markers |
| 42 | `react.use_event_source.001` | mid | `new EventSource` + cleanup |

## Four structural moves

**1. Tasks 33 forbids SQL keywords (`LIMIT`/`OFFSET`).** The Prisma capability is the framework-native pagination shape (`cursor` + `take` + `skip: 1`). A model that drops to raw SQL or computes offsets manually fails the capability, even if the query "works."

**2. Task 36 enforces the `??` pattern as a regex.** The canonical Next.js + Prisma dev singleton pattern is `globalForPrisma.prisma ?? new PrismaClient()`. A model that writes `if (!globalForPrisma.prisma) { ... }` is doing the same thing but isn't following the standard recipe — and the regex forces the recipe. This is intentional: this task is testing pattern recognition more than first-principles reasoning.

**3. Task 37 is graded primarily on the regex `authorId !== user.id`.** The capability is "do you check ownership before mutating?" — not "do you write the prettiest error response." Following the 002d Task 29 pattern, the structural ownership comparison is the primary capability marker; `findUnique` is supporting context. A model that calls `prisma.post.delete(...)` without first reading the post and comparing IDs will fail the regex.

**4. Tasks 39 and 42 are paired** — one produces SSE (`text/event-stream` Content-Type, `data: ${...}\n\n` payload), one consumes it (`new EventSource` + `onmessage` + cleanup). Together they validate that the model understands both halves of the SSE story, not just the buzzword.

---

# Task 31 — `database.prisma_transaction.001`

**Capability.** Two writes in a single `$transaction([...])` so either both apply or both roll back. The classic balance-transfer pattern.

**Source.** [Prisma `$transaction`](https://www.prisma.io/docs/orm/prisma-client/queries/transactions).

**Why distinct.** v0.1 has Prisma update tasks but no `$transaction` — and the common wrong answer (`Promise.all`) looks correct but lacks rollback semantics.

### Prompt

```typescript
'use server'
import { prisma } from '@/lib/db'
import { revalidatePath } from 'next/cache'

export async function transferFunds(
  fromAccountId: string,
  toAccountId: string,
  amount: number,
) {
```

### Ideal continuation

```typescript
  await prisma.$transaction([
    prisma.account.update({
      where: { id: fromAccountId },
      data: { balance: { decrement: amount } },
    }),
    prisma.account.update({
      where: { id: toAccountId },
      data: { balance: { increment: amount } },
    }),
  ])
  revalidatePath('/accounts')
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["$transaction", "decrement", "increment", "revalidatePath"],
    "must_not_contain": ["Promise.all"],
    "must_match_regex": ["\\$transaction\\s*\\("],
    "min_lines": 4,
    "max_lines": 18
  }
}
```

**Anti-pattern.** `Promise.all` runs both updates in parallel but without rollback — looks right, isn't. Hard discriminator.

Difficulty: `hard`. file_path: `app/actions/transfer.ts`.

---

# Task 32 — `database.prisma_nested_create.001`

**Capability.** Create a parent record and related child records in a single Prisma query via nested writes (`tags: { create: [...] }`).

**Source.** [Prisma nested writes](https://www.prisma.io/docs/orm/prisma-client/queries/relation-queries).

**Why distinct.** No v0.1 task tests the relational nested-write capability. The wrong answer is `prisma.post.create(...)` followed by a loop calling `prisma.tag.create(...)` — works but issues N+1 queries.

### Prompt

```typescript
'use server'
import { prisma } from '@/lib/db'

type Tag = { name: string }

export async function createPostWithTags(input: {
  title: string
  content: string
  authorId: string
  tags: Tag[]
}) {
```

### Ideal continuation

```typescript
  return prisma.post.create({
    data: {
      title: input.title,
      content: input.content,
      author: { connect: { id: input.authorId } },
      tags: {
        create: input.tags.map((t) => ({ name: t.name })),
      },
    },
  })
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["prisma.post.create", "tags:", "create:", "connect:"],
    "must_not_contain": ["Promise.all", "for (const", "tags.forEach"],
    "must_match_regex": ["tags\\s*:\\s*\\{\\s*create"],
    "min_lines": 5,
    "max_lines": 20
  }
}
```

**Anti-pattern.** Loops or `Promise.all` over `tags` indicate the model didn't reach for the nested-write primitive.

Difficulty: `mid`. file_path: `app/actions/create-post.ts`.

---

# Task 33 — `database.prisma_cursor_pagination.001`

**Capability.** Cursor-based pagination using `cursor: { id }`, `take`, `skip: 1` (skipping the cursor row itself).

**Source.** [Prisma pagination](https://www.prisma.io/docs/orm/prisma-client/queries/pagination).

**Why distinct.** v0.1 has no pagination tests at all. Cursor pagination is the production-correct pattern (stable under inserts); offset pagination is the common wrong answer.

### Prompt

```typescript
import { NextResponse } from 'next/server'
import { prisma } from '@/lib/db'

export async function GET(request: Request) {
  const url = new URL(request.url)
  const cursor = url.searchParams.get('cursor')
  const take = Number(url.searchParams.get('take') ?? '20')
```

### Ideal continuation

```typescript
  const posts = await prisma.post.findMany({
    take,
    ...(cursor ? { skip: 1, cursor: { id: cursor } } : {}),
    orderBy: { createdAt: 'desc' },
  })
  const nextCursor = posts.length === take ? posts[posts.length - 1].id : null
  return NextResponse.json({ posts, nextCursor })
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["cursor", "take", "findMany"],
    "must_not_contain": ["LIMIT", "OFFSET", "Math.ceil"],
    "must_match_regex": ["cursor\\s*:\\s*\\{\\s*id"],
    "min_lines": 4,
    "max_lines": 18
  }
}
```

### Grading philosophy

`cursor` and `take` are the **primary capability markers** — they're the Prisma-native pagination shape and a model that uses both is demonstrating cursor pagination. The `skip: 1` step (excluding the cursor row from results) is real but implementation-dependent; some valid implementations handle cursor exclusion at the query layer or by trimming results. Forcing it via a regex would penalize correct-but-different code, so it's omitted. The forbidden tokens (`LIMIT`/`OFFSET`/`Math.ceil`) still catch the actual wrong answer (offset pagination).

**Anti-pattern.** `LIMIT`/`OFFSET` = raw SQL bypass. `Math.ceil` = computing offset from page numbers = the wrong pagination model entirely.

Difficulty: `mid`. file_path: `app/api/posts/route.ts`.

---

# Task 34 — `database.prisma_count_groupby.001`

**Capability.** Aggregate via Prisma's `groupBy` with `_count` and ordering by the aggregate.

**Source.** [Prisma aggregation](https://www.prisma.io/docs/orm/prisma-client/queries/aggregation-grouping-summarizing).

**Why distinct.** v0.1 has no aggregation tasks. `groupBy` is one of the most idiomatic Prisma features; many models default to raw SQL or manual counting.

### Prompt

```typescript
import { prisma } from '@/lib/db'

export async function getPostCountByAuthor() {
```

### Ideal continuation

```typescript
  return prisma.post.groupBy({
    by: ['authorId'],
    _count: {
      _all: true,
    },
    orderBy: {
      _count: {
        authorId: 'desc',
      },
    },
  })
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["groupBy", "by:", "_count", "authorId"],
    "must_not_contain": ["GROUP BY", "raw(", "SELECT COUNT"],
    "must_match_regex": ["groupBy\\s*\\(\\s*\\{", "_count\\s*:"],
    "min_lines": 4,
    "max_lines": 18
  }
}
```

**Anti-pattern.** Raw SQL fallback signals the model didn't know Prisma's aggregation API.

Difficulty: `mid`. file_path: `lib/analytics.ts`.

---

# Task 35 — `database.prisma_upsert.001`

**Capability.** Atomic `upsert` using `where` / `create` / `update` blocks. No findUnique + conditional logic (which is racy).

**Source.** [Prisma `upsert`](https://www.prisma.io/docs/orm/prisma-client/queries/crud#upsert-an-existing-record).

**Why distinct.** v0.1 has no upsert tests. The common wrong answer is `findUnique` → if-else → `create`/`update` — works under low concurrency, races under contention.

### Prompt

```typescript
'use server'
import { prisma } from '@/lib/db'

export async function savePreference(
  userId: string,
  key: string,
  value: string,
) {
```

### Ideal continuation

```typescript
  return prisma.preference.upsert({
    where: {
      userId_key: { userId, key },
    },
    create: {
      userId,
      key,
      value,
    },
    update: {
      value,
    },
  })
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["upsert", "where:", "create:", "update:"],
    "must_not_contain": ["findUnique", "findFirst", "if (existing)"],
    "must_match_regex": ["\\.upsert\\s*\\(\\s*\\{"],
    "min_lines": 5,
    "max_lines": 20
  }
}
```

**Anti-pattern.** `findUnique` + branching is exactly the race-prone version this capability replaces.

Difficulty: `mid`. file_path: `app/actions/save-preference.ts`.

---

# Task 36 — `database.connection_pool_singleton.001`

**Capability.** The canonical Next.js + Prisma `globalThis` singleton — avoids dev hot-reload connection exhaustion.

**Source.** [Prisma Next.js best practices](https://www.prisma.io/docs/orm/more/help-and-troubleshooting/help-articles/nextjs-prisma-client-dev-practices).

**Why distinct.** v0.1 has no infrastructure tasks. This is a production bug a model will reliably reproduce if it instantiates `new PrismaClient()` at module top-level.

### Prompt

```typescript
import { PrismaClient } from '@prisma/client'

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined
}
```

### Ideal continuation

```typescript

export const prisma =
  globalForPrisma.prisma ?? new PrismaClient()

if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.prisma = prisma
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["globalForPrisma.prisma", "new PrismaClient()", "NODE_ENV", "production"],
    "must_not_contain": ["export default new PrismaClient", "let prisma = new"],
    "must_match_regex": ["globalForPrisma\\.prisma\\s*\\?\\?\\s*new\\s+PrismaClient"],
    "min_lines": 3,
    "max_lines": 12
  }
}
```

### Classification

`task_class: "pattern_knowledge"` — this task tests whether the model can reproduce the canonical Next.js + Prisma singleton recipe, not whether it can reason about connection pooling from first principles. A functionally-correct if/else variant that doesn't use the `??` shape will fail by design. Flagging the class explicitly avoids confusion when comparing scores against true capability-reasoning tasks like `prisma_transaction` (Task 31) or `resource_owner` (Task 37).

This is the first task in the corpus to carry the `pattern_knowledge` class. The broader taxonomy rollout (Type A: Framework APIs / Type B: Architecture / Type C: Infrastructure Patterns) is deferred to the v0.2 release pass alongside the `framework_version` metadata sweep.

**Anti-pattern.** `export default new PrismaClient()` is the canonical bug — a fresh connection on every hot reload.

Difficulty: `mid`. file_path: `lib/db.ts`.

---

# Task 37 — `auth.resource_owner.001`

**Capability.** Before mutating a resource, fetch it, compare its owner field to the current user ID, and only proceed if they match. The fix for OWASP Broken Object-Level Authorization.

**Source.** [OWASP BOLA](https://owasp.org/www-community/Broken_Object_Level_Authorization).

**Why distinct.** v0.1 has no authorization tasks (only authentication ones). The killer detail is the explicit `authorId !== user.id` comparison; models that skip it produce confidently-wrong code.

### Prompt

```typescript
'use server'
import { prisma } from '@/lib/db'
import { getCurrentUser } from '@/lib/auth'
import { revalidatePath } from 'next/cache'

export async function deletePost(postId: string) {
  const user = await getCurrentUser()
  if (!user) return { error: 'Not authenticated' }
```

### Ideal continuation

```typescript
  const post = await prisma.post.findUnique({
    where: { id: postId },
    select: { authorId: true },
  })
  if (!post) return { error: 'Post not found' }
  if (post.authorId !== user.id) {
    return { error: 'Forbidden' }
  }
  await prisma.post.delete({ where: { id: postId } })
  revalidatePath('/posts')
  return { success: true }
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["findUnique", "authorId", "user.id"],
    "must_not_contain": ["// TODO", "FIXME"],
    "must_match_regex": ["authorId\\s*(!==|===)\\s*user\\.id", "findUnique"],
    "min_lines": 6,
    "max_lines": 24
  }
}
```

### Grading philosophy

`authorId !== user.id` is the **primary capability marker** — same approach as 002d Task 29 (`timingSafeEqual`). A model that writes the ownership comparison correctly is demonstrating real authorization understanding. `findUnique` is supporting context (it has to fetch the resource to compare). A model that calls `prisma.post.delete(...)` without the ownership check will fail the regex even if the rest of the code looks plausible.

Difficulty: `hard`. file_path: `app/actions/delete-post.ts`.

---

# Task 38 — `auth.session_check_redirect.001`

**Capability.** Server component reads the current user; if absent, calls `redirect('/login')`. The canonical Next.js App Router auth gate.

**Source.** [Next.js authentication](https://nextjs.org/docs/app/building-your-application/authentication).

**Why distinct.** v0.1 has no server-component auth gate. The wrong answer is reaching for `useRouter` / `router.push` (client-side); doing it in a server component is what Next.js wants.

### Prompt

```typescript
import { redirect } from 'next/navigation'
import { getCurrentUser } from '@/lib/auth'

export default async function DashboardPage() {
```

### Ideal continuation

```typescript
  const user = await getCurrentUser()
  if (!user) {
    redirect('/login')
  }
  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Welcome, {user.name}</h1>
    </main>
  )
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["getCurrentUser", "redirect", "/login"],
    "must_not_contain": ["useRouter", "router.push", "'use client'"],
    "must_match_regex": ["redirect\\s*\\(\\s*['\"]/login['\"]", "if\\s*\\(\\s*!\\s*user"],
    "min_lines": 4,
    "max_lines": 18
  }
}
```

**Anti-pattern.** Client-side redirect signals the model put this in a client component, which renders the protected content (briefly) before redirecting — the exact bug this pattern solves.

Difficulty: `mid`. file_path: `app/dashboard/page.tsx`.

---

# Task 39 — `nextjs.sse_response.001`

**Capability.** Build a Server-Sent Events response in an edge route handler: `ReadableStream` + `text/event-stream` Content-Type + `data: ...\n\n` payload format.

**Source.** [MDN Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events).

**Why distinct from 002c `api-routes.streaming_response`.** 002c tests generic streaming. This tests **SSE format compliance**: the `text/event-stream` Content-Type and the `data: ...\n\n` framing. A model that streams plain text fails both required signals.

### Prompt

```typescript
export const runtime = 'edge'

export async function GET() {
```

### Ideal continuation

```typescript
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    async start(controller) {
      for (let i = 0; i < 5; i++) {
        const data = `data: ${JSON.stringify({ tick: i })}\n\n`
        controller.enqueue(encoder.encode(data))
        await new Promise((r) => setTimeout(r, 1000))
      }
      controller.close()
    },
  })
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    },
  })
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["ReadableStream", "controller.enqueue", "text/event-stream", "data:"],
    "must_not_contain": ["NextResponse.json"],
    "must_match_regex": ["['\"]text/event-stream['\"]", "ReadableStream\\s*\\(\\s*\\{"],
    "min_lines": 8,
    "max_lines": 32
  }
}
```

**Anti-pattern.** `NextResponse.json` returns a buffered JSON object — directly incompatible with streaming.

Difficulty: `hard`. file_path: `app/api/events/route.ts`.

---

# Task 40 — `react.use_websocket_hook.001`

**Capability.** Custom hook opens a WebSocket, listens for messages, and **cleans up on unmount** via the useEffect return function.

**Source.** [MDN WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket).

**Why distinct.** v0.1 has no realtime client hooks. The killer detail is the cleanup function — leaking WebSockets on unmount is a real production pattern bug. The regex `return () => { ... .close(...) }` explicitly enforces it.

### Prompt

```typescript
'use client'
import { useEffect, useRef, useState } from 'react'

export function useWebSocket(url: string) {
```

### Ideal continuation

```typescript
  const [messages, setMessages] = useState<string[]>([])
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const ws = new WebSocket(url)
    wsRef.current = ws
    ws.onmessage = (event) => {
      setMessages((prev) => [...prev, event.data])
    }
    return () => {
      ws.close()
    }
  }, [url])

  return { messages, send: (msg: string) => wsRef.current?.send(msg) }
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["new WebSocket", "useEffect", "onmessage", "ws.close()", "useRef"],
    "must_not_contain": ["EventSource", "fetch(", "setInterval"],
    "must_match_regex": ["return\\s*\\(\\s*\\)\\s*=>\\s*\\{[^}]*\\.close\\s*\\("],
    "min_lines": 8,
    "max_lines": 28
  }
}
```

### Grading philosophy

The `useEffect` cleanup regex (`return () => { ... .close(...) }`) is the **primary capability marker**. A model that opens a WebSocket but forgets to close it has not solved this task. The required `useRef` signals state-holding without re-render thrash. WebSocket + onmessage are the obvious tokens; cleanup is what separates passing from failing.

Difficulty: `hard`. file_path: `hooks/use-websocket.ts`.

---

# Task 41 — `react.optimistic_chat.001`

**Capability.** Use `useOptimistic` over a **list** (not a scalar) so newly-sent chat messages appear instantly with a `pending: true` marker that flips to false on confirmation.

**Source.** [`useOptimistic`](https://react.dev/reference/react/useOptimistic).

**Why distinct from v0.1 `react.optimistic_ui`.** v0.1's task tests `useOptimistic` over a scalar (a counter or a single record). This tests **list-append semantics** plus the `pending` field that drives styling — a different state-shape pattern.

### Prompt

```typescript
'use client'
import { useOptimistic } from 'react'
import { sendMessage } from './actions'

type Message = { id: string; text: string; pending?: boolean }

export function ChatList({ messages }: { messages: Message[] }) {
```

### Ideal continuation

```typescript
  const [optimisticMessages, addOptimisticMessage] = useOptimistic(
    messages,
    (state, newText: string) => [
      ...state,
      { id: crypto.randomUUID(), text: newText, pending: true },
    ],
  )

  async function handleSubmit(formData: FormData) {
    const text = formData.get('text') as string
    addOptimisticMessage(text)
    await sendMessage(text)
  }

  return (
    <form action={handleSubmit}>
      <ul>
        {optimisticMessages.map((m) => (
          <li key={m.id} className={m.pending ? 'opacity-50' : ''}>
            {m.text}
          </li>
        ))}
      </ul>
      <input name="text" />
      <button type="submit">Send</button>
    </form>
  )
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["useOptimistic", "pending"],
    "must_not_contain": ["useState", "onSubmit"],
    "must_match_regex": ["useOptimistic\\s*\\(", "<form[^>]*action\\s*=\\s*\\{"],
    "min_lines": 10,
    "max_lines": 40
  }
}
```

**Anti-pattern.** `useState` over the messages list means the model is bypassing `useOptimistic` entirely. `onSubmit` instead of `action={...}` skips the form-action progressive-enhancement contract.

Difficulty: `hard`. file_path: `app/chat/ChatList.tsx`.

---

# Task 42 — `react.use_event_source.001`

**Capability.** Client-side SSE consumer hook — `new EventSource(url)` inside `useEffect`, `onmessage` accumulates parsed data, cleanup closes the connection on unmount.

**Source.** [MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource).

**Why distinct from Task 40.** Different API (EventSource is SSE-only, server-initiated; WebSocket is bidirectional). Pairs with Task 39 (which produces SSE).

### Prompt

```typescript
'use client'
import { useEffect, useState } from 'react'

export function useEventSource<T>(url: string) {
```

### Ideal continuation

```typescript
  const [data, setData] = useState<T[]>([])

  useEffect(() => {
    const source = new EventSource(url)
    source.onmessage = (event) => {
      setData((prev) => [...prev, JSON.parse(event.data)])
    }
    return () => {
      source.close()
    }
  }, [url])

  return data
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["EventSource", "useEffect", "onmessage"],
    "must_not_contain": ["WebSocket", "fetch(", "setInterval"],
    "must_match_regex": ["new\\s+EventSource\\s*\\(", "return\\s*\\(\\s*\\)\\s*=>\\s*\\{[^}]*\\.close"],
    "min_lines": 6,
    "max_lines": 20
  }
}
```

**Anti-pattern.** `WebSocket` = wrong primitive. `fetch(`/`setInterval` = the polling antipattern this hook is meant to replace.

Difficulty: `mid`. file_path: `hooks/use-event-source.ts`.

---

## Notes for review

- All 12 pre-checked against `capabilities.jsonl` — zero collisions.
- The four net-new capabilities (`prisma_upsert`, `connection_pool_singleton`, `session_check_redirect`, `use_event_source`) were added when expanding 002e from 8 → 12 per the new batch-size target. Each fits cleanly into its existing cluster (database, auth, realtime).
- Grading-philosophy notes appear on Tasks 37 and 40, following the 002d Task 29 precedent: name the **primary capability marker** explicitly so reviewers can assess whether the right signal is what carries the most grading weight.
- Tasks 39 ↔ 42 form a produces/consumes pair — together they validate both halves of SSE comprehension.
- `framework_version` metadata sweep is still deferred to the v0.2 release pass.
- Difficulty distribution: 5 hard (31, 37, 39, 40, 41) · 7 mid (32, 33, 34, 35, 36, 38, 42). The hardest cluster is realtime + transactions + authorization, which is where v0.2 most differentiates from v0.1.
