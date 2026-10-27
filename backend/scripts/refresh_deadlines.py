"""
Re-read programme pages and write the deadlines they currently state.

WHY THIS IS THE MOST IMPORTANT SCRIPT IN THE REPO.

Measured 2026-10-05, a frontier model with no tools and no web access was asked
to recall 24 curated catalog rows. It knew all 24 existed: 8/8 seed, 8/8 human,
8/8 sheet. So "this programme is real" is not information a student needs this
catalog for, they can get it free, in a chat window, in thirty seconds.

What the model could not do was dates. Asked for the current deadline of twelve
open rows it said UNKNOWN twelve times, correctly refusing to guess. That is the
gap this catalog exists to fill, and it was not filling it:

    curated rows (seed + human) with a deadline in the future:   2 of 48
    scraped rows (ai) with a deadline in the future:            52 of 94

The half of the shelf with real value had dead dates, median 218 days stale,
MIT PRIMES reading 2025-11-30. A student asking a chatbot got a better answer
about Regeneron than the shelf gave them, because the chatbot said "check the
official page" and the shelf said a date that had already passed.

WHAT IT WILL AND WILL NOT WRITE. A deadline is written only when the page says
one, it parses to a real date, and that date is in the future. Everything else
leaves the row alone:

  - a page that says nothing about dates            -> untouched, logged
  - a date that has already passed                  -> NOT written. The programme
      has not opened its next cycle yet, and last cycle's date is not this
      cycle's. Writing it would recreate the exact defect this fixes.
  - a page that cannot be fetched                   -> untouched, logged
  - a model reply that will not parse               -> untouched, logged

A row whose stored deadline is in the past and whose page offers no new one has
its deadline CLEARED to NULL. "Rolling deadline" is the honest rendering of "we
do not know when this opens next"; a date from last February is not.

Usage:
    cd backend && .venv/bin/python scripts/refresh_deadlines.py [--limit N] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import time
from datetime import date, datetime, timezone

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.db import get_supabase  # noqa: E402
from app.llm import LLMUnavailable, chat  # noqa: E402

LEDGER = pathlib.Path(__file__).parent / "scraped" / "deadline_refresh_ledger.json"
USER_AGENT = (
    "northstar-catalog/1.0 (student nonprofit opportunity map; "
    "contact: dev.thorfinn@gmail.com)"
)
# Wider than the importer's 7000. A deadline often sits below the fold, after
# the marketing: MIT PRIMES mentions "Deadline" inside 7000 chars but the date
# itself falls outside it. Tokens are the cheap part of this job.
PAGE_CHARS = 14000
REQUEST_DELAY_S = 1.0

# Per run. The daily job has a 90-minute ceiling and the scrape stages use most
# of it; this is sized so a full pass over the stale half of the shelf takes
# about a week of mornings rather than one long afternoon that times out.
MAX_PER_RUN = 25

# How long a row is trusted before it is worth re-reading. A programme that
# published a date in March has probably not moved it by April.
RECHECK_AFTER_DAYS = 21

SYSTEM = """You read one programme's web page and report the application deadline it states.

Reply with JSON only:
{"deadline": "YYYY-MM-DD" or null, "quote": "the sentence the date came from", "cycle": "what cycle this is for, e.g. 2027"}

Rules:
- Report ONLY a date the page actually states. Never infer one from a past cycle.
- If the page gives a month with no day, use null. A guess at the day is a guess.
- If the page shows last cycle's date and says nothing about the next, use null.
- If several dates appear, report the one a student must act on to ENTER
  (the application or registration deadline), not the event date.
