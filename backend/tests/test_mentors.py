"""Behavioural tests for the mentor matching engine (backend/app/mentors.py)."""

from __future__ import annotations

from app.mentors import score_mentors

STUDENT = {
    "id": "s1",
    "grade": "11",
    "interests": ["Computer Science"],
    "goals": "I want to work on machine learning systems.",
}


def _mentor(**over) -> dict:
    base = {
        "id": "m1",
        "name": "Pat Doe",
        "email": "pat@example.com",
        "bio": "",
        "expertise": [],
    }
    base.update(over)
    return base


def test_empty_catalog_returns_empty() -> None:
    assert score_mentors(STUDENT, []) == []


def test_student_with_no_signal_returns_empty() -> None:
    blank = {"id": "s1", "interests": [], "goals": ""}
    assert score_mentors(blank, [_mentor()]) == []


def test_results_are_sorted_and_bounded() -> None:
    catalog = [
        _mentor(id="a", bio="Machine learning researcher.", expertise=["cs"]),
        _mentor(id="b", bio="Marine biologist.", expertise=["biology"]),
        _mentor(id="c", bio="Structural engineer.", expertise=["engineering"]),
    ]
    results = score_mentors(STUDENT, catalog)

    assert len(results) == len(catalog)
    scores = [r["score"]["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 <= s <= 1.0 for s in scores)


def test_expertise_match_outranks_unrelated() -> None:
    catalog = [
        _mentor(id="cs", bio="I build machine learning systems.", expertise=["cs"]),
        _mentor(id="bio", bio="I study coral reefs.", expertise=["biology"]),
    ]
    results = score_mentors(STUDENT, catalog)
    assert results[0]["score"]["mentor_id"] == "cs"


def test_expertise_booster_is_explained() -> None:
    result = score_mentors(STUDENT, [_mentor(expertise=["cs"])])[0]
    assert "expertise" in result["score"]["explanation"].lower()


def test_breadth_booster_fires_for_three_or_more_fields() -> None:
    broad = score_mentors(STUDENT, [_mentor(id="x", expertise=["cs", "math", "physics"])])[0]
    narrow = score_mentors(STUDENT, [_mentor(id="x", expertise=["cs"])])[0]
    assert broad["score"]["score"] > narrow["score"]["score"]


def test_every_result_has_id_and_explanation() -> None:
    results = score_mentors(STUDENT, [_mentor(id="a"), _mentor(id="b", expertise=["cs"])])
    for r in results:
        assert r["score"]["mentor_id"]
        assert r["score"]["explanation"].strip()
        assert set(r) == {"mentor", "score"}
