"""
Retire duplicate opportunity rows.

public.opportunities carries unique(title, host), which does not catch the same
programme entered twice with the host spelled differently:

    FIRST Robotics Competition   host "FIRST"  and  "FIRST (For Inspiration and…)"
    Research Science Institute   host "CEE / MIT"  and  "Center for Excellence in…"
    Conrad Challenge             host "Conrad Foundation / NASA"  and  "Conrad Foundation"

Five such pairs sit on the high-school shelf because the 35-row seed and the
33-row curated seed both included the same well-known programmes. A student sees
RSI twice in one ranked list, which reads as a broken product rather than a
thorough one.

Retired, not deleted — same contract as every other removal here, because
outcomes, bookmarks, matches and dismissals all cascade from opportunities(id).

WHICH COPY SURVIVES. The richer record: a real deadline first, then the longer
description, then the older row. Not provenance — the curated rows are usually
better scoped, but not always, and "has a deadline" is the field a student
actually needs.

Idempotent. Usage:
    cd backend && .venv/bin/python scripts/dedupe_opportunities.py [--dry-run]
"""

from __future__ import annotations

import pathlib
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.db import get_supabase  # noqa: E402


# Pairs the exact-title pass cannot see, because the same programme was entered
# under two different names. Each was confirmed by hand to be one programme:
#
#   SEES  — "STEM Enhancement in Earth Science" IS what the acronym expands to.
#   STS   — the same Society for Science competition, once with the acronym.
#   USAPhO — the "Physics Olympiad Summer Camp" is not a programme you enter. It
#            is the training camp the top ~20 USAPhO scorers are invited to, so
#            listing it beside USAPhO offers a student a door that does not exist.
#
# Written as (retire, keep) so the intent is reviewable, rather than letting the
# richness heuristic pick between two differently-named rows.
ALIAS_DUPES: list[tuple[str, str]] = [
    ("NASA SEES Summer Intern Program",
     "STEM Enhancement in Earth Science (SEES) Internship"),
    ("Regeneron Science Talent Search (STS)",
     "Regeneron Science Talent Search"),
    ("Physics Olympiad Summer Camp (US Physics Team)",
     "U.S. Physics Team (USAPhO)"),
]


def richness(row: dict) -> tuple:
    """Higher sorts first. A deadline beats a long description beats age."""
    return (
        1 if row.get("deadline") else 0,
        len(row.get("description") or ""),
        len(row.get("blurb") or ""),
        row.get("created_at") or "",
    )


def main() -> int:
    dry = "--dry-run" in sys.argv
    sb = get_supabase()
    stamp = datetime.now(timezone.utc).isoformat()

    rows = (
        sb.table("opportunities")
        .select("id, title, host, audience, added_by, deadline, description, blurb, created_at")
        .is_("retired_at", "null")
        .execute()
    ).data or []

    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row.get("title") or "").strip().lower()].append(row)

    dupes = {k: v for k, v in groups.items() if len(v) > 1}
    print(f"{'DRY RUN — ' if dry else ''}{len(dupes)} duplicated titles, "
          f"{sum(len(v) - 1 for v in dupes.values())} rows to retire\n")

    retired = 0
    for _, group in sorted(dupes.items()):
        group.sort(key=richness, reverse=True)
        keep, drop = group[0], group[1:]
        print(f"  {keep['title'][:54]}")
        print(f"      KEEP    added_by={keep['added_by']:6} deadline={keep.get('deadline')} "
              f"desc={len(keep.get('description') or '')}")
        for row in drop:
            print(f"      retire  added_by={row['added_by']:6} deadline={row.get('deadline')} "
                  f"desc={len(row.get('description') or '')}")
            if dry:
                continue
            sb.table("opportunities").update({
                "retired_at": stamp,
                "retired_reason": (
                    f"Duplicate of the same programme kept at id {keep['id']}. "
                    f"unique(title, host) missed it because the host was spelled "
                    f"differently ({row.get('host')!r} vs {keep.get('host')!r}). "
                    "The richer record survived."
                ),
            }).eq("id", row["id"]).execute()
            retired += 1

    # Same-programme-different-name pairs, retired by explicit instruction.
    print()
    by_title = {(r.get("title") or "").strip().lower(): r for r in rows}
    for retire_title, keep_title in ALIAS_DUPES:
        row = by_title.get(retire_title.strip().lower())
        keep = by_title.get(keep_title.strip().lower())
        if row is None or keep is None:
            print(f"  alias: skip {retire_title!r} (row or its keeper is gone)")
            continue
        print(f"  alias: retire {retire_title[:46]!r}\n"
              f"                 -> kept as {keep_title[:46]!r}")
        if dry:
            continue
        sb.table("opportunities").update({
            "retired_at": stamp,
            "retired_reason": (
                f"The same programme is already listed as {keep_title!r} "
                f"(id {keep['id']}). Entered twice under two names, so "
                "unique(title, host) could not catch it."
            ),
        }).eq("id", row["id"]).execute()
        retired += 1

    live = (
        sb.table("opportunities")
        .select("id", count="exact")
        .is_("retired_at", "null")
        .execute()
    ).count
    print(f"\n  retired {retired}. Live opportunities now: {live}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
