"""
Retire rows that are the same programme listed twice.

WHY canonical_url ALONE CANNOT DO THIS. scripts/dedupe_opportunities.py keys on
the canonical URL, which is right for catching "same link, scraped twice" and
wrong here in both directions:

  - It MISSES http://broadinstitute.org/bssp vs https://www.broadinstitute.org/
    bssp, because scheme and www survive canonicalisation on purpose (a path's
    case is meaningful, so the function is deliberately conservative).

  - It would WRONGLY MERGE four real competitions. AMC 10, AMC 12, AIME and
    USAJMO all live at maa.org/student-programs/amc, and HMMT February and HMMT
    November share hmmt.org. One page, several programmes. Merging those would
    delete three real opportunities to tidy a link report, which is the same
    trade scripts/check_links.py exists to refuse.

So: same host+path AND near-identical title. Titles are normalised by dropping
the year, the format words scrapers append ("Jeopardy", "Capture the Flag
Competition", "Jeopardy-Style Security Competition"), parentheticals and
punctuation. "BackdoorCTF 2026" and "BackdoorCTF 2026 Jeopardy CTF" collapse;
"AMC 10" and "AMC 12" do not.

Retirement is a stamp, never a DELETE: bookmarks, matches, outcomes and
dismissals reference opportunities(id) on delete cascade.

Usage:
    cd backend && .venv/bin/python scripts/dedupe_by_title.py --dry-run
"""

from __future__ import annotations

import argparse
import collections
import pathlib
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.db import get_supabase  # noqa: E402

# Words a scraper appends that describe the FORMAT, never the programme.
NOISE = re.compile(
    r"\b(jeopardy|jeopardy[- ]style|capture[- ]the[- ]flag|ctf|competition|"
    r"contest|security|programme|program|the|a|an|and|20\d\d)\b",
    re.I,
)


def host_path(url: str) -> str:
    parsed = urlparse((url or "").lower())
    return parsed.netloc.removeprefix("www.") + parsed.path.rstrip("/")


def title_key(title: str) -> str:
    text = re.sub(r"\([^)]*\)", " ", title or "")      # drop parentheticals
    text = NOISE.sub(" ", text)
    text = re.sub(r"[^a-z0-9]+", "", text.lower())
    return text


def completeness(row: dict) -> tuple:
    """Which of two identical rows to keep: the one a student learns more from."""
    return (
        1 if row.get("deadline") else 0,
        1 if (row.get("entry_note") or "").strip() else 0,
        1 if (row.get("state") or row.get("location")) else 0,
        len((row.get("blurb") or "")),
        len((row.get("description") or "")),
        # Stable tiebreak so a re-run keeps the same winner.
        row.get("created_at") or "",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv or [])

    sb = get_supabase()
    rows = (
        sb.table("opportunities")
        .select("id, title, url, deadline, entry_note, blurb, description, "
                "state, location, created_at")
        .is_("retired_at", "null")
        .execute()
    ).data or []

    groups: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for row in rows:
        groups[(host_path(row["url"]), title_key(row["title"]))].append(row)

    retire: list[tuple[dict, dict]] = []
    for (path, _), members in groups.items():
        if len(members) < 2:
            continue
        members.sort(key=completeness, reverse=True)
        keeper = members[0]
        for loser in members[1:]:
            retire.append((loser, keeper))

    print(f"{len(rows)} live rows, {len(retire)} duplicate(s) to retire\n")
    for loser, keeper in retire:
        print(f"  RETIRE  {loser['title'][:52]:54}")
        print(f"  keeping {keeper['title'][:52]:54} {keeper['url'][:44]}\n")

    if args.dry_run:
        print("(dry run — nothing retired)")
        return 0

    stamp = datetime.now(timezone.utc).isoformat()
    for loser, keeper in retire:
        sb.table("opportunities").update({
            "retired_at": stamp,
            "retired_reason": (
                f"Duplicate of {keeper['title']!r} ({keeper['id']}): same page, "
                "same programme, listed twice by two feeds. Retired rather than "
                "deleted so a bookmark on this row keeps its title."
            ),
        }).eq("id", loser["id"]).execute()
    print(f"retired {len(retire)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
