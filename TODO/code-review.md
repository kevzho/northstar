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

- [ ] TIER 1: `backend/app/collab.py` — the ALS implementation. Be able to
      derive the ridge solve (Σ v vᵀ + λI)x = Σ r·v and explain fold-in,
      the rating scale, and why the blend is centered and capped (24e8ded).
- [ ] TIER 1: the blend in `backend/app/match.py` (COLLAB_WEIGHT 0.15,
      ±0.075 cap) and the outcomes fetch in `main.py` /match (24e8ded).
- [ ] TIER 3: `backend/scripts/train_als.py` — synthetic cohort rule and
      artifact provenance fields (24e8ded).
- [ ] `backend/tests/test_collab.py` — read what each of the 8 tests
      proves (24e8ded).

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

- [ ] TIER 3: flat button variants in `components/ui/button.tsx` — why
      outline inverts on hover, and the `nativeButton={!props.render}`
      fix for link-rendered buttons (7e64414).
- [ ] TIER 3: `--radius: 0` in `app/globals.css` flattens every card,
      input, and badge — check no component depended on rounding (7e64414).
- [ ] Know why light mode "didn't work": stale dev server serving CSS
      from before `.light` existed — restart the dev server after theme
      CSS changes (7e64414).

- [ ] TIER 1: proportional field boost in `backend/app/match.py` — own
      the 0.25 × share/100 formula, the flat-0.15 fallback, and the
      bookmark nudge cap (0.02/bookmark, max 0.06) (72b36bb).
- [ ] TIER 1: field-interest scoring in `frontend/lib/scoring.ts` —
      share-of-total + largest-remainder rounding (always sums to 100),
      and the leadingFields half-the-leader rule (72b36bb).
- [ ] TIER 2: the six field-signal questions (q9-q14) in
      `frontend/lib/assessment.ts` — every field weight should be yours
      (72b36bb).
- [ ] TIER 3: `backend/app/projects.py` — GitHub query qualifiers encode
      approachability; ranking is a visible sum (72b36bb).
- [ ] TIER 3: dismissals flow (migration → /dismissals routes → 'Not for
      me' on cards → excluded from /match) and the assessment-profile
      sync endpoint (72b36bb).
- [ ] Read `frontend/lib/scoring.test.ts` + the 6 new match tests — these
      are the invariants CI now enforces on every push (72b36bb).

- [ ] TIER 1: readiness gap math in `components/MissionBoard.tsx` —
      archetype traits are 0-10, student traits 0-100; own the ×10
      normalization and the top-2 gap rule (84f2bb3).
- [ ] TIER 2: all 36 mission descriptions in
      `supabase/migrations/20260815140000_proof_missions.sql` — these are
      product voice; every mission should sound like you (84f2bb3).
- [ ] TIER 3: /timeline aggregation in `backend/app/main.py` (field
      deltas between consecutive profile_history rows) and the
      no-op-skip on identical sync snapshots (84f2bb3).
- [ ] TIER 3: the OpenAPI contract loop — export_openapi.py →
      api-schema.json → gen:api → test_openapi_contract.py; know the
      regeneration command when the drift test reds (84f2bb3).
- [ ] Run `backend/scripts/review_candidates.py` once for real — the
      review session IS the fresh catalog (84f2bb3).
