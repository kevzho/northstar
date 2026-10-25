"""
The free claim has to be checkable, not asserted.

Every test here is about one thing: a row only reaches public.learning_resources
when the sentence that proves it is free is really on the page. The shelf is
read by students with no money; a list of forty free resources where three are
paywalled is worse for them than a list of twelve where none are, because now
they have to check every one themselves.
"""

from __future__ import annotations

import pytest

from app.resource_verifier import (
    CONFIDENCE_FLOOR,
    contains_quote,
    decide_resource,
    is_resource_host,
    normalise,
    slug,
)

PAGE = (
    "<h1>Introduction to Statistics</h1>"
    "<p>This course and its textbook are freely available to anyone, "
    "with no registration required.</p>"
    "<p>Covers sampling, confidence intervals and hypothesis tests.</p>"
)

VERDICT = {
    "is_free": True,
    "teaches_a_skill": True,
    "high_school_reachable": True,
    "confidence": 0.95,
    "free_evidence": "freely available to anyone, with no registration required",
    "kind": "course",
    "field": "math",
    "skill_key": "statistics",
    "skill_label": "statistics — hypothesis tests and what a confidence interval is not",
    "title": "Introduction to Statistics",
    "host": "OpenIntro",
    "effort": "4 weeks at 3h/week",
    "prerequisite": "algebra",
    "why_this_one": "Starts from sampling rather than formulas.",
}

CANDIDATE = {"url": "https://openintro.org/book/os/", "mentions": 7}


def accepted(**overrides):
    verdict = {**VERDICT, **overrides}
    return decide_resource(CANDIDATE, verdict, PAGE)


def test_a_clean_candidate_becomes_a_row() -> None:
    row = accepted()
    assert row is not None
    assert row["url"] == CANDIDATE["url"]
    assert row["is_free"] is True
    assert row["added_by"] == "ai"
    assert row["skill_key"] == "statistics"
    assert row["free_evidence"] in VERDICT["free_evidence"]


def test_a_quote_that_is_not_on_the_page_is_refused() -> None:
    """The guard the whole catalog rests on.

    A model asked for a quote will produce one whether or not the page contains
    it, and an invented quote is a hallucination wearing a citation. This is the
    only check in the pipeline that cannot be talked out of its answer.
    """
    assert accepted(free_evidence="This course is completely free of charge") is None


def test_a_paraphrase_is_not_a_quote() -> None:
    # Every word is on the page; the sentence is not.
    assert accepted(free_evidence="available freely to anyone with no registration") is None


def test_a_quote_survives_curly_quotes_soft_hyphens_and_line_wraps() -> None:
    """Real pages do not store text the way they render it.

    Each of these broke an exact comparison on a page that was being honest,
    which is the failure mode that would quietly empty the shelf.
    """
    page = (
        "<p>This text­book is\n   freely   available to anyone, "
        "with no “registration” required.</p>"
    )
    assert contains_quote(page, 'freely available to anyone, with no "registration" required')
    assert contains_quote("Everything is &quot;free&quot; here for students", '"free" here for students')


def test_free_trial_wording_is_a_price_not_an_absence_of_one() -> None:
    for pitch in (
        "Start your free trial today and keep learning",
        "Free for 14 days, then $19 a month",
        "The first chapter is free, the rest with a subscription",
        "Free with a subscription to the platform",
        "Get a 30-day free pass to every course",
        "Free to start, upgrade any time",
        "Some of our lessons are free",
    ):
        page = f"<p>{pitch}</p>"
        assert decide_resource(CANDIDATE, {**VERDICT, "free_evidence": pitch}, page) is None, pitch


def test_a_sample_of_the_paid_thing_is_not_a_free_resource() -> None:
    """The one this module got wrong in production, and its family.

    On the first real import run roadmap.sh was accepted at 0.9 confidence
    quoting "Every pack starts with free lessons" -- a sentence about where the
    paywall is, from a site that sells courses. The earlier pattern only knew
    the phrasing "first lesson free". A page saying SOME of it is free is saying
    the rest is not, which is a price.
    """
    for pitch in (
        "Every pack starts with free lessons",          # the actual one
        "Each track begins with a free module",
        "A few chapters are free to read",
        "Preview the first unit free",
        "Free sample chapters available",
        "The intro course is free; premium unlocks the rest",
        "Free lessons and paid certificates",
        "Upgrade for the rest — the basics are free",
    ):
        page = f"<p>{pitch}</p>"
        assert decide_resource(CANDIDATE, {**VERDICT, "free_evidence": pitch}, page) is None, pitch


def test_the_broadened_pattern_still_lets_genuinely_free_wording_through() -> None:
    """The guard above is wide, so this pins the other side of it: these are
    sentences from the real shelf, and a pattern that refuses them would empty
    the catalog instead of cleaning it."""
    for pitch in (
        "Free to read under a Creative Commons license",
        "Our full stack curriculum is free and supported by a passionate open source community",
        "freely available to anyone, with no registration required",
        "All course materials are free and openly licensed",
        "This textbook is free to download in PDF form",
        "No cost, no account, no advertising",
    ):
        page = f"<p>{pitch}</p>"
        row = decide_resource(CANDIDATE, {**VERDICT, "free_evidence": pitch}, page)
        assert row is not None, pitch


