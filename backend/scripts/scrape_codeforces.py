"""
Codeforces -> candidate pool. Algorithmic contests an individual enters alone.

The complement to CTFtime: where CTFs are occasional and team-flavoured, a
Codeforces round is strictly individual, free, requires nothing but an account,
and one runs every few days — roughly 150 a year. For a student with no
counsellor, no team and no teacher sponsor, this is the lowest-barrier
competitive STEM thing that exists, and it is a real line on an application.

Only `phase == "BEFORE"` contests are taken: Codeforces returns the entire
2,153-contest history in one response, and importing finished rounds is how the
catalog previously ended up with 123 expired rows out of 195.

Division matters and is preserved in the blurb. Div. 3 and Div. 4 are written
for beginners; Div. 1 is not, and sending a student who has never competed to a
Div. 1 round is the same failure as sending a sophomore to a juniors-only
programme — technically eligible, practically a wall.

No auth, no key, documented public API. Field is always cs; see
scrape_ctftime.py's docstring for why that is capped rather than celebrated.

Usage:
    cd backend && .venv/bin/python scripts/scrape_codeforces.py
"""

from __future__ import annotations

import json
import pathlib
import re
from datetime import datetime, timezone

import requests

POOL = pathlib.Path(__file__).parent / "scraped" / "reddit_candidates.json"
API = "https://codeforces.com/api/contest.list"
USER_AGENT = "northstar-catalog/1.0 (student nonprofit opportunity map)"

# Small on purpose. Six to eight rounds are typically scheduled at a time, and
# the feed refills continuously — there is no reason to hold more.
MAX_IMPORT = 10


def beginner_note(name: str) -> str:
    """Division-aware guidance, because 'eligible' and 'suitable' differ.

    Order matters. A "Div. 1 + Div. 2" round is a COMBINED round that Div. 2
    competitors enter normally, so matching "Div. 1" first told a beginner to
    skip a contest they were welcome at — the same eligible-but-walled mistake
    as listing a juniors-only programme for grades 9-12. Combined rounds are
    checked before either division alone.
    """
    if re.search(r"Div\.\s*1\s*\+\s*Div\.\s*2", name):
        return "A combined Div. 1 + Div. 2 round: Div. 2 entrants get their own scoreboard."
    if re.search(r"Div\.\s*[34]", name):
        return "Div. 3/4 rounds are written for newer competitors — a reasonable first contest."
    if re.search(r"Div\.\s*1", name):
        return "Div. 1 is for rated competitors; start with a Div. 3 or 4 round instead."
    if re.search(r"Div\.\s*2", name):
        return "Div. 2 is the common entry point once you have solved a few problems."
    return "Open to anyone with a free account."


def main() -> None:
    pool_entries = json.loads(POOL.read_text()) if POOL.exists() else []
    pool = {e["url"]: e for e in pool_entries}
    known = len(pool)

    try:
        response = requests.get(
            API,
            params={"gym": "false"},
            headers={"User-Agent": USER_AGENT},
            timeout=25,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "OK":
            print(f"codeforces: skipped (api status {payload.get('status')})")
            return
        contests = payload.get("result", [])
    except (requests.RequestException, ValueError) as error:
        print(f"codeforces: skipped ({error})")
        return

    upcoming = [c for c in contests if c.get("phase") == "BEFORE"]
    added = 0
    for contest in sorted(upcoming, key=lambda c: c.get("startTimeSeconds") or 0):
        if added >= MAX_IMPORT:
            break
        cid = contest.get("id")
        name = (contest.get("name") or "").strip()
        start_s = contest.get("startTimeSeconds")
        if not cid or not name or not start_s:
            continue
        url = f"https://codeforces.com/contest/{cid}"
        if url in pool:
            continue

        start = datetime.fromtimestamp(start_s, tz=timezone.utc)
        hours = round((contest.get("durationSeconds") or 0) / 3600, 1)

        pool[url] = {
            "source": "codeforces",
            "reddit_permalink": "",
            "posted_utc": datetime.now(timezone.utc).isoformat(),
            "score": 0,
            "title": name,
            "url": url,
            "blurb": (
                f"Individual algorithmic programming contest, online, free. "
                f"Starts {start:%Y-%m-%d %H:%M} UTC"
                + (f", runs {hours}h. " if hours else ". ")
                + beginner_note(name)
            ),
            # Registration closes at the start, so the start IS the deadline.
            "deadline_guess": start.date().isoformat(),
            "field_guess": "cs",
            "type_guess": "competition",
            # Genuinely open to any age — Codeforces has no enrolment
            # requirement, which is exactly why it belongs on the shelf that
            # has almost nothing open.
            "audience_guess": "high_school",
            "location_guess": "global",
            "needs_review": True,
        }
        added += 1

    ordered = sorted(pool.values(), key=lambda c: c.get("score", 0), reverse=True)
    POOL.write_text(json.dumps(ordered, indent=2))
    print(
        f"codeforces: {len(contests)} contests total, {len(upcoming)} upcoming, "
        f"{added} new candidates (pool {known} -> {len(pool)})"
    )


if __name__ == "__main__":
    main()
