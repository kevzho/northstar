"""
Unit tests for the GitHub project ranking, pure function, no network.
"""

from datetime import datetime, timedelta, timezone

from app.projects import STARS_MAX, STARS_MIN, _build_query, rank_repos


def _repo(**overrides) -> dict:
    base = {
        "full_name": "org/repo",
        "html_url": "https://github.com/org/repo",
        "description": "A useful thing",
        "stargazers_count": 1200,
        "language": "Python",
        "topics": ["robotics"],
        "license": {"key": "mit"},
        "homepage": "https://docs.example.com",
        "pushed_at": datetime.now(timezone.utc).isoformat(),
    }
    base.update(overrides)
    return base


def test_fresh_documented_repo_outranks_stale_bare_one() -> None:
    stale = _repo(
        full_name="org/stale",
        pushed_at=(datetime.now(timezone.utc) - timedelta(days=400)).isoformat(),
        description="",
        homepage=None,
        license=None,
    )
    ranked = rank_repos([stale, _repo()], "engineering")
    assert ranked[0]["repo"]["full_name"] == "org/repo"
    assert ranked[0]["score"] > ranked[1]["score"]


def test_explanation_names_every_scored_signal() -> None:
    (result,) = rank_repos([_repo()], "engineering")
    explanation = result["explanation"]
    assert "topic robotics" in explanation
    assert "1,200 stars" in explanation
    assert "pushed this week" in explanation
    assert "good first issues" in explanation
    assert "licensed" in explanation


def test_good_first_issues_url_is_built() -> None:
    (result,) = rank_repos([_repo()], "cs")
    assert "label:%22good+first+issue%22" in result["repo"][
        "good_first_issues_url"
    ].replace('"', "%22").replace(" ", "+")


def test_query_encodes_approachability_gates() -> None:
    query = _build_query("biology")
    assert "topic:bioinformatics" in query
    assert "good-first-issues:>1" in query
    assert f"stars:{STARS_MIN}..{STARS_MAX}" in query
    assert "archived:false" in query


def test_unknown_field_falls_back_to_interdisciplinary_topic() -> None:
    assert "topic:data-science" in _build_query("underwater-basket-weaving")


def test_malformed_pushed_at_scores_zero_freshness_not_crash() -> None:
    (result,) = rank_repos([_repo(pushed_at="not-a-date")], "math")
    assert "pushed this week" not in result["explanation"]
    assert result["score"] > 0  # other signals still count
