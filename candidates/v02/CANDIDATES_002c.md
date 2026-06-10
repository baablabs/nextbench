# NextBench v0.2 — Candidate Batch 002c (React 19 + Edge Runtime)

**7 candidate tasks.** Two sub-clusters in one batch:
- **React 19 form / context primitives** (4 tasks) — APIs that didn't exist in v0.1's training-data era
- **Edge runtime + route handler streaming** (3 tasks) — folded under `api-routes` rather than a separate `edge` category, since the capabilities all live in route handler files

Capability registry pre-check: zero collisions with batches 001/002a/002b. Run `python scripts/check_capability_dup.py` to re-verify.

## The 7 capabilities

| # | task_id | Diff | Tests |
|---|---|---|---|
| 17 | `react.form_action.001` | trivial | `<form action={serverAction}>` progressive enhancement |
| 18 | `react.use_form_state.001` | mid | `useFormState` + server action with returned state |
| 19 | `react.action_state.001` | mid | React 19's `useActionState` with `isPending` |
| 20 | `react.use_context_typed.001` | mid | Typed `useContext` consumer hook that throws outside provider |
| 21 | `api-routes.edge_runtime.001` | trivial | `export const runtime = 'edge'` declaration |
| 22 | `api-routes.geo_response.001` | mid | Read `x-vercel-ip-country` / `cf-ipcountry` headers |
| 23 | `api-routes.streaming_response.001` | hard | `Response` with `ReadableStream` body and `controller.enqueue` |

## Three structural moves

**1. Task 18 vs Task 19 — explicit React-version split.** `useFormState` (older, `react-dom`) vs `useActionState` (React 19, `react`). A model that conflates them or uses the old name in a v19 context fails Task 19. The old/new distinction IS the capability.

**2. Task 17 forbids `onSubmit` and `preventDefault`** — those are the *anti-pattern* for `<form action>`. They defeat progressive enhancement (the form must work without JS).

**3. Task 21 is intentionally tiny** (~1 line ideal output) — the capability is "do you know this exact declaration exists" with no implementation flexibility. Strong discrimination because it's binary.

---

# Task 17 — `react.form_action.001`

**Capability.** Bind a server action directly to a `<form>` via the `action` prop — the progressive-enhancement pattern that works without JavaScript.

