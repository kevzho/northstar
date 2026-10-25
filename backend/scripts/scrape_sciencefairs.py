"""
ROBOTS. findafair.societyforscience.org publishes no robots.txt and
societyforscience.org publishes "Disallow:" (an empty rule, meaning allow),
verified 2026-10-24. That is no longer taken on trust: app/robots.py asks
before the listing is fetched and fails closed if the file cannot be read.

Society for Science Find-a-Fair -> candidate pool. ISEF-affiliated science fairs.

WHY THIS SOURCE. It is the only feed found so far that supplies all three things
the high-school shelf is short of at once:

    non-CS      a science fair takes biology, chemistry, physics, engineering,
                maths and behavioural science. Of 34 open high-school rows on
                2026-10-04, 33 were cs.
    dated       each fair publishes its own Entry Deadline, which is the field
                the curated spreadsheet never had and Reddit has never once
                supplied.
    local       a fair is the student's region. northstar-docs/SHEET-SPEC.md
                describes 250 state rows that had to be skipped because they all
                carried one national url; here every fair carries its own.

HOW IT IS FETCHED. findafair.societyforscience.org is a server-rendered form:
one GET for an antiforgery token and a cookie, then one POST per state. There is
no API and no JSON. Results come back as repeated `.formListFair` blocks, which
is what parse_fairs reads.

DATES ARE ONLY EVER COPIED, NEVER CARRIED FORWARD. The directory is updated as
fairs re-affiliate each autumn, so in October most rows still show LAST cycle:
"Entry Deadline 2/4/2026" on a fair whose 2027 date nobody has published. A past
date is therefore dropped rather than stored. Projecting it forward a year would
be the same mistake the catalog has already made and undone -- a date no human
confirmed, shown to a student as though someone had. The fair's own site is in
the row, and the verifier reads the real date from there.

CAPPED, FOR THE REASON IN tests/test_competition_feeds.py. There are roughly 400
affiliated fairs in the US. They are real and they are distinct, but 400 rows
reading "<County> Science and Engineering Fair" arriving in one night would do
to `interdisciplinary` exactly what CTFtime would do to `cs` uncapped. The cap
is per run, so the set still accumulates -- it just does so at a rate someone
could notice going wrong.

Usage:
    cd backend && .venv/bin/python scripts/scrape_sciencefairs.py [--limit N]
"""

from __future__ import annotations

import argparse
import html
import json
import pathlib
import sys
import re
import time
from datetime import date, datetime, timezone

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.urls import canonical_url  # noqa: E402

POOL = pathlib.Path(__file__).parent / "scraped" / "reddit_candidates.json"
BASE = "https://findafair.societyforscience.org/"
USER_AGENT = (
    "northstar-catalog/1.0 (student nonprofit opportunity map; "
    "contact: dev.thorfinn@gmail.com)"
)
COUNTRY = "United States of America"
STATE_DELAY_SECONDS = 1.2
# See the CAPPED note in the module docstring.
MAX_IMPORT = 150


