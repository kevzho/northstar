"""
Retire the seeded opportunities that an audit found are not real as listed.

Every one of the 35 hand-authored rows in 20260815090000_seed_catalog.sql was
checked against the program's own website on 2026-09-23, each flagged row
re-checked by a second independent reviewer. Result: 1 row accurate as listed,
25 needing corrections, 9 that should not be shown to a student at all.

These nine are not stale deadlines. They are programs that ended, programs
renamed and re-scoped to a different audience, programs that never accepted
high schoolers, and two rows describing TEACHER professional development as a
student opportunity.

Retirement is a stamp, not a DELETE: outcomes, bookmarks, matches and
dismissals all reference opportunities(id) with `on delete cascade`, so
deleting would destroy any student history attached to the row, and the row is
also the evidence of why it was removed.

Idempotent, re-running only re-stamps the same rows.

Usage:
    cd backend && .venv/bin/python scripts/retire_dead_opportunities.py [--dry-run]
"""

from __future__ import annotations

import pathlib
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.db import get_supabase  # noqa: E402

# (title, reason). Titles are matched exactly against public.opportunities.
RETIRE: list[tuple[str, str]] = [
    (
        "Gates Millennium Scholars",
        "Program ended: final cohort was the class of 2016 and the last "
        "application cycle closed 2016-01-13. APIA Scholars, the administering "
        "partner, states the GMS Program is closed to new applicants. Students "
        "seeking the successor should look at The Gates Scholarship.",
    ),
    (
        "Broadcom MASTERS",
        "Renamed the Thermo Fisher Scientific Junior Innovators Challenge in "
        "2023, and it is a MIDDLE school competition — the top 10% of 6th-8th "
        "grade competitors at affiliated fairs. It was listed as grades 8-9, so "
        "the name, sponsor and audience were all wrong.",
    ),
    (
        "NSF Research Experiences for Undergraduates (REU) - High School Track",
        "No such program. NSF states REU is for 'Undergraduates (college and "
        "university students)' and the phrase 'high school' does not appear on "
        "the REU page. The 'High School Track' was fabricated, so no high "
        "schooler could ever have applied.",
    ),
    (
        "CERN Summer Student Program (US-based)",
        "Requires enrolment in a bachelor's or master's degree — CERN's own "
        "wording is 'students pursuing bachelor's or master's degrees'. High "
        "schoolers are ineligible, and the row was listed as grades 11-12.",
    ),
    (
        "Google Computer Science Summer Institute",
        "Discontinued. Google removed the CSSI program page — archived captures "
        "return 200 through late 2023 and 404 from 2023-11-16 onward — and CSSI "
        "no longer appears in Google's student program listings.",
    ),
    (
        "Jackson Laboratory Summer Student Program",
        "No longer open to high schoolers. JAX states on both its admission and "
        "FAQ pages that it is 'no longer accepting high school seniors into the "
        "program', and now lists the Summer Student Program as undergraduate. "
        "It was listed as grades 11-12.",
    ),
    (
        "BJC CS Principles Summer Workshop",
        "Teacher professional development, not a student opportunity. The page "
        "describes it as for teachers intending to teach BJC. No student can "
        "apply at any grade; it was listed as grades 9-12.",
    ),
    (
        "PROMYS for Teachers (Student Track)",
        "PROMYS for Teachers is a program for teachers; the 'Student Track' in "
        "this title does not exist. PROMYS does run a genuine student program, "
        "which is a different thing and should be added as its own row after "
        "verifying its current eligibility and deadline.",
    ),
    (
        "Telluride Association Summer Seminar (TASS)",
        "Suspended: TASS will not run in 2027 and no return date has been "
        "announced, so no student reading this can act on it. Restore this row "
        "if and when a future cycle is announced.",
    ),
]


def main() -> int:
    dry = "--dry-run" in sys.argv
    sb = get_supabase()
    stamp = datetime.now(timezone.utc).isoformat()

    print(f"{'DRY RUN — ' if dry else ''}retiring {len(RETIRE)} opportunities\n")

    retired = missing = 0
    for title, reason in RETIRE:
        found = (
            sb.table("opportunities")
            .select("id, title, retired_at")
            .eq("title", title)
            .execute()
        ).data or []

        if not found:
            print(f"  ?? not found, skipping: {title}")
            missing += 1
            continue

        for row in found:
            already = row.get("retired_at")
            mark = "already retired" if already else "retiring"
            print(f"  {mark}: {row['title'][:62]}")
            if dry or already:
                continue
            sb.table("opportunities").update(
                {"retired_at": stamp, "retired_reason": reason}
            ).eq("id", row["id"]).execute()
            retired += 1

    live = (
        sb.table("opportunities")
        .select("id", count="exact")
        .is_("retired_at", "null")
        .execute()
    )
    print(f"\n  retired this run: {retired}   not found: {missing}")
    print(f"  opportunities still live: {live.count}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