- quote must be text that appears verbatim on the page."""


def page_text(url: str) -> str | None:
    """The page as plain text, or None if it cannot be read."""
    try:
        response = requests.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=20, allow_redirects=True
        )
        if not response.ok:
            return None
        html = response.text[:400_000]
    except requests.RequestException:
        return None
    html = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = (
        text.replace("&nbsp;", " ").replace("&amp;", "&")
        .replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'")
    )
    return (re.sub(r"\s+", " ", text).strip()[:PAGE_CHARS]) or None


def read_deadline(title: str, url: str, text: str) -> dict | None:
    try:
        result = chat(
            base=os.getenv("LLM_API_BASE", ""),
            key=os.getenv("LLM_API_KEY", ""),
            model=os.getenv("LLM_MODEL", ""),
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Programme: {title}\nURL: {url}\n\nPage text:\n{text}"},
            ],
            max_tokens=400,
            temperature=0.0,
        )
    except LLMUnavailable:
        return None
    body = result.text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", body, re.S)
    if fenced:
        body = fenced.group(1)
    else:
        brace = re.search(r"\{.*\}", body, re.S)
        if brace:
            body = brace.group(0)
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return None


def iso_or_none(value: object) -> str | None:
    try:
        return date.fromisoformat(str(value).strip()[:10]).isoformat()
    except (ValueError, TypeError):
        return None


def load_ledger() -> dict:
    try:
        return json.loads(LEDGER.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=MAX_PER_RUN)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--all", action="store_true",
                        help="ignore the recheck interval and re-read everything")
    args = parser.parse_args(argv or [])

    if not (os.getenv("LLM_API_BASE") and os.getenv("LLM_API_KEY") and os.getenv("LLM_MODEL")):
        print("refresh_deadlines: skipped (LLM not configured)")
        return 0

    sb = get_supabase()
    today = date.today().isoformat()
    rows = (
        sb.table("opportunities")
        .select("id,title,url,deadline,added_by,audience")
        .is_("retired_at", "null")
        .execute()
    ).data or []

    ledger = load_ledger()
    now = datetime.now(timezone.utc)

    def due(row: dict) -> bool:
        if not str(row.get("url") or "").strip():
            return False
        # Rows with a live future date are already answering the question.
        if row.get("deadline") and str(row["deadline"]) >= today:
            return False
        if args.all:
            return True
        seen = ledger.get(str(row["id"]), {}).get("at")
        if not seen:
            return True
        try:
            age = (now - datetime.fromisoformat(seen)).days
        except ValueError:
            return True
        return age >= RECHECK_AFTER_DAYS

    # Curated rows first: they are the ones a student actually wants and the
    # ones measured to be stale. The scraped CTF tail already has live dates.
    candidates = [r for r in rows if due(r)]
    candidates.sort(key=lambda r: (r.get("added_by") == "ai", str(r.get("title") or "")))
    batch = candidates[: max(1, args.limit)]
    print(f"refresh_deadlines: {len(candidates)} rows need a look, taking {len(batch)}")

    found = cleared = unchanged = unreadable = 0
    for index, row in enumerate(batch, 1):
        title, url = str(row.get("title") or ""), str(row.get("url") or "")
        text = page_text(url)
        if index < len(batch):
            time.sleep(REQUEST_DELAY_S)
        if not text:
            unreadable += 1
            ledger[str(row["id"])] = {"at": now.isoformat(), "outcome": "unreadable", "title": title[:90]}
            print(f"  --  unreadable  {title[:58]}")
            continue

        verdict = read_deadline(title, url, text) or {}
        fresh = iso_or_none(verdict.get("deadline"))
        stale_stored = bool(row.get("deadline")) and str(row["deadline"]) < today

        if fresh and fresh >= today:
            found += 1
            print(f"  +   {fresh}  {title[:52]}")
            print(f"        \"{str(verdict.get('quote') or '')[:88]}\"")
            if not args.dry_run:
                sb.table("opportunities").update(
                    {"deadline": fresh, "verified_at": now.isoformat()}
                ).eq("id", row["id"]).execute()
            ledger[str(row["id"])] = {"at": now.isoformat(), "outcome": "found",
                                      "deadline": fresh, "title": title[:90]}
        elif stale_stored:
            # The stored date has passed and the page offers nothing newer.
            # NULL renders as "Rolling deadline", which is the honest statement
            # of "we do not know when this opens next". Last February is not.
            cleared += 1
            print(f"  ∅   cleared (was {row['deadline']})  {title[:46]}")
            if not args.dry_run:
                sb.table("opportunities").update({"deadline": None}).eq("id", row["id"]).execute()
            ledger[str(row["id"])] = {"at": now.isoformat(), "outcome": "cleared",
                                      "was": row["deadline"], "title": title[:90]}
        else:
            unchanged += 1
            ledger[str(row["id"])] = {"at": now.isoformat(), "outcome": "no_date_on_page",
                                      "title": title[:90]}

    if not args.dry_run:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        LEDGER.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
    print(
        f"\n  {'would write' if args.dry_run else 'wrote'}: {found} live deadlines   "
        f"cleared stale: {cleared}   page gave no date: {unchanged}   unreadable: {unreadable}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
