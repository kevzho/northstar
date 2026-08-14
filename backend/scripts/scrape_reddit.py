"""
Reddit opportunity scraper — candidate STEM opportunities from student subreddits.

Harvests posts from subreddits where real programs, competitions, internships,
and scholarships get posted, filters them down to opportunity-shaped posts,
and MERGES them into a growing review pool. It deliberately does NOT insert
into the database: scraped posts are candidates, not catalog entries — the
maintainer reviews `scraped/reddit_candidates.json`, fixes fields the
heuristics guessed, and only then adds keepers to the seed catalog.

Designed to be run repeatedly: each run paginates several pages deep per
subreddit, runs targeted searches on top of the /new listings, and merges
into the existing pool keyed by URL — entries you have already reviewed
keep whatever fields you added to them (e.g. "review": "keep" / "drop"),
and re-runs only append genuinely unseen posts.

Politeness / terms:
- Uses Reddit's official OAuth API (app-only grant) with a descriptive
  User-Agent and one request every ~1.5 seconds — far inside the free
  tier's 100 queries/minute. Only public subreddit listings and searches.

Setup (one time):
    1. https://www.reddit.com/prefs/apps -> create app -> type "script"
       (name: northstar-scraper, redirect uri: http://localhost:8080)
    2. Add to backend/.env:
           REDDIT_CLIENT_ID=<the string under the app name>
           REDDIT_CLIENT_SECRET=<the secret>

Usage:
    cd backend && .venv/bin/python scripts/train_als.py   # unrelated
    cd backend && .venv/bin/python scripts/scrape_reddit.py
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import time
from datetime import datetime, timezone

import requests

try:
    from dotenv import load_dotenv

    load_dotenv(pathlib.Path(__file__).resolve().parents[1] / ".env", override=False)
except ImportError:
    pass

USER_AGENT = "northstar-opportunity-scraper/0.2 (student project; contact: dev.thorfinn@gmail.com)"

SUBREDDITS = [
    "summerprograms",
    "scholarships",
    "internships",
    "highschool",
    "ApplyingToCollege",
    "csMajors",
    "premed",
]

# Targeted searches sweep further back than /new can reach.
SEARCHES = [
    "high school summer program",
    "high school research program",
    "scholarship deadline",
    "STEM competition high school",
    "high school internship",
]
SEARCH_SUBREDDITS = ["summerprograms", "scholarships", "ApplyingToCollege"]

PAGES_PER_LISTING = 4  # 4 x 75 = up to 300 posts per subreddit per run
REQUEST_DELAY_S = 1.5

LISTING = "https://oauth.reddit.com/r/{sub}/new"
SEARCH = "https://oauth.reddit.com/r/{sub}/search"
TOKEN_URL = "https://www.reddit.com/api/v1/access_token"


def get_token() -> str:
    """App-only OAuth token; read-only scope, no user context."""
    client_id = os.getenv("REDDIT_CLIENT_ID", "")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        sys.exit(
            "Missing REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET in backend/.env.\n"
            "Create a 'script' app at https://www.reddit.com/prefs/apps and add both values."
        )
    response = requests.post(
        TOKEN_URL,
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()["access_token"]


# A post has to look like an opportunity, not a question about one.
INCLUDE = re.compile(
    r"\b(program|internship|competition|scholarship|fellowship|research|"
    r"hackathon|olympiad|summer|apply|applications?\s+open|deadline)\b",
    re.IGNORECASE,
)
EXCLUDE = re.compile(
    r"\b(chance me|rejected|rant|meme|advice\??$|help\??$|should i|"
    r"is it worth|anyone else|results thread)\b",
    re.IGNORECASE,
)

FIELD_HINTS: list[tuple[str, re.Pattern[str]]] = [
    ("cs", re.compile(r"\b(cs|coding|programming|software|ai|ml|computer|hackathon|robotics?)\b", re.I)),
    ("biology", re.compile(r"\b(bio|biology|medic|neuro|pre-?med|health|genome)\b", re.I)),
    ("math", re.compile(r"\b(math|olympiad|amc|aime|putnam)\b", re.I)),
    ("physics", re.compile(r"\b(physics|astro|space|quantum)\b", re.I)),
    ("engineering", re.compile(r"\b(engineer|mechanical|electrical|aero|rocket)\b", re.I)),
]

TYPE_HINTS: list[tuple[str, re.Pattern[str]]] = [
    ("scholarship", re.compile(r"\b(scholarship|grant|award)\b", re.I)),
    ("competition", re.compile(r"\b(competition|contest|olympiad|challenge|hackathon)\b", re.I)),
    ("mentorship", re.compile(r"\b(mentor|mentorship)\b", re.I)),
    ("program", re.compile(r"\b(program|internship|fellowship|camp|course)\b", re.I)),
]


def classify(pattern_list: list[tuple[str, re.Pattern[str]]], text: str, default: str) -> str:
    for label, pattern in pattern_list:
        if pattern.search(text):
            return label
    return default


def fetch_page(
    url: str, token: str, params: dict
) -> tuple[list[dict], str | None]:
    response = requests.get(
        url,
        params=params,
        headers={"User-Agent": USER_AGENT, "Authorization": f"bearer {token}"},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json().get("data", {})
    posts = [c["data"] for c in data.get("children", []) if c.get("kind") == "t3"]
    return posts, data.get("after")


def harvest_listing(sub: str, token: str) -> list[dict]:
    """Paginate /r/{sub}/new several pages deep."""
    posts: list[dict] = []
    after: str | None = None
    for _ in range(PAGES_PER_LISTING):
        params = {"limit": 75}
        if after:
            params["after"] = after
        page, after = fetch_page(LISTING.format(sub=sub), token, params)
        posts.extend(page)
        time.sleep(REQUEST_DELAY_S)
        if not after:
            break
    return posts


def harvest_search(sub: str, query: str, token: str) -> list[dict]:
    """One page of subreddit-restricted search, sorted newest, past year."""
    posts, _ = fetch_page(
        SEARCH.format(sub=sub),
        token,
        {"q": query, "restrict_sr": 1, "sort": "new", "t": "year", "limit": 75},
    )
    time.sleep(REQUEST_DELAY_S)
    return posts


def to_candidate(post: dict, source: str) -> dict:
    title = post.get("title", "").strip()
    text = f"{title}\n{post.get('selftext', '')[:2000]}"
    blurb = re.sub(r"\s+", " ", post.get("selftext", "")).strip()[:220]
    external = post.get("url_overridden_by_dest") or ""
    return {
        "source": source,
        "reddit_permalink": f"https://www.reddit.com{post.get('permalink', '')}",
        "posted_utc": datetime.fromtimestamp(
            post.get("created_utc", 0), tz=timezone.utc
        ).isoformat(),
        "score": post.get("score", 0),
        "title": title,
        "url": external or f"https://www.reddit.com{post.get('permalink', '')}",
        "blurb": blurb or title,
        "field_guess": classify(FIELD_HINTS, text, "interdisciplinary"),
        "type_guess": classify(TYPE_HINTS, text, "program"),
        "needs_review": True,
    }


def looks_like_opportunity(post: dict) -> bool:
    title = post.get("title", "")
    body = post.get("selftext", "")[:2000]
    return bool(INCLUDE.search(f"{title}\n{body}")) and not EXCLUDE.search(title)


def main() -> None:
    token = get_token()

    out_dir = pathlib.Path(__file__).parent / "scraped"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "reddit_candidates.json"

    # The pool is cumulative: reviewed entries keep every field the reviewer
    # added; re-runs only append URLs the pool has never seen.
    pool: dict[str, dict] = {}
    if out_path.exists():
        try:
            for entry in json.loads(out_path.read_text()):
                pool[entry["url"]] = entry
        except (ValueError, KeyError):
            print(f"warning: could not parse existing {out_path}; starting fresh")

    known = len(pool)
    new_count = 0

    def consider(post: dict, source: str) -> None:
        nonlocal new_count
        if not looks_like_opportunity(post):
            return
        candidate = to_candidate(post, source)
        if candidate["url"] in pool:
            return
        pool[candidate["url"]] = candidate
        new_count += 1

    for sub in SUBREDDITS:
        try:
            posts = harvest_listing(sub, token)
        except requests.RequestException as error:
            print(f"r/{sub}: skipped ({error})")
            continue
        before = new_count
        for post in posts:
            consider(post, f"r/{sub}")
        print(f"r/{sub}: {len(posts)} posts, {new_count - before} new candidates")

    for sub in SEARCH_SUBREDDITS:
        for query in SEARCHES:
            try:
                posts = harvest_search(sub, query, token)
            except requests.RequestException as error:
                print(f"r/{sub} search '{query}': skipped ({error})")
                continue
            before = new_count
            for post in posts:
                consider(post, f"r/{sub} search:{query}")
            if new_count > before:
                print(f"r/{sub} search '{query}': {new_count - before} new")

    ordered = sorted(pool.values(), key=lambda c: c.get("score", 0), reverse=True)
    out_path.write_text(json.dumps(ordered, indent=2))

    print(f"\npool: {known} known + {new_count} new = {len(ordered)} candidates")
    print(f"-> {out_path}")
    print("Review them, fix guessed fields, then add keepers to the seed catalog.")


if __name__ == "__main__":
    main()
