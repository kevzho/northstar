"""
ALS collaborative filtering — math and blend behavior.

No credentials, no artifact file: training runs in-memory on toy matrices,
and the blend tests inject factors through the loader's cache.
"""

import app.collab as collab
from app.collab import (
    STATUS_RATING,
    collaborative_scores,
    fold_in_user,
    predict,
    solve,
    train_als,
)
from app.match import score_opportunities


def make_interactions() -> list[tuple[str, str, float]]:
    """Two taste clusters: STEM-a users love a-items, hate b-items; vice versa."""
    rows = []
    for u in range(6):
        for i in range(4):
            rows.append((f"a{u}", f"item_a{i}", 1.0))
            rows.append((f"a{u}", f"item_b{i}", -0.5))
            rows.append((f"b{u}", f"item_b{i}", 1.0))
            rows.append((f"b{u}", f"item_a{i}", -0.5))
    return rows


def test_solve_recovers_known_solution() -> None:
    # A x = b with known x = [2, -1]
    a = [[3.0, 1.0], [1.0, 2.0]]
    b = [5.0, 0.0]
    x = solve(a, b)
    assert abs(x[0] - 2.0) < 1e-9
    assert abs(x[1] - (-1.0)) < 1e-9


def test_training_reconstructs_with_low_error() -> None:
    interactions = make_interactions()
    users, items, rmse = train_als(interactions, n_factors=4, iterations=10)
    # This toy matrix converges within the first sweep; the meaningful claims
    # are near-perfect reconstruction and stability, not monotonic descent.
    assert rmse[-1] < 0.2
    assert max(rmse) < 0.5
    # Reconstruction keeps the taste structure, not just low error:
    assert predict(users["a0"], items["item_a1"]) > predict(
        users["a0"], items["item_b1"]
    )


def test_fold_in_matches_cluster_preferences() -> None:
    interactions = make_interactions()
    _, items, _ = train_als(interactions, n_factors=4, iterations=10)
    # A brand-new student who loved one a-item and rejected one b-item
    # should rank unseen a-items above unseen b-items.
    vec = fold_in_user(
        [("item_a0", 1.0), ("item_b0", -0.5)], items, n_factors=4, l2=0.1
    )
    assert vec is not None
    assert predict(vec, items["item_a2"]) > predict(vec, items["item_b2"])


def test_fold_in_with_no_known_items_returns_none() -> None:
    interactions = make_interactions()
    _, items, _ = train_als(interactions, n_factors=4, iterations=5)
    assert fold_in_user([("unknown", 1.0)], items, 4, 0.1) is None


def _install_artifact(monkeypatch, items: dict) -> None:
    collab.load_item_factors.cache_clear()
    monkeypatch.setattr(
        collab, "load_item_factors", lambda: {"k": 4, "l2": 0.1, "items": items}
    )


def test_collaborative_scores_bounded_and_empty_without_outcomes(monkeypatch) -> None:
    interactions = make_interactions()
    _, items, _ = train_als(interactions, n_factors=4, iterations=10)
    _install_artifact(monkeypatch, items)

    assert collaborative_scores([], ["item_a0"]) == {}

    scores = collaborative_scores(
        [{"opportunity_id": "item_a0", "status": "accepted"}],
        list(items.keys()),
    )
    assert scores
    assert all(0.0 <= s <= 1.0 for s in scores.values())


def _catalog() -> list[dict]:
    base = {
        "blurb": "", "description": "", "tags": [], "cost": 0,
        "grade_min": 9, "grade_max": 12, "host": "Org",
    }
    return [
        {**base, "id": "item_a0", "title": "Robotics research program",
         "opportunity_field": "engineering", "type": "program"},
        {**base, "id": "item_b0", "title": "Robotics research program",
         "opportunity_field": "engineering", "type": "program"},
    ]


def test_blend_breaks_ties_using_outcomes(monkeypatch) -> None:
    """Two textually identical opportunities: outcomes decide the order."""
    interactions = make_interactions()
    _, items, _ = train_als(interactions, n_factors=4, iterations=10)
    _install_artifact(monkeypatch, items)

    student = {"grade": "11", "interests": ["Engineering"], "goals": "robotics research"}
    outcomes = [{"opportunity_id": "item_a1", "status": "accepted"}]

    ranked = score_opportunities(student, _catalog(), outcomes)
    assert ranked[0]["score"]["opportunity_id"] == "item_a0"
    delta = ranked[0]["score"]["score"] - ranked[1]["score"]["score"]
    assert 0.0 < delta <= 2 * 0.075 + 1e-9

    # The lift is explained in the student's terms.
    assert "outcomes like yours" in ranked[0]["score"]["explanation"]


def test_no_artifact_means_identical_scores(monkeypatch) -> None:
    collab.load_item_factors.cache_clear()
    monkeypatch.setattr(collab, "load_item_factors", lambda: None)
    student = {"grade": "11", "interests": ["Engineering"], "goals": "robotics"}
    outcomes = [{"opportunity_id": "item_a1", "status": "accepted"}]
    with_outcomes = score_opportunities(student, _catalog(), outcomes)
    without = score_opportunities(student, _catalog())
    assert [r["score"]["score"] for r in with_outcomes] == [
        r["score"]["score"] for r in without
    ]


def test_status_ratings_mirror_edge_weight_signs() -> None:
    assert STATUS_RATING["accepted"] > STATUS_RATING["completed"] > 0
    assert STATUS_RATING["waitlisted"] > 0
    assert STATUS_RATING["rejected"] < STATUS_RATING["withdrew"] < 0
