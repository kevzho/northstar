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
from uuid import UUID

HANDLE_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,19}$")

PUBLIC_OUTCOME_STATUSES = ("accepted", "completed")

TEAMUP_PITCH_MAX = 240

REPORT_REASONS = ("inappropriate", "harassment", "impersonation", "spam", "other")
REPORT_DETAILS_MAX = 2000

SOCIAL_KEYS = ("github", "website", "youtube", "linkedin")
SOCIAL_URL_MAX = 200


def clean_social_links(links: dict) -> dict:
    """Validate and normalize the student-entered social links.

    Allowlisted keys only, https:// prepended when the scheme is missing,
    and anything that does not parse to an http(s) URL with a dotted host
    raises ValueError (the route turns that into a 422).
    """
    from urllib.parse import urlparse

    if not isinstance(links, dict):
        raise ValueError("social_links must be an object")
    out: dict[str, str] = {}
    for key in SOCIAL_KEYS:
        url = str(links.get(key, "") or "").strip()
        if not url:
            continue
        if len(url) > SOCIAL_URL_MAX:
            raise ValueError(f"{key} link is too long")
        if not url.lower().startswith(("http://", "https://")):
            url = "https://" + url
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or "." not in parsed.netloc:
            raise ValueError(f"{key} is not a valid link")
        out[key] = url
    return out


def mission_counts(sb, student_ids: list[str]) -> dict[str, int]:
    """Completed-mission counts for a set of students, in ONE query.

    Both discover and team-up used to fire one count query per candidate,
    which is where the pages' lag came from — a page of 12 candidates was
    12 extra round-trips.
    """
    if not student_ids:
        return {}
    rows = (
        sb.table("mission_completions")
        .select("student_id")
        .in_("student_id", student_ids)
        .execute()
    ).data or []
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["student_id"]] = counts.get(r["student_id"], 0) + 1
    return counts


def valid_handle(handle: str) -> bool:
    return bool(HANDLE_RE.fullmatch(handle))


def first_name(name: str | None) -> str:
    return (name or "").strip().split(" ")[0] or "A student"


def leading_fields(field_scores: dict | None, top: int = 3) -> list[str]:
    """The fields a student leans toward, strongest first."""
    if not isinstance(field_scores, dict):
        return []
    ranked = sorted(
        ((f, v) for f, v in field_scores.items() if isinstance(v, (int, float)) and v > 0),
        key=lambda kv: kv[1],
        reverse=True,
    )
    return [f for f, _ in ranked[:top]]


def affinity(me: dict, other: dict) -> tuple[float, list[str]]:
    """How much two students overlap, and the human reasons why.

    Interest-first: shared leading fields dominate, a shared chosen path
    adds a strong bonus. Returns (score, reasons) so the UI can show
    'why you two' instead of an opaque number.
    """
    mine = set(leading_fields(me.get("field_scores")))
    theirs = set(leading_fields(other.get("field_scores")))
    shared = mine & theirs

    reasons: list[str] = []
    score = 0.0
    if shared:
        score += 1.0 * len(shared)
        reasons.append(
            "both into " + ", ".join(sorted(shared))
        )
    if (
        me.get("chosen_archetype")
        and me.get("chosen_archetype") == other.get("chosen_archetype")
    ):
        score += 1.5
        reasons.append("charting the same path")
    elif (
        me.get("chosen_kind")
        and me.get("chosen_kind") == other.get("chosen_kind")
    ):
        score += 0.3

    return score, reasons


