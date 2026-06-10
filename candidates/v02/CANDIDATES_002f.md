# NextBench v0.2 — Candidate Batch 002f (Files + i18n + Routing + SEO + UX Hooks)

**12 candidate tasks** — the final v0.2 generation batch. Composition is more diffuse than 002e (which clustered around database/auth/realtime); these are the remaining patterns a real Next.js app touches but that v0.1 missed:

- **Files** (2 tasks) — multipart parsing on the server, drag-drop on the client
- **Internationalization** (2 tasks) — `next-intl` setup at the layout level, server-side translations in pages
- **Search params** (2 tasks) — Zod-validated on server, mutable via `useSearchParams` on client
- **SEO / routing surfaces** (3 tasks) — `generateMetadata` with OG, dynamic `sitemap.ts`, `app/error.tsx` boundary
- **React UX hooks** (3 tasks) — `useTransition`, `IntersectionObserver` cleanup, click-outside cleanup

**Composition vs the reviewer's A/B/C taxonomy:** 8 Type A · 1 Type B · 3 Type C. More A-heavy than 002e — which matches the natural shape of "remaining patterns" (mostly framework APIs and Web Platform APIs). The Type C cluster is anchored by the two cleanup-discipline hooks (53, 54) which are textbook production-bug capabilities.

**Net-new capabilities added during scope expansion (6 of 12):** `generate_metadata`, `sitemap_dynamic`, `error_boundary_segment`, `use_transition_state`, `intersection_observer_hook`, `click_outside_hook`. The last one — `parallel_route_modal` — was dropped from the proposal because parallel-route behavior lives in the file path, not the content, and isn't meaningfully testable via content-only completion. Swapped for `use_transition_state`.

Registry pre-check: zero collisions across batches 001/002a/002b/002c/002d/002e.

## The 12 capabilities

| # | task_id | Diff | Type | Tests |
|---|---|---|---|---|
| 43 | `api-routes.file_upload_formdata.001` | mid | A | `instanceof File` + `arrayBuffer` after `formData()` |
| 44 | `react.file_drop_zone.001` | mid | A/C | `onDragOver` + `preventDefault` + `dataTransfer.files` |
| 45 | `nextjs.next_intl_setup.001` | mid | A | `NextIntlClientProvider` + `getMessages` |
| 46 | `nextjs.locale_segment_param.001` | mid | A | `await params` + `getTranslations({ locale, namespace })` |
| 47 | `nextjs.search_params_zod.001` | mid | B | Zod `safeParse` on `searchParams` with discriminated result |
| 48 | `react.use_search_params_client.001` | mid | A | `useSearchParams` + `URLSearchParams` + `router.push` |
| 49 | `nextjs.generate_metadata.001` | mid | A | `generateMetadata` with `openGraph` + `await params` |
| 50 | `nextjs.sitemap_dynamic.001` | mid | A | `MetadataRoute.Sitemap` shape, NOT raw XML |
| 51 | `nextjs.error_boundary_segment.001` | mid | B | `error.tsx` with `reset` button + `useEffect` logger |
| 52 | `react.use_transition_state.001` | mid | A | `useTransition` + `startTransition` + `isPending` |
| 53 | `react.intersection_observer_hook.001` | mid | C | `IntersectionObserver` + `disconnect()` cleanup |
| 54 | `react.click_outside_hook.001` | mid | C | `addEventListener` + `removeEventListener` + `.contains(` |

## Four structural moves

**1. Tasks 43 vs 44 are the multipart pair.** 43 tests the *server* extraction (`request.formData()` → `instanceof File` → `arrayBuffer()`); 44 tests the *client* drop zone (`onDragOver` + `preventDefault` + `dataTransfer.files`). Together they're the full file-upload story.

**2. Tasks 47 vs 48 split server/client search params.** 47 reads `searchParams` (server, async) and validates with Zod; 48 reads via `useSearchParams()` (client hook) and *mutates* via `URLSearchParams` + `router.push`. Both APIs are named "searchParams" but the surface and rules are completely different — a model that confuses them fails one or both.

