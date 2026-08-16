"""
The social layer: opt-in public profiles, friendships, and comparison.

Design boundaries, chosen deliberately for an audience that includes
minors:
- Everything is opt-in. public_profile defaults false; a student without
  a handle cannot be found or friended.
- The public page shows highlights only: first name, trait/field shape,
  completed missions, and POSITIVE outcomes (accepted/completed).
  Rejections are never public.
- The full side-by-side comparison is reserved for accepted friendships,
  and even then shows counts for negative outcomes, not which programs.
"""

from __future__ import annotations

import re

HANDLE_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,19}$")

PUBLIC_OUTCOME_STATUSES = ("accepted", "completed")


def valid_handle(handle: str) -> bool:
    return bool(HANDLE_RE.fullmatch(handle))


def first_name(name: str | None) -> str:
    return (name or "").strip().split(" ")[0] or "A student"


def public_payload(sb, student: dict) -> dict:
    """The shareable highlights for one student row (already vetted)."""
    sid = student["id"]

    completions = (
        sb.table("mission_completions")
        .select("evidence, created_at, missions(title, trait_focus)")
        .eq("student_id", sid)
        .order("created_at", desc=True)
        .execute()
    ).data or []

    outcomes = (
        sb.table("outcomes")
        .select("opportunity_id, status, created_at")
        .eq("student_id", sid)
        .in_("status", list(PUBLIC_OUTCOME_STATUSES))
        .order("created_at", desc=True)
        .execute()
    ).data or []
    titles = {}
    if outcomes:
        rows = sb.table("opportunities").select("id, title").execute().data or []
        titles = {r["id"]: r["title"] for r in rows}

    return {
        "handle": student.get("handle"),
        "name": first_name(student.get("name")),
        "audience": student.get("audience") or "high_school",
        "trait_scores": student.get("trait_scores"),
        "field_scores": student.get("field_scores"),
        "chosen_archetype": student.get("chosen_archetype"),
        "chosen_kind": student.get("chosen_kind"),
        "missions": [
            {
                "title": (c.get("missions") or {}).get("title", ""),
                "trait_focus": (c.get("missions") or {}).get("trait_focus", ""),
                "evidence": c.get("evidence", ""),
                "at": c.get("created_at"),
            }
            for c in completions
        ],
        "outcomes": [
            {
                "title": titles.get(o["opportunity_id"], "An opportunity"),
                "status": o["status"],
                "at": o.get("created_at"),
            }
            for o in outcomes
        ],
    }


def compare_payload(sb, student: dict) -> dict:
    """What accepted friends see of each other: shape + counts, side by side."""
    sid = student["id"]
    completions = (
        sb.table("mission_completions").select("id").eq("student_id", sid).execute()
    ).data or []
    outcomes = (
        sb.table("outcomes").select("status").eq("student_id", sid).execute()
    ).data or []
    by_status: dict[str, int] = {}
    for o in outcomes:
        by_status[o["status"]] = by_status.get(o["status"], 0) + 1

    return {
        "handle": student.get("handle"),
        "name": first_name(student.get("name")),
        "audience": student.get("audience") or "high_school",
        "trait_scores": student.get("trait_scores"),
        "field_scores": student.get("field_scores"),
        "chosen_archetype": student.get("chosen_archetype"),
        "chosen_kind": student.get("chosen_kind"),
        "missions_completed": len(completions),
        "outcome_counts": by_status,
    }