def discover_peers(sb, me: dict, exclude_ids: set[str], limit: int = 12) -> list[dict]:
    """Opted-in, same-audience students ranked by shared interests.

    Discovery is gated on public_profile: a student only appears here if
    they chose to be findable. Same audience only (high schoolers see
    high schoolers). Never returns anyone already connected or the
    student themselves.
    """
    audience = me.get("audience") or "high_school"
    rows = (
        sb.table("students")
        .select("id, name, handle, field_scores, chosen_archetype, chosen_kind")
        .eq("public_profile", True)
        .eq("audience", audience)
        .limit(200)
        .execute()
    ).data or []

    scored = []
    for other in rows:
        if other["id"] == me.get("id") or other["id"] in exclude_ids:
            continue
        if not other.get("handle"):
            continue
        score, reasons = affinity(me, other)
        if score <= 0:
            continue
        scored.append({
            "student_id": other["id"],
            "name": first_name(other.get("name")),
            "handle": other.get("handle"),
            "shared_fields": leading_fields(other.get("field_scores")),
            "chosen_archetype": other.get("chosen_archetype"),
            "reasons": reasons,
            "_score": score,
        })

    scored.sort(key=lambda p: p["_score"], reverse=True)
    top = scored[:limit]
    # Missions completed — the "what they're doing" learning hook —
    # batched into one query for just the page that will be shown.
    counts = mission_counts(sb, [p["student_id"] for p in top])
    for p in top:
        p["missions_completed"] = counts.get(p["student_id"], 0)
        del p["_score"]
    return top


def blocked_ids(sb, student_id: str) -> set[str]:
    """Everyone the student has blocked or been blocked by.

    Blocks are a hard wall in both directions: neither party appears in
    the other's discover, team-up pool, or friend requests.
    """
    # Coerced rather than trusted: this value is interpolated into a filter
    # string, and postgrest-py passes `.or_()` through verbatim. Every caller
    # passes the JWT-derived user.id today, but the safety of this line
    # should not depend on remembering that.
    sid = str(UUID(str(student_id)))
    rows = (
        sb.table("blocks")
        .select("blocker, blocked")
        .or_(f"blocker.eq.{sid},blocked.eq.{sid}")
        .execute()
    ).data or []
    return {
        (r["blocked"] if r["blocker"] == sid else r["blocker"])
        for r in rows
    }


def teamup_candidates(sb, me: dict, exclude_ids: set[str], limit: int = 8) -> list[dict]:
    """Opted-in, same-audience students ranked for collaboration fit.

    Like discover, but the pool is only students who explicitly enabled
    team-up matching, and nobody is dropped for low affinity — the pitch
    ("what I'm building") is signal the score can't see. A candidate's
    handle is exposed only when their profile is public, so team-up never
    leaks a private student's handle.
    """
    audience = me.get("audience") or "high_school"
    rows = (
        sb.table("students")
        .select(
            "id, name, handle, grade, field_scores, chosen_archetype,"
            " chosen_kind, teamup_pitch, public_profile"
        )
        .eq("teamup_enabled", True)
        .eq("audience", audience)
        .limit(200)
        .execute()
    ).data or []

    scored = []
    for other in rows:
        if other["id"] == me.get("id") or other["id"] in exclude_ids:
            continue
        score, reasons = affinity(me, other)
        scored.append({
            "student_id": other["id"],
            "name": first_name(other.get("name")),
            "handle": other.get("handle") if other.get("public_profile") else None,
            "grade": other.get("grade"),
            "fields": leading_fields(other.get("field_scores")),
            "chosen_archetype": other.get("chosen_archetype"),
            "pitch": (other.get("teamup_pitch") or "").strip(),
            "reasons": reasons,
            "_score": score,
        })

    scored.sort(key=lambda p: p["_score"], reverse=True)
    top = scored[:limit]
    counts = mission_counts(sb, [p["student_id"] for p in top])
    for p in top:
        p["missions_completed"] = counts.get(p["student_id"], 0)
        del p["_score"]
    return top


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
        # `audience` is deliberately absent here. This payload is served
        # unauthenticated by GET /public/{handle}, and "high_school" next to
        # a first name, behavioral trait scores and social links tells any
        # reader they are looking at a minor. Nothing renders it --
        # frontend/app/p/[handle]/page.tsx never reads the field.
        # compare_payload below is friends-only and still includes it.
        "trait_scores": student.get("trait_scores"),
        "field_scores": student.get("field_scores"),
        "chosen_archetype": student.get("chosen_archetype"),
        "chosen_kind": student.get("chosen_kind"),
        "social_links": student.get("social_links") or {},
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
