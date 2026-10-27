"""
Run every scraper into the shared candidate pool, then verify and import.

Each source is isolated so one failing never blocks the others -- but a
failure is REPORTED and the process exits non-zero. It did not used to.

Why that mattered: on 2026-08-26 the configured model
(meta/llama-3.1-70b-instruct) reached end of life, and every verifier call
began returning HTTP 410. verify_and_import logged each failure and moved
on; this module caught the stage error and printed a traceback; the workflow
then committed the refreshed candidate pool and exited 0. The run was green
every single day. The pool grew from 2,683 to 8,864 candidates while the
catalog imported nothing for four weeks, and nothing anywhere said so.

The rule now: scrapers are allowed to fail softly (a subreddit 500s, Devpost
changes markup) because partial data is still data. The verify+import stage
is not -- if it cannot judge anything, the daily loop did not happen, and
the workflow should go red so someone finds out the same day.

Usage:
    cd backend && .venv/bin/python scripts/scrape_all.py
"""

from __future__ import annotations

import sys
import traceback

import embed_catalog
import embed_students
import scrape_codeforces
import scrape_ctftime
import scrape_devpost
import scrape_pathways
import scrape_reddit
import refresh_deadlines
import check_links
import import_resources
import scrape_openstax
import scrape_reddit_resources
import scrape_sciencefairs
import verify_and_import

# (name, module, required). A required stage failing fails the whole run.
STAGES = (
    ("reddit", scrape_reddit, False),
    ("devpost", scrape_devpost, False),
    # Recurring competitions, added because the shelf's real problem was never
    # the row count, it was that four of 55 high-school rows were open at once.
    # Annual programmes cannot fix that; their deadlines cluster in winter by
    # nature. These two feeds always have something open, need no auth, and
    # publish whether an unaffiliated individual may enter.
    ("ctftime", scrape_ctftime, False),
    ("codeforces", scrape_codeforces, False),
    # The counterweight to the three above. Every dated candidate in the pool
    # came from ctftime, devpost or codeforces, and all three are computer
    # science -- which is why 33 of the 34 open high-school rows were cs and
    # exactly one was not. Pathways is a directory of funded STEM programmes
    # filtered to the ones that take high schoolers: of its first 65 candidates,
    # one was cs. It adds about 90 seconds, because the per-programme fetch that
    # finds the organiser's own url is deliberately serialised.
    ("pathways", scrape_pathways, False),
    # The only feed found so far that is non-CS, dated AND local at once. Each
    # ISEF-affiliated fair publishes its own entry deadline and its own site, so
    # it does not repeat the spreadsheet's 250 state rows that all pointed at one
    # national url. Capped per run; see the module docstring.
    ("sciencefairs", scrape_sciencefairs, False),
    # THE SHELF, as opposed to the catalog. Everything above finds programmes
    # with deadlines, which is the smaller half of what a student needs: four
    # deadlines are open at a time and a Tuesday in February has none. These two
    # find free material, from reddit COMMENTS rather than titles -- the post is
    # the question ("best free resource for linear algebra?") and the answer is
    # in a reply, which is why the opportunity pool was never going to feed this
    # (891 of 11,293 pooled candidates carry a non-reddit URL at all).
    ("reddit-resources", scrape_reddit_resources, False),
    # A publisher's own catalogue, which is how the shelf stops being 44 rows
    # of archetype skill rungs and starts carrying the subjects a high
    # schooler actually takes. Only books OpenStax marks "live": 45 of their
    # 129 are retired, unlisted or deprecated, and importing those would be
    # the exact defect retire_dead_opportunities.py exists to undo.
    ("openstax", scrape_openstax, False),
    ("verify+import", verify_and_import, True),
    # Fetches each candidate page and refuses any free claim it cannot quote
    # from it. Not required: a provider outage here costs a day of shelf growth,
    # while the same outage in verify+import means the catalog went stale, and
    # conflating the two is how a green run hid four weeks of nothing.
    ("import-resources", import_resources, False),
    # Re-read programme pages and write the dates they currently state.
    #
    # Daily because the information arrives daily. Measured 2026-10-05, only 2
    # of 48 curated rows had a deadline in the future -- the rest had passed,
    # median 218 days stale -- while a free chat model, asked the same
    # questions, correctly said UNKNOWN rather than guessing. A catalog whose
    # dates are worse than "check the official page" has no reason to exist,
    # and dates are the one thing a model genuinely cannot recall.
    #
    # Most autumn runs will find nothing: programmes post 2027 dates through
    # the season ("The 2027 application will open in the Fall of 2026" --
    # davidsongifted.org). That is the argument FOR daily, not against it. The
    # day a date appears, the shelf has it.
    # Link health. The shelf tells every visitor that anything which stopped
    # holding up was removed; until 2026-10-12 nothing enforced that and seven
    # of sixty-six open rows did not load. Only a domain that has stopped
    # resolving retires a row -- a moved page is reported for a human, because
    # deleting a live programme to keep a link promise trades the student's
    # interest for ours.
    ("check-links", check_links, False),
    ("refresh-deadlines", refresh_deadlines, False),
    # Embed whatever the import just added, so a new opportunity is matchable
    # by meaning the next morning. Optional: a missing embedding simply means
    # the row is absent from semantic_scores() and scoring falls back to
    # lexical, which is how the product worked before embeddings.
    ("embed", embed_catalog, False),
    # The student half of the same loop. refresh_student_embedding fires on
    # profile save, which covers everyone who edits a profile AFTER semantic
    # matching shipped and nobody who existed before it -- measured 2026-10-18,
    # 0 of 6 students had an embedding, so semantic_scores() returned nothing
    # for everybody and every ranking silently fell back to pure TF-IDF.
    ("embed-students", embed_students, False),
)


def main() -> int:
    failures: list[str] = []

    for name, stage, required in STAGES:
        print(f"=== {name} ===", flush=True)
        try:
            stage.main()
        except SystemExit as exit_:
            # Stages sys.exit() on a fatal block -- an unconfigured LLM, or
            # a verify pass where every call failed. A message means failure;
            # a bare exit or code 0 is a clean stop.
            message = str(exit_) if exit_.code not in (0, None) else ""
            if message:
                print(f"{name} stopped: {message}", flush=True)
                if required:
                    failures.append(f"{name}: {message}")
            else:
                print(f"{name} finished early (nothing to do).", flush=True)
        except Exception:
            traceback.print_exc()
            if required:
                failures.append(f"{name}: raised, see traceback above")

    if failures:
        print("\n" + "=" * 60, flush=True)
        print("DAILY LOOP FAILED. The candidate pool may still have grown,", flush=True)
        print("but nothing reached the catalog:", flush=True)
        for failure in failures:
            print(f"  - {failure}", flush=True)
        print("=" * 60, flush=True)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
