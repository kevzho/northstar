# Northstar

Personalized opportunity map for high school students.

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
pytest -q                   # 67 tests, no Supabase credentials needed
```

## Environment

Two files, both gitignored. `frontend/.env.example` documents every variable.

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

See `docs/supabase-setup.md` for where each value lives in the dashboard.

## Deploy

### Frontend (Vercel)

```bash
cd frontend
vercel          # produces a preview URL
vercel --prod   # production deployment (after `vercel link`)
```

Set these env vars in the Vercel project dashboard (or via `vercel env add`):

- `NEXT_PUBLIC_API_URL` — the deployed backend URL, e.g.
  `https://northstar-api.onrender.com`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`

Those three are all the frontend reads. Do **not** put `SUPABASE_SECRET_KEY` or
`SUPABASE_JWT_SECRET` in the Vercel project — nothing in `frontend/` uses them,
and the service-role key bypasses row-level security. They belong only in the
backend host's dashboard, below.

### Backend (Render)

The repo includes a Render Blueprint at `backend/render.yaml`. Import the repo
in the Render dashboard and the blueprint auto-configures the service.

For Railway instead:

```bash
cd backend
railway up
```

Required env vars in the provider dashboard:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`
- `SUPABASE_JWT_SECRET`
- `FRONTEND_URL` (the production frontend URL — matches backend CORS allow-list)
