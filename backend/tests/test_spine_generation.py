"""
Guards on the generated spine.

app/roadmap.py sequences learn -> build -> publish -> apply, and the middle
rungs came from one of twenty-four hand-written spines keyed by archetype. Two
measured problems with that, on 2026-10-04:

    Twenty-four buckets is a genre, not a plan. A 9th grader who has shipped
    nothing and a 12th grader with three projects both landed on
    "applied-ai-builder" and both read the same sentence about a study-note
    summariser.

    Twelve of the twenty-four named a skillKey with NO learning resource behind
    it -- argument-mapping, playtesting, public-records, causal-inference and
    eight more. Those students' learn rung rendered as nothing, silently.

So the model writes the project and the publish step from the student's own
traits, grade, field and real matches, and CHOOSES a skill rung from the keys
that actually have verified resources. These tests cover the four ways that can
go wrong, because each one is a generated plan making a claim the catalog has
not earned.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.spine_generation import build_prompt, parse_spine  # noqa: E402

LABELS = {
    "evaluation": "evaluation — measuring whether an AI feature actually works",
    "statistical-honesty": "statistical honesty — confounders and base rates",
}


def reply(**over: object) -> str:
    body = {"project": "Reproduce one figure", "publish": "Write it up", "skill_key": "evaluation"}
    body.update(over)
    import json

    return json.dumps(body)


def test_a_key_with_no_resources_is_refused() -> None:
    """The exact defect this module exists to fix. `playtesting` is one of the
    twelve archetype keys with nothing behind it; accepting it would render an
    empty learn rung, which is what the hand-written spine already did."""
    assert parse_spine(reply(skill_key="playtesting"), LABELS) is None
    assert parse_spine(reply(skill_key=""), LABELS) is None
    assert parse_spine(reply(skill_key="EVALUATION"), LABELS) is None


def test_the_skill_sentence_comes_from_the_catalog_not_the_model() -> None:
    """Measured failure, first run: a student got "Rigor — a bioethics case file
    is only as strong as its sources" attached to the key `regulatory-literacy`.
    roadmap.py would have printed that sentence and then linked four resources
    about something else. The label is human-written and already matches its
    resources, so it is taken from there and the model's wording discarded."""
    spine = parse_spine(reply(skill="Rigor — something else entirely"), LABELS)
    assert spine is not None
    assert spine["skill"] == LABELS["evaluation"]
    assert "Rigor" not in spine["skill"]


def test_a_link_in_generated_prose_is_refused() -> None:
    """The learn rung links to curated, verified resources. A model-supplied
    link would sit in identical styling with none of that behind it."""
    for field in ("project", "publish"):
        assert parse_spine(reply(**{field: "see https://example.com"}), LABELS) is None
        assert parse_spine(reply(**{field: "go to www.example.com"}), LABELS) is None


def test_empty_prose_falls_back_rather_than_shipping_a_blank_step() -> None:
    for field in ("project", "publish"):
        assert parse_spine(reply(**{field: ""}), LABELS) is None
        assert parse_spine(reply(**{field: "   "}), LABELS) is None


def test_junk_and_fences_are_handled_without_raising() -> None:
    assert parse_spine("", LABELS) is None
    assert parse_spine("I'm sorry, I can't help with that.", LABELS) is None
    assert parse_spine("[1, 2, 3]", LABELS) is None
    fenced = f"Here you go:\n```json\n{reply()}\n```\nHope that helps."
    assert parse_spine(fenced, LABELS) is not None


def test_a_generated_spine_says_so() -> None:
    """roadmap.py words authored edges as "a common route, not a requirement".
    No human wrote this one and no outcome data supports it, so it must not
    inherit that wording."""
    spine = parse_spine(reply(), LABELS)
    assert spine["source"] == "generated"


