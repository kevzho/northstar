# Northstar

Personalized opportunity map for high school students. A project of Minorities
in STEM, a fiscally sponsored non-profit.

**[AI-USE.md](AI-USE.md) — how AI was used to build this, what I designed, and
what this project does not do.** Read that first if you are evaluating the
submission.

## Development

### Frontend

```bash
cd frontend
npm install      # if not already
npm run dev      # http://localhost:3000
```

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload   # http://localhost:8000
pytest -q                   # 181 tests, no Supabase credentials needed
```

### Database

The API reads and writes Supabase, so a fresh clone needs the schema applied
before any signed-in route works. From the repo root, with the Supabase CLI
installed and the project linked:

```bash
supabase link --project-ref <your-project-ref>
supabase db push            # applies supabase/migrations/ in order
```

That creates every table, row-level-security policy and index, and seeds the
opportunity catalog (68 curated rows). Without it, `GET /me` and `GET /match`
return errors and the dashboard stays empty.

## Environment

Two files, both gitignored. `frontend/.env.example` ships with the repo and
documents the variables both sides read; copy the relevant half into each.

**`frontend/.env.local`** — read by the browser:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://<project>.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=<anon key>
```

`NEXT_PUBLIC_API_URL` is required. Without it `lib/api.ts` falls back to `""`
and every API call is issued against the Next.js server instead of FastAPI.

**`backend/.env`** — loaded by `backend/app/settings.py`; process env wins, so
this file is ignored on Render/Railway:

```
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SECRET_KEY=<service-role key>
SUPABASE_JWT_SECRET=<JWT secret>
FRONTEND_URL=http://localhost:3000
```

Where to find each value in the Supabase dashboard: `SUPABASE_URL` and
`NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` are under Project Settings → API (the
publishable key is the `anon` key). `SUPABASE_SECRET_KEY` is the `service_role`
key on the same page — it bypasses row-level security, so it belongs only in
the backend's environment, never in the frontend project.
`SUPABASE_JWT_SECRET` is under Project Settings → API → JWT Settings.

## Deploy

### Frontend (Vercel)

```bash
cd frontend
vercel          # produces a preview URL
vercel --prod   # production deployment (after `vercel link`)
```

Set these env vars in the Vercel project dashboard (or via `vercel env add`):

- `NEXT_PUBLIC_API_URL` — the deployed backend URL, e.g.
  `https://northstar-api-theta.vercel.app`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`

Those three are all the frontend reads. Do **not** put `SUPABASE_SECRET_KEY` or
`SUPABASE_JWT_SECRET` in the Vercel project — nothing in `frontend/` uses them,
and the service-role key bypasses row-level security. They belong only in the
backend host's dashboard, below.

### Backend (Vercel)

Production runs the FastAPI app as a Vercel serverless function:
`backend/vercel.json` rewrites every path to `backend/api/index.py`, which
re-exports `app` from `backend/app/main.py`.

```bash
cd backend
vercel --prod
```

`backend/render.yaml` is kept as an unused fallback for a non-serverless host;
nothing currently deploys from it, and no frontend environment points at
Render.

Required env vars in the Vercel project for the backend:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`
- `SUPABASE_JWT_SECRET`
- `FRONTEND_URL` (the production frontend URL — matches backend CORS allow-list)
