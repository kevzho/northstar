"""
Catalog review tool — the scraped pool, one keystroke at a time.

Walks every unreviewed candidate in scraped/reddit_candidates.json and
turns a decision into either a row in public.opportunities (keep) or a
tombstone in the pool (drop). The pool file is saved after every decision,
so quitting mid-session loses nothing, and re-runs of the scraper never
resurrect anything you have already judged.

Keys:
    k  keep — prompts once for a deadline, then upserts to Supabase
    d  drop
    f  cycle field guess        t  cycle type guess
    a  toggle audience guess    o  open the URL in your browser
    s  skip for now             q  quit (saved already)

Usage:
    cd backend && .venv/bin/python scripts/review_candidates.py
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import termios
import tty
import webbrowser
from datetime import date
from urllib.parse import urlparse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.db import get_supabase  # noqa: E402  (path shim above)

POOL = pathlib.Path(__file__).parent / "scraped" / "reddit_candidates.json"
FIELDS = ["cs", "biology", "math", "physics", "engineering", "interdisciplinary"]
TYPES = ["program", "scholarship", "competition", "mentorship"]
AUDIENCES = ["high_school", "college"]


def read_key() -> str:
    """One raw keystroke, no Enter."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    if ch == "\x03":  # Ctrl-C
        raise KeyboardInterrupt
    return ch


def host_for(url: str) -> str:
    """A presentable host: the URL's domain, sans www."""
    domain = urlparse(url).netloc.removeprefix("www.")
    return domain or "Community-sourced"


def ask_deadline() -> str | None:
    """Deadline prompt: YYYY-MM-DD, MM-DD (this/next year), or blank."""
    while True:
        raw = input("  deadline (YYYY-MM-DD, MM-DD, or blank for rolling): ").strip()
        if not raw:
            return None
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
            return raw
        if re.fullmatch(r"\d{2}-\d{2}", raw):
            today = date.today()
            candidate = date(today.year, int(raw[:2]), int(raw[3:]))
            if candidate < today:
                candidate = candidate.replace(year=today.year + 1)
            return candidate.isoformat()
        print("  ! unrecognized format")


def keep(sb, entry: dict) -> bool:
    deadline = ask_deadline()
    row = {
        "title": entry["title"][:200],
        "host": host_for(entry["url"]),
        "opportunity_field": entry.get("field_guess", "interdisciplinary"),
        "type": entry.get("type_guess", "program"),
        "blurb": entry.get("blurb", "")[:400],
        "description": entry.get("blurb", ""),
        "deadline": deadline,
        "cost": 0,
        "url": entry["url"],
        "audience": entry.get("audience_guess", "high_school"),
        "tags": [],
    }
    result = (
        sb.table("opportunities")
        .upsert(row, on_conflict="title,host", returning="representation")
        .execute()
    )
    return bool(result.data)


def main() -> None:
    pool = json.loads(POOL.read_text())
    queue = [e for e in pool if e.get("needs_review") and "review" not in e]
    # Freshest first: a 2024 thread is rarely a live opportunity.
    queue.sort(key=lambda e: e.get("posted_utc", ""), reverse=True)

    sb = get_supabase()
    kept = dropped = 0
    print(f"{len(queue)} unreviewed candidates. k/d/f/t/a/o/s/q.\n")

    for entry in queue:
        while True:
            print(
                f"\x1b[1m{entry['title'][:100]}\x1b[0m\n"
                f"  {entry.get('blurb', '')[:160]}\n"
                f"  {entry['url']}\n"
                f"  [{entry.get('field_guess')}] [{entry.get('type_guess')}] "
                f"[{entry.get('audience_guess', 'high_school')}] "
                f"score {entry.get('score')} · {entry.get('posted_utc', '')[:10]} "
                f"· {entry.get('source')}"
            )
            key = read_key()
            if key == "q":
                POOL.write_text(json.dumps(pool, indent=2))
                print(f"\nsaved. kept {kept}, dropped {dropped}.")
                return
            if key == "s":
                print("  → skipped\n")
                break
            if key == "f":
                current = FIELDS.index(entry.get("field_guess", FIELDS[-1]))
                entry["field_guess"] = FIELDS[(current + 1) % len(FIELDS)]
                continue
            if key == "t":
                current = TYPES.index(entry.get("type_guess", TYPES[0]))
                entry["type_guess"] = TYPES[(current + 1) % len(TYPES)]
                continue
            if key == "a":
                current = entry.get("audience_guess", "high_school")
                entry["audience_guess"] = AUDIENCES[1 - AUDIENCES.index(current)]
                continue
            if key == "o":
                webbrowser.open(entry["url"])
                continue
            if key == "d":
                entry["review"] = "drop"
                dropped += 1
                POOL.write_text(json.dumps(pool, indent=2))
                print("  → dropped\n")
                break
            if key == "k":
                if keep(sb, entry):
                    entry["review"] = "keep"
                    kept += 1
                    POOL.write_text(json.dumps(pool, indent=2))
                    print("  → kept ✓\n")
                else:
                    print("  ! upsert returned nothing — not marked\n")
                break

    POOL.write_text(json.dumps(pool, indent=2))
    print(f"\npool exhausted. kept {kept}, dropped {dropped}.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted — decisions so far are saved.")