**3. Tasks 53 and 54 are cleanup-discipline tests.** Both pair `useEffect` with a Web API that requires cleanup; both regex the `return () => { ... }` form. These are Type C tasks — they're not testing whether a model knows IntersectionObserver exists, they're testing whether it remembers to disconnect/removeEventListener on unmount. That distinction is exactly where production bugs come from.

**4. Task 50 forbids raw XML.** The Next.js `sitemap.ts` capability is the typed `MetadataRoute.Sitemap` shape. A model that produces a `<urlset>` XML document "works" but bypasses the framework primitive — and Next.js generates the XML for you. Forbidding `<urlset` + `<?xml` enforces the framework-first approach.

---

# Task 43 — `api-routes.file_upload_formdata.001`

**Capability.** Parse multipart in a route handler, narrow `FormDataEntryValue` to `File` via `instanceof`, validate size, read bytes via `arrayBuffer()`.

**Source.** [`Request.formData()`](https://developer.mozilla.org/en-US/docs/Web/API/Request/formData).

**Why distinct from 002d Task 28.** 28 tested text-field extraction with string narrowing. This tests **File extraction** specifically — the `instanceof File` narrow is the typing capability, and `arrayBuffer()` is the byte-access capability. A model that knows `formData.get('field')` for strings may not know it returns `File | string | null` for file inputs.

### Prompt

```typescript
import { NextResponse } from 'next/server'

const MAX_SIZE = 5 * 1024 * 1024 // 5MB

export async function POST(request: Request) {
```

### Ideal continuation

```typescript
  const formData = await request.formData()
  const file = formData.get('file')

  if (!(file instanceof File)) {
    return NextResponse.json({ error: 'No file provided' }, { status: 400 })
  }

  if (file.size > MAX_SIZE) {
    return NextResponse.json({ error: 'File too large' }, { status: 413 })
  }

  const arrayBuffer = await file.arrayBuffer()
  // persist arrayBuffer to storage

  return NextResponse.json({
    name: file.name,
    size: file.size,
    type: file.type,
  })
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["request.formData()", "instanceof File", "arrayBuffer", "NextResponse"],
    "must_not_contain": ["request.json(", "JSON.parse"],
    "must_match_regex": ["formData\\.get\\s*\\(\\s*['\"]file['\"]", "instanceof\\s+File"],
    "min_lines": 6,
    "max_lines": 26
  }
}
```

**Anti-pattern.** `request.json()` / `JSON.parse` = trying to handle this as a JSON body.

Difficulty: `mid`. file_path: `app/api/upload/route.ts`.

---

# Task 44 — `react.file_drop_zone.001`

**Capability.** Drop zone that handles `onDragOver` (with `preventDefault` — required for drop to fire!), `onDrop`, drag-state visual feedback, and extracts `File[]` from `dataTransfer.files`.

**Source.** [HTML Drag and Drop API](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API).

**Why distinct.** v0.1 has no drag-drop tasks. The killer detail is `preventDefault()` on `onDragOver` — without it, browsers reject the drop. Many models forget this and write a drop zone that looks correct but doesn't fire.

### Prompt

```typescript
'use client'
import { useState } from 'react'

export function FileDropZone({ onFiles }: { onFiles: (files: File[]) => void }) {
```

### Ideal continuation

```typescript
  const [isDragging, setIsDragging] = useState(false)

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault()
        setIsDragging(true)
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setIsDragging(false)
        const files = Array.from(e.dataTransfer.files)
        onFiles(files)
      }}
      className={`border-2 border-dashed p-8 rounded ${
        isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
      }`}
    >
      Drop files here
    </div>
  )
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["onDragOver", "onDrop", "preventDefault", "dataTransfer", "useState"],
    "must_not_contain": ["<input type=\"file\"", "fetch("],
    "must_match_regex": ["dataTransfer\\.files", "preventDefault\\s*\\(\\s*\\)"],
    "min_lines": 8,
    "max_lines": 32
  }
}
```

**Anti-pattern.** `<input type="file">` is the *button* upload pattern, not drag-drop. `fetch(` indicates the model conflated this with the upload action itself.

Difficulty: `mid`. file_path: `components/file-drop-zone.tsx`.

---

# Task 45 — `nextjs.next_intl_setup.001`

**Capability.** Wrap a `[locale]` layout in `NextIntlClientProvider`, load messages via `getMessages()` from server, pass `messages` + `locale` props.

**Source.** [next-intl App Router setup](https://next-intl-docs.vercel.app/docs/getting-started/app-router).

**Why distinct.** v0.1 has no i18n. This is the canonical recipe for the most-used Next.js i18n library.

### Prompt

```typescript
import { NextIntlClientProvider } from 'next-intl'
import { getMessages } from 'next-intl/server'

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode
  params: Promise<{ locale: string }>
}) {
```

### Ideal continuation

```typescript
  const { locale } = await params
  const messages = await getMessages()

  return (
    <html lang={locale}>
      <body>
        <NextIntlClientProvider messages={messages} locale={locale}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  )
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["NextIntlClientProvider", "getMessages", "await params"],
    "must_not_contain": ["useEffect", "useState"],
    "must_match_regex": ["NextIntlClientProvider[^>]*messages\\s*=", "getMessages\\s*\\("],
    "min_lines": 4,
    "max_lines": 20
  }
}
```

### Classification

`task_class: "ecosystem_specific"` — this task tests the `next-intl` library specifically (its `NextIntlClientProvider` + `getMessages` API), not a Next.js framework primitive. A model that's strong on generic i18n concepts but unfamiliar with `next-intl` will fail; that's the intended discrimination. Classifying it explicitly avoids confusion when comparing scores against framework-API tasks like Task 49 (`generateMetadata`) which tests a true Next.js primitive.

This is the second task in the corpus to carry an explicit class (alongside `connection_pool_singleton`'s `pattern_knowledge`). Together they establish two of the non-default classes; the broader taxonomy rollout remains deferred to the release pass.

**Anti-pattern.** `useState` / `useEffect` in a layout = the model put `'use client'` and broke server-side message loading.

Difficulty: `mid`. file_path: `app/[locale]/layout.tsx`.

---

# Task 46 — `nextjs.locale_segment_param.001`

**Capability.** Server page reads `[locale]` from `await params`, fetches translations with `getTranslations({ locale, namespace })`.

**Source.** [Next.js i18n routing](https://nextjs.org/docs/app/building-your-application/routing/internationalization).

**Why distinct from 45.** 45 sets up the provider context once at the layout level. 46 *consumes* translations in a page using the server-side function (`getTranslations`, not the `useTranslations` hook — which is client-only). The server/client split is the capability.

### Prompt

```typescript
import { getTranslations } from 'next-intl/server'

export default async function AboutPage({
  params,
}: {
  params: Promise<{ locale: string }>
}) {
```

### Ideal continuation

```typescript
  const { locale } = await params
  const t = await getTranslations({ locale, namespace: 'about' })

  return (
    <main className="p-8">
      <h1>{t('title')}</h1>
      <p>{t('description')}</p>
    </main>
  )
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["await params", "getTranslations", "namespace"],
    "must_not_contain": ["useEffect", "useTranslations"],
    "must_match_regex": ["await\\s+params", "getTranslations\\s*\\("],
    "min_lines": 4,
    "max_lines": 18
  }
}
```

**Anti-pattern.** `useTranslations` is the client hook — using it in a server component without `'use client'` would break.

Difficulty: `mid`. file_path: `app/[locale]/about/page.tsx`.

---

# Task 47 — `nextjs.search_params_zod.001`

**Capability.** Server component receives `searchParams` (Promise in Next.js 15+), validates with Zod's `safeParse`, branches on the discriminated `.success` result.

**Source.** [Zod `safeParse`](https://zod.dev/?id=safeparse).

**Why distinct from 002d Task 24.** 24 tested zod field errors on FormData (server action context). 47 tests it on URL searchParams (page-rendering context). Different input, different schema (with `z.coerce` for numbers), different consumer.

### Prompt

```typescript
import { z } from 'zod'

const SearchSchema = z.object({
  q: z.string().min(1).optional(),
  page: z.coerce.number().int().positive().default(1),
  sort: z.enum(['newest', 'price-asc', 'price-desc']).default('newest'),
})

export default async function ProductsPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>
}) {
```

### Ideal continuation

```typescript
  const raw = await searchParams
  const parsed = SearchSchema.safeParse(raw)

  if (!parsed.success) {
    return <div>Invalid search parameters</div>
  }

  const { q, page, sort } = parsed.data

  return (
    <main className="p-8">
      <h1>Products</h1>
      <p>
        Page {page}, sorted by {sort}
        {q ? `, query: ${q}` : ''}
      </p>
    </main>
  )
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["safeParse", "searchParams"],
    "must_not_contain": ["SearchSchema.parse(", "useSearchParams"],
    "must_match_regex": ["safeParse\\s*\\(", "await\\s+searchParams", "\\.success"],
    "min_lines": 5,
    "max_lines": 26
  }
}
```

**Anti-pattern.** `SearchSchema.parse(` throws on invalid — can't return a fallback render. `useSearchParams` is the *client* hook and would break in a server component.

Difficulty: `mid`. file_path: `app/products/page.tsx`.

---

# Task 48 — `react.use_search_params_client.001`

**Capability.** Client component reads URL search params via `useSearchParams()`, mutates them via `URLSearchParams` + `router.push(pathname?params)` — the canonical "update filter without remount" pattern.

**Source.** [`useSearchParams`](https://nextjs.org/docs/app/api-reference/functions/use-search-params).

**Why distinct from 47.** 47 reads server-side `searchParams` (async). 48 reads *and writes* via the client hook plus `useRouter`/`usePathname` for navigation. The mutation half is the discriminator — many models know how to *read* but not how to *push without full-page navigation*.

### Prompt

```typescript
'use client'
import { useSearchParams, useRouter, usePathname } from 'next/navigation'

export function FilterBar() {
```

### Ideal continuation

```typescript
  const searchParams = useSearchParams()
  const router = useRouter()
  const pathname = usePathname()
  const currentSort = searchParams.get('sort') ?? 'newest'

  function setSort(sort: string) {
    const params = new URLSearchParams(searchParams.toString())
    params.set('sort', sort)
    router.push(`${pathname}?${params.toString()}`)
  }

  return (
    <select value={currentSort} onChange={(e) => setSort(e.target.value)}>
      <option value="newest">Newest</option>
      <option value="price-asc">Price: low to high</option>
      <option value="price-desc">Price: high to low</option>
    </select>
  )
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["useSearchParams", "useRouter", "usePathname", "URLSearchParams", "router.push"],
    "must_not_contain": ["window.location", "window.history"],
    "must_match_regex": ["useSearchParams\\s*\\(\\s*\\)", "router\\.push\\s*\\("],
    "min_lines": 6,
    "max_lines": 30
  }
}
```

**Anti-pattern.** `window.location.href = ...` does a full page reload — the entire point of `useRouter` is client-side navigation without losing component state.

Difficulty: `mid`. file_path: `components/filter-bar.tsx`.

---

# Task 49 — `nextjs.generate_metadata.001`

**Capability.** Server-side `generateMetadata` reads `await params`, fetches the relevant entity, returns `Metadata` shape with `title`, `description`, **and `openGraph`** for social sharing.

**Source.** [`generateMetadata` reference](https://nextjs.org/docs/app/api-reference/functions/generate-metadata).

**Why distinct.** v0.1 has no SEO metadata tasks. The OG field is what separates a barebones implementation from a production-real one — `title` alone is incomplete capability.

### Prompt

```typescript
import type { Metadata } from 'next'
import { getPost } from '@/lib/posts'

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>
}): Promise<Metadata> {
```

### Ideal continuation

```typescript
  const { slug } = await params
  const post = await getPost(slug)

  if (!post) {
    return { title: 'Post not found' }
  }

  return {
    title: post.title,
    description: post.excerpt,
    openGraph: {
      title: post.title,
      description: post.excerpt,
      images: [post.coverImage],
    },
  }
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["title:", "description:", "openGraph", "await params"],
    "must_not_contain": ["useState", "useEffect"],
    "must_match_regex": ["openGraph\\s*:\\s*\\{[^}]*\\b(title|description|images)\\b", "await\\s+params"],
    "min_lines": 6,
    "max_lines": 28
  }
}
```

### Grading philosophy

`openGraph` is the **primary capability marker** — the regex `openGraph\s*:\s*\{[^}]*\b(title|description|images)\b` requires not just the field's presence but also at least one canonical OG sub-field. A model that produces shallow metadata (just `title` + `description` at the root, no OG block) won't pass. This follows the same pattern as 002d Task 29 (`timingSafeEqual`), 002e Task 37 (`authorId !== user.id`), 002e Task 40 / 002f Tasks 53–54 (cleanup return). The "primary capability marker" frame is now consistently applied to Type B tasks where the architectural decision is the signal.

`title:` / `description:` at the root level are supporting context — they confirm the model returned the Metadata shape, but they're not the discriminator.

**Anti-pattern.** `useState` / `useEffect` = the model added `'use client'`, which breaks `generateMetadata` (it's server-only).

Difficulty: `mid`. file_path: `app/blog/[slug]/page.tsx`.

---

# Task 50 — `nextjs.sitemap_dynamic.001`

**Capability.** Return `MetadataRoute.Sitemap` array from `app/sitemap.ts` with both static and dynamically-derived entries; Next.js renders the XML for you.

**Source.** [Sitemap file convention](https://nextjs.org/docs/app/api-reference/file-conventions/metadata/sitemap).

**Why distinct.** v0.1 has no SEO file conventions. The capability is "let the framework handle XML serialization." Models that drop to writing raw `<urlset>` XML are bypassing the primitive.

### Prompt

```typescript
import type { MetadataRoute } from 'next'
import { getAllPosts } from '@/lib/posts'

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
```

### Ideal continuation

```typescript
  const posts = await getAllPosts()
  const postEntries: MetadataRoute.Sitemap = posts.map((post) => ({
    url: `https://example.com/blog/${post.slug}`,
    lastModified: post.updatedAt,
    changeFrequency: 'weekly',
    priority: 0.7,
  }))

  return [
    {
      url: 'https://example.com',
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1.0,
    },
    {
      url: 'https://example.com/blog',
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 0.9,
    },
    ...postEntries,
  ]
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["url:", "lastModified", "changeFrequency", "priority"],
    "must_not_contain": ["<?xml", "<urlset"],
    "must_match_regex": ["url\\s*:\\s*[`'\"]", "lastModified\\s*:"],
    "min_lines": 8,
    "max_lines": 40
  }
}
```

**Anti-pattern.** `<?xml` or `<urlset` = wrote raw XML, bypassing the typed primitive.

Difficulty: `mid`. file_path: `app/sitemap.ts`.

---

# Task 51 — `nextjs.error_boundary_segment.001`

**Capability.** `app/error.tsx` with required `'use client'`, takes `error` + `reset` props, displays the error and provides a retry button wired to `reset()`. Logs the error in `useEffect` for observability.

**Source.** [Next.js error handling](https://nextjs.org/docs/app/building-your-application/routing/error-handling).

**Why distinct.** v0.1 has error-handling tasks but none for the *segment-level boundary* with `reset`. This is the Next.js App Router primitive specifically — a class-based React error boundary won't work here.

### Prompt

```typescript
'use client'
import { useEffect } from 'react'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
```

### Ideal continuation

```typescript
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div className="p-8">
      <h2 className="text-xl font-semibold">Something went wrong</h2>
      <p className="text-sm text-gray-600">{error.message}</p>
      <button
        onClick={() => reset()}
        className="mt-4 px-4 py-2 rounded bg-zinc-900 text-white"
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
    "must_contain": ["useEffect", "reset", "error.message"],
    "must_not_contain": ["redirect", "router.push"],
    "must_match_regex": ["onClick\\s*=\\s*\\{[^}]*reset", "useEffect\\s*\\("],
    "min_lines": 6,
    "max_lines": 26
  }
}
```

**Anti-pattern.** `redirect` / `router.push` = the model defaulted to navigating away from the error, instead of using `reset()` to retry the segment in place.

Difficulty: `mid`. file_path: `app/error.tsx`.

---

# Task 52 — `react.use_transition_state.001`

**Capability.** Use `useTransition()` to mark a state update as non-urgent. The transition wrapper gets `isPending` for UX feedback.

**Source.** [`useTransition`](https://react.dev/reference/react/useTransition).

**Why distinct from 002c/002d React hooks.** `useFormState` (002c) / `useActionState` (002c) wrap server actions; `useFormStatus` (002d) reads form-pending in a child component. `useTransition` is a *general* concurrent-React primitive — it can wrap any state update, not just form submissions. Different surface.

### Prompt

```typescript
'use client'
import { useState, useTransition } from 'react'
import { searchPosts } from '@/lib/search'

export function SearchForm() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<string[]>([])
```

### Ideal continuation

```typescript
  const [isPending, startTransition] = useTransition()

  function handleSearch(value: string) {
    setQuery(value)
    startTransition(async () => {
      const data = await searchPosts(value)
      setResults(data)
    })
  }

  return (
    <div>
      <input
        type="text"
        value={query}
        onChange={(e) => handleSearch(e.target.value)}
        className={isPending ? 'opacity-50' : ''}
      />
      {isPending && <p>Searching...</p>}
      <ul>
        {results.map((r) => (
          <li key={r}>{r}</li>
        ))}
      </ul>
    </div>
  )
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["useTransition", "startTransition", "isPending"],
    "must_not_contain": ["useEffect", "setTimeout", "useFormStatus"],
    "must_match_regex": ["useTransition\\s*\\(\\s*\\)", "startTransition\\s*\\("],
    "min_lines": 6,
    "max_lines": 32
  }
}
```

**Anti-pattern.** `setTimeout` = manual debouncing instead of using `useTransition`'s concurrent-render priority. `useFormStatus` = wrong hook for non-form use cases.

Difficulty: `mid`. file_path: `components/search-form.tsx`.

---

# Task 53 — `react.intersection_observer_hook.001`

**Capability.** Custom hook that uses `IntersectionObserver` to detect element visibility. The discipline test: **disconnect on unmount** via `useEffect` return.

**Source.** [`IntersectionObserver`](https://developer.mozilla.org/en-US/docs/Web/API/IntersectionObserver).

**Why distinct.** v0.1 has no DOM-observer hooks. The killer detail is the cleanup — leaked observers cause memory bloat and stale `isIntersecting` callbacks on dead components.

### Prompt

```typescript
'use client'
import { useEffect, useRef, useState } from 'react'

