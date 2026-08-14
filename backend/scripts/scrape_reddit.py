"""
Reddit opportunity scraper — candidate STEM opportunities from student subreddits.

Pulls recent posts from a small list of subreddits where real programs,
competitions, internships, and scholarships get posted, filters them down to
opportunity-shaped posts, and writes them to a review file. It deliberately
does NOT insert into the database: scraped posts are candidates, not catalog
entries — the maintainer reviews `scraped/reddit_candidates.json`, fixes
fields the heuristics guessed (field, type, deadline), and only then adds the
keepers to scripts/seed_opportunities.sql.

Politeness / terms:
- Uses Reddit's official OAuth API (app-only grant) with a descriptive
  User-Agent and one request every ~1.5 seconds. Only public subreddit
  listings, no user pages. Run occasionally by hand, not on a schedule.

Setup (one time):
    1. https://www.reddit.com/prefs/apps -> create app -> type "script"
       (name: northstar-scraper, redirect uri: http://localhost:8080)
    2. Add to backend/.env:
           REDDIT_CLIENT_ID=<the string under the app name>
           REDDIT_CLIENT_SECRET=<the secret>

Usage:
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

USER_AGENT = "northstar-opportunity-scraper/0.1 (student project; contact: dev.thorfinn@gmail.com)"

SUBREDDITS = [
    "summerprograms",
    "scholarships",
    "internships",
    "highschool",
    "ApplyingToCollege",
]

LISTING = "https://oauth.reddit.com/r/{sub}/new?limit=75"
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


def fetch_listing(sub: str, token: str) -> list[dict]:
    response = requests.get(
        LISTING.format(sub=sub),
        headers={"User-Agent": USER_AGENT, "Authorization": f"bearer {token}"},
        timeout=20,
    )
    response.raise_for_status()
    children = response.json().get("data", {}).get("children", [])
    return [child["data"] for child in children if child.get("kind") == "t3"]


def to_candidate(post: dict, sub: str) -> dict:
    title = post.get("title", "").strip()
    text = f"{title}\n{post.get('selftext', '')[:2000]}"
    blurb = re.sub(r"\s+", " ", post.get("selftext", "")).strip()[:220]
    external = post.get("url_overridden_by_dest") or ""
    return {
        "source": f"r/{sub}",
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


def main() -> None:
    token = get_token()
    seen_urls: set[str] = set()
    candidates: list[dict] = []

    for sub in SUBREDDITS:
        try:
            posts = fetch_listing(sub, token)
        except requests.RequestException as error:
            print(f"r/{sub}: skipped ({error})")
            time.sleep(1.5)
            continue

        kept = 0
        for post in posts:
            title = post.get("title", "")
            body = post.get("selftext", "")[:2000]
            haystack = f"{title}\n{body}"
            if not INCLUDE.search(haystack) or EXCLUDE.search(title):
                continue
            candidate = to_candidate(post, sub)
            if candidate["url"] in seen_urls:
                continue
            seen_urls.add(candidate["url"])
            candidates.append(candidate)
            kept += 1
        print(f"r/{sub}: {len(posts)} posts, kept {kept}")
        time.sleep(1.5)

    candidates.sort(key=lambda c: c["score"], reverse=True)

    out_dir = pathlib.Path(__file__).parent / "scraped"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "reddit_candidates.json"
    out_path.write_text(json.dumps(candidates, indent=2))
    print(f"\n{len(candidates)} candidates -> {out_path}")
    print("Review them, fix guessed fields, then add keepers to scripts/seed_opportunities.sql.")


if __name__ == "__main__":
    main()
