# Code review checklist

Read in tier order. Tier 1 you must be able to explain cold, out loud, to a
judge pointing at any line. Tier 2 is prose wearing code's clothes — edit it
until it sounds like you. Tiers 3–4 are understand/skim.

## Tier 1 — algorithms (whiteboard-level understanding)

- [ ] `backend/app/match.py` — TF-IDF pipeline and the four boosters
      (+0.15 field, +0.10 grade, +0.10 tags, +0.05 free). Verify you can
      derive a score by hand for one opportunity.
- [ ] `frontend/lib/scoring.ts` — trait deltas → normalization by achievable
      maximum → cosine vs archetypes → safe/ambitious/unconventional
      selection rules. Check the three selection rules match what /futures
      shows.
- [ ] `frontend/lib/plan.ts` — the three generation rules (archetype spine,
      strongest/weakest trait bend, match targets), the award-guarantee
      (top 2 + best competition/scholarship), and the 30-day urgency window.
- [ ] `supabase/migrations/20250711134903_edge_weight_update.sql` — the
      outcome → edge-weight trigger and its deltas (accepted +0.10,
      completed +0.08, waitlisted +0.02, rejected −0.05, withdrew −0.03).
- [ ] `backend/app/mentors.py` — mentor ranking; how it reuses the matcher.
- [ ] `backend/app/auth.py` — HS256 verification, fail-closed behavior.
      Run `backend/tests/test_auth.py` and read what each test proves.

## Tier 2 — content that should sound like you (rewrite freely)

- [ ] `frontend/lib/plan.ts` — the five archetype spines, LEAN_IN and
      STRETCH action wording, voyage phrasing.
- [ ] `frontend/lib/outreach.ts` — the cold-email template. Send one to
      yourself; check it reads like a real student wrote it.
- [ ] `frontend/lib/assessment.ts` — the eight questions and their trait
      weights (these ARE the assessment; own every number).
- [ ] `frontend/lib/archetypes.ts` — archetype labels, summaries, trait
      vectors.
- [ ] Landing page copy (`frontend/app/page.tsx`) — hero, waypoints, footer.
- [ ] All empty-state and error copy across pages.

## Tier 3 — understand the mechanism, summarize is fine

- [ ] `frontend/app/globals.css` — the token system: how one file retokenizes
      the whole app (dark :root, .light override, shadcn semantic mapping).
- [ ] `frontend/components/decor/starfield.tsx` — three.js scene lifecycle:
      seeded placement, sprites, dispose-on-unmount, reduced-motion.
- [ ] `backend/scripts/scrape_reddit.py` — OAuth flow, filters, and why
      output goes to a review file instead of the database.
- [ ] `backend/app/main.py` — every route, its auth guard, CORS config.
- [ ] `frontend/lib/api.ts` — how the token rides every request.
- [ ] `frontend/app/map/page.tsx` — d3 force simulation, zoom/drag handlers.
- [ ] Backend tests — skim each `backend/tests/test_*.py`; know what CI
      proves and what it cannot (no live DB).

## Tier 4 — skim only

- [ ] `frontend/components/ui/*` — generated shadcn primitives (Base UI).
- [ ] `frontend/components/motion/*` — vendored motion-primitives (MIT;
      file headers note origin and local adaptations).
- [ ] Config: `vercel.json` ×2, `components.json`, `pytest.ini`, CI workflow.

## Recently added (sort into tiers after review)

- [ ] TIER 1 candidate: interest-field bonus + localized "ambitious" rule in
      `frontend/lib/scoring.ts` — own the numbers (+4/field, cap +8, top-half
      stretch pool) (016eaf2).
- [ ] TIER 2 candidate: seven new archetypes and their trait vectors in
      `frontend/lib/archetypes.ts`, plus their plan spines in
      `frontend/lib/plan.ts` — every summary and weight should be yours (016eaf2).

- [ ] Alternating landing pathway (grid placement logic in
      `frontend/app/page.tsx`) and textured sky — banded/cratered canvas
      textures, four galaxies, moonlet in
      `frontend/components/decor/starfield.tsx` (0a32cb1).

- [ ] `frontend/components/decor/voyage.tsx` — shared Planet/Ship glyphs
      (9485943).
- [ ] Landing scroll journey + plan voyage layout (9485943).
- [ ] Theme system: `next-themes` wiring in `app/layout.tsx`,
      `components/theme-toggle.tsx` (cd9f2a8).