**Source.** [React `<form>` reference](https://react.dev/reference/react-dom/components/form).

**Why distinct.** v0.1 has 19 `form` tasks but none test `<form action={fn}>` (most use `onSubmit`). Progressive enhancement is a distinct architectural capability.

### Prompt

```typescript
// app/contact/page.tsx
import { sendMessage } from './actions'

export default function ContactPage() {
```

### Ideal continuation

```typescript
  return (
    <main className="max-w-md mx-auto p-6">
      <h1 className="text-2xl mb-4">Contact us</h1>
      <form action={sendMessage} className="space-y-4">
        <input
          name="email"
          type="email"
          required
          className="w-full border rounded p-2"
        />
        <textarea
          name="message"
          required
          className="w-full border rounded p-2"
        />
        <button type="submit" className="px-4 py-2 rounded bg-zinc-900 text-white">
          Send
        </button>
      </form>
    </main>
  )
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["<form", "action={sendMessage}", "name=", "<button"],
    "must_not_contain": ["onSubmit", "useState", "preventDefault", "fetch("],
    "must_match_regex": ["<form[^>]*action\\s*=\\s*\\{sendMessage\\}", "name\\s*=\\s*['\"]\\w+['\"]"],
    "min_lines": 8,
    "max_lines": 24
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `onSubmit` | Defeats progressive enhancement — form action with no JS is the capability. |
| `useState` | Controlled state isn't needed; FormData is collected automatically. |
| `preventDefault` | Implies trying to handle submission manually, which `<form action>` should not need. |
| `fetch(` | Should not bypass the server action with a raw fetch. |

Difficulty: `trivial`. Tags: `["typescript", "server-component", "server-action", "form", "progressive-enhancement"]`. file_path: `app/contact/page.tsx`.

---

# Task 18 — `react.use_form_state.001`

**Capability.** `useFormState` from `react-dom` — wraps a server action so the action's returned state (errors, success messages) is rendered alongside the form.

**Source.** [`useFormState` API reference](https://react.dev/reference/react-dom/hooks/useFormState).

**Why distinct from Task 17.** Task 17 is the unmanaged form-action pattern. This adds *state echo* — server action returns structured data that the UI consumes. Different capability.

### Prompt

```typescript
'use client'
import { useFormState } from 'react-dom'
import { signupAction, type SignupState } from '@/app/auth/actions'

const INITIAL_STATE: SignupState = { errors: {}, message: null }

export function SignupForm() {
  const [state, formAction] = useFormState(signupAction, INITIAL_STATE)
```

### Ideal continuation

```typescript
  return (
    <form action={formAction} className="space-y-3">
      <input
        name="email"
        type="email"
        required
        className="w-full border rounded p-2"
      />
      {state.errors.email && <p className="text-sm text-red-600">{state.errors.email}</p>}
      <input
        name="password"
        type="password"
        required
        className="w-full border rounded p-2"
      />
      {state.errors.password && <p className="text-sm text-red-600">{state.errors.password}</p>}
      <button type="submit" className="px-4 py-2 rounded bg-zinc-900 text-white">
        Sign up
      </button>
      {state.message && <p className="text-sm">{state.message}</p>}
    </form>
  )
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["action={formAction}", "state.errors", "name=", "<button"],
    "must_not_contain": ["useState", "onSubmit", "preventDefault", "fetch("],
    "must_match_regex": ["action\\s*=\\s*\\{formAction\\}", "state\\.(errors|message)"],
    "min_lines": 8,
    "max_lines": 28
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `useState` | `useFormState` IS the state — adding parallel `useState` creates races. |
| `onSubmit`, `preventDefault` | Action handling is via `formAction`, not manual. |
| `fetch(` | Should not bypass the server action. |

Difficulty: `mid`. Tags: `["typescript", "client-component", "react-hook", "server-action", "form"]`. file_path: `components/SignupForm.tsx`.

---

# Task 19 — `react.action_state.001`

**Capability.** React 19's `useActionState` (imported from `react`, not `react-dom`) — adds `isPending` to the form-state pattern, enabling disabled states and pending UI.

**Source.** [`useActionState` API reference](https://react.dev/reference/react/useActionState).

**Why distinct from Task 18.** Different API surface and different import path. `useActionState` is the React 19 evolution — adds `isPending` tuple element. A model that uses `useFormState` here fails the capability test.

### Prompt

```typescript
'use client'
import { useActionState } from 'react'
import { createPost, type CreatePostState } from '@/app/posts/actions'

const INITIAL: CreatePostState = { ok: false, error: null }

export function CreatePostForm() {
  const [state, formAction, isPending] = useActionState(createPost, INITIAL)
```

### Ideal continuation

```typescript
  return (
    <form action={formAction} className="space-y-3">
      <input
        name="title"
        required
        disabled={isPending}
        className="w-full border rounded p-2"
      />
      <textarea
        name="body"
        required
        disabled={isPending}
        className="w-full border rounded p-2"
      />
      {state.error && <p className="text-sm text-red-600">{state.error}</p>}
      {state.ok && <p className="text-sm text-green-600">Post created</p>}
      <button
        type="submit"
        disabled={isPending}
        className="px-4 py-2 rounded bg-zinc-900 text-white"
      >
        {isPending ? 'Creating…' : 'Create post'}
      </button>
    </form>
  )
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["action={formAction}", "isPending", "state.error", "disabled"],
    "must_not_contain": ["useState", "useFormState", "onSubmit", "preventDefault"],
    "must_match_regex": ["isPending", "disabled\\s*=\\s*\\{\\s*isPending"],
    "min_lines": 8,
    "max_lines": 28
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `useFormState` | This task tests React 19's `useActionState` specifically; reaching for the older `useFormState` indicates the model didn't recognize the new API. |
| `useState` | `useActionState` already provides state. |
| `onSubmit`, `preventDefault` | Manual form handling defeats the action pattern. |

Difficulty: `mid`. Tags: `["typescript", "client-component", "react-19", "react-hook", "server-action", "form"]`. file_path: `components/CreatePostForm.tsx`.

---

# Task 20 — `react.use_context_typed.001`

**Capability.** A typed React context with a custom consumer hook that throws a clear error when used outside the provider — the canonical "no nullable context" pattern.

**Source.** [`useContext` reference](https://react.dev/reference/react/useContext). Pattern from Kent C. Dodds' "How to use React Context effectively."

**Why distinct.** v0.1 has zero typed-context tasks. Tests TS narrowing knowledge alongside React hook composition.

### Prompt

```typescript
'use client'
import { createContext, useContext, type ReactNode } from 'react'

type Theme = 'light' | 'dark'
type ThemeContextValue = {
  theme: Theme
  toggle: () => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children, value }: { children: ReactNode; value: ThemeContextValue }) {
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeContextValue {
```

### Ideal continuation

```typescript
  const ctx = useContext(ThemeContext)
  if (!ctx) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return ctx
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["useContext(ThemeContext)", "throw", "ThemeProvider", "return"],
    "must_not_contain": ["useState", "useEffect", "fetch(", "as ThemeContextValue"],
    "must_match_regex": ["throw\\s+new\\s+Error"],
    "min_lines": 3,
    "max_lines": 10
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `useState`, `useEffect` | Hook body only needs to consume context and narrow types. |
| `fetch(` | No network here. |
| `as ThemeContextValue` | Type-assertion away from null is the anti-pattern — the runtime check is the capability. A model that does `return ctx as ThemeContextValue` defeats the narrowing. |

Difficulty: `mid`. Tags: `["typescript", "client-component", "react-hook"]`. file_path: `components/ThemeContext.tsx`.

---

# Task 21 — `api-routes.edge_runtime.001`

**Capability.** Declare a route handler to run on the edge runtime via `export const runtime = 'edge'`. Single-line capability test; binary discrimination.

**Source.** [Route segment config](https://nextjs.org/docs/app/api-reference/file-conventions/route-segment-config).

**Why distinct.** v0.1 has 36 route-handler tasks; none specify runtime. Edge runtime is the canonical "low-latency global endpoint" pattern.

### Prompt

```typescript
// app/api/ping/route.ts — lightweight health check; must run on edge runtime
import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({
    ok: true,
    timestamp: Date.now(),
    region: process.env.VERCEL_REGION ?? 'local',
  })
}
```

### Ideal continuation

```typescript

export const runtime = 'edge'
```

### Checks

```json
{
  "static": {
    "must_contain": ["runtime", "edge"],
    "must_not_contain": ["useState", "useEffect", "fetch(", "next.config", "runtime = 'nodejs'"],
    "must_match_regex": ["runtime\\s*=\\s*['\"`]edge['\"`]"],
    "min_lines": 1,
    "max_lines": 6
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `runtime = 'nodejs'` | Opposite of the requested capability. |
| `next.config` | Wrong file — runtime is declared per-route in App Router. |
| `useState`, `useEffect`, `fetch(` | Not relevant; should be just the export. |

Tight `max_lines: 6` enforces the discipline. A verbose answer suggests the model didn't recognize how minimal this is.

Difficulty: `trivial`. Tags: `["typescript", "route-handler", "edge-runtime"]`. file_path: `app/api/ping/route.ts`.

---

# Task 22 — `api-routes.geo_response.001`

**Capability.** Read the requester's country from Vercel's `x-vercel-ip-country` or Cloudflare's `cf-ipcountry` header — the edge-platform geolocation pattern.

**Source.** [Vercel edge headers](https://vercel.com/docs/edge-network/headers/request-headers).

**Why distinct.** No v0.1 task touches edge headers or geolocation. Tests platform-specific knowledge that real edge deployments need.

### Prompt

```typescript
// app/api/geo/route.ts — return the requester's country from edge headers
import { type NextRequest, NextResponse } from 'next/server'

export const runtime = 'edge'

export async function GET(request: NextRequest) {
```

### Ideal continuation

```typescript
  const country =
    request.headers.get('x-vercel-ip-country') ??
    request.headers.get('cf-ipcountry') ??
    'unknown'
  return NextResponse.json({ country })
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["headers.get", "country", "NextResponse.json"],
    "must_not_contain": ["useState", "fetch(", "ip-api.com", "ipinfo.io"],
    "must_match_regex": ["headers\\.get\\(['\"`]\\s*(x-vercel-ip-country|cf-ipcountry)"],
    "min_lines": 3,
    "max_lines": 10
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `ip-api.com`, `ipinfo.io` | The capability is *reading edge headers*, not calling an external IP-lookup API. The platform provides this for free; using an external service is the wrong solution. |
| `useState`, `fetch(` | Not relevant — synchronous header read. |

Difficulty: `mid`. Tags: `["typescript", "route-handler", "edge-runtime"]`. file_path: `app/api/geo/route.ts`.

---

# Task 23 — `api-routes.streaming_response.001`

**Capability.** Return a `Response` with a `ReadableStream` body — chunked output via `controller.enqueue` + `controller.close`. The foundation for SSE, AI response streaming, and any long-running response.

**Source.** [`ReadableStream` MDN](https://developer.mozilla.org/en-US/docs/Web/API/ReadableStream).

**Why distinct.** No v0.1 task touches `ReadableStream` or chunked responses. Tests Web Streams API knowledge that AI integrations and SSE require.

### Prompt

```typescript
// app/api/tick/route.ts — stream a tick every second for 5 ticks
export async function GET() {
  const encoder = new TextEncoder()

  const stream = new ReadableStream({
```

### Ideal continuation

```typescript
    async start(controller) {
      for (let i = 1; i <= 5; i++) {
        controller.enqueue(encoder.encode(`tick ${i}\n`))
        await new Promise((resolve) => setTimeout(resolve, 1000))
      }
      controller.close()
    },
  })

  return new Response(stream, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  })
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["controller.enqueue", "encoder.encode", "controller.close", "new Response"],
    "must_not_contain": ["useState", "useEffect", "fetch("],
    "must_match_regex": ["controller\\.(enqueue|close)", "new Response\\s*\\("],
    "min_lines": 6,
    "max_lines": 26
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `useState`, `useEffect` | Wrong context (server-side, not React). |
| `fetch(` | The capability is *producing* a stream, not consuming one. |

Difficulty: `hard`. Tags: `["typescript", "route-handler", "streaming"]`. file_path: `app/api/tick/route.ts`.

---

## After this batch

If 6–7 promote with minor fixes, batch 002d (server-actions + api-routes, ~7 tasks) goes next.

Running total after 002c approval: **28 capabilities** of the 49 in the registry. Batches 002d, 002e, 002f remaining (21 capabilities to go).