export function useInView<T extends HTMLElement>() {
```

### Ideal continuation

```typescript
  const ref = useRef<T>(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const target = ref.current
    if (!target) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        setInView(entry.isIntersecting)
      },
      { threshold: 0.1 },
    )

    observer.observe(target)
    return () => {
      observer.disconnect()
    }
  }, [])

  return { ref, inView }
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["IntersectionObserver", "useEffect", "isIntersecting", "useRef"],
    "must_not_contain": ["addEventListener", "getBoundingClientRect"],
    "must_match_regex": ["new\\s+IntersectionObserver\\s*\\(", "return\\s*\\(\\s*\\)\\s*=>\\s*\\{[^}]*\\.(disconnect|unobserve)"],
    "min_lines": 8,
    "max_lines": 32
  }
}
```

### Grading philosophy

The cleanup regex `return () => { ... .(disconnect|unobserve)(` is the **primary capability marker** — same pattern as 002e Task 40 (`use_websocket_hook`). A model that creates the observer but forgets to disconnect on unmount has not solved the capability, even if the observation logic is otherwise correct.

**Anti-pattern.** `addEventListener('scroll', ...)` + `getBoundingClientRect()` is the legacy approach this hook replaces. Forbidding both forces the modern primitive.

Difficulty: `mid`. file_path: `hooks/use-in-view.ts`.

---

# Task 54 — `react.click_outside_hook.001`

**Capability.** Custom hook that detects clicks outside a referenced element. Adds a `mousedown` listener on `document`; **must remove it on unmount**.

**Source.** [`Element.contains()`](https://developer.mozilla.org/en-US/docs/Web/API/Element/contains).

**Why distinct.** v0.1 has no global-listener hooks. The cleanup discipline (removing the document listener) is the killer detail. Pairs philosophically with Task 53 — both are Type C tests.

### Prompt

```typescript
'use client'
import { useEffect, useRef } from 'react'

export function useClickOutside<T extends HTMLElement>(
  onOutsideClick: () => void,
) {
```

### Ideal continuation

```typescript
  const ref = useRef<T>(null)

  useEffect(() => {
    function handleClick(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        onOutsideClick()
      }
    }

    document.addEventListener('mousedown', handleClick)
    return () => {
      document.removeEventListener('mousedown', handleClick)
    }
  }, [onOutsideClick])

  return ref
}
```

### Checks

```json
{
  "static": {
    "must_contain": ["addEventListener", "removeEventListener", ".contains(", "useRef"],
    "must_not_contain": ["onBlur"],
    "must_match_regex": ["return\\s*\\(\\s*\\)\\s*=>\\s*\\{[^}]*removeEventListener", "\\.contains\\s*\\("],
    "min_lines": 8,
    "max_lines": 28
  }
}
```

### Grading philosophy

The cleanup regex `return () => { ... removeEventListener }` is the **primary capability marker**. A model that adds a global `document` listener without removing it on unmount creates a memory leak; this regex forces the matching teardown.

**Anti-pattern.** `onBlur` on the element itself is unreliable — it fires for any focus loss including clicks on nested children. The document-level listener + `contains()` check is the robust pattern.

Difficulty: `mid`. file_path: `hooks/use-click-outside.ts`.

---

## Notes for review

- All 12 pre-checked against `capabilities.jsonl` — zero collisions across batches 001/002a/002b/002c/002d/002e.
- Six net-new capabilities were added during the 6→12 scope expansion. The proposed `parallel_route_modal` was dropped because parallel-route behavior is encoded in the file path (`app/@modal/(.)photos/[id]/page.tsx`), not in the content the model generates — a content-only completion task can't meaningfully test it. Swapped for `use_transition_state`, which IS testable via content and completes the React 19 concurrent-rendering coverage.
- **Pre-review self-rubric scan applied.** Three brittleness fixes were caught before sending:
  - Task 44: regex relaxed from `e\.dataTransfer\.files` → `dataTransfer\.files` (allows destructured access)
  - Task 50: `"xml"` (case-insensitive — would false-positive on Tailwind `overflow-scroll`-style class names and comments) → kept only `<?xml` and `<urlset`
  - Task 53: dropped `"scroll"` from forbidden tokens for the same case-insensitivity reason
- Grading-philosophy notes appear on Tasks 53 and 54 — both are Type C cleanup-discipline tests where the `useEffect` return is the primary capability marker (same pattern as 002e Task 40, 002d Task 29).
- Difficulty distribution: 12 mid, 0 hard. This batch's natural theme (routing/SEO/UX patterns) doesn't have many genuinely hard capabilities — the prior batches absorbed the hard cluster (transactions, HMAC, BOLA, realtime). That's OK; not every batch needs hard tasks.
- A/B/C taxonomy: 8 A · 1 B · 3 C. More framework-API-heavy than 002e by design — these are the remaining patterns that fill out the "what every real Next.js app touches" coverage.
- `framework_version` metadata sweep + broader `task_class` rollout are still deferred to the v0.2 release pass.
- **After this batch:** v0.2 generation is complete. Next phase is the release pass — v0.1 dedup, re-grade 12 models on the new corpus, update REPORT/LEADERBOARD/ANALYSIS docs, tag GitHub + HF Hub as `v0.2`.
