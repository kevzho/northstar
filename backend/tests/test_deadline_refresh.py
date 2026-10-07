"""
Guards on the deadline refresh.

WHY THIS SCRIPT IS THE ONE THAT MATTERS. Measured 2026-10-05: a frontier model
with no tools, asked to recall 24 curated catalog rows, knew all 24 existed —
8/8 seed, 8/8 human, 8/8 sheet. So "this programme is real" is not information a
student needs this catalog for. Asked instead for the current deadlines of
twelve open rows, it said UNKNOWN twelve times, correctly refusing to guess.

Dates are the gap. And the catalog was not filling it: 2 of 48 curated rows had
a deadline in the future, median staleness 218 days, MIT PRIMES reading
2025-11-30. A student asking a chatbot got a better answer than the shelf.

These tests exist because the two ways to "fix" that are both worse than the
bug: writing a date the page does not state, and keeping a date that has passed.
"""

from __future__ import annotations

import inspect
import pathlib
import sys

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS.parent))

import refresh_deadlines as refresh  # noqa: E402


def test_only_a_future_date_is_ever_written() -> None:
    """Last cycle's date is not this cycle's date.

    The whole defect being repaired is a shelf asserting dates that had passed.
    Re-reading a page and writing the February date it still displays would
    recreate it with fresher provenance, which is worse.
    """
    src = inspect.getsource(refresh.main)
    assert "fresh >= today" in src, "a past date must never be written"
    # And the model's reply has to survive a real date parse first.
    assert "iso_or_none(verdict.get(\"deadline\"))" in src


def test_a_stale_date_is_cleared_rather_than_kept() -> None:
    """NULL renders as "Rolling deadline", which is the honest statement of "we
    do not know when this opens next". A date from last February is not."""
    src = inspect.getsource(refresh.main)
    assert "stale_stored" in src
    assert '{"deadline": None}' in src, (
        "a row whose date has passed and whose page offers nothing newer must "
        "have the dead date cleared, not left in place"
    )


def test_dates_are_parsed_strictly() -> None:
    assert refresh.iso_or_none("2027-01-20") == "2027-01-20"
    assert refresh.iso_or_none("2027-01-20T00:00:00") == "2027-01-20"
    for junk in ("January 2027", "rolling", "", None, "2027-13-45", "TBA", "soon"):
        assert refresh.iso_or_none(junk) is None, f"{junk!r} must not become a date"


def test_the_model_is_told_not_to_infer() -> None:
    """Measured behaviour this depends on: davidsongifted.org displays last
    cycle's deadline alongside "The 2027 application will open in the Fall of
    2026", and the model correctly returned null. That only holds while the
    instruction does."""
    assert "Never infer one from a past cycle" in refresh.SYSTEM
    assert "If the page gives a month with no day, use null" in refresh.SYSTEM
    assert "not the event date" in refresh.SYSTEM
    # A quote keeps the claim auditable against the page it came from.
    assert "verbatim" in refresh.SYSTEM


def test_rows_with_a_live_date_are_not_re_fetched() -> None:
    """Politeness and budget: a row already answering the question does not need
    the organiser's server hit again today."""
    src = inspect.getsource(refresh.main)
    assert 'row.get("deadline") and str(row["deadline"]) >= today' in src


def test_curated_rows_are_checked_before_the_scraped_tail() -> None:
    """2 of 48 curated rows had a live date against 52 of 94 scraped ones. The
    curated half is both the stale half and the half a student actually wants,
    so a capped run must spend its budget there."""
    src = inspect.getsource(refresh.main)
    assert 'r.get("added_by") == "ai"' in src, "scraped rows must sort last"


def test_the_run_is_capped_and_registered_daily() -> None:
    assert refresh.MAX_PER_RUN <= 50, "a daily job must not blow its time budget"
    import scrape_all

    names = [n for n, _, _ in scrape_all.STAGES]
    assert "refresh-deadlines" in names, "the refresh must run every day"
    # Soft-failing: a dead organiser page must not fail the whole daily loop.
    required = {n: req for n, _, req in scrape_all.STAGES}
    assert required["refresh-deadlines"] is False
