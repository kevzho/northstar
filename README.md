# Northstar

**A STEM opportunity catalog and planner for US high school students who don't have a college counselor.**

Live at **[northstar.study](https://northstar.study)** · A project of [Minorities in STEM](https://northstar.study), a fiscally sponsored non-profit · Apache-2.0

---

Research internships, olympiads and scholarships mostly reach students whose
families already know the names. Northstar is an attempt to close that gap with
software: a hand-verified catalog of **361 opportunities** (353 of them free to
apply to, 351 open to a 10th grader), and a sequenced plan telling a student
what to learn, build and publish *before* an application is worth sending.

What makes it different from a list of links is that it is built to refuse:

- **The language model never ranks anything.** Scores come from a deterministic
  TF-IDF engine with a semantic retrieval supplement. Every match carries a
  reason a student can read and argue with. The model writes prose and
  classifies candidates; it has no authority over what appears where.
- **Nothing enters the catalog unverified.** Scraped candidates pass a verifier
  that may only classify, never invent a programme or a deadline. Free-resource
  claims carry a verbatim quote from the source page.
- **Dead programmes are retired, never deleted.** Rows get a `retired_at` stamp
  and a reason, so a student can see what changed. A 404 alone does not retire
  anything — a moved deep link is not a dead programme.
- **Entry gates are recorded honestly.** "Open to all" usually isn't: 40 of the
  361 need a teacher nomination or a qualifying round first, and the card says
  so.

## Architecture

```
northstar.study              northstar-api               Supabase
Next.js 16 · React 19   →    FastAPI · Python 3.11   →   Postgres + pgvector
Vercel                       Vercel (root: backend/)     27 tables, RLS on
                                      ↓
                             NVIDIA NIM (OpenAI-compatible)
                             nemotron-3.5-bolt-e4b
```

The browser never queries a table directly. Every read and write goes through
the API on the service-role key, which is what lets row-level security deny all
client access outright rather than trying to express the rules twice.

| Module | What it does |
| --- | --- |
| `backend/app/match.py` | TF-IDF scoring over the student profile. Sole authority on ranking. |
| `backend/app/embeddings.py` | pgvector semantic retrieval, supplements TF-IDF. |
| `backend/app/collab.py` | ALS matrix factorization, hand-implemented. Stays out of ranking until a student has logged outcomes. |
| `backend/app/roadmap.py` | Sequences steps learn → build → publish → apply, on grade progression. |
| `backend/app/branch_generation.py` | Breaks one plan step into the moves inside it, recursively. |
| `backend/app/verifier.py` | Screens scraped candidates. May classify, may not invent. |
| `backend/app/robots.py` | RFC 9309 robots.txt, fails closed on 5xx. |
| `backend/app/link_health.py` | alive / dead / moved. Only DNS death retires a row. |
| `backend/app/limits.py` | DB-backed sliding-window rate limits, per action. |
| `backend/scripts/` | Scrapers and maintenance jobs. `scrape_all.py` runs the daily refresh. |

**Tests:** 451 backend (pytest, no Supabase credentials needed) and 99 frontend
(vitest). CI runs lint → typecheck → both suites → build on every push.

## Quick start

Requires Node 20, Python 3.11 and a Supabase project.

```bash
git clone https://github.com/kevzho/northstar.git
cd northstar
```

**Database** — apply the schema first; signed-in routes fail without it.

```bash
supabase link --project-ref <your-project-ref>
supabase db push          # applies supabase/migrations/ in order
```

This creates every table, RLS policy and index, and seeds the catalog.

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # fill in the values below
uvicorn app.main:app --reload     # http://localhost:8000
pytest -q                          # 451 tests, no credentials needed
```

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev               # http://localhost:3000
```

## Configuration

Two files, both gitignored.

**`frontend/.env.local`** — read by the browser, so nothing secret belongs here.

| Variable | Notes |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Required. Without it `lib/api.ts` falls back to `""` and every call hits the Next.js server instead of FastAPI. |
| `NEXT_PUBLIC_SUPABASE_URL` | Project Settings → API |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | The `anon` key, same page |

**`backend/.env`** — loaded by `app/settings.py`; real process env wins, so the
file is ignored in hosted environments.

| Variable | Notes |
| --- | --- |
| `SUPABASE_URL` | Project Settings → API |
| `SUPABASE_SECRET_KEY` | The `service_role` key. **Bypasses RLS — backend only, never in the frontend project.** |
| `SUPABASE_JWT_SECRET` | Project Settings → API → JWT Settings |
| `FRONTEND_URL` | Must match the backend CORS allow-list |
| `LLM_API_BASE` | Optional. Defaults to `https://integrate.api.nvidia.com/v1` |
| `LLM_API_KEY` | Optional. Without it the advisor returns 503 and no profile embeddings are written; everything else works. |
| `LLM_MODEL` | Optional. Defaults to `nvidia/nemotron-3.5-bolt-e4b` |

## Deploying

Both projects deploy from `main` via Vercel's GitHub integration. The backend
project uses root directory `backend`, so **`vercel --prod` from inside
`backend/` fails** — Vercel applies the root directory on top of what you
upload and looks for `backend/backend`. Push to `main`, or redeploy from the
dashboard.

Confirm which build is actually answering before drawing conclusions about a
backend change:

```bash
curl -s https://northstar-api-theta.vercel.app/health
# {"status":"ok","commit":"e944c9b","semantic":"available",
#  "advisor":"available","model":"nvidia/nemotron-3.5-bolt-e4b"}

git rev-parse --short=7 HEAD    # must match "commit"
```

`semantic` and `advisor` report whether those features can actually *run*, not
whether their modules imported — both need `LLM_API_KEY`, and a health check
that goes green on the outage it exists to catch is worse than none.

`backend/render.yaml` is an unused fallback for a non-serverless host.

## Contributing

Issues and pull requests are welcome. Before opening a PR:

```bash
cd backend  && pytest -q
cd frontend && npm run lint && npx tsc --noEmit && npx vitest run && npm run build
```

Two things CI enforces that are easy to trip over:

- `backend/app/spines.py` and `frontend/lib/api-schema.json` are **generated**.
  Run `python scripts/sync_spines.py` and `python scripts/export_openapi.py`
  rather than editing them.
- Scrapers must respect `robots.txt` via `app/robots.py`, and anything entering
  the catalog must go through `app/verifier.py`.

If you are adding to the catalog, the bar is that a claim can be checked: a
real URL, a real deadline, and an entry gate that reflects what the programme
actually requires.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
