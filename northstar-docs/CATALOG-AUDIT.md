# Catalog audit record

Repo documentation, not website copy. This is the evidence behind the one
sentence the landing page makes public: *"every listing is checked against the
program's own website, and anything that does not hold up comes down."*

It sits here rather than on the site because a landing page is the wrong place
for a defect log — a visitor needs to know the practice exists, not read the
changelog of it. It is not secret: anyone who clones the repo gets it, and a
judge reading it is the point.

Useful when writing the Congressional App Challenge submission, where
describing the verification process *is* appropriate, and when someone asks why
the shelf is 53 rows rather than thousands.

## Scope

All 35 hand-authored rows from `20260815090000_seed_catalog.sql` were checked
against each program's own website on 2026-09-23, and every flagged row was
re-checked by a second reviewer.

**Result: 1 of 35 accurate as listed.** That ratio is the reason the project
does not hand-author rows any more, and the reason "extremely large" and
"verified" are treated as being in tension.

## 1. Retired — not real as listed (9 rows)

`backend/scripts/retire_dead_opportunities.py`

Retirement is a stamp (`retired_at`), never a DELETE: `outcomes`, `bookmarks`,
`matches` and `dismissals` all cascade from `opportunities(id)`, so deleting
would destroy student history, and the row is also the evidence of why it went.

Representative cases:

| Row | Why |
| --- | --- |
| Gates Millennium Scholars | Program ended; final cohort was the class of 2016 |
| Broadcom MASTERS | Renamed in 2023, and it is a **middle** school competition |
| NSF REU "High School Track" | **Fabricated** — no such track exists |
| CERN Summer Student Program | Requires enrolment in a bachelor's or master's degree |
| 2 further rows | **Teacher** professional development listed as a student opportunity |

## 2. Eligibility corrected (22 rows)

`backend/scripts/correct_opportunity_eligibility.py`

**Ten grade ranges**, all wrong in the direction that costs a student a year:

- RSI listed 11–12, takes juniors only
- MIT PRIMES listed 9–12, takes sophomores and juniors
- Stanford Summer Institutes listed 9–12, is 8–11
- BWSI listed 12–12 and explicitly does **not** accept current seniors — the
  one grade it was offered to
- Math Prize for Girls, Simons, NASA HAS, SEES, Davidson, Congressional App
  Challenge — each off at one or both ends

**Fifteen entry routes.** These rows carried an application deadline for
something you cannot apply to, which is worse than a wrong date: a student who
waits for the deadline does nothing at all.

| Gate | Rows | Meaning |
| --- | --- | --- |
| `qualify` | USAMO, USAPhO, USNCO, USABO, Math Prize for Girls, BWSI | Entry is by exam score or admissions ladder |
| `teacher` | Lemelson-MIT, FRC, FTC, VEX, TARC, Science Olympiad, AMC | An adult registers a team or a test site |
| `advance` | ISEF | You advance from an affiliated regional fair |
| `nominate` | Simons | Needs a recommendation |

`opportunities.entry_gate` (`20260925140000_entry_gate.sql`) carries this, and
`app/roadmap.py` reads it to pick the step verb — without it the sequencer
emitted "Apply to USAMO".

## 3. Duplicates retired (8 rows)

`backend/scripts/dedupe_opportunities.py`

`unique(title, host)` cannot see the same programme entered twice with the host
spelled differently, and both seed migrations included the well-known ones.

- By host spelling: RSI, ISEF, Conrad, Simons, FRC
  (e.g. `FIRST` vs `FIRST (For Inspiration and Recognition…)`)
- By second name: NASA SEES = "STEM Enhancement in Earth Science", Regeneron
  STS = "Regeneron Science Talent Search", and the USAPhO summer camp — which
  is not a programme you enter at all, but where the top ~20 USAPhO scorers are
  invited

The richer row survives: a real deadline beats a longer description beats age.

## 4. Expired listings retired (100 rows)

`backend/scripts/expire_opportunities.py`, now a step in the daily scrape.

Importing only ever added. Of 195 live rows, **123 had a deadline that had
already passed**, and `/catalog` sorted deadline-ascending — so browse opened on
the single most expired row in the catalog.

One-off scraped events (`added_by = 'ai'`) are retired automatically once their
deadline passes, because a closed hackathon will not reopen. Curated annual
programmes are **reported and never touched**: a past deadline on RSI means this
cycle closed, and inferring next year's date from last year's is precisely the
fabrication `recurrence_*` was added to prevent.

## Net effect

| | Before | After |
| --- | --- | --- |
| Live rows | 195 | 86 |
| High-school shelf | 61 claimed | 53 (49 hosts, 9 fields) |
| Free to apply | — | 45 of 53 |
| Expired rows shown | 123 | 0 |

## Keeping the public claim true

The landing page states the shelf size, the field count and the free share.
Those rot on their own, and have three times:

1. Nine rows retired → the page still said 70
2. The free-share guard shipped without a raw-count check → false within the hour
3. Duplicates and expiries retired → the page still said 61

`backend/tests/test_impact_claims.py` bounds the claim from above against the
seed migrations (CI has no credentials). `backend/scripts/check_impact_claims.py`
checks it against **production**, and runs in the daily scrape job — the same
job that changes the numbers.
