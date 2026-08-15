# The two-week engineering goal (2026-08-15 → 2026-08-29)

1. Build proof missions v1: a missions table keyed to archetypes, three
   to five concrete real-world missions per future path, and a
   completion flow that writes evidence onto the student record — the
   evolving profile becomes the product's spine, not a roadmap bullet.
2. Turn the record into a visible timeline: a profile history view that
   shows every synced assessment, mission completion, outcome, and
   dismissal as one chronological evidence stream, with shift tracking
   moved from localStorage snapshots to server-side history.
3. Ship readiness gaps + deadline routing (roadmap phase 2): compute the
   distance between the student's current profile and their chosen
   path's demands, then route them to the specific missions and
   deadline-bearing opportunities that close the gap.
4. Finish the Stripe-hardening list: idempotent outcome writes,
   OpenAPI-generated frontend types replacing the hand-mirrored
   schemas, Sentry on both apps, and a scheduled production smoke test
   that alerts within minutes when the live site breaks.
5. Build the catalog review tool: a maintainer view that renders the
   scraped candidate pool (1,920 and growing daily) with one-keystroke
   keep/drop/fix-field actions and writes keepers straight into the
   opportunities table — so weekly freshness costs twenty minutes, not
   an evening.