def strip_tags(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def us_date(value: str) -> str:
    """M/D/YYYY -> ISO, or "" if it will not parse. Never guesses a year."""
    try:
        return datetime.strptime(value.strip(), "%m/%d/%Y").date().isoformat()
    except ValueError:
        return ""


def field_after(block: str, label: str) -> str:
    """The text of the <span> that follows a bolded label in a fair block."""
    match = re.search(
        rf"<(?:strong|b)>{label}</(?:strong|b)>.*?<span>(.*?)</span>", block, re.S | re.I
    )
    return strip_tags(match.group(1)) if match else ""


def parse_fairs(page: str) -> list[dict]:
    """One record per `.formListFair` block.

    Each block holds the fair's ISEF code, its name linked to its OWN site, the
    territory it covers, and the two dates that matter.
    """
    out: list[dict] = []
    for block in re.split(r'<div class="formListFair">', page)[1:]:
        link = re.search(r'<a href="(https?://[^"]+)"[^>]*>\s*(?:<u>)?(.*?)(?:</u>)?\s*</a>', block, re.S)
        if not link:
            continue
        url = link.group(1).split("#", 1)[0].strip()
        name = strip_tags(link.group(2))
        if not name or "@" in url:
            continue
        headers = [strip_tags(h) for h in re.findall(r"<h4[^>]*>(.*?)</h4>", block, re.S)]
        code = headers[0] if headers else ""
        territory = field_after(block, "Territory") or (headers[-1] if len(headers) > 2 else "")
        window = field_after(block, "Competition Dates")
        deadline = field_after(block, "Entry Deadline")
        out.append(
            {
                "code": code,
                "name": name,
                "url": url,
                "territory": territory,
                "window": window,
                "deadline": us_date(deadline.split("—")[0]),
            }
        )
    return out



def _permitted(url: str) -> bool:
    """robots.txt, asked rather than assumed. See app/robots.py."""
    from app.robots import allowed

    if allowed(url, USER_AGENT):
        return True
    print(f"  robots.txt disallows {url} for {USER_AGENT.split('/')[0]}; skipping.")
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=MAX_IMPORT)
    parser.add_argument("--states", type=int, default=0, help="only the first N states")
    args = parser.parse_args(argv if argv is not None else [])

    pool_entries = json.loads(POOL.read_text()) if POOL.exists() else []
    pool = {canonical_url(e["url"]): e for e in pool_entries}
    known = len(pool)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    try:
        if not _permitted(BASE):
            return 0
        landing = session.get(BASE, timeout=30)
        landing.raise_for_status()
    except requests.RequestException as error:
        print(f"sciencefairs: skipped ({error})")
        return 0

    token_match = re.search(
        r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', landing.text
    )
    if not token_match:
        print("sciencefairs: skipped (no antiforgery token on the form)")
        return 0
    token = token_match.group(1)

    state_select = re.search(
        r'<select[^>]*name="State"[^>]*>(.*?)</select>', landing.text, re.S | re.I
    )
    states = [
        value
        for value, _ in re.findall(
            r'<option[^>]*value="([^"]*)"[^>]*>([^<]*)</option>', state_select.group(1)
        )
        if value.strip()
    ] if state_select else []
    if args.states:
        states = states[: args.states]
    if not states:
        print("sciencefairs: skipped (no states on the form)")
        return 0

    now = datetime.now(timezone.utc).isoformat()
    today = date.today().isoformat()
    added = stale = seen = 0
    for index, state in enumerate(states, 1):
        if added >= args.limit:
            break
        try:
            response = session.post(
                BASE,
                data={
                    "__RequestVerificationToken": token,
                    "grpRadio": "chkISEF",
                    "Country": COUNTRY,
                    "State": state,
                },
                timeout=35,
            )
            response.raise_for_status()
        except requests.RequestException:
            continue
        finally:
            if index < len(states):
                time.sleep(STATE_DELAY_SECONDS)

        for fair in parse_fairs(response.text):
            seen += 1
            if added >= args.limit:
                break
            if canonical_url(fair["url"]) in pool:
                continue
            # Last cycle's date is not this cycle's date. See the module
            # docstring: it is dropped, not carried forward.
            upcoming = fair["deadline"] if fair["deadline"] >= today else ""
            if not upcoming:
                # A fair with no confirmed upcoming date is not yet a listing.
                #
                # Importing them anyway was tried on 2026-10-04 and made the
                # shelf worse: 89 fair rows landed, 3 of them dated, and
                # `interdisciplinary` went to 54% of the high-school shelf. All
                # 89 share the words "science" and "fair" and 64 share
                # "engineering", so to the matcher they are one row repeated,
                # and the schema has no state granularity -- location_scope is
                # us/international/global -- so a student in Alabama is shown
                # all 89 rather than theirs.
                #
                # The directory re-affiliates each autumn and publishes the new
                # dates then. Waiting costs nothing: the fair will be picked up
                # on the run after it posts, with a date a student can act on.
                stale += 1
                continue
            where = fair["territory"] or state
            pool[canonical_url(fair["url"])] = {
                "source": "sciencefairs",
                "reddit_permalink": "",
                "posted_utc": now,
                "score": 0,
                "title": fair["name"],
                "url": fair["url"],
                "blurb": (
                    f"ISEF-affiliated regional science fair"
                    + (f" ({fair['code']})" if fair["code"] else "")
                    # "serving Bullock County" would understate a fair named
                    # "Greater East Alabama Regional": the directory prints one
                    # territory row per fair and a regional fair covers many. So
                    # the claim is what the directory actually says, not an
                    # inference about catchment.
                    + f" in {state}."
                    + (f" Listed territory: {fair['territory']}." if fair["territory"] else "")
                    + (f" Competition dates {fair['window']}." if fair["window"] else "")
                    + " Open to high-school projects across biology, chemistry,"
                    " physics, engineering, maths and behavioural science."
                    " Winners advance to the International Science and"
                    " Engineering Fair."
                )[:600],
                "deadline_guess": upcoming,
                # A science fair is genuinely every field at once; guessing one
                # would be wrong for most entrants.
                "field_guess": "interdisciplinary",
                "type_guess": "competition",
                "audience_guess": "high_school",
                "location_guess": f"{where}, {state}",
                "needs_review": True,
            }
            added += 1

    ordered = sorted(pool.values(), key=lambda c: c.get("score", 0), reverse=True)
    POOL.write_text(json.dumps(ordered, indent=2))
    print(
        f"sciencefairs: {seen} fairs seen across {len(states)} states, {added} new "
        f"candidates, {stale} skipped for having no confirmed upcoming deadline "
        f"(pool {known} -> {len(pool)})"
    )
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
