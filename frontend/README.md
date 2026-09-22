# frontend

The Northstar web app: Next.js 16 App Router, React 19, Tailwind v4.

This file used to be unedited `create-next-app` boilerplate — it described
editing `app/page.tsx` to "start editing", pointed at the Next.js tutorial,
and claimed the app loads Geist via `next/font`. It loads Bricolage
Grotesque, Onest and IBM Plex Mono (`app/layout.tsx`).

Setup, environment variables and deployment live in the [root
README](../README.md); this directory has no separate install step.

```bash
npm install
npm run dev     # http://localhost:3000
npm run lint
npm test        # vitest — scoring invariants and copy-count guards
npm run build
```

`NEXT_PUBLIC_API_URL` must point at the running backend or every request goes
to the Next.js server instead and 404s. See `.env.example`.

## Layout

| Path | What lives there |
|---|---|
| `app/` | 22 page routes, plus `robots.ts` and the `noindex` layout for `/p/[handle]` |
| `components/` | Shared UI. `ui/` is the shadcn-style primitive set; `decor/` and `motion/` are presentational |
| `lib/` | Scoring (`scoring.ts`, `assessment.ts`, `archetypes.ts`, `plan.ts`), the API client (`api.ts`), and generated API types (`api-types.gen.ts`) |

`lib/api-types.gen.ts` is generated — run `npm run gen:api` after the backend
schema changes, and `backend/tests/test_openapi_contract.py` fails the build if
you forget.
