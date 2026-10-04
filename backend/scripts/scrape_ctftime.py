"""
CTFtime -> candidate pool. Security capture-the-flag events an individual can enter.

WHY THIS SOURCE. The shelf's problem was never total rows, it was rows a student
can act on TODAY: of 55 high-school entries, four were open. Annual programmes
cannot fix that — their deadlines cluster in winter by nature. Recurring
competitions can, because something is always open.

CTFtime's public API is the cleanest example: no auth, and it publishes the one
field most sources omit — `restrictions`, which says who is allowed to enter.

    Open (32)          anyone, including a 15-year-old with a laptop
    Casual (1)         same, informally run
    Prequalified (6)   you must already have qualified elsewhere
    Academic (3)       restricted to enrolled students at institutions

Only Open and Casual are imported. Prequalified is `entry_gate='qualify'` by
another name, and importing it would repeat the error this catalog just spent a
day undoing: 15 rows that carried an application deadline for something you
cannot apply to. Academic is dropped because the restriction is usually
university enrolment, which a high schooler does not have, and the API does not
say which.

FIELD IS ALWAYS cs, AND THAT IS THE RISK. Every high-volume competition feed
available is computer science. app/match.py boosts a field match, so pouring
these in unbounded would make a student who wrote "biology" start seeing CTFs.
MAX_IMPORT caps the damage; balance comes from curating non-CS competitions,
which no API provides.

Usage:
    cd backend && .venv/bin/python scripts/scrape_ctftime.py
"""

from __future__ import annotations

import json
import pathlib
import re
from datetime import datetime, timedelta, timezone

import requests

POOL = pathlib.Path(__file__).parent / "scraped" / "reddit_candidates.json"
API = "https://ctftime.org/api/v1/events/"

# CTFtime asks for a descriptive User-Agent and returns 403 without one.
USER_AGENT = "northstar-catalog/1.0 (student nonprofit opportunity map)"

# How far ahead to look. A CTF announced more than a season out is rare, and a
# deadline further away than this is not something a student acts on now.
HORIZON_DAYS = 120

# Ceiling per run. Not a rate limit — a relevance limit. See the field note above.
MAX_IMPORT = 25

# Entry restrictions an unaffiliated individual can satisfy.
OPEN_RESTRICTIONS = {"Open", "Casual"}


def main() -> None:
    pool_entries = json.loads(POOL.read_text()) if POOL.exists() else []
    pool = {e["url"]: e for e in pool_entries}
    known = len(pool)

    now = datetime.now(timezone.utc)
    try:
        response = requests.get(
            API,
            params={
                "limit": 100,
                "start": int(now.timestamp()),
                "finish": int((now + timedelta(days=HORIZON_DAYS)).timestamp()),
            },
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=25,
        )
        response.raise_for_status()
        events = response.json()
    except (requests.RequestException, ValueError) as error:
        print(f"ctftime: skipped ({error})")
        return

    added = skipped_gated = 0
    for event in events:
        if added >= MAX_IMPORT:
            break
        restriction = (event.get("restrictions") or "").strip()
        if restriction not in OPEN_RESTRICTIONS:
            skipped_gated += 1
            continue

        # Prefer the event's own site; fall back to its CTFtime page, which
        # always exists and always resolves.
        url = (event.get("url") or "").strip() or (event.get("ctftime_url") or "").strip()
        if not url or url in pool:
            continue

        title = (event.get("title") or "").strip()
        if not title:
            continue

        # The deadline is when it STARTS, not when it finishes: a student who
        # arrives after kickoff has missed it. Stored as a date because
        # opportunities.deadline is a date column.
        start = (event.get("start") or "")[:10] or None
        onsite = bool(event.get("onsite"))
        fmt = (event.get("format") or "").strip()
        players = event.get("participants") or 0
        dur = event.get("duration") or {}
        hours = (dur.get("days") or 0) * 24 + (dur.get("hours") or 0)
        # Long-running CTFs are real — some stay open for weeks — and "1680h"
        # is not a length a person can picture.
        span = (
            f"{round(hours / 24)} days" if hours >= 72
            else f"{hours}h" if hours else ""
        )
        weight = event.get("weight") or 0
        where = (event.get("location") or "").strip()
        # CTFtime's own description, trimmed. This is the field that actually
        # differentiates one event from another.
        blurb_src = " ".join((event.get("description") or "").split())[:240]

        pool[url] = {
            "source": "ctftime",
            "reddit_permalink": "",
            "posted_utc": now.isoformat(),
            "score": 0,
            "title": title,
            "url": url,
            # WHY THIS IS SO DETAILED. The first version read "{format}
            # security competition, online, open entry" for every event, so nine
            # CTFs produced byte-identical text after the title, TF-IDF scored
            # them at exactly 0.4219, and a CS-focused student got six
            # interchangeable rows in a row. Identical inputs SHOULD score
            # identically — the bug was feeding the matcher nothing to tell them
            # apart. Duration, difficulty weight, venue and the organiser's own
            # description differentiate them, and they are what a student
            # actually chooses between: a 48-hour attack-defense event and a
            # 12-hour beginner jeopardy CTF are not the same evening.
            "blurb": (
                f"{fmt or 'Capture-the-flag'} security competition, "
                f"{where or ('in person' if onsite else 'online')}, open entry."
                + (f" Runs {span}." if span else "")
                + (f" {players} teams registered." if players else "")
                + (
                    f" Rated {weight:.1f} on CTFtime"
                    + (
                        " — beginner-friendly."
                        if weight and weight < 20
                        else " — competitive field."
                        if weight
                        else "."
                    )
                    if weight
                    else ""
                )
                + (f" Starts {start}." if start else "")
                + " Solo entry is permitted."
                + (f" {blurb_src}" if blurb_src else "")
            ),
            "deadline_guess": start,
            "field_guess": "cs",
            "type_guess": "competition",
            # Open CTFs genuinely accept high schoolers, and the high-school
            # shelf is the one starved of open deadlines — but see the field
            # note in the module docstring: this is capped for a reason.
            "audience_guess": "high_school",
            # public.location_scope takes us/international/global and nothing
            # else. This field said "onsite" from the day the feed was written,
            # so every in-person CTF was rejected by postgres on insert and the
            # loss was invisible -- the run reported a verdict, the row never
            # landed. An online CTF is genuinely global; an onsite one is placed
            # by its own location string, and defaults to international because
            # most of this feed is not American.
            "location_guess": (
                "global" if not onsite
                else "us" if re.search(
                    r"\b(usa|united states|u\.s\.|[A-Z]{2})\s*$", where or "", re.I
                )
                else "international"
            ),
            "needs_review": True,
        }
        added += 1

    ordered = sorted(pool.values(), key=lambda c: c.get("score", 0), reverse=True)
    POOL.write_text(json.dumps(ordered, indent=2))
    print(
        f"ctftime: {len(events)} events in the next {HORIZON_DAYS} days, "
        f"{skipped_gated} skipped as gated, {added} new candidates "
        f"(pool {known} -> {len(pool)})"
    )


if __name__ == "__main__":
    main()
