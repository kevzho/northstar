"""
Read path for public.learning_resources, the free material a roadmap step
points at.

Kept deliberately small and separate from app/match.py: resources are not
ranked against a student profile the way opportunities are. A student on the
"statistics" rung needs the statistics resources, ordered so the gentlest entry
point comes first. There is nothing to score.

Only rows that survive every honesty check are served: not retired, marked
free, and carrying the quoted evidence that proves it. A row without evidence
is a claim nobody checked, and this catalog exists for students with no money.
"""

from __future__ import annotations

import time

CACHE_TTL_S = 300

# Gentlest first. A student who has never met the topic should hit the
# interactive or documentation entry before a 300-page textbook.
KIND_ORDER = {
    "interactive": 0,
    "documentation": 1,
    "course": 2,
    "problem-set": 3,
    "video-series": 4,
    "pdf": 5,
    "textbook": 6,
}

# What a visitor needs to decide whether a resource is worth their evening,
# and nothing about how it got here. An allowlist, so a column added to the
# table later is private until someone decides otherwise -- the same stance
# /catalog/public takes.
SHELF_FIELDS = (
    "id", "title", "host", "url", "kind", "skill_key", "skill_label",
    "effort", "prerequisite", "why_this_one", "free_evidence",
)

_cache: dict[str, tuple[float, list[dict]]] = {}
_shelf: tuple[float, list[dict]] | None = None


def _order(row: dict) -> tuple[int, str]:
    return (KIND_ORDER.get(row.get("kind", ""), 9), row.get("title", ""))


def fetch_for_skill(sb, skill_key: str, *, limit: int = 4) -> list[dict]:
    """Verified free resources for one spine skill rung, gentlest first."""
    if not skill_key or not isinstance(skill_key, str) or len(skill_key) > 64:
        return []

    cached = _cache.get(skill_key)
    if cached and time.time() - cached[0] < CACHE_TTL_S:
        return cached[1][:limit]

    rows = (
        sb.table("learning_resources")
        .select(
            "id, title, host, url, kind, skill_key, skill_label, effort, "
            "prerequisite, why_this_one, free_evidence, verified_at"
        )
        .eq("skill_key", skill_key)
        .eq("is_free", True)
        .is_("retired_at", "null")
        .limit(20)
        .execute()
    ).data or []

    # The free claim must carry its receipt. A row whose evidence went missing
    # is not shown, rather than shown on trust.
    rows = [r for r in rows if (r.get("free_evidence") or "").strip()]
    rows.sort(key=_order)

    _cache[skill_key] = (time.time(), rows)
    return rows[:limit]


def clear_cache() -> None:
    global _shelf
    _cache.clear()
    _shelf = None


def fetch_shelf(sb) -> list[dict]:
    """Every verified free resource, for the browsable hub.

    WHY THIS EXISTS. ``fetch_for_skill`` serves one rung of one path, reachable
    only as a side effect of a roadmap step -- so a student who wanted to learn
    something the plan had not told them to learn could not get at this shelf at
    all, and a visitor with no account could not see that it existed. Northstar
    was an opportunity hub with a learning catalog hidden inside it.

    Same honesty gate as the per-skill read, applied to the whole shelf: not
    retired, marked free, and carrying the quoted evidence from the page that
    proves the free claim. A row without evidence is a claim nobody checked, and
    this catalog exists for students with no money.

    Ordered skill group first, then gentlest entry point within it, so the shelf
    reads as a set of subjects rather than an undifferentiated list.
    """
    global _shelf
    if _shelf and time.time() - _shelf[0] < CACHE_TTL_S:
        return _shelf[1]

    rows = (
        sb.table("learning_resources")
        .select(", ".join((*SHELF_FIELDS, "opportunity_field")))
        .eq("is_free", True)
        .is_("retired_at", "null")
        .limit(1000)
        .execute()
    ).data or []

    out: list[dict] = []
    for row in rows:
        if not (row.get("free_evidence") or "").strip():
            continue
        item = {k: row.get(k) for k in SHELF_FIELDS}
        item["field"] = row.get("opportunity_field")
        out.append(item)

    out.sort(key=lambda r: (r.get("skill_label") or "", *_order(r)))
    _shelf = (time.time(), out)
    return out
