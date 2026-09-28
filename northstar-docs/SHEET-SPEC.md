# Curated opportunity sheet — what the importer needs

The contract for `backend/scripts/import_opportunity_sheet.py`. Written after
importing `stem_database_2000_with_timing.xlsx`, where **24 of 2,000 rows** made
it into the catalog. This documents exactly why, so the next version of the sheet
converts at a far higher rate.

The importer does not trust the sheet, and should not: it fetches each row's page
and reads it. The sheet's job is to get it **to the right page** and tell it what
to look for. Almost every loss below is a row that never reached a page worth
reading.

---

## The one change that matters most

**Put a `website` column on the Opportunities sheet.**

Sheet 2 (`Opportunities 1001-2000`) has 436 US/Global high-school rows, with the
best non-CS spread in either file — Science Research, Biomedical, Engineering,
Science Fair. **Every one is unimportable, because there is no URL column.**
`decide()` refuses any row without a destination, on purpose: a listing a student
cannot click is worse than one they never saw.

One column unlocks ~420 rows. Nothing else on this page comes close.

---

## Required columns

| Column | Notes |
| --- | --- |
| `name` | Becomes `title`. The programme's own name, not a description of it. |
| `website` | **Required.** See *Deep-link, do not home-link* below. |
| `organizer` | Becomes `host`. |
| `country` | Only `United States` and `Global` are imported today. |
| `level` | Must contain `HS` or `Open` to be imported. `grade_min`/`grade_max` below are better. |
| `category` | Mapped to one of: `cs biology math physics engineering interdisciplinary design business humanities health`. Anything else lands as `interdisciplinary`. |
| `entry_type` | Mapped to one of: `program scholarship competition mentorship internship volunteer journal`. |
| `scope` | `International` / `National` / `Regional` / `State`. See *State rows* below. |

## Deep-link, do not home-link

This is the second-biggest loss. A URL must point at **the page that describes
the programme**, not the organisation's front door. Real refusals from the run:

> *"The page is AAPT's general homepage and contains no information about PhysicsBowl"*
> *"The page text contains only the single word 'Bebras'"*
> *"The page is raw CMS/translation configuration JSON"*

`aapt.org` cannot confirm PhysicsBowl exists. `aapt.org/programs/physicsbowl` can.
If only the homepage is known, leave `website` blank — a blank is a to-do, a
homepage is a row that costs a page fetch and an LLM call to reject.

Also avoid: pages that render client-side. `igem.org`, `spaceappschallenge.org`,
`arml.com`, `leetcode.com/contest/` and `acs.org` all returned no readable text.
If a programme's only page is a JavaScript app, note it — those need a different
tool, not a better row.

## State and regional rows

**250 rows were skipped without being read.** The sheet's own README says state
rows are rounds of national programmes (TSA, HOSA, Science Olympiad, MATHCOUNTS,
Envirothon, FTC) — but every one carries the **national** URL. So
`TSA State Conference – Alabama` points at `tsaweb.org`, which describes TSA and
says nothing about Alabama, and the model correctly refuses all fifty.

Two ways to fix, either is fine:

1. **Give each state row its own URL** (`tsa-alabama.org`, the state affiliate
   page). Then they import, and a student in Alabama gets their actual round —
   which is more useful than the national row.
2. **Drop them and keep one national row per programme**, with a note that state
   qualifying rounds exist. Fewer rows, no loss of truth.

What does not work is fifty rows sharing one URL.

## Columns worth adding

| Column | Why | Example |
| --- | --- | --- |
| `grade_min`, `grade_max` | US grade numbers. `level: HS` becomes a 9–12 guess, and that guess has been wrong in costly ways — AMC 10 is **6–10**, and a row listed 9–12 sends juniors and seniors to something that will reject them. | `6`, `10` |
| `cost_usd` | Entry fee, `0` if free. The page reading found USAAAO's $30 fee; most pages bury it. The site claims "more than four in five free", and that claim is checked nightly. | `0`, `30` |
| `entry_route` | One of `apply qualify advance nominate teacher`. You often know this and the page often obscures it. Drives the roadmap's verb — `Qualify for USAMO`, not `Apply to USAMO`. | `teacher` |
| `eligibility_url` | Where the rules actually live, if not the main page. | |
| `state` | Two-letter code for state rows, so they can be matched to a student's location. | `AL` |

`entry_route` note: `apply` means an individual student can enter unaided.
Anything needing a school team, an adult registration, a qualifying score, a prior
round or a nomination is **not** `apply`. This is the field that decides whether
the plan tells a student to do something they can actually do.

## Timing

Keep `typical_deadline`, `typical_event_timing` and `timing_basis` as they are —
the graded basis is genuinely useful, and the honesty in the README is right.

How they are used: a month is parsed **only** when `timing_basis` says "known
typical annual cycle", and it goes to `recurrence_month`, never to `deadline`.
`recurrence_verified_at` stays NULL because no human confirmed the programme's
site. A real `deadline` is only ever taken from the page itself, and only if it is
in the future.

Two things would raise the 11% parse rate on sheet 1:

- **Name a month** where one is known: `Application ~mid-December` parses,
  `Application ~spring` does not.
- **Do not put gate information in the deadline field.** 886 rows read
  `Via national team selection`, which is not a deadline — it is
  `entry_route: qualify`. Put it there instead and both fields become useful.

## Conversion, measured

From `stem_database_2000_with_timing.xlsx`:

| Stage | Competitions | Opportunities |
| --- | --- | --- |
| Rows | 1000 | 1000 |
| US or Global | 564 | 805 |
| …high-school-inclusive | 429 | 436 |
| …with a URL | 307 | **0** |
| …not a state/regional template | **57** | — |
| Reached a readable page | 48 | — |
| **Written to the catalog** | **24** | **0** |

Refusals and their reasons are recorded in
`backend/scripts/scraped/sheet_import_ledger.json`, so a rerun does not re-pay
for the same verdict and the rejections can be read as feedback on the sheet.

## Summary of asks

1. `website` on the Opportunities sheet — unlocks ~420 rows.
2. Deep links, not homepages. Blank beats a front door.
3. Fix or drop the state rows; do not give fifty rows one URL.
4. Add `grade_min`, `grade_max`, `cost_usd`, `entry_route`.
5. Move "via national selection" out of `typical_deadline` and into `entry_route`.
6. Name months where known.
