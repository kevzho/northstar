# Northstar — Technical Architecture

*Read against commit `3746d27` (2026-08-24). Regenerate this doc when the deploy topology or the scoring pipeline changes.*

---

## 1. Topology

```
                    ┌──────────────────────────────┐
   browser ───────► │ Next.js 16 (App Router)      │
                    │ Vercel · northstar.study     │
                    └──────┬──────────────┬────────┘
                           │              │
             Bearer <JWT>  │              │  anon key + RLS
                           ▼              ▼
              ┌────────────────────┐   ┌──────────────────────┐
              │ FastAPI            │   │ Supabase Auth        │
              │ Vercel serverless  │   │ (session, JWKS)      │
              │ northstar-api-…    │   └──────────────────────┘
              └─────────┬──────────┘
       service-role key │ (bypasses RLS)
                        ▼
              ┌────────────────────┐
              │ Supabase Postgres  │  22 tables · 22 migrations
              └─────────▲──────────┘
                        │ upsert
              ┌─────────┴──────────┐
              │ GitHub Actions     │  scrape (daily) · smoke (2h) · CI (push)
              └────────────────────┘
```

Two credential paths into Postgres, deliberately distinct:

- **Browser → Supabase directly**: publishable/anon key, every read constrained by RLS policies. Used for auth only (`frontend/lib/supabase.ts`).
- **Browser → FastAPI → Supabase**: the backend holds `SUPABASE_SECRET_KEY` (service role) and bypasses RLS entirely. It owns profile upserts, catalog reads, match persistence. Authorization is therefore the backend's own responsibility on every route — enforced by the `RequireUser` dependency, not by the database.

---

## 2. Frontend

**`frontend/`** — Next.js 16.2.0, React 19.2.4, TypeScript 5, App Router.

| Concern | Choice |
|---|---|
| Styling | Tailwind CSS v4 (`@tailwindcss/postcss`), `tw-animate-css` |
| Components | shadcn 4 + `@base-ui/react` 1.7, `class-variance-authority`, `tailwind-merge` |
| Icons | `lucide-react` 1.31 |
| Motion | `motion` 13.1 (`components/motion/*`) |
| Visualization | `d3` 7.9 (pathway map), `three` 0.185 (`components/decor/*`) |
| Theming | `next-themes` — `components/theme-toggle.tsx` |
| Errors | `@sentry/browser` 10.70 via `components/SentryInit.tsx` |
| Tests | `vitest` 4.1 |

**23 route segments** under `frontend/app/`: `/`, `/login`, `/auth/callback`, `/onboarding`, `/assessment`, `/dashboard`, `/discover`, `/opportunities`, `/opportunities/[id]`, `/map`, `/futures`, `/plan`, `/projects`, `/mentors`, `/advisor`, `/teamup`, `/friends`, `/profile`, `/p/[handle]`, `/contact`, `/faq`, plus `layout.tsx` and `not-found.tsx`.

### Theming

`next-themes` with `attribute="class"`, `defaultTheme="dark"`, `enableSystem={false}` (`app/layout.tsx`). Both palettes are CSS custom properties in `globals.css`: `:root` holds the night set, `.light` overrides the primitives. Because the semantic tokens are declared as `var()` references (`--card: var(--panel)`), overriding a primitive in `.light` re-resolves everything downstream — the light block only needs to restate primitives, not the whole token table.

`ThemeToggle` is mounted via `AppNav` and `PageHeader`, plus 5 pages that render their own header. It uses `useSyncExternalStore` for the mounted check rather than setState-in-effect, which the project's lint rejects.

**The pathway map is the one place color carries data**, so its palette is themed too: `--field-*` (10 fields) + `--field-unknown`, `--on-field`, `--map-label`, `--map-meta`. Light values are the same hues darkened until each clears 4.5:1 on `--background`, saturation held so they read as ink rather than neon; `humanities` is nudged 14° toward brown because tan and gold collapse into each other once both are dark enough to read.

D3 writes these as inline **style** properties, not presentation attributes — only the former resolve `var()`. That matters beyond tidiness: resolving tokens in JS via `getComputedStyle` reads stale values, because the effect re-runs before the browser recomputes styles for the new `.light` class. Letting CSS own the resolution means the map re-themes with no redraw and no `resolvedTheme` dependency at all.

### Client boundary