def test_a_two_word_quote_proves_nothing() -> None:
    """'Free' appears on most commercial pages, usually followed by 'trial'."""
    assert accepted(free_evidence="freely") is None
    assert contains_quote("it is free", "free") is False


def test_the_model_saying_free_is_not_enough_on_its_own() -> None:
    assert accepted(is_free=False) is None
    assert accepted(free_evidence="") is None
    assert accepted(free_evidence=None) is None


@pytest.mark.parametrize(
    "confidence,expected",
    [(CONFIDENCE_FLOOR, True), (CONFIDENCE_FLOOR - 0.01, False), ("nonsense", False), (None, False)],
)
def test_an_unclear_page_is_left_for_a_human(confidence, expected) -> None:
    assert (accepted(confidence=confidence) is not None) is expected


def test_material_a_high_schooler_cannot_reach_is_refused() -> None:
    assert accepted(high_school_reachable=False) is None
    # Unstated is allowed through: the prompt asks the model to lower its
    # confidence instead of guessing, and the floor handles it.
    assert accepted(high_school_reachable=None) is not None


def test_something_that_teaches_nothing_is_refused() -> None:
    assert accepted(teaches_a_skill=False) is None


def test_a_kind_the_table_would_reject_is_refused_here_instead() -> None:
    """learning_resources.kind is a check constraint, so a bad value is a 400
    from postgrest at insert time. Caught here, where it can be counted."""
    assert accepted(kind="blog") is None
    assert accepted(kind="") is None
    assert accepted(kind="COURSE") is not None  # case is not the row's problem


def test_a_subject_the_enum_lacks_is_mapped_rather_than_refused() -> None:
    """The bug this caught, in production, on the day OpenStax landed.

    public.opportunity_field predates the learning shelf and has no
    "chemistry". Asked to classify a chemistry textbook, every model tested
    answers "chemistry" -- correctly -- and the row was then refused and
    reported as "low confidence", which is both wrong and unhelpful. It cost
    the shelf every chemistry, statistics and economics title in the import.

    These are normalisations, not guesses: each maps to where the existing
    catalog already files that subject, so the shelf and the opportunity
    catalog keep agreeing with each other.
    """
    for said, stored in [
        ("chemistry", "biology"),
        ("statistics", "math"),
        ("economics", "business"),
        ("psychology", "health"),
        ("history", "humanities"),
        ("astronomy", "physics"),
    ]:
        row = accepted(field=said)
        assert row is not None, f"{said!r} was refused"
        assert row["opportunity_field"] == stored, f"{said!r} -> {row['opportunity_field']}"


def test_a_resource_with_no_field_at_all_is_still_refused() -> None:
    """The subject filter on /learn is how most students will find it. A row
    with no field is on the shelf and off the index."""
    assert accepted(field="") is None
    assert accepted(field="quidditch") is None


def test_an_aggregator_or_a_shortener_is_never_the_resource() -> None:
    for url in (
        "https://www.reddit.com/r/learnmath/comments/abc/best_book/",
        "https://bit.ly/3xyz",
        "https://imgur.com/a/abc",
        "https://www.amazon.com/dp/B000",
        "https://medium.com/@someone/learn-stats",
        "https://discord.gg/invite",
        "ftp://files.example.com/book.pdf",
        "not a url",
        "",
    ):
        assert is_resource_host(url) is False, url
        assert decide_resource({"url": url}, VERDICT, PAGE) is None, url

    for url in ("https://openintro.org/x", "https://ocw.mit.edu/courses/18-06", "http://example.edu/notes.pdf"):
        assert is_resource_host(url) is True, url


def test_a_row_missing_what_makes_it_usable_is_refused() -> None:
    assert accepted(title="") is None
    assert accepted(skill_label="") is None
    assert accepted(skill_key="   ") is None
    assert accepted(why_this_one="") is None


def test_defaults_fill_only_what_is_optional() -> None:
    row = accepted(effort="", prerequisite="", host="")
    assert row is not None
    assert row["effort"] == "a weekend"
    assert row["prerequisite"] == "none"
    assert row["host"] == "openintro.org"


def test_slug_and_normalise_are_boring_on_purpose() -> None:
    assert slug("Linear Algebra!") == "linear-algebra"
    assert slug("  --Stats--  ") == "stats"
    assert slug(None) == ""
    assert normalise("A  B—C") == "a b-c"


def test_an_overlong_quote_is_refused_rather_than_truncated() -> None:
    """Truncating would store a quote the page does not contain, which is the
    thing this module exists to prevent."""
    long_quote = "freely available to anyone, " * 20
    assert decide_resource(CANDIDATE, {**VERDICT, "free_evidence": long_quote}, PAGE) is None
