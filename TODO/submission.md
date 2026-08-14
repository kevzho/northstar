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
- [ ] **Demo script rewrite in your voice** — draft at docs/DEMO_SCRIPT.md.
      Update it for the new landing (scroll journey, theme toggle) and the
      plan voyage; the route order and claims are otherwise still verified.
- [ ] **Record the 2:00 video** against the deployed site, 1440px, signed
      out at start, per the script's pre-record checklist.
- [ ] **AI disclosure finalized** — docs/CAC_AI_DISCLOSURE.md has drafts;
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

- [ ] Verify all 35 seed opportunities still have live URLs and real
      deadlines (a judge will click one).
- [ ] Read every mentor bio once (they're seed data — make sure none reads
      oddly).
- [ ] Landing footer line and all judge-visible copy: final read.