`frontend/lib/api.ts` is the single module that talks to FastAPI. Every function is browser-only by construction: the access token comes from the supabase-js session in `localStorage`, so calling any of these from a server component sends an anonymous request and gets `401`. Base URL is `NEXT_PUBLIC_API_URL`.

`lib/supabase.ts` throws at import when `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` are missing. CI therefore injects placeholder values for `next build` — otherwise the build fails for the wrong reason.

### Client-side scoring (`lib/scoring.ts`)

The assessment never round-trips to the server. Three steps, all local:

1. **Aggregate** — sum the `TraitDeltas` attached to each chosen answer in `lib/assessment.ts`. Answers are on a 1–5 Likert scale (`LIKERT_VALUES`, weighted by `likertWeight`).
2. **Normalize** — divide each trait by the maximum that trait could have scored had every answer been its strongest option → 0–100. Normalizing against the *achievable* maximum rather than a constant keeps traits comparable despite unequal question counts.
3. **Rank** — cosine similarity between the student's 6-dimension trait vector and each archetype vector in `lib/archetypes.ts`, then label three: `safe` (nearest), `ambitious` (of the rest, highest overall demand), `unconventional` (of the rest, furthest from `safe`).

Traits: `builder`, `analyst`, `riskTolerance`, `ambiguityComfort`, `collaboration`, `executionTempo`.

No weight is computed at runtime — every number is a literal in `assessment.ts` or `archetypes.ts`. `lib/scoring.test.ts` guards the invariants and runs in CI.

Results sync to the backend via `POST /assessment-profile`; `lib/use-assessment.ts`, `use-auth.ts`, `use-chosen-path.ts` hold the client state.

---

## 3. Backend

**`backend/`** — FastAPI 0.135.1 on Python 3.11, uvicorn 0.42, Pydantic 2.12.

### Module map

| Module | LOC | Responsibility |
|---|---:|---|
| `app/main.py` | 1535 | `create_app()` factory, all 39 route handlers, CORS, Sentry init |
| `app/match.py` | 343 | TF-IDF ranking engine + boosters |
| `app/social.py` | 324 | friendships, discover, compare, teamup, reports, blocks |
| `app/collab.py` | 224 | ALS collaborative filtering (serving side) |
| `app/advisor.py` | 206 | LLM route advisor, budget ledger, cache |
| `app/schemas.py` | 184 | Pydantic request/response models + enums |
| `app/verifier.py` | 178 | LLM candidate screening, `decide()` guardrail |
| `app/projects.py` | 170 | GitHub-sourced project recommendations |
| `app/mentors.py` | 125 | mentor matching |
| `app/auth.py` | 110 | JWT verification dependency |
| `app/settings.py` | 87 | env → `Settings`, `.env` loading |
| `app/db.py` | 34 | cached service-role Supabase client |

Entrypoints: `backend/main.py` re-exports `app` so `uvicorn main:app` keeps working; `backend/api/index.py` re-exports it for Vercel's Python runtime.

### Auth (`app/auth.py`)

Accepts **both** Supabase token families, with the token's own header selecting the path and each path permitting exactly one algorithm — so neither can be used to confuse the other, and `alg=none` is rejected on both:

- **ES256** — current signing-key projects. Public keys fetched from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` via a lazily-built `PyJWKClient` (PyJWT caches internally: one fetch per process, not per request).
- **HS256** — legacy projects and the test suite, verified against the static `SUPABASE_JWT_SECRET`.

The `sub` claim is the `auth.users.id` UUID and is the key for `public.students`. Any failure raises `401`, keeping route handlers free of JWT plumbing.

### Route table (39)

```
GET    /                              GET    /friends
GET    /health                        POST   /friends/{id}/accept
GET    /me                            DELETE /friends/{id}
POST   /students                      GET    /discover
POST   /assessment-profile            GET    /friends/{sid}/compare
GET    /timeline                      GET    /teamup/settings
POST   /advisor                       POST   /teamup/settings
POST   /sharing                       GET    /teamup/candidates
GET    /public/{handle}               POST   /teamup/interest
POST   /chosen-path                   POST   /report
GET    /match                         POST   /block
GET    /catalog                       GET    /missions
GET    /opportunities/{opp_id}        GET    /missions/completions
GET    /bookmarks                     POST   /missions/{id}/complete
POST   /bookmarks                     GET    /dismissals
DELETE /bookmarks/{opp_id}            POST   /dismissals
POST   /outcomes                      DELETE /dismissals/{opp_id}
GET    /outcomes                      GET    /pathways
POST   /friends                       GET    /projects
                                      GET    /mentors
