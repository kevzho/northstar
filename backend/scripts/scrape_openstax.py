"""
OpenStax: peer-reviewed, openly licensed textbooks, each with a free PDF.

WHY THIS SOURCE. The learning shelf had 44 rows and every one of them was a
skill rung for some archetype -- "accessibility", "control basics",
"regulatory literacy". Genuinely useful to the student whose generated path
names that rung, and useless to a tenth grader who just wants the biology
textbook. The shelf was deep and narrow when the students using it need the
opposite.

OpenStax is the one source that fixes that in a single pass: Algebra 1,
Biology, Chemistry, Physics, Statistics, Psychology, US History, Economics --
the actual courses a high schooler takes -- written to standard scope and
sequence, peer reviewed, and free to read online or download as a PDF. There
is no "free tier" to misread, which is the failure mode app/resource_verifier.py
spends most of its rules on.

WHY THE CMS API AND NOT THE HTML. openstax.org/apps/cms/api/v2/pages is the
site's own public Wagtail API and is permitted by their robots.txt (only
/apps/cms/api/spike is disallowed; the /books/ rule names GPTBot specifically,
which we are not). It returns book_state, so their own retirement flag comes
with the data.

ONLY `live` BOOKS. Of 129 entries, 30 are retired, 6 unlisted and 3 deprecated.
A retired textbook is exactly what this catalog refuses everywhere else, and
here the publisher is telling us which ones they are -- there is no excuse for
importing them.

CANDIDATES, NOT ROWS. This writes to the resource candidate pool.
scripts/import_resources.py still fetches each page and refuses anything whose
free claim it cannot quote from it. A textbook that is obviously free still has
to prove it, the same as everything else.

Usage:
    cd backend && .venv/bin/python scripts/scrape_openstax.py
    cd backend && .venv/bin/python scripts/import_resources.py
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from datetime import datetime, timezone

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.robots import allowed  # noqa: E402

POOL = pathlib.Path(__file__).parent / "scraped" / "resource_candidates.json"
API = "https://openstax.org/apps/cms/api/v2/pages/"
# The BOOK, not the marketing page. /details/books/<slug> is a React shell
# whose server HTML is the single word "OpenStax", so nothing can be verified
# from it and import_resources correctly refused all 83. /books/<slug>/pages/
# preface is server-rendered, is per-book, and is a better place to land a
# student anyway: it is the book. robots.txt disallows /books/ for GPTBot
# specifically, not for everyone.
DETAIL = "https://openstax.org/books/{slug}/pages/preface"
USER_AGENT = (
    "northstar-catalog/1.0 (student nonprofit learning shelf; "
    "contact: dev.thorfinn@gmail.com)"
)
PAGE_SIZE = 50
REQUEST_DELAY_S = 1.0

# OpenStax's subject names -> this catalog's field vocabulary. Only a hint:
# import_resources reads the page and the model assigns the final field.
FIELD = {
    "math": "math",
    "science": "biology",
    "social sciences": "humanities",
    "humanities": "humanities",
    "business": "business",
    "college success": "interdisciplinary",
    "nursing": "health",
    "high school": "interdisciplinary",
}

# Books whose subject says Science but which are plainly not biology. The hint
# only has to be close enough to sort the pool; the verifier decides.
TITLE_FIELD = (
    ("physic", "physics"), ("astronom", "physics"),
    ("chemistr", "biology"), ("biolog", "biology"), ("anatomy", "health"),
    ("microbiolog", "biology"),
    ("statistic", "math"), ("calculus", "math"), ("algebra", "math"),
    ("precalculus", "math"), ("trigonometr", "math"),
    ("psycholog", "health"), ("sociolog", "humanities"),
    ("econom", "business"), ("account", "business"), ("business", "business"),
    ("history", "humanities"), ("government", "humanities"),
    ("philosoph", "humanities"), ("writing", "humanities"),
    ("engineering", "engineering"), ("manufactur", "engineering"),
    ("computer", "cs"), ("python", "cs"), ("programming", "cs"),
)


def field_for(title: str, subject: str) -> str:
    low = title.lower()
    for needle, field in TITLE_FIELD:
        if needle in low:
            return field
    return FIELD.get((subject or "").strip().lower(), "interdisciplinary")


def fetch_books(session: requests.Session) -> list[dict]:
    fields = "title,book_subjects,book_state,high_resolution_pdf_url,description"
    books: list[dict] = []
    offset = 0
    while True:
        response = session.get(
            API,
            params={"type": "books.Book", "limit": PAGE_SIZE, "offset": offset,
                    "fields": fields},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("items", [])
        books.extend(items)
        offset += len(items)
        total = payload.get("meta", {}).get("total_count", 0)
        time.sleep(REQUEST_DELAY_S)
        if not items or offset >= total:
            break
    return books


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv or [])

    if not allowed(API, USER_AGENT):
        print("openstax: robots.txt disallows the CMS API; stopping.")
        return 0

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        books = fetch_books(session)
    except (requests.RequestException, ValueError) as error:
        print(f"openstax: {error}")
        return 0

    live = [b for b in books if (b.get("book_state") or "").lower() == "live"]
    print(f"{len(books)} books, {len(live)} live "
          f"({len(books) - len(live)} retired, unlisted or deprecated: skipped)")

    pool = json.loads(POOL.read_text()) if POOL.exists() else []
    seen = {row.get("url") for row in pool}
    now = datetime.now(timezone.utc).isoformat()

    added = 0
    for book in live:
        # The slug lives under meta, not as a top-level field: asking for it
        # in `fields` is silently ignored, which is how the first run quietly
        # produced zero candidates from 84 live books.
        slug = ((book.get("meta") or {}).get("slug") or "").strip()
        title = (book.get("title") or "").strip()
        if not slug or not title:
            continue
        url = DETAIL.format(slug=slug)
        if url in seen:
            continue

        subjects = book.get("book_subjects") or []
        subject = ""
        if subjects and isinstance(subjects[0], dict):
            subject = subjects[0].get("subject_name") or ""

        pdf = (book.get("high_resolution_pdf_url") or "").strip()
        blurb = (book.get("description") or "").strip()

        pool.append({
            # Trusted to be REACHED by import_resources, not trusted to skip
            # it: the page is still fetched and the free claim still has to be
            # quotable from it.
            "source": "openstax",
            "url": url,
            "title": title,
            "blurb": blurb[:600],
            "field_guess": field_for(title, subject),
            "subject": subject,
            # Recorded so the importer can say so, and so a human reviewing the
            # pool can see which of these actually ship a downloadable book.
            "pdf_url": pdf,
            "mentions": 1,
            "thread_count": 0,
            "threads": [],
            "subreddits": [],
            "upvotes": 0,
            "quotes": [],
            "first_seen": now,
        })
        added += 1

    if args.dry_run:
        print(f"would add {added} candidates (pool stays {len(pool) - added})")
        for row in (pool[-added:] if added else [])[:8]:
            print(f"   {row['field_guess']:16} {row['title'][:46]:48} pdf={bool(row['pdf_url'])}")
        return 0

    POOL.parent.mkdir(parents=True, exist_ok=True)
    POOL.write_text(json.dumps(pool, indent=2) + "\n")
    print(f"added {added}; pool now {len(pool)}")
    print("Next: .venv/bin/python scripts/import_resources.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
