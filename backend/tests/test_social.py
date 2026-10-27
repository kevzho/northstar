"""
Unit tests for the peer-affinity math, pure, no database.
"""

from app.social import affinity, leading_fields


def test_leading_fields_ranks_and_drops_zeros() -> None:
    scores = {"cs": 40, "math": 30, "biology": 0, "design": 10}
    assert leading_fields(scores, top=2) == ["cs", "math"]
    assert "biology" not in leading_fields(scores)


def test_shared_fields_drive_affinity_with_readable_reason() -> None:
    me = {"field_scores": {"cs": 50, "math": 30}}
    other = {"field_scores": {"cs": 40, "math": 35}}
    score, reasons = affinity(me, other)
    assert score >= 2.0  # two shared leading fields
    assert any("both into" in r for r in reasons)


def test_same_path_adds_a_strong_bonus() -> None:
    me = {"field_scores": {"cs": 60}, "chosen_archetype": "applied-ai-builder"}
    same = {"field_scores": {"cs": 60}, "chosen_archetype": "applied-ai-builder"}
    diff = {"field_scores": {"cs": 60}, "chosen_archetype": "data-scientist"}
    assert affinity(me, same)[0] > affinity(me, diff)[0]
    assert any("same path" in r for r in affinity(me, same)[1])


def test_no_overlap_scores_zero() -> None:
    me = {"field_scores": {"cs": 100}}
    other = {"field_scores": {"humanities": 100}}
    assert affinity(me, other)[0] == 0.0


def test_missing_field_scores_do_not_crash() -> None:
    assert leading_fields(None) == []
    assert affinity({}, {})[0] == 0.0
