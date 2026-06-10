# NextBench v0.2 — Candidate Batch 002d (Server Actions + API Routes)

**7 candidate tasks.** Two sub-clusters in one batch:
- **Server actions** (4 tasks) — zod-driven validation, useFormStatus pending UI, cookies, headers
- **API route handlers** (3 tasks) — multipart parsing + two HMAC-driven security capabilities

Capability registry pre-check: zero collisions with batches 001/002a/002b/002c. Run `python scripts/check_capability_dup.py` to re-verify.

## The 7 capabilities

| # | task_id | Diff | Tests |
|---|---|---|---|
| 24 | `server-actions.zod_field_errors.001` | mid | `safeParse` → `flatten().fieldErrors` returned as form state |
| 25 | `server-actions.use_form_status_pending.001` | mid | `useFormStatus()` in a child component reads parent form pending |
| 26 | `server-actions.cookies_set.001` | mid | `cookies().set(...)` with HttpOnly + sameSite + secure |
| 27 | `server-actions.headers_check.001` | mid | `headers().get('x-forwarded-for')` for IP capture |
| 28 | `api-routes.form_data_parse.001` | mid | `request.formData()` + `formData.get('field')` |
| 29 | `api-routes.signed_url_redirect.001` | hard | HMAC verify + `timingSafeEqual` + 302 redirect on success |
| 30 | `api-routes.webhook_signature_verify.001` | hard | HMAC verify of inbound webhook against raw body |

## Three structural moves

**1. Tasks 24/25 split the React 19 form ecosystem cleanly.** v0.2 now covers all four hooks in their canonical positions:
- 002c Task 17: `<form action={fn}>` — unmanaged
- 002c Task 18: `useFormState` (react-dom, older) — parent-level state echo
- 002c Task 19: `useActionState` (react, React 19) — combined hook with `isPending`
- 002d Task 25: `useFormStatus` — *child* component pending consumer

The four are distinct APIs that conflate easily in training data. Together they discriminate models that genuinely know the React 19 form story vs. those guessing from name similarity.

**2. Tasks 29 vs 30 share a primitive (HMAC + timing-safe) but test different flows.**
- 29: signed query-string URL, expiry check, **redirect** on success
- 30: signed header, raw body verify, **process event** on success

Required tokens are disjoint (`NextResponse.redirect` + `exp` for 29; `request.text()` + `x-webhook-signature` for 30), so a model that ports the verification primitive but misses the surrounding flow fails one or both.

**3. Tasks 29/30 forbid bare `===` signature compare.** Direct string equality is the classic timing-attack anti-pattern; `timingSafeEqual` is the capability under test. `must_contain: ["timingSafeEqual"]` + `must_not_contain: ["sig === expected", "signature === expected"]` lock both signals.

---

# Task 24 — `server-actions.zod_field_errors.001`

**Capability.** Validate FormData with `Schema.safeParse(...)`, return Zod's `flatten().fieldErrors` shape as the action's state so the UI can render per-field errors.

