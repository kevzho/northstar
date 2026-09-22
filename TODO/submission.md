# Submission checklist — Congressional App Challenge

## Blocking (only you can do these)

- [ ] **Authenticated smoke test on the live site**: sign in (magic link or
      Google), complete onboarding, confirm the dashboard populates with
      ranked matches. This is the one untested link in the deployed stack.
- [ ] **Seed the demo account in the same session**: take the assessment,
      chart a path, log one "accepted" outcome (fires the edge-weight
      trigger for the demo).
- [ ] **Deploy latest main** (or confirm Vercel git integration is doing it)
      — the live site must match what the video shows.
- [ ] **Demo script rewrite in your voice** — draft at docs/DEMO_SCRIPT.md
      (local only; `docs/` is gitignored and is not in a clone).
      Update it for the new landing (scroll journey, theme toggle) and the
      plan voyage; the route order and claims are otherwise still verified.
- [ ] **Record the 2:00 video** against the deployed site, 1440px, signed
      out at start, per the script's pre-record checklist.
- [ ] **AI disclosure finalized** — docs/CAC_AI_DISCLOSURE.md has drafts
      (local only; `docs/` is gitignored). Decide where the final text ships,
      because right now it ships nowhere;
      make it specific: algorithms designed/validated by you; shadcn/ui
      component base; AI-assisted implementation reviewed file-by-file
      (that's what TODO/code-review.md proves). Rename Meridian → Northstar
      in the "stronger version" paragraph.
- [ ] **Judge-prep dry run**: answer the seven questions in the disclosure
      doc out loud, plus "walk me through match.py."

## Operational

- [ ] **Seed the live catalog**: run `supabase db push` (applies
      20260815090000_seed_catalog.sql — the live opportunities table was
      found EMPTY on 2026-08-15; nothing works signed-in until this runs).
      The migration now also creates the unique indexes that the repaired
      history claimed but never ran (005's title+host index).
- [ ] **Verify the edge-weight trigger actually exists** (migration 004 was
      also only 'repair-marked'): during the authenticated smoke test, log
      one outcome and confirm a pathway_edges weight changed. If nothing
      changes, the 004 trigger needs the same treatment as 005.
- [ ] **Train the ALS model**: after seeding, run
      `cd backend && .venv/bin/python scripts/train_als.py`, review the
      printed report, and commit `backend/app/data/als_item_factors.json`
      so the deployed backend ships the model (24e8ded).

- [ ] Reddit scraper credentials: create the script app at
      reddit.com/prefs/apps, add REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET to
      backend/.env, run one scrape, review candidates.
- [ ] Free disk space before recording (~/Library/Caches held ~12 GB:
      Google 5.4 GB, Spotify 1.8 GB).
- [ ] Freeze main once the video is recorded — further work goes on a
      branch so the live site never drifts from the recording.
- [ ] Optional: phone glance at the signed-in dashboard (everything
      unauthenticated is already mobile-verified).

## Content quality passes

- [ ] Verify the 68 seeded opportunities still have live URLs and real
      deadlines (a judge will click one). 31 of the 35 dated rows were
      already past as of 2026-09-21 — that is the blocker, not the URLs.
- [ ] Landing footer line and all judge-visible copy: final read.

(The mentor-bio pass is gone: the 25 seeded mentors were invented people at
reserved `.example` addresses and were removed in
`20260922090000_remove_placeholder_mentors.sql`. The directory is empty until
real mentors record a `consented_at`.)
