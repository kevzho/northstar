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
```

## Environment

Copy `frontend/.env.example` to `frontend/.env.local` and fill in real keys
(see `docs/supabase-setup.md` for where to find each value).

## Deploy

### Frontend (Vercel)

```bash
cd frontend
vercel          # produces a preview URL
vercel --prod   # production deployment (after `vercel link`)
```

Set these env vars in the Vercel project dashboard (or via `vercel env add`):

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`
- `SUPABASE_URL` (server-only, no `NEXT_PUBLIC_` prefix)
- `SUPABASE_SECRET_KEY`
- `SUPABASE_JWT_SECRET`
- `FRONTEND_URL` (set to the production Vercel URL — also enforces CORS)

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