def test_the_prompt_offers_only_real_matches_and_real_keys() -> None:
    """The model may name a programme only if the student is actually matched to
    it, so the prompt carries the match list and says so."""
    prompt = build_prompt(
        {"grade": 11, "chosen_archetype": "bioethicist",
         "trait_scores": {"rigor": 0.9}, "field_scores": {"biology": 0.8}},
        [{"title": "Regeneron Science Talent Search", "opportunity_field": "biology",
          "deadline": "2026-11-10"}],
        [{"skill_key": "evaluation", "skill_label": LABELS["evaluation"]}],
    )
    assert "Regeneron Science Talent Search" in prompt
    assert "the only programmes you may name" in prompt
    assert "evaluation" in prompt
    assert "Grade: 11" in prompt
    # No matches is a legitimate state and must not produce a bare list.
    empty = build_prompt({"grade": 9}, [], [{"skill_key": "evaluation", "skill_label": "x"}])
    assert "none yet" in empty


# --- how a generated spine is described to the student -------------------


def test_a_generated_step_is_not_called_a_common_route() -> None:
    """"A common route" is a claim about what students generally do. It is true
    of the twenty-four authored spines, because a person wrote each after
    looking at the field. It is not true of a sentence the model wrote for one
    student this week: nobody has seen anyone follow it, and public.outcomes
    still has no rows. Same wording for both would launder a guess into a
    pattern -- the same error as showing an unconfirmed deadline as confirmed.
    """
    from datetime import date

    from app.roadmap import build_roadmap

    authored = {"project": "Build a thing", "publish": "Post it",
                "skill": "evaluation — why", "skillKey": "evaluation"}
    generated = {**authored, "source": "generated"}

    def notes(spine: dict) -> str:
        """Only the two steps the spine supplies.

        Not every edge note on the page: the mentorship step legitimately reads
        "A common route: most students never send the email", and that one IS
        authored, so sweeping up the whole plan would make this test fail for
        the right wording in the wrong place.
        """
        plan = build_roadmap(
            student={"grade": 10, "chosen_archetype": "applied-ai-builder"},
            ranked=[], spine=spine, resources=[], missions=[],
            today=date(2026, 10, 4),
        )
        return " ".join(
            step.get("edge_note", "")
            for phase in plan["phases"]
            for step in phase["steps"]
            if str(step.get("step_key", "")).startswith("spine:")
        )

    assert "A common route" in notes(authored)
    said = notes(generated)
    assert "A common route" not in said, (
        "a model-written step inherited the wording reserved for authored ones"
    )
    assert "Written for you" in said
    assert "not a route anyone has walked" in said


def test_trait_scores_are_already_out_of_100_and_must_not_be_scaled_again() -> None:
    """students.trait_scores is stored 0-100, not 0-1.

    build_prompt multiplied by 100 anyway, so the model was handed "builder
    7000%, executionTempo 6700%, analyst 4500%" — which is not a trait profile,
    it is noise with a percent sign on it, and it was the input to every
    personalised plan this endpoint has ever written.
    """
    from app.spine_generation import build_prompt

    prompt = build_prompt(
        {
            "grade": 12,
            "trait_scores": {"builder": 70.0, "analyst": 45.0, "collaboration": 17.0},
            "field_scores": {"math": 21.0},
        },
        matches=[],
        skill_keys=[{"skill_key": "statistics", "skill_label": "statistics — x"}],
    )
    assert "builder 70" in prompt
    assert "7000" not in prompt
    # And the scale is stated, because the numbers no longer carry a unit.
    assert "out of 100" in prompt


def test_the_spine_call_asks_for_json_and_not_for_thinking() -> None:
    """The settings that make the reply parseable at all.

    Measured against the configured model: with neither of these, 700 tokens
    went entirely on "We need to produce JSON with three keys... Let's think:
    they lean math, business, design. They " — truncated mid-sentence, the JSON
    object never emitted, parse_spine found no braces, and the endpoint refused
    with "the path that came back did not meet the bar" on every request. The
    verifier learned the same lesson in app/verifier.py and says so there.
    """
    import inspect

    from app import main as main_mod

    src = inspect.getsource(main_mod.create_app)
    start = src.index('@app.post("/roadmap/spine")')
    body = src[start : src.index("return {**spine", start)]

    assert 'response_format={"type": "json_object"}' in body
    assert 'reasoning_effort="none"' in body
    # And headroom, because reasoning_effort is dropped by providers that do not
    # know it and the preamble comes back anyway.
    assert "max_tokens=700" not in body
