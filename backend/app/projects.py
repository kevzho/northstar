"""
GitHub project recommendations, what a student should build next.

Real repositories, not generated ideas. The GitHub Search API is queried
once per field with qualifiers that make every result approachable by
construction: it must carry open good-first-issues, sit in a stars band
that filters out both toys and monoliths, and have been pushed recently.
Ranking on top of that is a sum of visible signals, same philosophy as
the opportunity matcher in ``app/match.py``: every score is explainable
in one line.

Rate limits: unauthenticated search allows 10 requests/minute; setting
GITHUB_TOKEN in backend/.env raises it to 30. One query serves a field
for an hour via the in-process cache, so a handful of students browsing
stays far inside either limit.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import requests

from .settings import settings

SEARCH_URL = "https://api.github.com/search/repositories"
USER_AGENT = "northstar-project-recs/0.1 (student project)"

# One search topic per opportunity field. Topics are how GitHub's own
# explore surface groups repos, so they are well-populated and curated.
FIELD_TOPICS: dict[str, str] = {
    "cs": "machine-learning",
    "biology": "bioinformatics",
    "math": "mathematics",
    "physics": "astronomy",
    "engineering": "robotics",
    "interdisciplinary": "data-science",
    "design": "design-system",
    "business": "fintech",
    "humanities": "digital-humanities",
    "health": "healthcare",
}

# Approachability band: below the floor a repo is usually a personal toy
# with no issue flow to join; above the ceiling newcomers drown.
STARS_MIN = 50
STARS_MAX = 20_000

CACHE_TTL_S = 3600
_cache: dict[str, tuple[float, list[dict]]] = {}


def _build_query(field: str) -> str:
    topic = FIELD_TOPICS.get(field, FIELD_TOPICS["interdisciplinary"])
    pushed_after = (datetime.now(timezone.utc) - timedelta(days=120)).date()
    return (
        f"topic:{topic} good-first-issues:>1 "
        f"stars:{STARS_MIN}..{STARS_MAX} pushed:>{pushed_after} archived:false"
    )


def _fetch_repos(field: str) -> list[dict]:
    """One cached Search API call; empty list on any network failure."""
    query = _build_query(field)
    cached = _cache.get(query)
    if cached and time.time() - cached[0] < CACHE_TTL_S:
        return cached[1]

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    try:
        response = requests.get(
            SEARCH_URL,
            params={"q": query, "per_page": 12, "sort": "updated"},
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        items = response.json().get("items", [])
    except (requests.RequestException, ValueError):
        return cached[1] if cached else []

    _cache[query] = (time.time(), items)
    return items


def rank_repos(items: list[dict], field: str) -> list[dict]:
    """Pure ranking over raw Search API items, no network, unit-testable.

    Score components (each visible in the explanation):
      +0.30  stars, scaled within the approachability band
      +0.30  pushed within 14 days (0.15 within 60)
      +0.20  has a description (you can tell what it is)
      +0.10  has a homepage or docs link
      +0.10  permissive license present
    """
    now = datetime.now(timezone.utc)
    ranked = []
    for item in items:
        stars = item.get("stargazers_count", 0) or 0
        stars_score = 0.3 * min(stars, 5000) / 5000

        pushed_raw = item.get("pushed_at") or ""
        try:
            pushed = datetime.fromisoformat(pushed_raw.replace("Z", "+00:00"))
            days_stale = (now - pushed).days
        except ValueError:
            days_stale = 999
        fresh_score = 0.3 if days_stale <= 14 else 0.15 if days_stale <= 60 else 0.0

        described = bool((item.get("description") or "").strip())
        documented = bool(item.get("homepage"))
        licensed = bool(item.get("license"))

        score = round(
            stars_score
            + fresh_score
            + (0.2 if described else 0.0)
            + (0.1 if documented else 0.0)
            + (0.1 if licensed else 0.0),
            3,
        )

        bits = [f"topic {FIELD_TOPICS.get(field, field)}"]
        bits.append(f"{stars:,} stars")
        if fresh_score >= 0.3:
            bits.append("pushed this week")
        elif fresh_score > 0:
            bits.append("recently active")
        bits.append("has good first issues")
        if licensed:
            bits.append("licensed")

        full_name = item.get("full_name", "")
        ranked.append(
            {
                "field": field,
                "score": score,
                "explanation": " · ".join(bits),
                "repo": {
                    "full_name": full_name,
                    "html_url": item.get("html_url", ""),
                    "description": item.get("description") or "",
                    "stars": stars,
                    "language": item.get("language") or "",
                    "topics": item.get("topics", []) or [],
                    "good_first_issues_url": (
                        f"https://github.com/{full_name}/issues"
                        '?q=is:issue+is:open+label:"good first issue"'
                        if full_name
                        else ""
                    ),
                },
            }
        )
    return sorted(ranked, key=lambda r: r["score"], reverse=True)


def recommend_projects(fields: list[str], per_field: int = 5) -> list[dict]:
    """Top approachable repos for up to three fields, best first per field."""
    results: list[dict] = []
    for field in fields[:3]:
        results.extend(rank_repos(_fetch_repos(field), field)[:per_field])
    return results
