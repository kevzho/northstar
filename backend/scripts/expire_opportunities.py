"""
Retire scraped one-off events whose deadline has passed.

WHY THIS EXISTS. On 2026-09-25 the catalog held 186 live rows, and 123 of them
had a deadline that was already gone — 101 of those were Devpost hackathons the
scraper imported over the preceding weeks. Nothing ever removed them, because
the import path only ever adds. /opportunities orders by deadline ascending, so
the browse page opened on the single most-expired row in the catalog.

A large pool of dead listings is worse than a small live one: it is the failure
mode a student can detect in ten seconds, by clicking the first thing they see.

WHAT IS SAFE TO AUTOMATE, AND WHAT IS NOT.

Scraped events (added_by = 'ai') are one-off: a hackathon that closed on
2026-08-17 will not reopen, and the row carries no claim beyond that date. Once
the deadline passes the row is dead with certainty, so retiring it needs no
human.

Curated programmes (added_by in 'seed', 'human') are annual. RSI closes in
January every year. A past deadline there means "this year's cycle closed", not
"the programme ended", and the right repair is a fresh deadline or a verified
recurrence — both of which are human claims. 20260923120000 is explicit about
this: recurrence is "Only a human sets that, after checking the program's site.
Default NULL means the honest answer is 'no confirmed window'." So this script
reports curated expiries and changes nothing about them. Inferring next year's
date from last year's is exactly the fabrication that column exists to prevent.

Retirement is a stamp, not a DELETE — outcomes, bookmarks, matches and
dismissals all cascade from opportunities(id), so deleting would destroy a
student's logged history.

Idempotent: a retired row is filtered out of the next run's query.

Usage:
    cd backend && .venv/bin/python scripts/expire_opportunities.py [--dry-run]
"""

from __future__ import annotations

import pathlib
import sys
from datetime import date, datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.db import get_supabase  # noqa: E402

# Sources whose rows describe a single dated event rather than a recurring
# programme. Keep this narrow: adding 'seed' here would silently retire RSI
# every February.
ONE_OFF_SOURCES = ("ai",)

# A small grace window. A deadline is a date, not an instant, and entrants in
# later timezones are still submitting after UTC midnight. Retiring a listing
# the same day it closes would cut off the students most likely to act on it.
GRACE_DAYS = 2


def main() -> int:
    dry = "--dry-run" in sys.argv
    sb = get_supabase()
    today = date.today()
    cutoff = date.fromordinal(today.toordinal() - GRACE_DAYS).isoformat()
    stamp = datetime.now(timezone.utc).isoformat()

    rows = (
        sb.table("opportunities")
        .select("id, title, audience, added_by, deadline")
        .is_("retired_at", "null")
        .not_.is_("deadline", "null")
        .lt("deadline", cutoff)
        .execute()
    ).data or []

    expired = [r for r in rows if r.get("added_by") in ONE_OFF_SOURCES]
    curated = [r for r in rows if r.get("added_by") not in ONE_OFF_SOURCES]

    print(f"{'DRY RUN — ' if dry else ''}deadline before {cutoff}: "
          f"{len(rows)} rows ({len(expired)} scraped, {len(curated)} curated)\n")

    for row in sorted(expired, key=lambda r: r["deadline"]):
        print(f"  retire  {row['deadline']}  {row['title'][:56]}")
        if dry:
            continue
        sb.table("opportunities").update({
            "retired_at": stamp,
            "retired_reason": (
                f"One-off scraped event; its deadline ({row['deadline']}) "
                f"passed more than {GRACE_DAYS} days ago. Retired "
                "automatically by scripts/expire_opportunities.py."
            ),
        }).eq("id", row["id"]).execute()

    if curated:
        print(f"\n  {len(curated)} curated rows have a stale deadline. NOT "
              "touched — these are annual programmes, and a new date or a "
              "recurrence month is a human claim:")
        for row in sorted(curated, key=lambda r: r["deadline"]):
            print(f"      {row['deadline']}  {row['added_by']:6} {row['title'][:52]}")

    live = (
        sb.table("opportunities").select("id", count="exact")
        .is_("retired_at", "null").execute()
    ).count
    print(f"\n  retired {0 if dry else len(expired)}. Live now: {live}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
