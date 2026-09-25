# northstar-docs

Architecture reference. **These files ship with the repo** — unlike `docs/`, this folder is tracked, so anyone who clones Northstar gets them. Nothing here is imported, built, or deployed; it is documentation, and it is meant to be read.

| File | For | Read it when |
|---|---|---|
| [PLAIN-ENGLISH.md](PLAIN-ENGLISH.md) | Non-engineers, judges, a demo walkthrough | You need to explain what Northstar is made of without assuming a CS background |
| [TECHNICAL.md](TECHNICAL.md) | You, six months from now | You need exact modules, scoring formulas, env vars, cron schedules, or deploy topology |
| [CATALOG-AUDIT.md](CATALOG-AUDIT.md) | You, a judge, a skeptic | You need the evidence behind the landing page's claim that listings are verified — what was wrong, what was removed, and why the shelf is 53 rows and not thousands |

Both were written against commit `3746d27` (2026-08-24) by reading the tree directly, and refreshed 2026-09-22 after a security and consistency pass.

**Refresh these when:** the deploy topology changes, the scoring pipeline in `backend/app/match.py` or `frontend/lib/scoring.ts` changes, a workflow schedule changes, or a route is added or removed. A stale architecture doc is worse than none.
