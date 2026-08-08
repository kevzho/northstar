"""
Behavioural tests for the TF-IDF match engine (backend/app/match.py).

These pin the properties the student can defend in the CAC interview: ranking is
driven by profile overlap, the documented boosters actually fire, the score stays
in [0, 1], and the explanation names the reason. The booster magnitudes belong to
the student (ARCHITECTURE.md §2) — the tests assert relationships, not constants,
so tuning the numbers does not break the suite.
"""

from __future__ import annotations

from app.match import score_opportunities

STUDENT = {
    "id": "s1",
    "grade": "11",
    "interests": ["Computer Science"],
    "goals": "I want to build machine learning tools for hospitals.",
}


def _opp(**over) -> dict:
    base = {
        "id": "o1",
        "title": "Summer Program",
        "host": "Some University",
        "opportunity_field": "cs",
        "type": "program",
        "blurb": "",
        "description": "",
        "cost": 0,
        "grade_min": 9,
        "grade_max": 12,
        "url": "https://example.com",
        "tags": [],
    }
    base.update(over)
    return base


def test_empty_catalog_returns_empty() -> None:
    assert score_opportunities(STUDENT, []) == []


def test_student_with_no_signal_returns_empty() -> None:
    blank = {"id": "s1", "grade": "11", "interests": [], "goals": ""}
    assert score_opportunities(blank, [_opp()]) == []


def test_scores_are_bounded_and_sorted() -> None:
    catalog = [
        _opp(id="a", title="Machine Learning for Hospitals", description="machine learning"),
        _opp(id="b", opportunity_field="physics", title="Particle Physics Camp"),
        _opp(id="c", title="Robotics Build Season", opportunity_field="engineering"),
    ]
    results = score_opportunities(STUDENT, catalog)

    assert len(results) == len(catalog)
    scores = [r["score"]["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 <= s <= 1.0 for s in scores)


def test_semantic_overlap_outranks_unrelated() -> None:
    catalog = [
        _opp(id="match", title="Machine Learning in Medicine",
             description="Students build machine learning tools for hospitals."),
        _opp(id="other", opportunity_field="physics", title="Astronomy Night",
             description="Telescope observation of distant galaxies."),
    ]
    results = score_opportunities(STUDENT, catalog)
    assert results[0]["score"]["opportunity_id"] == "match"


def test_field_booster_fires_for_mapped_interest() -> None:
    """"Computer Science" must map onto the `cs` field enum."""
    on_field = score_opportunities(STUDENT, [_opp(id="x", opportunity_field="cs")])[0]
    off_field = score_opportunities(STUDENT, [_opp(id="x", opportunity_field="physics")])[0]

    assert on_field["score"]["score"] > off_field["score"]["score"]
    assert "field matches" in on_field["score"]["explanation"].lower()


def test_grade_booster_respects_range() -> None:
    eligible = score_opportunities(STUDENT, [_opp(grade_min=9, grade_max=12)])[0]
    too_senior = score_opportunities(STUDENT, [_opp(grade_min=6, grade_max=8)])[0]

    assert eligible["score"]["score"] > too_senior["score"]["score"]
    assert "grade" in eligible["score"]["explanation"].lower()


def test_unparseable_grade_does_not_crash() -> None:
    student = dict(STUDENT, grade="Gap year")
    results = score_opportunities(student, [_opp()])
    assert 0.0 <= results[0]["score"]["score"] <= 1.0


def test_cost_booster_prefers_free() -> None:
    free = score_opportunities(STUDENT, [_opp(cost=0)])[0]
    paid = score_opportunities(STUDENT, [_opp(cost=4500)])[0]

    assert free["score"]["score"] > paid["score"]["score"]
    assert "funded" in free["score"]["explanation"].lower()


def test_tag_overlap_boosts_and_is_explained() -> None:
    tagged = score_opportunities(STUDENT, [_opp(tags=["computer", "science"])])[0]
    untagged = score_opportunities(STUDENT, [_opp(tags=["welding"])])[0]

    assert tagged["score"]["score"] > untagged["score"]["score"]
    assert "tag" in tagged["score"]["explanation"].lower()


def test_field_key_accepts_either_column_name() -> None:
    """Rows come back as `opportunity_field` from Postgres, `field` from the API."""
    a = score_opportunities(STUDENT, [_opp(id="x", opportunity_field="cs")])[0]
    row = _opp(id="x")
    del row["opportunity_field"]
    row["field"] = "cs"
    b = score_opportunities(STUDENT, [row])[0]

    assert a["score"]["score"] == b["score"]["score"]


def test_every_result_carries_an_explanation() -> None:
    results = score_opportunities(STUDENT, [_opp(id="a"), _opp(id="b", cost=100)])
    for r in results:
        assert r["score"]["explanation"].strip()
        assert r["score"]["opportunity_id"]