```

### Settings (`app/settings.py`)

Plain Pydantic `BaseModel` read from `os.environ` — no `pydantic-settings` dependency. `python-dotenv` loads `backend/.env` with `override=False`, so real process env (Vercel, Render, CI) stays authoritative.

`_int()` treats unset, empty, *and* malformed values as "use the default" — because `os.getenv` returns `""` for a set-but-empty variable, which is exactly what a CI runner exporting an undefined secret produces.

Notable fields: `frontend_url` is comma-separated (multiple origins during a domain migration), exposed as `frontend_urls` for CORS. `advisor_per_student_daily=10`, `advisor_global_daily=150`, `advisor_cache_ttl_h=24`. `llm_api_base` defaults to DeepSeek.

---

## 4. Ranking pipeline

### 4.1 TF-IDF engine (`app/match.py`)

Pure stdlib — `math`, `re`, `collections` only. No numpy, no sklearn.

**Corpus construction.** Each opportunity becomes a document of `title + blurb + description + tags + field + type`. The student profile becomes a query of `interests + goals`. `_tokenize` lowercases, strips to `[a-z0-9+-]+`, drops a 25-word stopword set and single characters.

**Score:**

```
score = clip(0.5 * tfidf_cosine + boosters + collab, 0, 1)
```

**Boosters** (additive, capped at 1.0):

| Condition | Δ |
|---|---:|
| Opportunity field matches a student interest keyword (via `INTEREST_TO_FIELD`) | +0.15 |
| Student grade within `[grade_min, grade_max]` | +0.10 |
| Tag overlap (non-empty intersection) | +0.10 |
| `cost == 0` | +0.05 |

Each booster that fires contributes a clause to a human-readable `explanation` returned alongside the score. This is the product commitment: every ranking is defensible in one sentence.

### 4.2 Collaborative term (`app/collab.py`)

ALS matrix factorization over logged outcomes, `k = 8`, again pure stdlib — the linear algebra is a k×k Gaussian elimination, small enough to derive by hand.

- **Training** (offline, `scripts/train_als.py`): alternate closed-form least-squares solves for user and item rows until RMSE settles. Writes **item factors only** to `app/data/als_item_factors.json`. User factors are never shipped — derivable, and privacy-irrelevant to retain.
- **Serving** (request time): fold in the current student via one regularized least-squares solve of their outcomes against the fixed item factors, then predict per-opportunity.

Contribution is `COLLAB_WEIGHT * (cf - 0.5)`, bounded at **±0.075**. A student with no logged outcomes, or an absent trained model, gets exactly zero — nothing is invented for them.

### 4.3 Mentor matching (`app/mentors.py`)

Reuses the same TF-IDF/cosine machinery so both ranking surfaces behave consistently. Student query = `interests + goals`; mentor doc = `name + bio + flattened expertise`. Boosters: +0.15 when a mentor's expertise maps to a student interest's field enum (shared `INTEREST_TO_FIELD`), +0.05 for expertise breadth. `score = min(0.5 * tfidf + boosters, 1.0)`.

**pgvector status:** the schema already carries a `vector(384)` `bio_embedding` column and the supporting SQL functions (`20250711134901_meridian_core_schema.sql`). It is **not populated and not on the serving path** — swapping sparse TF-IDF for sentence-transformer embeddings is a drop-in the schema is waiting for, not something running today.

---

## 5. Data layer

**Supabase Postgres**, 22 migrations in `supabase/migrations/`, timestamped `20250621` → `20260822`.

Tables: `students`, `opportunities`, `matches`, `outcomes`, `bookmarks`, `dismissals`, `missions`, `mission_completions`, `pathway_nodes`, `pathway_edges`, `future_paths`, `latent_profiles`, `profile_history`, `behaviour_events`, `actions`, `mentors`, `mentor_sessions`, `friendships`, `blocks`, `reports`, `teamup_interest`, `advisor_calls`.

Migration highlights:
- `20250711134903_edge_weight_update` — the outcome→pathway-edge feedback rule.
- `20260816160000_opportunity_provenance` — `added_by` column; AI-promoted rows are stamped `'ai'`.
- `20260815160000_outcomes_idempotent` — safe outcome re-submission.
- `20260822090000_advisor_budget` — `advisor_calls`, the ledger/cache table.

`backend/tests/test_seed_sql.py`, `test_students_schema_drift.py`, and `test_postgrest_surface.py` apply static guards over the SQL and the PostgREST query chains, so schema drift fails CI rather than production.

---

## 6. Content pipeline

`.github/workflows/scrape.yml`, cron `17 16 * * *` (≈09:17 PT — deliberately off the hour, since on-the-hour crons queue behind everyone else's and get dropped). `concurrency: {group: scrape, cancel-in-progress: false}`, 90-minute timeout for a ~40-minute pass.

`backend/scripts/scrape_all.py` runs three stages, each isolated in a `try` so one failure never blocks the others:

```
scrape_reddit (475 LOC) ─┐
                         ├─► scripts/scraped/reddit_candidates.json ─► verify_and_import (131) ─► public.opportunities
