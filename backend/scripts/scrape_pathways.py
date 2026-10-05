"""
Pathways to Science -> candidate pool. Funded STEM programmes, mostly not CS.

WHY THIS SOURCE. scrape_ctftime.py ends its own docstring with the problem:
"balance comes from curating non-CS competitions, which no API provides." This
is the source that answers it. Measured against production the day it was
written:

    high-school shelf          115 rows across 9 fields
    open to apply today         34 rows -- 33 of them cs, 1 biology

The shelf's breadth is real and its urgency is a monoculture. The cause is not
the scrapers' reach but their SHAPE: every candidate in the pool that carries a
date came from ctftime, devpost or codeforces (258 of 10,568), and all three are
computer science. Reddit supplies the other 10,310 and has never supplied a
single deadline, because a thread titled "Potential dimethylmercury incident at
MIT" is a conversation, not a programme.

Pathways to Science is a directory rather than a forum: ~1,000 funded STEM
programmes, filterable to the 80 that take high schoolers, drawn from REUs,
national labs, medical schools and field stations. Biology, chemistry, physics,
earth science and engineering, which is exactly where the one open row is.

WHAT THIS TAKES FROM EACH LISTING, AND WHY IT IS NOT THE DEADLINE. The listing
page shows a deadline for only a handful of rows, and the detail page shows none
in any machine-readable form. What the detail page always carries is the
programme's OWN url -- afrlscholars.usra.edu, not a pathwaystoscience page --
and that is the more valuable field. northstar-docs/SHEET-SPEC.md spent a whole
section on it: a deep link is what lets the verifier read a real deadline off
the organiser's page, and an aggregator's summary is not evidence about the
2026-27 cycle. So this scraper's job is to deliver a deep link and a description;
the deadline is the verifier's job, from the source that actually knows it.

ROBOTS. pathwaystoscience.org/robots.txt carries no Disallow rules -- it is a
bare sitemap pointer -- so the listing and detail pages are permitted. The
detail fetches are serialised with a delay because 80 requests from one student
project should not be the reason anyone's afternoon gets worse.

Usage:
    cd backend && .venv/bin/python scripts/scrape_pathways.py [--limit N]
"""

from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import time
from datetime import datetime, timezone

import requests

POOL = pathlib.Path(__file__).parent / "scraped" / "reddit_candidates.json"
# slug -> the programme's own url, learned once and kept.
#
# Without it this scraper fetched all ~80 detail pages on every daily run to
# rediscover addresses it already had. The listing changes a few times a year;
# the mapping from a slug to the organiser's site does not change at all. That
# is 80 requests a day at a small nonprofit directory to learn nothing, which is
# not a cost anyone should pay for our convenience.
#
# Tracked in git like the pool, because it is the record of what has already
# been asked, and a fresh clone that lost it would start the 80 requests again.
URL_CACHE = pathlib.Path(__file__).parent / "scraped" / "pathways_urls.json"
BASE = "https://www.pathwaystoscience.org"
# The one filter that matters. Values come from the advanced-search form; this
# is the literal option value, spaces and all.
LISTING = f"{BASE}/programs.aspx?u=HighSchool_High School Students&submit=y"

USER_AGENT = (
    "northstar-catalog/1.0 (student nonprofit opportunity map; "
    "contact: dev.thorfinn@gmail.com)"
)
# Serialised, with a pause. See the ROBOTS note above.
DETAIL_DELAY_SECONDS = 1.1

# Keyword -> the catalog's field vocabulary. Only a hint: field_guess exists to
# give the screening pass a starting point, and the verifier overrides it from
# the programme's own page. Ordered, because "biomedical engineering" should
# land on engineering rather than on whichever key hashed first.
FIELD_HINTS: tuple[tuple[str, str], ...] = (
    ("engineer", "engineering"),
    ("comput", "cs"),
    ("software", "cs"),
    ("data scien", "cs"),
    ("robot", "engineering"),
    ("biomed", "health"),
    ("medic", "health"),
    ("health", "health"),
    ("nursing", "health"),
    ("biolog", "biology"),
    ("ecolog", "biology"),
    ("genom", "biology"),
    ("neuro", "biology"),
    ("marine", "biology"),
    ("chemis", "biology"),
    ("physic", "physics"),
    ("astro", "physics"),
    ("geolog", "physics"),
    ("ocean", "physics"),
    ("atmospher", "physics"),
    ("climate", "physics"),
    ("mathemat", "math"),
    ("statistic", "math"),
)


def field_guess(text: str) -> str:
    low = text.lower()
    for needle, field in FIELD_HINTS:
        if needle in low:
            return field
    # Most of this directory is lab research that spans disciplines, and
    # guessing a specific one wrongly is worse than declining to.
    return "interdisciplinary"


