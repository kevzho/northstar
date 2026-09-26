"""
Guards on the recurring-competition feeds.

These exist because volume is the easy half. Every high-volume competition feed
that is free and needs no auth is computer science — CTFtime, Codeforces,
Devpost, Hack Club, Kaggle, all of it. app/match.py boosts a field match, so an
uncapped import makes CS crowd out every other field and a student who wrote
"biology" starts being shown capture-the-flag events. The shelf would get bigger
and worse at the same time, which is the specific failure this catalog has
already had once, with 134 of 138 AI-imported rows landing on one shelf.

So the caps are not politeness to an API. They are the product constraint, and
a test is the only thing that keeps a constant from being raised to "just get
more rows".
"""

from __future__ import annotations

import importlib
import pathlib
import sys

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

ctftime = importlib.import_module("scrape_ctftime")
codeforces = importlib.import_module("scrape_codeforces")


def test_per_run_import_caps_stay_small() -> None:
    """A single CS feed must not be able to outnumber the curated shelf.

    The high-school shelf is ~55 rows across 9 fields. One feed importing 50 a
    day would pass 55 within a day and 500 within a fortnight.
    """
    assert ctftime.MAX_IMPORT <= 30, (
        f"CTFtime cap is {ctftime.MAX_IMPORT}. Above ~30 per run, one field "
        "overwhelms the shelf — see this module's docstring before raising it."
    )
    assert codeforces.MAX_IMPORT <= 15, (
        f"Codeforces cap is {codeforces.MAX_IMPORT}. Six to eight rounds are "
        "scheduled at a time and the feed refills; a larger cap only imports "
        "contests nobody will reach."
    )


def test_ctftime_only_imports_entry_that_needs_no_permission() -> None:
    """The whole point is "an individual can dive right in".

    CTFtime's `restrictions` field is the signal: Prequalified means you must
    have qualified elsewhere, which is entry_gate='qualify' by another name, and
    Academic usually means university enrolment. Importing either would recreate
    the 15 rows that carried an application deadline for something you cannot
    apply to.
    """
    assert ctftime.OPEN_RESTRICTIONS == {"Open", "Casual"}, (
        "CTFtime restrictions widened. 'Prequalified' and 'Academic' are not "
        "things a student can just enter."
    )


def test_a_combined_division_round_is_not_discouraged() -> None:
    """A Div. 1 + Div. 2 round is enterable by Div. 2 competitors.

    Matching "Div. 1" first told a beginner to skip a contest they were welcome
    at — eligible but walled, the same error as a juniors-only programme listed
    for grades 9-12.
    """
    combined = codeforces.beginner_note("Codeforces Round (Div. 1 + Div. 2)")
    assert "combined" in combined.lower()
    assert "instead" not in combined.lower(), (
        "a combined round is being described as one to skip"
    )
    # And the plain divisions must still say the right thing.
    assert "instead" in codeforces.beginner_note("Codeforces Round 1124 (Div. 1)")
    assert "newer competitors" in codeforces.beginner_note("Codeforces Round (Div. 3)")


def test_feeds_are_registered_in_the_daily_run() -> None:
    """An adapter nobody calls is a file, not a feature. This is the mistake
    that left three semantic-matching files committed but unreachable."""
    body = (SCRIPTS / "scrape_all.py").read_text()
    for name in ("scrape_ctftime", "scrape_codeforces"):
        assert f"import {name}" in body, f"{name} is not imported by scrape_all"
    assert '("ctftime", scrape_ctftime, False)' in body
    assert '("codeforces", scrape_codeforces, False)' in body


def test_feeds_never_import_a_past_deadline() -> None:
    """Codeforces returns its entire 2,153-contest history in one response, and
    CTFtime's archive is likewise complete. Importing finished events is how the
    catalog reached 123 expired rows out of 195."""
    cf = (SCRIPTS / "scrape_codeforces.py").read_text()
    assert 'phase") == "BEFORE"' in cf, (
        "the Codeforces adapter no longer filters to upcoming contests"
    )
    ct = (SCRIPTS / "scrape_ctftime.py").read_text()
    assert '"start": int(now.timestamp())' in ct, (
        "the CTFtime adapter no longer bounds its query to future events"
    )


def test_feed_candidates_are_verified_before_the_reddit_pool() -> None:
    """A feed whose candidates are never reached imports nothing.

    The pool holds 9,000+ reddit candidates, the per-run verify cap is 60, and
    ordering inside a tier falls back to pool order, which is score-descending.
    A structured feed has no upvotes, so its entries sort last of all — the
    adapters would run daily, write candidates, and import nothing, which looks
    exactly like working.
    """
    import importlib

    vi = importlib.import_module("verify_and_import")
    assert {"ctftime", "codeforces"} <= vi.KNOWN_REAL_SOURCES, (
        "the competition feeds are not in the priority tier; their candidates "
        "will sit behind thousands of reddit links forever"
    )

    feed = {"source": "ctftime", "title": "Some CTF", "blurb": "competition",
            "url": "https://example.org/", "deadline_guess": "2026-10-01"}
    reddit = {"source": "reddit", "title": "Great internship program", "score": 9000,
              "blurb": "competition", "url": "https://example.com/"}
    assert vi.rank_key(feed) < vi.rank_key(reddit)
    assert vi.promising(feed) is True


def test_sooner_deadlines_are_verified_first() -> None:
    """A contest starting tomorrow deserves a token before one in three months."""
    import importlib

    vi = importlib.import_module("verify_and_import")
    soon = {"source": "ctftime", "title": "A", "blurb": "competition",
            "url": "https://a.org/", "deadline_guess": "2026-10-01"}
    later = {"source": "ctftime", "title": "B", "blurb": "competition",
             "url": "https://b.org/", "deadline_guess": "2026-12-01"}
    assert vi.rank_key(soon) < vi.rank_key(later)