scrape_devpost (141 LOC) ┘
```

### The verifier gate (`app/verifier.py`)

This replaces a human reviewer, so it is built to be strict:

- The model returns a **structured verdict, never prose**. It decides only whether a candidate is a real, current opportunity and extracts clean fields. It does not invent programs or deadlines.
- `decide()` is a **pure function with no network access**, applying three guardrails: `is_opportunity`, a confidence floor, and a usable external link. All three must clear for auto-promotion. This is the safety boundary and it is unit-tested (`tests/test_verifier.py`).
- Everything that fails stays in the pool for `scripts/review_candidates.py` (human triage).
- Auto-promoted rows carry `added_by='ai'`, so a bad batch is auditable and one `DELETE` away.

Provider is any OpenAI-compatible chat API (`LLM_API_BASE` / `LLM_MODEL` / `LLM_API_KEY`); NVIDIA NIM and DeepSeek both work.

**Candidate pool persistence.** The workflow commits `scripts/scraped/reddit_candidates.json` back to `main` with `[skip ci]`, then `git pull --rebase --autostash`. The pool is the scrapers' memory of what they've already seen — without it, every run rediscovers the same posts as new.

**Fail-fast on secrets.** A preflight step asserts `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `LLM_API_KEY` are all non-empty. Without Reddit credentials the scraper silently degrades to the unauthenticated endpoint and is rate-limited into returning nothing; without the LLM key the verifier exits cleanly and imports zero. Both failure modes otherwise look like "ran fine, found nothing."

*History: this was a launchd job (`com.northstar.reddit-scraper`) on one laptop. `StartCalendarInterval` cannot fire on a sleeping Mac, so no scrape happened on any day that machine was closed.*

---

## 7. Advisor (`app/advisor.py`)

Conversational exploration grounded strictly in the verified catalog. The model receives the student's deterministic profile (traits, field shares, goals) plus their matched opportunities as **numbered sources**, and must cite `[n]`.

Hard boundaries:
- **Never produces fit percentages or rankings.** That authority stays with `app/match.py`.
- Every response returns the source list so the UI can render "backed by" links.
- Instructed to state plainly when the catalog has nothing relevant.
- No `LLM_API_KEY` → `503`, and the frontend renders the feature as off.

**Budget as ledger + cache in one table.** `public.advisor_calls` holds one row per **billed** call and no row for a cache hit — so `count(rows)` literally means "credits spent." A cache hit is checked before the budget and never consumes quota. `cache_key()` hashes question + sources + model, so a catalog change invalidates the stale answer. `GLOBAL_PER_MINUTE = 20`, leaving headroom under the provider's 40 rpm free tier, which the nightly verifier shares.

---

## 8. Contract enforcement

The frontend/backend boundary is machine-checked rather than trusted:

```
backend/app/main.py
  └─ scripts/export_openapi.py  →  frontend/lib/api-schema.json
       └─ npm run gen:api (openapi-typescript)  →  frontend/lib/api-types.gen.ts
```

`backend/tests/test_openapi_contract.py` fails CI when the checked-in schema drifts from the live app.

---

## 9. CI and monitoring

### `ci.yml` — push/PR on `main`, `development`

**frontend:** `npm ci` → `npm run lint` → `npx tsc --noEmit` → `npm test` (vitest) → `npx next build`.
The real `next build` matters: `tsc --noEmit` does not exercise the App Router, so it will not catch a client-only import pulled into a server component, a bad route export, or a page that crashes while prerendering.

