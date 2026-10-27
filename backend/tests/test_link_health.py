"""
A link checker that is wrong in the wrong direction empties the catalog.

The product's claim is that nothing on the shelf is broken. Enforcing it badly
is worse than not enforcing it: a student who never sees an opportunity cannot
discover it was wrongly hidden, whereas a dead link wastes one click. Every test
here is about keeping the checker shy.
"""

from __future__ import annotations

import pytest

from app.link_health import FAIL_STRIKES, classify, needs_url_review, should_retire


@pytest.mark.parametrize("status", [200, 201, 204, 301, 302, 308])
def test_anything_that_answered_is_alive(status: int) -> None:
    assert classify(status) == "alive"


@pytest.mark.parametrize("status", [404, 410])
def test_a_404_on_a_host_that_answered_is_a_moved_page_not_a_dead_programme(status: int) -> None:
    """The mistake that cost a real catalog its best rows.

    The first version of this module retired on any repeated failure. Its first
    real run removed USA Mathematical Olympiad (maa.org reorganised and
    /math-competitions/ now 404s), the Clark Scholar Program, the Adroit Prizes,
    Harvard International Review and the Conrad Challenge. All five are running.
    A host that answers at all still exists; only the URL was stale.
    """
    assert classify(status) == "moved"


@pytest.mark.parametrize("status", [401, 403, 405, 406, 429, 999])
def test_a_refusal_aimed_at_us_is_never_death(status: int) -> None:
    """The failure mode that would empty this catalog.

    Measured 2026-10-12: broadinstitute.org, mathworks.com and hitcon.org all
    returned 403 to an automated browser while serving a person fine. A checker
    that counted those as dead would have retired three live programmes on its
    first run.
    """
    assert classify(status) == "inconclusive"


def test_a_name_that_does_not_resolve_is_the_strongest_signal_there_is() -> None:
    """Nobody bot-blocks a DNS lookup.

    THE STRINGS ARE VERBATIM FROM THE LIBRARIES, not paraphrased. The first
    version of this module matched on "gaierror" and "ERR_NAME_NOT_RESOLVED"
    and caught none of the real cases, because requests wraps a DNS failure in
    a ConnectionError whose text says "NameResolutionError" and "Failed to
    resolve". Five genuinely dead domains were filed as inconclusive and would
    never have been retired. Paraphrasing an error string is the same mistake
    as paraphrasing a quote.
    """
    real = [
        # requests, copied from a live run on 2026-10-12
        "ConnectionError: HTTPSConnectionPool(host='ctf.csaw.io', port=443): Max "
        "retries exceeded with url: / (Caused by NameResolutionError(\"<urllib3."
        "connection.HTTPSConnection object>: Failed to resolve 'ctf.csaw.io'\"))",
        # chromium, via the browser harness
        "net::ERR_NAME_NOT_RESOLVED",
        # stdlib socket
        "gaierror: [Errno 8] nodename nor servname provided",
        "ConnectionRefusedError: [Errno 61] Connection refused",
    ]
    for error in real:
        assert classify(error) == "dead", error[:60]


def test_a_server_error_or_a_timeout_says_nothing_about_the_programme() -> None:
    for outcome in (500, 502, 503, 522, "ReadTimeout", "net::ERR_CONNECTION_CLOSED",
                    "SSLError: TLSV1_UNRECOGNIZED_NAME"):
        assert classify(outcome) == "moved"


def test_an_unrecognised_outcome_does_nothing() -> None:
    assert classify("something nobody has seen before") == "inconclusive"
    assert classify(None) == "inconclusive"
    assert classify(True) == "inconclusive"


class TestShouldRetire:
    def test_one_bad_day_is_not_enough(self) -> None:
        assert should_retire(["dead"]) is False
        assert needs_url_review(["moved"]) is False

    def test_two_runs_agreeing_on_a_gone_domain_is_enough(self) -> None:
        assert should_retire(["dead", "dead"]) is True

    def test_a_moved_page_is_never_retired_however_long_it_persists(self) -> None:
        """The whole point of that verdict is that somebody has to go and look.
        A stale link is a worse experience than a correct one and a far better
        one than a real programme silently deleted."""
        assert should_retire(["moved"] * 10) is False
        assert should_retire(["moved", "dead"]) is False
        assert needs_url_review(["moved", "moved"]) is True

    def test_a_row_that_answered_recently_is_neither_retired_nor_flagged(self) -> None:
        assert needs_url_review(["alive", "moved", "moved"]) is False

    def test_a_single_success_clears_the_whole_record(self) -> None:
        """A page that answered at all this week is not gone, whatever else
        happened, the point is to be shy, not consistent."""
        assert should_retire(["alive", "dead", "dead"]) is False
        assert should_retire(["dead", "alive", "dead"]) is False

    def test_being_refused_forever_never_retires_anything(self) -> None:
        """A programme behind a permanent bot wall stays on the shelf and
        becomes a human's problem, which is the right place for it."""
        assert should_retire(["inconclusive"] * 10) is False

    def test_a_refusal_breaks_the_streak(self) -> None:
        assert should_retire(["dead", "inconclusive"]) is False

    def test_the_strike_count_is_what_the_module_says_it_is(self) -> None:
        assert should_retire(["dead"] * FAIL_STRIKES) is True
        assert should_retire(["dead"] * (FAIL_STRIKES - 1)) is False
