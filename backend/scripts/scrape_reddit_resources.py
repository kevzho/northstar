"""
Reddit resource scraper, free learning material, from the COMMENTS.

WHY A SECOND REDDIT SCRAPER. scrape_reddit.py reads post titles, which is right
for opportunities: a programme announcement IS the post. It is wrong for
learning material, because the post is the question ("best free resource for
linear algebra?") and the material is in a reply. Measured on the pooled
candidates 2026-10-07: 891 of 11,293 carry a non-reddit URL at all, and the
most common hosts among them are sites.google.com, forms.gle and youtu.be --
the pool was never going to be a resource feed, because the resources were
never in the field it collects.

WHAT THIS GIVES THAT RECALL DOES NOT. Not "does OpenIntro Stats exist" -- any
model knows that, the same way it knew all 24 catalog rows existed. What it
gives is the long tail and the count: one professor's problem-set page, a
university's own notes, the free textbook that is not the famous free textbook,
each ranked by how many separate threads of students recommended it. A model
can tell you what is famous. It cannot tell you what the people who actually
did the thing keep telling each other to use.

CANDIDATES, NOT CATALOG ENTRIES. Nothing here is inserted. This writes
scraped/resource_candidates.json; scripts/import_resources.py fetches each page
and refuses anything whose free claim is not quotable from it.

Politeness / terms: reuses scrape_reddit.py's client, so it inherits the same
OAuth-or-public-fallback, the same descriptive User-Agent, and the same one
request every 1.5s (OAuth) or 6s (public). Only public listings, searches and
comment trees.

Usage:
    cd backend && .venv/bin/python scripts/scrape_reddit_resources.py
    cd backend && .venv/bin/python scripts/scrape_reddit_resources.py --threads 40
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time
from datetime import datetime, timezone

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.resource_verifier import is_resource_host  # noqa: E402
from app.urls import canonical_url  # noqa: E402

from scrape_reddit import Client, build_client  # noqa: E402

POOL = pathlib.Path(__file__).parent / "scraped" / "resource_candidates.json"

# Where students ask each other what to learn from. Deliberately not the
# opportunity subreddits: r/ApplyingToCollege talks about programmes, and
# r/learnmath talks about books.
SEARCHES: list[tuple[str, str, str]] = [
    # (subreddit, query, field)
    ("learnmath", "free textbook recommendation", "math"),
    ("learnmath", "best free resource", "math"),
    ("math", "free lecture notes", "math"),
    ("MathOlympiad", "free resources olympiad", "math"),
    ("statistics", "free textbook self study", "math"),
    ("learnprogramming", "free course recommendation", "cs"),
    ("learnpython", "best free resource beginner", "cs"),
    ("cscareerquestions", "free resources learn", "cs"),
    ("PhysicsStudents", "free textbook recommendation", "physics"),
    ("Physics", "free lecture notes self study", "physics"),
    ("AskPhysics", "free resource learn", "physics"),
    ("chemhelp", "free textbook resource", "biology"),
    ("chemistry", "free resources learn", "biology"),
    ("biology", "free textbook recommendation", "biology"),
    ("premed", "free resources learn biology", "health"),
    ("EngineeringStudents", "free textbook resource", "engineering"),
    ("AskEngineers", "free resources learn", "engineering"),
    ("AskElectronics", "free resources beginner", "engineering"),
    ("AskHistorians", "free primary sources online", "humanities"),
    ("history", "free online course", "humanities"),
    ("AskEconomics", "free textbook recommendation", "business"),
    ("writing", "free resources craft", "humanities"),
    ("userexperience", "free resources learn", "design"),
    ("gamedev", "free tutorial recommendation", "design"),
    ("highschool", "free resources learn", "interdisciplinary"),
    ("APStudents", "free resources study", "interdisciplinary"),
]

# The post has to be ASKING FOR MATERIAL. "Free resources?" yes; "is this
# programme worth it" no, because its replies are opinions about a programme,
# and this pipeline has no use for those.
ASKS_FOR_MATERIAL = re.compile(
    # Every noun plural-optional. "\bcourse\b" does not match "courses", and
    # "Any free courses on electronics?" is the archetypal thread this wants.
    r"\b(resources?|textbooks?|books?|courses?|lectures?|notes?|tutorials?|problem\s?sets?|"
    r"where (do|should|can) i (start|learn)|how (do|did) you learn|self[- ]?stud|"
    r"recommend)\b",
    re.I,
)

# A reply that is clearly not a recommendation. Cheap, and it keeps the
# aggregate counts meaning what they say.
NOT_A_RECOMMENDATION = re.compile(r"\b(don'?t\s+(use|bother|waste)|avoid|scam|paywall)\b", re.I)

# Parens are ALLOWED in the match and balanced afterwards. Excluding them was
# wrong in the one place it mattered: a wiki URL like
# .../wiki/Algebra_(ring_theory) is cut to .../wiki/Algebra, which 404s.
URL_IN_TEXT = re.compile(r"https?://[^\s<>\[\]\"'`]+")
# Sentence punctuation that is never the last character of a link anyone meant.
# Deliberately WITHOUT ")": whether a closing paren belongs to the URL or to the
# prose around it depends on balance, which trim_url works out.
TRAILING_JUNK = ".,;:!?'\"*_>"

# NOTE ON WHERE THE THRESHOLD LIVES. It is in import_resources.py, not here.
#
# This pool keeps EVERY external link it finds, including the ones mentioned
# once, because agreement is supposed to accumulate across runs: merge() unions
# the thread lists, so a resource recommended in one thread in October and
# another in January is two threads by January. Filtering here would throw away
# the first half of that count every night and nothing would ever reach two --
# the first run of this scraper found 197 distinct links and only 8 mentioned
# more than once, and under a filter here the other 189 would have had to be
# rediscovered from scratch tomorrow to be worth anything.
#
# So: remembering is cheap and happens here; spending a page fetch and a model
# verdict is not, and that decision belongs where the budget is.


def trim_url(raw: str) -> str:
    """Strip the prose off the end of a link without eating the link.

    "see https://ocw.mit.edu/18.06." and "[notes](https://x.edu/a)" and
    ".../wiki/Algebra_(ring_theory)" all have to come out right, and the third
    is why this is not one rstrip: a closing paren is part of the path when the
    parens balance and part of the sentence when they do not.
    """
    url = raw.rstrip(TRAILING_JUNK)
    while url.endswith(")") and url.count(")") > url.count("("):
        url = url[:-1].rstrip(TRAILING_JUNK)
    return url.rstrip("]}")


def extract_links(body: str) -> list[str]:
    """External links from one comment, canonicalised and deduped.

    Markdown links arrive as [text](url); the bare regex catches the url inside
    them, so they need no separate case. Trailing punctuation is stripped
    because "see https://ocw.mit.edu/18.06." is how people write.
    """
    out: list[str] = []
    seen: set[str] = set()
    for raw in URL_IN_TEXT.findall(body or ""):
        url = trim_url(raw)
        if not is_resource_host(url):
            continue
        canonical = canonical_url(url)
        if canonical in seen:
            continue
        seen.add(canonical)
        out.append(canonical)
    return out


def walk_comments(node: object) -> list[dict]:
    """Flatten a reddit comment tree into its comment dicts.

    A comments response nests Listing -> children -> t1 -> replies -> Listing,
    `replies` is the empty STRING when a comment has none, and the last child of
    every listing is a "more" stub with no body. All three are why this is a
    recursive walk over whatever it is handed rather than a couple of indexes.
    """
    out: list[dict] = []
    if isinstance(node, list):
        for item in node:
            out.extend(walk_comments(item))
    elif isinstance(node, dict):
        if node.get("kind") == "t1":
            data = node.get("data") or {}
            out.append(data)
            out.extend(walk_comments(data.get("replies")))
        elif isinstance(node.get("data"), dict):
            out.extend(walk_comments(node["data"].get("children")))
    return out


def tally(threads: list[dict]) -> dict[str, dict]:
    """Aggregate links across threads into candidates.

    `mentions` counts COMMENTS, `threads` counts distinct discussions, and the
    second is the honest one: ten people in one thread agreeing is one thread
    agreeing. import_resources sorts on threads first for that reason.
    """
    found: dict[str, dict] = {}
    for thread in threads:
        for comment in thread["comments"]:
            body = comment.get("body") or ""
            if NOT_A_RECOMMENDATION.search(body):
                continue
            score = comment.get("score")
            for url in extract_links(body):
                entry = found.setdefault(url, {
                    "url": url,
                    "mentions": 0,
                    "threads": [],
                    "subreddits": [],
                    "field_guess": thread["field"],
                    "upvotes": 0,
                    "quotes": [],
                    "first_seen": datetime.now(timezone.utc).isoformat(),
                })
                entry["mentions"] += 1
                entry["upvotes"] += score if isinstance(score, int) else 0
                if thread["permalink"] not in entry["threads"]:
                    entry["threads"].append(thread["permalink"])
                if thread["subreddit"] not in entry["subreddits"]:
                    entry["subreddits"].append(thread["subreddit"])
                # One short quote, so a human reviewing the pool can see WHY it
                # was recommended rather than only that it was.
                if len(entry["quotes"]) < 3:
                    entry["quotes"].append(body.strip().replace("\n", " ")[:240])
    for entry in found.values():
        entry["thread_count"] = len(entry["threads"])
    return found


def merge(existing: list[dict], found: dict[str, dict]) -> list[dict]:
    """Union by url, keeping any review field a human added.

    Same contract as the opportunity pool: a re-run must never erase a verdict
    someone recorded by hand. Counts accumulate across runs because a resource
    recommended in March and again in October is more recommended, not newly
    recommended.
    """
    by_url = {row["url"]: row for row in existing}
    for url, entry in found.items():
        previous = by_url.get(url)
        if previous is None:
            by_url[url] = entry
            continue
        previous["mentions"] = max(previous.get("mentions", 0), entry["mentions"])
        previous["upvotes"] = max(previous.get("upvotes", 0), entry["upvotes"])
        previous["threads"] = sorted({*previous.get("threads", []), *entry["threads"]})
        previous["subreddits"] = sorted({*previous.get("subreddits", []), *entry["subreddits"]})
        previous["thread_count"] = len(previous["threads"])
        if not previous.get("quotes"):
            previous["quotes"] = entry["quotes"]
    rows = list(by_url.values())
    rows.sort(key=lambda r: (-r.get("thread_count", 0), -r.get("mentions", 0), r["url"]))
    return rows


def fetch_comments(client: Client, subreddit: str, post_id: str) -> list[dict]:
    """One post's comment tree. Returns [] on anything unexpected."""
    url = f"{client.base}/r/{subreddit}/comments/{post_id}{client.suffix}"
    response = requests.get(
        url,
        params={"limit": 100, "sort": "top", "depth": 2},
        headers=client.headers,
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    # A comments response is a LIST of two listings (the post, then the
    # replies) -- not the single listing fetch_page in scrape_reddit.py expects,
    # which is why this does its own request.
    if not isinstance(payload, list) or len(payload) < 2:
        return []
    return walk_comments(payload[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threads", type=int, default=60,
                        help="how many comment trees to read this run")
    # `argv or []` and sys.argv[1:] passed from __main__, not parse_args(None).
    # scrape_all.py calls stage.main() with no arguments and must get no flags;
    # a bare parse_args(None) would hand it the runner's own command line. The
    # inverse mistake -- hardcoding [] here -- is worse and was made: it made
    # import_resources ignore --dry-run and write to the live table.
    args = parser.parse_args(argv or [])

    client = build_client()
    print(f"Reading comment trees at one request every {client.delay}s.")

    # Find the threads worth reading.
    posts: list[tuple[str, dict, str]] = []
    seen_ids: set[str] = set()
    errors = 0
    for subreddit, query, field in SEARCHES:
        try:
            url = f"{client.base}/r/{subreddit}/search{client.suffix}"
            response = requests.get(
                url,
                params={"q": query, "restrict_sr": 1, "sort": "top", "t": "year", "limit": 25},
                headers=client.headers,
                timeout=20,
            )
            response.raise_for_status()
            children = response.json().get("data", {}).get("children", [])
            time.sleep(client.delay)
        except (requests.RequestException, ValueError) as error:
            errors += 1
            print(f"  r/{subreddit} '{query}': {error}")
            continue
        kept = 0
        for child in children:
            post = child.get("data", {})
            if post.get("id") in seen_ids:
                continue
            if not ASKS_FOR_MATERIAL.search(post.get("title", "")):
                continue
            seen_ids.add(post.get("id"))
            posts.append((subreddit, post, field))
            kept += 1
        print(f"  r/{subreddit} '{query}': {kept} threads asking for material")

    posts.sort(key=lambda p: -(p[1].get("num_comments") or 0))
    posts = posts[: args.threads]
    print(f"\nReading {len(posts)} comment trees (busiest first).")

    threads: list[dict] = []
    for subreddit, post, field in posts:
        try:
            comments = fetch_comments(client, subreddit, post.get("id", ""))
        except (requests.RequestException, ValueError) as error:
            errors += 1
            print(f"  {post.get('id')}: {error}")
            continue
        time.sleep(client.delay)
        threads.append({
            "subreddit": f"r/{subreddit}",
            "field": field,
            "permalink": "https://www.reddit.com" + (post.get("permalink") or ""),
            "title": post.get("title", ""),
            "comments": comments,
        })

    found = tally(threads)
    agreed = sum(1 for e in found.values() if e["thread_count"] > 1)
    print(f"{len(found)} distinct links, {agreed} recommended in more than one thread.")

    POOL.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(POOL.read_text()) if POOL.exists() else []
    rows = merge(existing, found)
    POOL.write_text(json.dumps(rows, indent=2) + "\n")
    print(f"Pool: {len(existing)} -> {len(rows)} candidates at {POOL}")

    for row in rows[:10]:
        print(f"  {row['thread_count']}x threads  {row['url'][:72]}")

    # Soft failure, like the other scrapers: partial data is still data. The
    # import stage is the one that must go red.
    if errors:
        print(f"\n{errors} request(s) failed; pool was still written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
