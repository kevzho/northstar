"""
Ceilings on the actions that cost a PERSON something.

The two LLM endpoints already had limits, because they cost money
(app/advisor.py#budget_block). The ones that cost somebody their afternoon had
none, which is the wrong way round for a product used by minors:

    friend_request   the harassment surface. Nothing stopped one account
                     sending a request to every student on the platform in a
                     loop, and "decline" does not undo having received it.
    report           the other half of that. A report queue anyone can flood is
                     a report queue nobody can read.
    handle           the impersonation surface. Handles are first-come,
                     3-20 characters, and appear on public pages; a loop could
                     take every plausible name a student might want.
    mentor_apply     unauthenticated, so this one is open to the whole
                     internet, not just to accounts. It writes to a table a
                     human reads before anything is published, and a human
                     reading ten thousand rows reads none of them.

WINDOWS ARE SLIDING, NOT CALENDAR. A daily counter that resets at midnight is a
ceiling plus a free burst at 00:01. Counting back from now costs the same query
and has no such edge.

LIMITS ARE DELIBERATELY GENEROUS. The purpose is to make abuse slow, not to
ration ordinary use: a student having an enthusiastic evening should never meet
one of these. Measured against what real use looks like, every number here is
at least ten times the busiest plausible hour.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

# (per-student limit, window in minutes, message). A None student limit means
# the action is counted globally only -- the unauthenticated case.
POLICIES: dict[str, tuple[int | None, int, str]] = {
    "friend_request": (
        40, 60,
        "That is a lot of connection requests in an hour. Give it a little "
        "while — the students you already asked can still accept.",
    ),
    "report": (
        20, 60,
        "You have sent a lot of reports in a short time. They are all in the "
        "queue; a person reads every one.",
    ),
    "handle": (
        10, 60,
        "You have changed your handle several times in the last hour. Pick one "
        "and give it an hour to settle.",
    ),
    "teamup": (
        30, 60,
        "You have registered a lot of team-up interest this hour. Give the "
        "matches you already have a chance to come back.",
    ),
    # The one limit here that is about MONEY rather than about people.
    #
    # /plan asks for a spine automatically when a student has never been
    # written one, which is the right behaviour and also the first thing in
    # this product that spends on its own initiative. One student needs exactly
    # one; the allowance is three in thirty days so that a reply which failed to
    # parse can be retried on a later visit, and no more, because a profile the
    # model keeps refusing would otherwise retry on every single page load for
    # the rest of the month.
    #
    # The attempt is counted BEFORE the call, not after it succeeds. Counting
    # successes would make a persistently failing generation free and therefore
    # infinite, which is exactly the runaway this exists to prevent.
    "auto_spine": (
        3, 60 * 24 * 30,
        "Northstar has already tried to write you a plan a few times and it did "
        "not come back usable. Your matches and deadlines are still here — pick "
        "a path on Future paths and you will get a project with it.",
    ),
    "mentor_apply": (
        None, 60,
        "This form has had a lot of submissions in the last hour. Try again "
        "shortly — every application is read by a person.",
    ),
}

# The global ceiling for every action, whoever sent it. Catches a distributed
# burst that no single per-student count would see.
GLOBAL_PER_WINDOW: dict[str, int] = {
    # A ceiling on the whole product's spend, not one student's. At three per
    # student this is ~130 students a day arriving with no path charted, which
    # is far above anything this has seen and far below anything that would
    # matter on the bill. It is the number to raise deliberately when real
    # signups start, and the one that stops a bug costing a month of credit
    # overnight.
    "auto_spine": 400,
    "friend_request": 2000,
    "report": 300,
    "handle": 500,
    "teamup": 1500,
    "mentor_apply": 60,
}


def _since(minutes: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


def _count(sb, action: str, since: str, student: str | None = None) -> int:
    query = (
        sb.table("rate_events")
        .select("id", count="exact")
        .eq("action", action)
        .gte("created_at", since)
    )
    if student is not None:
        query = query.eq("student_id", student)
    result = query.execute()
    return result.count or 0


def limit_block(sb, action: str, student: str | None) -> str | None:
    """Why this action must be refused, or None to let it through.

    Per-student first, because that message is the one a real person is most
    likely to see and it should name their own behaviour rather than the
    platform's. The global ceiling is checked second and says less, because a
    student who trips it has usually done nothing wrong.
    """
    policy = POLICIES.get(action)
    if policy is None:
        return None
    per_student, window, message = policy

    if per_student is not None and student is not None:
        if _count(sb, action, _since(window), student) >= per_student:
            return message

    ceiling = GLOBAL_PER_WINDOW.get(action)
    if ceiling is not None and _count(sb, action, _since(window)) >= ceiling:
        return (
            "This is busier than usual right now. Try again in a few minutes — "
            "nothing you have already done was lost."
        )
    return None


def record_event(sb, action: str, student: str | None) -> None:
    """Count one action.

    Never raises. A rate limiter that can 500 the endpoint it protects has
    turned a safeguard into an outage, and the failure mode of not counting one
    event is that somebody gets one extra request through.
    """
    try:
        sb.table("rate_events").insert(
            {"action": action, "student_id": student}
        ).execute()
    except Exception:  # noqa: BLE001 — see the docstring
        pass