**backend:** `pip install -r requirements.txt` → `python -m py_compile main.py` → `python -m pytest -q`.
The suite runs **without Supabase credentials** — 14 test files covering the JWT layer, both ranking engines, the auth gate on every route, and static guards over the migrations and PostgREST chains:

```
test_advisor_budget  test_auth      test_collab           test_match
test_mentors         test_projects  test_openapi_contract test_postgrest_surface
test_routes          test_seed_sql  test_social           test_students_schema_drift
test_teamup          test_verifier
```

### `smoke.yml` — cron `0 */2 * * *`

Read-only, unauthenticated, against **production**:
1. `https://northstar.study` responds and mentions "northstar" — the custom domain, not the `.vercel.app` URL, since that's what students actually visit and what has DNS/cert/assignment to watch.
2. `GET /health` returns exactly `{"status":"ok"}`.
3. `GET /match` unauthenticated returns `401` or `403` — a `200` there means the auth gate fell off.

*Why 2 hours and not 30 minutes: GitHub never delivered 30-minute runs (measured gaps ran 30–70 min on shared runners), and on a private repo every job bills a full minute regardless of duration — 30 runs/day of a 10-second check spent ~900 of the 2,000 monthly minutes. Twelve runs/day costs ~360 and leaves room for the scrape. Alert latency is "within a couple of hours"; CI still gates every push.*

---

## 10. Deployment

| Target | Config | Notes |
|---|---|---|
| Frontend | Vercel project | `northstar.study` |
| Backend (primary) | `backend/vercel.json` + `api/index.py` | `rewrites: /(.*) → /api/index`, so FastAPI owns the full route table |
| Backend (fallback) | `backend/render.yaml` | Blueprint, Oregon, free plan, `healthCheckPath: /health`, `autoDeploy: true` |
| Backend (local/PaaS) | `backend/Procfile` | `uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}` |

Sentry is initialized on both sides **only when `SENTRY_DSN` is set** (`traces_sample_rate=0.0`), so local dev and CI run without it and without noise.

### Environment variables

```
# Browser-exposed (frontend/.env.local)
NEXT_PUBLIC_API_URL                  # unset ⇒ same-origin ⇒ every call 404s
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY

# Server-only (backend/.env)
SUPABASE_URL  SUPABASE_SECRET_KEY  SUPABASE_JWT_SECRET
FRONTEND_URL                         # comma-separated for CORS
GITHUB_TOKEN                         # /projects: 10 → 30 req/min
LLM_API_KEY  LLM_API_BASE  LLM_MODEL
ADVISOR_PER_STUDENT_DAILY  ADVISOR_GLOBAL_DAILY  ADVISOR_CACHE_TTL_H
SENTRY_DSN
REDDIT_CLIENT_ID  REDDIT_CLIENT_SECRET   # Actions secrets, scrape job only
```

---

## 11. Design invariants

Things that should survive refactors, and the reason each exists:

1. **Ranking stays explainable.** `match.py` is arithmetic, not a model. Every score ships with the sentence that justifies it. The ALS term is capped at ±0.075 precisely so it can never overturn an explanation.
2. **The advisor never ranks.** Exploration and authority are separate features on purpose.
3. **`decide()` stays pure and network-free.** It is the boundary between "an AI suggested this" and "students see this."
4. **AI-sourced rows stay stamped.** `added_by='ai'` is what makes a bad batch reversible.
5. **The auth gate is asserted in production, not just in CI.** The backend holds the service-role key; if `RequireUser` ever falls off a route, RLS will not catch it. Hence smoke check #3.
6. **Both engines are pure stdlib.** No numpy, no sklearn — a judge can be walked through every line, and the serverless cold start stays small.
7. **The candidate pool is committed.** It is state, not build output.

---

## 12. Naming

Code, `FastAPI(title="Northstar API")`, and the production domain say **Northstar**. The repo directory and pre-July planning docs (`docs/personal/meridian_cac_concept.md`, `docs/ARCHITECTURE.md`) say **Meridian**. Same project, renamed mid-build; the residue was never worth the churn.

Note that `docs/ARCHITECTURE.md` is a *planning* document from before the backend existed and describes intent and an authorship split, not the current implementation. Where the two disagree — e.g. it lists pgvector semantic matching, which is provisioned in the schema but unused at serving time (§4.3) — this file describes what is actually deployed.
