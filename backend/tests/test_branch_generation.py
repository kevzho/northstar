"""
Breaking a step down without putting anything in the plan we cannot stand behind.

The plan's learn rungs link to resources this project opened and read, and its
application steps come from a student's verified matches. A branch is written
by a model in one call, so the guard is what keeps those two facts true when a
third kind of step appears beside them.
"""

from __future__ import annotations

import json

from app.branch_generation import MAX_DETAIL, MAX_TITLE, build_prompt, parse_branch


def reply(steps) -> str:
    return json.dumps({"steps": steps})


GOOD = [
    {"title": "Sketch the three screens on paper", "detail": "You can point at each and say what it does."},
    {"title": "Build the input form first", "detail": "Three number fields that log to the console."},
]


def test_a_clean_breakdown_survives() -> None:
    out = parse_branch(reply(GOOD))
    assert out is not None and len(out) == 2
    assert out[0]["title"] == "Sketch the three screens on paper"


def test_a_url_is_refused_however_helpful_it_looks() -> None:
    """The learn rungs link to resources this project checked. A model-supplied
    link would sit in the same plan wearing the same styling with none of that
    behind it."""
    for bad in (
        "Read the docs at https://example.com",
        "Use www.figma.com to sketch it",
        "Sign up on replit.com first",
    ):
        assert parse_branch(reply([{"title": bad, "detail": "x y z"}, GOOD[1]])) is None
        assert parse_branch(reply([GOOD[0], {"title": "Fine", "detail": bad}])) is None


def test_one_step_is_not_a_breakdown_and_six_is_a_new_plan() -> None:
    assert parse_branch(reply([GOOD[0]])) is None
    assert parse_branch(reply(GOOD * 3)) is None
    assert parse_branch(reply([])) is None


def test_two_identical_moves_are_refused() -> None:
    assert parse_branch(reply([GOOD[0], dict(GOOD[0])])) is None


def test_an_essay_is_refused_rather_than_truncated() -> None:
    """These render inside a node on a diagram. Truncating would store text the
    student never sees the end of."""
    assert parse_branch(reply([{"title": "x" * (MAX_TITLE + 1), "detail": "ok"}, GOOD[1]])) is None
    assert parse_branch(reply([{"title": "ok", "detail": "y" * (MAX_DETAIL + 1)}, GOOD[1]])) is None


def test_empty_prose_is_refused() -> None:
    assert parse_branch(reply([{"title": "", "detail": "something"}, GOOD[1]])) is None
    assert parse_branch(reply([{"title": "something", "detail": "  "}, GOOD[1]])) is None


def test_garbage_is_a_refusal_not_a_crash() -> None:
    for bad in ("", "not json at all", "{}", '{"steps": "two of them"}', '{"steps":[1,2]}'):
        assert parse_branch(bad) is None


def test_it_reads_json_out_of_a_fenced_or_chatty_reply() -> None:
    assert parse_branch("```json\n" + reply(GOOD) + "\n```") is not None
    assert parse_branch("Sure! Here you go:\n" + reply(GOOD)) is not None


def test_the_prompt_carries_the_student_not_just_the_step() -> None:
    """A breakdown written without the profile is a generic how-to, which the
    student could have got anywhere."""
    prompt = build_prompt(
        "Build a break-even calculator",
        "project",
        {"grade": 10, "trait_scores": {"builder": 70.0}, "field_scores": {"math": 21.0}},
        reason="I do not know where to start",
    )
    assert "Build a break-even calculator" in prompt
    assert "builder 70" in prompt and "7000" not in prompt
    assert "out of 100" in prompt
    assert "math" in prompt
    assert "I do not know where to start" in prompt
