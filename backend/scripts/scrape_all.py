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
import scrape_codeforces
import scrape_ctftime
import scrape_devpost
import scrape_reddit
import verify_and_import

# (name, module, required). A required stage failing fails the whole run.
STAGES = (
    ("reddit", scrape_reddit, False),
    ("devpost", scrape_devpost, False),
    # Recurring competitions, added because the shelf's real problem was never
    # the row count — it was that four of 55 high-school rows were open at once.
    # Annual programmes cannot fix that; their deadlines cluster in winter by
    # nature. These two feeds always have something open, need no auth, and
    # publish whether an unaffiliated individual may enter.
    ("ctftime", scrape_ctftime, False),
    ("codeforces", scrape_codeforces, False),
    ("verify+import", verify_and_import, True),
    # Embed whatever the import just added, so a new opportunity is matchable
    # by meaning the next morning. Optional: a missing embedding simply means
    # the row is absent from semantic_scores() and scoring falls back to
    # lexical, which is how the product worked before embeddings.
    ("embed", embed_catalog, False),
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