**Source.** [Zod `safeParse`](https://zod.dev/?id=safeparse).

**Why distinct.** v0.1 has no task that tests `safeParse` returning structured field errors. v0.1's zod tasks (~6 of them) all use `parse()` + try/catch or skip validation entirely. The return-shape contract is the capability.

### Prompt

```typescript
'use server'
import { z } from 'zod'
import { redirect } from 'next/navigation'

const SignupSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
})

export type SignupState = {
  errors: { email?: string[]; password?: string[] }
  message: string | null
}

export async function signupAction(
  _prev: SignupState,
  formData: FormData,
): Promise<SignupState> {
```

### Ideal continuation

```typescript
  const parsed = SignupSchema.safeParse({
    email: formData.get('email'),
    password: formData.get('password'),
  })

  if (!parsed.success) {
    return {
      errors: parsed.error.flatten().fieldErrors,
      message: 'Please fix the errors below.',
    }
  }

  // create user...
  redirect('/dashboard')
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["safeParse", "flatten", "fieldErrors", "errors:"],
    "must_not_contain": ["SignupSchema.parse(", "ZodError"],
    "must_match_regex": ["safeParse\\s*\\(", "fieldErrors"],
    "min_lines": 6,
    "max_lines": 22
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `SignupSchema.parse(` | Throws on invalid; can't return structured errors as state. |
| `ZodError` | Implies catching a thrown error — `safeParse` returns a discriminated result, no catch needed. |

Difficulty: `mid`. Tags: `["typescript","server-action","zod","form","validation"]`. file_path: `app/auth/signup/actions.ts`.

---

# Task 25 — `server-actions.use_form_status_pending.001`

**Capability.** Use `useFormStatus()` inside a child component to read the parent form's pending state and disable the submit button while the server action runs.

**Source.** [`useFormStatus`](https://react.dev/reference/react-dom/hooks/useFormStatus).

**Why distinct from Tasks 18 / 19.** `useFormState` / `useActionState` are *parent* hooks called next to the form. `useFormStatus` is the only hook that reads form state from a *child* component via React context — and it must be a separate component for the hook to work. Different API, different file structure, different capability.

### Prompt

```typescript
'use client'
import { useFormStatus } from 'react-dom'

export function SubmitButton({ children }: { children: React.ReactNode }) {
```

### Ideal continuation

```typescript
  const { pending } = useFormStatus()
  return (
    <button
      type="submit"
      disabled={pending}
      className="px-4 py-2 rounded bg-zinc-900 text-white disabled:opacity-50"
    >
      {pending ? 'Submitting...' : children}
    </button>
  )
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["useFormStatus", "pending", "disabled"],
    "must_not_contain": ["useState", "useFormState", "useActionState"],
    "must_match_regex": ["useFormStatus\\s*\\(\\s*\\)", "type\\s*=\\s*['\"]submit['\"]"],
    "min_lines": 4,
    "max_lines": 16
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `useState` | The pending state comes from the parent form, not local state. |
| `useFormState` / `useActionState` | Those are parent hooks; pulling them into the child means the model confused the three. |

Difficulty: `mid`. Tags: `["typescript","client-component","react-hook","server-action","form"]`. file_path: `components/submit-button.tsx`.

---

# Task 26 — `server-actions.cookies_set.001`

**Capability.** After successful auth, set an HttpOnly session cookie with secure flags via `cookies().set(...)` from `next/headers`, then redirect.

**Source.** [`cookies()` reference](https://nextjs.org/docs/app/api-reference/functions/cookies).

**Why distinct.** v0.1 has no task that tests the **async** `cookies()` API (Next.js 15 change) with the full security attribute set. Forgetting `httpOnly` or `sameSite` is the most common real-world failure mode, so the capability bundles them.

### Prompt

```typescript
'use server'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { verifyCredentials, createSession } from '@/lib/auth'

export async function loginAction(formData: FormData) {
  const email = formData.get('email') as string
  const password = formData.get('password') as string
  const user = await verifyCredentials(email, password)
  if (!user) return { error: 'Invalid credentials' }
```

### Ideal continuation

```typescript
  const session = await createSession(user.id)
  const cookieStore = await cookies()
  cookieStore.set('session', session.token, {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/',
    maxAge: 60 * 60 * 24 * 7,
  })
  redirect('/dashboard')
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["cookies()", ".set(", "httpOnly", "secure", "sameSite", "redirect"],
    "must_not_contain": ["document.cookie", "localStorage", "Set-Cookie"],
    "must_match_regex": ["cookies\\s*\\(\\s*\\)", "httpOnly\\s*:\\s*true"],
    "min_lines": 5,
    "max_lines": 20
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `document.cookie` | Client-side cookie write, not available in a server action; also can't set HttpOnly. |
| `localStorage` | Session tokens in localStorage are an XSS hazard; not the canonical Next.js pattern. |
| `Set-Cookie` | Raw header manipulation; the framework primitive is `cookies().set(...)`. |

Difficulty: `mid`. Tags: `["typescript","server-action","cookies","auth","security"]`. file_path: `app/auth/login/actions.ts`.

---

# Task 27 — `server-actions.headers_check.001`

**Capability.** Read request headers inside a server action via `headers()` from `next/headers` (the Next.js 15 async form) to capture client IP and user agent.

**Source.** [`headers()` reference](https://nextjs.org/docs/app/api-reference/functions/headers).

**Why distinct.** v0.1's middleware tasks use `request.headers` (middleware has a request object); server actions don't get one — they have to call `headers()` from `next/headers`. Models that conflate the two patterns fail this task.

### Prompt

```typescript
'use server'
import { headers } from 'next/headers'
import { saveFeedback } from '@/lib/db'

export async function submitFeedback(formData: FormData) {
  const message = formData.get('message') as string
  if (!message?.trim()) return { error: 'Message required' }
```

### Ideal continuation

```typescript
  const headerStore = await headers()
  const ip = headerStore.get('x-forwarded-for') ?? 'unknown'
  const userAgent = headerStore.get('user-agent') ?? 'unknown'
  await saveFeedback({ message, ip, userAgent })
  return { success: true }
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["headers()", ".get(", "x-forwarded-for"],
    "must_not_contain": ["request.headers", "req.headers"],
    "must_match_regex": ["headers\\s*\\(\\s*\\)", "['\"]x-forwarded-for['\"]"],
    "min_lines": 4,
    "max_lines": 14
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `request.headers` | No request object exists inside a server action's signature. |
| `req.headers` | Same — the model is reaching for an Express-style API that doesn't apply. |

Difficulty: `mid`. Tags: `["typescript","server-action","headers"]`. file_path: `app/feedback/actions.ts`.

---

# Task 28 — `api-routes.form_data_parse.001`

**Capability.** Parse a `multipart/form-data` request body in a route handler via `await request.formData()` and read string fields with `formData.get(...)`.

**Source.** [`Request.formData()`](https://developer.mozilla.org/en-US/docs/Web/API/Request/formData).

**Why distinct.** v0.1 form tasks all live in client components or server actions. None test the Fetch-API `Request.formData()` path that route handlers receive. The capability is "know which API to call on a Request object."

### Prompt

```typescript
import { NextResponse } from 'next/server'

export async function POST(request: Request) {
```

### Ideal continuation

```typescript
  const formData = await request.formData()
  const name = formData.get('name')
  const email = formData.get('email')
  const message = formData.get('message')

  if (typeof name !== 'string' || typeof email !== 'string' || typeof message !== 'string') {
    return NextResponse.json({ error: 'Invalid form data' }, { status: 400 })
  }

  // forward to inbox...

  return NextResponse.json({ ok: true })
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["request.formData()", ".get(", "NextResponse"],
    "must_not_contain": ["request.json(", "request.text(", "JSON.parse"],
    "must_match_regex": ["request\\.formData\\s*\\(\\s*\\)", "formData\\.get\\s*\\("],
    "min_lines": 5,
    "max_lines": 22
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `request.json(` | Wrong body parser — JSON ≠ multipart form data. |
| `request.text(` | Returns raw string; loses field structure. |
| `JSON.parse` | Same path — the model is trying to handle this as a JSON payload. |

Difficulty: `mid`. Tags: `["typescript","route-handler","form","multipart"]`. file_path: `app/api/contact/route.ts`.

---

# Task 29 — `api-routes.signed_url_redirect.001`

**Capability.** Verify an HMAC-signed download URL: check expiry, compute expected signature, constant-time compare, redirect on success.

**Source.** [Signed-URL pattern (AWS S3 presigned URLs)](https://aws.amazon.com/blogs/aws/amazon-s3-presigned-urls/) — referenced conceptually; implementation is pure Node `crypto`.

**Why distinct.** v0.1 has zero crypto / HMAC tasks. This is a baseline security capability that real Next.js apps need (download tokens, share links, magic links). Three sub-capabilities (HMAC compute, timing-safe compare, redirect) must compose correctly.

### Prompt

```typescript
import { NextResponse } from 'next/server'
import crypto from 'node:crypto'

const SIGNING_SECRET = process.env.SIGNING_SECRET!

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params
  const url = new URL(request.url)
  const sig = url.searchParams.get('sig')
  const exp = url.searchParams.get('exp')
  if (!sig || !exp) {
    return NextResponse.json({ error: 'Missing signature' }, { status: 400 })
  }
```

### Ideal continuation

```typescript
  if (Date.now() > Number(exp)) {
    return NextResponse.json({ error: 'Link expired' }, { status: 410 })
  }

  const payload = `${id}:${exp}`
  const expected = crypto.createHmac('sha256', SIGNING_SECRET).update(payload).digest('hex')

  const sigBuf = Buffer.from(sig, 'hex')
  const expectedBuf = Buffer.from(expected, 'hex')
  if (sigBuf.length !== expectedBuf.length || !crypto.timingSafeEqual(sigBuf, expectedBuf)) {
    return NextResponse.json({ error: 'Invalid signature' }, { status: 403 })
  }

  return NextResponse.redirect(`https://files.example.com/${id}`, 302)
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["createHmac", "timingSafeEqual", "NextResponse.redirect"],
    "must_not_contain": ["sig === expected", "sig == expected"],
    "must_match_regex": ["createHmac\\s*\\(\\s*['\"]sha256['\"]", "timingSafeEqual\\s*\\("],
    "min_lines": 8,
    "max_lines": 28
  }
}
```

### Grading philosophy

`timingSafeEqual` is the **primary capability marker**. The regex `timingSafeEqual\s*\(` is the signal we most care about — a model that gets the timing-safe comparison right is demonstrating real security understanding, even if the surrounding flow has minor variation. `createHmac` and `NextResponse.redirect` are supporting structural checks (HMAC primitive + actual redirect on success), but the timing-safe call is what separates a security-aware model from one that pattern-matched on "verify signature." The variable name `exp` was removed from `must_contain` for this reason — it was implementation trivia, not capability.

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `sig === expected` | Variable-time string comparison; timing-leak side channel. |
| `sig == expected` | Same — also non-strict equality is wrong for security primitives. |

Difficulty: `hard`. Tags: `["typescript","route-handler","redirect","security","crypto","hmac"]`. file_path: `app/r/[id]/route.ts`.

---

# Task 30 — `api-routes.webhook_signature_verify.001`

**Capability.** Verify an inbound webhook's HMAC signature against the raw request body, constant-time compare, then parse the event.

**Source.** [`SubtleCrypto.sign`](https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/sign) — referenced as the web-platform analog; implementation uses Node `crypto` for parity with most webhook SDKs.

**Why distinct from Task 29.** Same primitive (HMAC + timing-safe), different flow:
- Signature in **header**, not query
- Compute over the **raw body** (must read with `request.text()` *before* `JSON.parse`; using `request.json()` makes the body unverifiable)
- Outcome is **process the event**, not redirect

Required tokens are disjoint from Task 29: `request.text()` + `x-webhook-signature` (vs. `NextResponse.redirect` + `exp`). A model that copies the HMAC primitive but skips the raw-body discipline fails this one specifically.

### Prompt

```typescript
import { NextResponse } from 'next/server'
import crypto from 'node:crypto'

const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET!

export async function POST(request: Request) {
  const signature = request.headers.get('x-webhook-signature')
  if (!signature) {
    return NextResponse.json({ error: 'Missing signature' }, { status: 401 })
  }
  const rawBody = await request.text()
```

### Ideal continuation

```typescript
  const expected = crypto
    .createHmac('sha256', WEBHOOK_SECRET)
    .update(rawBody)
    .digest('hex')

  const sigBuf = Buffer.from(signature, 'hex')
  const expectedBuf = Buffer.from(expected, 'hex')
  if (sigBuf.length !== expectedBuf.length || !crypto.timingSafeEqual(sigBuf, expectedBuf)) {
    return NextResponse.json({ error: 'Invalid signature' }, { status: 401 })
  }

  const event = JSON.parse(rawBody)
  // process event...

  return NextResponse.json({ ok: true })
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["createHmac", "timingSafeEqual", "rawBody"],
    "must_not_contain": ["request.json()", "signature === expected"],
    "must_match_regex": ["createHmac\\s*\\(\\s*['\"]sha256['\"]", "timingSafeEqual\\s*\\(", "\\.update\\s*\\(\\s*rawBody"],
    "min_lines": 8,
    "max_lines": 26
  }
}
```

### Anti-pattern rationale

| Forbidden | Why |
|---|---|
| `request.json()` | Reads + consumes the body as JSON before HMAC; signature can no longer be verified against the exact byte sequence the sender signed. |
| `signature === expected` | Same timing-leak issue as Task 29. |

Difficulty: `hard`. Tags: `["typescript","route-handler","webhook","security","crypto","hmac"]`. file_path: `app/api/webhooks/inbound/route.ts`.

---

## Notes for review

- All 7 are pre-checked against `capabilities.jsonl` — zero collisions.
- Tasks 29 and 30 deliberately share the HMAC primitive but have disjoint required-token sets so a model that copy-pastes the security pattern but misses the flow can still fail one. The shared primitive is the *foundation*, not the capability.
- `framework_version` metadata sweep is deferred to the v0.2 release pass per the running roadmap decision; the Next.js 15 `await cookies()` / `await headers()` / `await params` patterns are baked into Tasks 26, 27, and 29's prompts.
- Grader signal estimates: 24 (mid), 25 (mid), 26 (mid–high — many models miss `sameSite`), 27 (low–mid), 28 (low — most strong models pass), 29 (high — timing-safe is the discriminator), 30 (high — raw-body discipline is the discriminator).