def strip_tags(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def parse_listing(page: str) -> list[dict]:
    """One record per programme block on the results page.

    The markup has no classes worth anchoring to -- every block is
    `class='progigert'` with the distinction carried in an inline background
    colour -- so the split is on the institution header that opens each block.
    """
    blocks = re.split(r"<div class='progigert' style='background: #dedede", page)[1:]
    out: list[dict] = []
    for block in blocks:
        slug = re.search(r"programhub\.aspx\?sort=([^'\"&]+)", block)
        title = re.search(r"programhub\.aspx\?sort=[^'\"]+'>([^<]{4,160})</a>", block)
        if not slug or not title:
            continue
        name = html.unescape(title.group(1)).strip()
        if not name or name.lower().startswith("...read more"):
            continue
        institution = re.search(r"<h2[^>]*>(.*?)</h2>", block, re.S)
        where = re.search(r"<i><span[^>]*>\s*\(([^)]{2,60})\)", block)
        blurb = re.search(
            r"<a href='programhub\.aspx\?sort=[^']+'>[^<]+</a>\s*<div[^>]*>(.*?)</div>",
            block,
            re.S,
        )
        deadline = re.search(r"Application Deadline:\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})", block)
        out.append(
            {
                "slug": slug.group(1),
                "title": name,
                "institution": strip_tags(institution.group(1)) if institution else "",
                "location": html.unescape(where.group(1)).strip() if where else "",
                "blurb": re.sub(r"\s*\.\.\.read more\s*$", "", strip_tags(blurb.group(1)))[:400]
                if blurb
                else "",
                "listing_deadline": deadline.group(1) if deadline else "",
            }
        )
    return out


def load_cache() -> dict[str, str]:
    try:
        return json.loads(URL_CACHE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def official_url(session: requests.Session, slug: str) -> str:
    """The programme's own site, from its detail page.

    Falls back to the Pathways page, which always resolves. A link to an
    aggregator is worth less than a link to the organiser, but it is worth more
    than a row the verifier has to throw away for having nowhere to go.
    """
    detail = f"{BASE}/programhub.aspx?sort={slug}"
    try:
        response = session.get(detail, timeout=25)
        response.raise_for_status()
    except requests.RequestException:
        return detail
    external = re.findall(
        r'href=["\'](https?://(?!(?:www\.)?pathwaystoscience\.org)[^"\']{10,160})["\']',
        response.text,
    )
    for href in external:
        # Skip the directory's own furniture and anything that is plainly not a
        # programme page.
        if re.search(r"(facebook|twitter|x\.com|linkedin|youtube|instagram|ibparticipation|google)", href, re.I):
            continue
        # Drop any fragment. Some listings link with Chrome's scroll-to-text
        # syntax (`#:~:text=...`), which is a 90-character instruction to a
        # browser, not part of the address, and it makes two records for one
        # programme if the directory ever rewrites the quote.
        return href.split("#", 1)[0]
    return detail


def us_date(value: str) -> str:
    """M/D/YYYY -> ISO, or "" if it will not parse. Never guesses a year."""
    try:
        return datetime.strptime(value, "%m/%d/%Y").date().isoformat()
    except ValueError:
        return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="cap programmes this run")
    parser.add_argument("--no-detail", action="store_true",
                        help="skip the per-programme fetch that finds the official url")
    # Defaults when imported. scrape_all calls stage.main() with no arguments,
    # and a bare parse_args() would read ITS argv instead of this scraper's.
    args = parser.parse_args(argv if argv is not None else [])

    pool_entries = json.loads(POOL.read_text()) if POOL.exists() else []
    pool = {e["url"]: e for e in pool_entries}
    known = len(pool)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    try:
        listing = session.get(LISTING, timeout=35)
        listing.raise_for_status()
    except requests.RequestException as error:
        print(f"pathways: skipped ({error})")
        return 0

    programmes = parse_listing(listing.text)
    if args.limit:
        programmes = programmes[: args.limit]
    print(f"pathways: {len(programmes)} high-school programmes on the listing")

    now = datetime.now(timezone.utc).isoformat()
    cache = load_cache()
    added = reused = fetched = 0
    for prog in programmes:
        slug = prog["slug"]
        if args.no_detail:
            url = f"{BASE}/programhub.aspx?sort={slug}"
        elif slug in cache:
            # Learned on an earlier run. A slug's organiser does not change.
            url = cache[slug]
        else:
            url = official_url(session, slug)
            cache[slug] = url
            fetched += 1
            time.sleep(DETAIL_DELAY_SECONDS)
        if url in pool:
            reused += 1
            continue

        host = prog["institution"] or "Pathways to Science"
        where = prog["location"]
        pool[url] = {
            "source": "pathwaystoscience",
            "reddit_permalink": "",
            "posted_utc": now,
            "score": 0,
            "title": prog["title"],
            "url": url,
            "blurb": (
                f"{prog['title']} at {host}"
                + (f" ({where})" if where else "")
                + ". Funded STEM research programme listed for high-school students."
                + (f" {prog['blurb']}" if prog["blurb"] else "")
            )[:600],
            # Only ever the listing's own printed date, never inferred. Most
            # rows have none, and that is the verifier's job -- see the module
            # docstring.
            "deadline_guess": us_date(prog["listing_deadline"]),
            "field_guess": field_guess(f"{prog['title']} {prog['blurb']}"),
            "type_guess": "program",
            "audience_guess": "high_school",
            "location_guess": where or "united states",
            "needs_review": True,
        }
        added += 1

    ordered = sorted(pool.values(), key=lambda c: c.get("score", 0), reverse=True)
    POOL.write_text(json.dumps(ordered, indent=2))
    if not args.no_detail:
        URL_CACHE.parent.mkdir(parents=True, exist_ok=True)
        URL_CACHE.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n")
    dated = sum(1 for p in programmes if p["listing_deadline"])
    print(
        f"pathways: {added} new candidates, {reused} already known, "
        f"{fetched} detail pages fetched ({len(cache) - fetched} served from cache), "
        f"{dated} carried a deadline on the listing (pool {known} -> {len(pool)})"
    )
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
