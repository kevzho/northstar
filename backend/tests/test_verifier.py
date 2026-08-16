"""
Tests for the verifier's guardrail — decide() is the safety boundary
between a scraped post and the live catalog, so it is pinned hard. Pure
function, no network.
"""

from app.verifier import CONFIDENCE_FLOOR, decide


def _candidate(**over) -> dict:
    base = {
        "title": "MIT PRIMES Research Program",
        "blurb": "A year-long research program for high schoolers.",
        "url": "https://math.mit.edu/research/highschool/primes/",
        "source": "r/summerprograms",
        "field_guess": "math",
        "type_guess": "program",
        "audience_guess": "high_school",
        "location_guess": "us",
    }
    base.update(over)
    return base


def _verdict(**over) -> dict:
    base = {
        "is_opportunity": True,
        "title": "MIT PRIMES",
        "host": "MIT",
        "field": "math",
        "type": "program",
        "confidence": 0.95,
        "reason": "Real, applyable research program.",
    }
    base.update(over)
    return base


def test_confident_real_opportunity_with_link_is_promoted() -> None:
    row = decide(_candidate(), _verdict())
    assert row is not None
    assert row["added_by"] == "ai"
    assert row["opportunity_field"] == "math"
    assert row["title"] == "MIT PRIMES"


def test_not_an_opportunity_is_rejected() -> None:
    assert decide(_candidate(), _verdict(is_opportunity=False)) is None


def test_low_confidence_is_rejected() -> None:
    assert decide(_candidate(), _verdict(confidence=CONFIDENCE_FLOOR - 0.01)) is None


def test_reddit_only_link_is_not_auto_imported() -> None:
    # A real opportunity lives on its own site; a bare reddit permalink
    # has no destination, so it stays for human review.
    reddit = _candidate(url="https://www.reddit.com/r/x/comments/abc/")
    assert decide(reddit, _verdict()) is None


def test_devpost_passes_on_its_own_domain() -> None:
    dp = _candidate(
        source="devpost",
        url="https://coolhack.devpost.com/",
        type_guess="competition",
    )
    row = decide(dp, _verdict(type="competition"))
    assert row is not None
    assert row["type"] == "competition"


def test_bad_field_or_type_falls_back_to_candidate_guess() -> None:
    row = decide(
        _candidate(field_guess="cs", type_guess="scholarship"),
        _verdict(field="not-a-field", type="not-a-type"),
    )
    assert row["opportunity_field"] == "cs"
    assert row["type"] == "scholarship"


def test_missing_title_is_rejected() -> None:
    assert decide(_candidate(title=""), _verdict(title="")) is None


def test_malformed_confidence_does_not_crash() -> None:
    assert decide(_candidate(), _verdict(confidence="high")) is None
