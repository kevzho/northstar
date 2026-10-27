"""
Check every link on the shelf, and retire the ones that are really gone.

WHY. /opportunities says, to everyone, signed in or not: "Each one has been
checked against the programme's own page, and anything that stopped holding up
was removed rather than left to pad the total." On 2026-10-12 that was false -
seven of sixty-six open rows did not load, four of them CTF domains that had
stopped resolving entirely, and nothing in the daily job had ever looked. This
is the thing that makes the sentence true.

HOW IT AVOIDS BEING THE BIGGER PROBLEM. See app/link_health.py: a refusal aimed
at the client (403, 429, a Cloudflare challenge) is never death, and death has
to repeat across runs before anything is retired. A ledger carries the verdict
history. Retiring a live programme is worse than keeping a dead link one more
day, because a student who never sees an opportunity cannot discover it was
wrongly hidden.

Retirement is a stamp, never a DELETE: outcomes, bookmarks, matches and
dismissals reference opportunities(id) on delete cascade, so deleting would
destroy a student's own history, and the row is the evidence of why it went.

Usage:
    cd backend && .venv/bin/python scripts/check_links.py --dry-run
    cd backend && .venv/bin/python scripts/check_links.py
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import pathlib
import sys
import time
from datetime import datetime, timezone

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.db import get_supabase  # noqa: E402
from app.link_health import (  # noqa: E402
    FAIL_STRIKES, classify, needs_url_review, should_retire,
)

LEDGER = pathlib.Path(__file__).parent / "scraped" / "link_health_ledger.json"

# WE SAY WHO WE ARE. This used to send a Chrome string, justified in a comment
# as "asking the way a student's browser asks". That was a rationalisation: a
# 403 from Akamai or Cloudflare is a site saying it does not want automated
# traffic, and wearing a browser's name to get past it is ignoring the answer
# rather than not hearing it. Every other scraper here identifies itself and
# carries a contact address, and the one piece of code whose entire job is
# checking other people's sites had no business being the exception.
#
# The cost is real and accepted: more hosts refuse this, so more rows land on
# "inconclusive" and are never retired. That is the correct direction to fail.
# app/link_health.py only ever retires on a domain that has stopped resolving,
# which no User-Agent can influence either way.
USER_AGENT = (
    "northstar-linkcheck/1.0 (student nonprofit opportunity catalog; "
    "verifying links we publish; contact: dev.thorfinn@gmail.com)"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
TIMEOUT_S = 20
WORKERS = 8
# Keep the whole sweep polite: these are hundreds of hosts, a handful of
# requests each per day, spread over a few minutes.
PAUSE_S = 0.15

MAX_HISTORY = 6


def probe(url: str) -> object:
    """One GET. Returns an int status, or a string naming the failure."""
    try:
        response = requests.get(
            url, headers=HEADERS, timeout=TIMEOUT_S, allow_redirects=True, stream=True
        )
        response.close()
        return response.status_code
    except requests.RequestException as error:
        return f"{type(error).__name__}: {error}"[:200]


def load_ledger() -> dict:
    try:
        return json.loads(LEDGER.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="check and report; retire nothing")
    parser.add_argument("--limit", type=int, default=0, help="check at most N rows")
    args = parser.parse_args(argv or [])

    sb = get_supabase()
    opportunities = (
        sb.table("opportunities").select("id, title, url")
        .is_("retired_at", "null").execute()
    ).data or []
    resources = (
        sb.table("learning_resources").select("id, title, url")
        .is_("retired_at", "null").execute()
    ).data or []

    targets = (
        [("opportunities", r) for r in opportunities if r.get("url")]
        + [("learning_resources", r) for r in resources if r.get("url")]
    )
    if args.limit:
        targets = targets[: args.limit]
    print(f"checking {len(targets)} links "
          f"({len(opportunities)} opportunities, {len(resources)} resources)")

    ledger = load_ledger()
    started = time.time()

    def work(item):
        table, row = item
        outcome = probe(row["url"])
        time.sleep(PAUSE_S)
        return table, row, outcome, classify(outcome)

    counts = {"alive": 0, "dead": 0, "moved": 0, "inconclusive": 0}
    retire: list[tuple[str, dict, str]] = []
    review: list[tuple[str, dict, str]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for table, row, outcome, verdict in pool.map(work, targets):
            counts[verdict] = counts.get(verdict, 0) + 1
            entry = ledger.setdefault(row["id"], {"url": row["url"], "history": []})
            entry["url"] = row["url"]
            entry["title"] = row.get("title", "")
            entry["last_outcome"] = outcome if isinstance(outcome, int) else str(outcome)
            entry["last_checked"] = datetime.now(timezone.utc).isoformat()
            entry["history"] = (entry.get("history", []) + [verdict])[-MAX_HISTORY:]
            if should_retire(entry["history"]):
                retire.append((table, row, entry["last_outcome"]))
            elif needs_url_review(entry["history"]):
                review.append((table, row, entry["last_outcome"]))

    print(f"\n{counts}  in {time.time() - started:.0f}s")
    print(f"\n{len(retire)} row(s) whose DOMAIN has been gone for "
          f"{FAIL_STRIKES} runs — these retire:")
    for table, row, outcome in retire:
        print(f"  {row['title'][:46]:48} {row['url'][:46]}")

    print(f"\n{len(review)} row(s) whose host answers but whose PAGE does not. "
          "These stay on the shelf;\nsomebody has to find the new URL. Deleting "
          "them would trade a real opportunity\nfor a tidy link report:")
    for table, row, outcome in review:
        short = str(outcome)[:60].replace("\n", " ")
        print(f"  {short:<62} {row['title'][:40]:42} {row['url'][:44]}")

    if not args.dry_run:
        stamp = datetime.now(timezone.utc).isoformat()
        for table, row, outcome in retire:
            sb.table(table).update({
                "retired_at": stamp,
                "retired_reason": (
                    f"Link unreachable on {FAIL_STRIKES} consecutive daily checks "
                    f"(last outcome: {outcome}). Retired by scripts/check_links.py "
                    "rather than left on a shelf that promises every entry has "
                    "been checked."
                ),
            }).eq("id", row["id"]).execute()
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        LEDGER.write_text(json.dumps(ledger, indent=2) + "\n")
        print(f"\nretired {len(retire)}, ledger written to {LEDGER}")
    else:
        print("\n(dry run — nothing retired, ledger not written)")

    # Soft failure like the scrapers: a bad network afternoon is not a reason to
    # fail the daily loop, and nothing was retired on one run's evidence anyway.
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
