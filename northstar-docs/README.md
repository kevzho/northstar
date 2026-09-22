# northstar-docs

Local-only architecture reference. **Gitignored on purpose** — this folder is scratch documentation, not a repo deliverable. Nothing here is imported, built, or deployed.

| File | For | Read it when |
|---|---|---|
| [PLAIN-ENGLISH.md](PLAIN-ENGLISH.md) | Non-engineers, judges, a demo walkthrough | You need to explain what Northstar is made of without assuming a CS background |
| [TECHNICAL.md](TECHNICAL.md) | You, six months from now | You need exact modules, scoring formulas, env vars, cron schedules, or deploy topology |

Both were written against commit `3746d27` (2026-08-24) by reading the tree directly.

**Refresh these when:** the deploy topology changes, the scoring pipeline in `backend/app/match.py` or `frontend/lib/scoring.ts` changes, a workflow schedule changes, or a route is added or removed. A stale architecture doc is worse than none.
