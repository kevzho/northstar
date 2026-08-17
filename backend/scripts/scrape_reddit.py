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
- Prefers Reddit's official OAuth API (app-only grant) with a descriptive
  User-Agent and one request every ~1.5 seconds — far inside the free
  tier's 100 queries/minute. Only public subreddit listings and searches.
- Without working credentials it falls back to the public `.json`
  endpoints at one request every 6 seconds (~10/minute). Same data,
  slower run; expect the full sweep to take several minutes.

Setup (one time; optional since the public fallback works without it):
    1. https://www.reddit.com/prefs/apps -> create app -> type "script"
       (name: northstar-scraper, redirect uri: http://localhost:8080)
    2. Add to backend/.env:
           REDDIT_CLIENT_ID=<the string under the app name>
           REDDIT_CLIENT_SECRET=<the secret>
    3. Since Dec 2025 Reddit's Responsible Builder Policy gates new OAuth
       access behind a manual approval request (Data API wiki -> contact
       us -> developer, non-commercial). Until approval lands the token
       call may 401/403 — the script detects that and uses the fallback.

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
from typing import NamedTuple

import requests

try:
    from dotenv import load_dotenv

    load_dotenv(pathlib.Path(__file__).resolve().parents[1] / ".env", override=False)
except ImportError:
    pass

USER_AGENT = "northstar-opportunity-scraper/0.2 (student project; contact: dev.thorfinn@gmail.com)"

# (subreddit, audience, field) — audience seeds each candidate's
# audience_guess so reviewed keepers land on the right catalog shelf;
# field is the default stamped when no FIELD_HINTS text hint overrides
# it, which is what makes single-field subreddits (r/FRC, r/Debate)
# worth sweeping: their posts rarely repeat the field in the title.
SUBREDDITS: list[tuple[str, str, str]] = [
    ("summerprogramresults", "high_school", "interdisciplinary"),
    ("HSSummerPrograms", "high_school", "interdisciplinary"),
    ("scholarships", "high_school", "interdisciplinary"),
    ("highschool", "high_school", "interdisciplinary"),
    ("ApplyingToCollege", "high_school", "interdisciplinary"),
    ("internships", "college", "interdisciplinary"),
    ("csMajors", "college", "cs"),
    ("premed", "college", "biology"),
    ("REU", "college", "interdisciplinary"),
    ("FinancialCareers", "college", "business"),
    ("quant", "college", "business"),
    ("chemistry", "high_school", "biology"),
    ("EngineeringStudents", "college", "engineering"),
    ("labrats", "college", "biology"),
    # Field-specific sweeps (verified public + SFW, 2026-08):
    ("MathOlympiad", "high_school", "math"),
    ("PhysicsStudents", "college", "physics"),
    ("FRC", "high_school", "engineering"),
    ("Debate", "high_school", "humanities"),
    ("ArtistLounge", "high_school", "design"),
    ("biology", "college", "biology"),
    ("volunteer", "high_school", "interdisciplinary"),
]

# Targeted searches sweep further back than /new can reach.
SEARCHES = [
    "high school summer program",
    "high school research program",
    "scholarship deadline",
    "STEM competition high school",
    "high school internship",
]
SEARCH_SUBREDDITS = ["summerprogramresults", "scholarships", "ApplyingToCollege", "highschool"]

# The matcher personalizes on opportunity_field, so the pool has to cover
# every field — /new listings alone skew cs/bio (csMajors, premed) and
# leave math/physics/engineering underrepresented. These searches also
# stamp the field onto the candidate when no text hint contradicts it.
FIELD_SEARCHES: dict[str, list[str]] = {
    "math": [
        "math olympiad qualifier", "math summer program", "AMC AIME preparation program",
        "math research program high school", "Ross Mathematics",
    ],
    "physics": [
        "physics olympiad", "astronomy research high school", "USAPhO",
        "physics summer program high school", "space research internship high school",
    ],
    "engineering": [
        "engineering summer program", "robotics competition high school",
        "aerospace program high school", "civil engineering internship high school",
    ],
    "biology": [
        "biology research program high school", "medical program high school",
        "USABO biology olympiad", "neuroscience program high school",
        "genetics research high school", "chemistry olympiad USNCO",
    ],
    "cs": ["AI research high school", "coding summer program"],
    "design": ["art portfolio program", "design summer program high school"],
    "business": [
        "business summer program high school",
        "entrepreneurship competition",
        "finance summer program high school",
        "economics competition high school",
        "investment banking high school program",
        "DECA scholarship",
    ],
    "humanities": ["writing program high school", "debate scholarship"],
    "health": ["public health program high school", "medical volunteering"],
}

# College sweep — r/REU is literally Research Experiences for
# Undergraduates; the others carry internship and program threads.
COLLEGE_SEARCHES = [
    "REU application",
    "undergraduate research program",
    "college internship application",
    "undergraduate scholarship",
]
COLLEGE_SEARCH_SUBREDDITS = ["csMajors", "internships", "REU"]

# Finance/econ sweep — these subreddits carry internship, fellowship, and
# competition threads that the generic college searches miss.
FINANCE_SEARCHES = [
    "summer analyst application",
    "finance internship deadline",
    "economics fellowship",
    "quant internship",
    "sophomore diversity program finance",
]
FINANCE_SEARCH_SUBREDDITS = ["FinancialCareers", "quant"]

# Volunteer sweep — service hours are the extracurricular every student
# needs and the catalog's newest type. r/volunteer posts real openings;
# the general HS subreddits carry "where do I volunteer" threads whose
# answers name organizations worth cataloging.
VOLUNTEER_SEARCHES: list[tuple[str, str]] = [
    ("high school volunteer opportunity", "interdisciplinary"),
    ("virtual volunteering students", "interdisciplinary"),
    ("community service hours program", "interdisciplinary"),
    ("hospital volunteer high school", "health"),
    ("environmental volunteering high school", "biology"),
    ("volunteer tutoring program", "interdisciplinary"),
    ("museum volunteer program", "humanities"),
]
VOLUNTEER_SEARCH_SUBREDDITS = ["volunteer", "highschool", "ApplyingToCollege"]

PAGES_PER_LISTING = 4  # 4 x 75 = up to 300 posts per subreddit per run

OAUTH_BASE = "https://oauth.reddit.com"
PUBLIC_BASE = "https://www.reddit.com"
TOKEN_URL = "https://www.reddit.com/api/v1/access_token"


class Client(NamedTuple):
    """Where to send requests and how fast; OAuth or public fallback."""

    base: str
    headers: dict[str, str]
    delay: float

    @property
    def suffix(self) -> str:
        return "" if self.base == OAUTH_BASE else ".json"


def build_client() -> Client:
    """OAuth when credentials work; public .json endpoints otherwise.

    Reddit's Responsible Builder Policy gates new OAuth access behind a
    manual approval, so a refused token is expected, not fatal.
    """
    client_id = os.getenv("REDDIT_CLIENT_ID", "")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
    if client_id and client_secret:
        try:
            response = requests.post(
                TOKEN_URL,
                auth=(client_id, client_secret),
                data={"grant_type": "client_credentials"},
                headers={"User-Agent": USER_AGENT},
                timeout=20,
            )
            response.raise_for_status()
            token = response.json()["access_token"]
            return Client(
                OAUTH_BASE,
                {"User-Agent": USER_AGENT, "Authorization": f"bearer {token}"},
                1.5,
            )
        except requests.RequestException as error:
            print(f"OAuth token refused ({error}); using public endpoints.")
    else:
        print("No REDDIT_CLIENT_ID/SECRET in backend/.env; using public endpoints.")
    return Client(PUBLIC_BASE, {"User-Agent": USER_AGENT}, 6.0)


# A post has to look like an opportunity, not a question about one.
# Volunteer terms stay phrase-shaped ("volunteers needed", "volunteer
# opportunity", "service hours"): the bare word would pass every personal
# story on r/volunteer, where all 300 listing posts contain it.
INCLUDE = re.compile(
    r"\b(program|internship|competition|scholarship|fellowship|research|"
    r"hackathon|olympiad|summer|apply|applications?\s+open|deadline|"
    r"volunteers?\s+(?:needed|wanted)|volunteer(?:ing)?\s+opportunit\w*|"
    r"service\s+hours)\b",
    re.IGNORECASE,
)
EXCLUDE = re.compile(
    r"\b(chance me|rejected|rant|meme|advice\??$|help\??$|should i|"
    r"is it worth|anyone else|results thread)\b"
    # Seeker posts, not offers: someone asking where to find an
    # opportunity is not one. Matters most on r/volunteer, where half
    # the listing is "Looking for volunteer opportunities in <city>?".
    r"|^\s*looking for\b|\bwhere (?:can|do|should) i\b|\bhow (?:do|can|should) i\b",
    re.IGNORECASE,
)

FIELD_HINTS: list[tuple[str, re.Pattern[str]]] = [
    ("cs", re.compile(r"\b(cs|coding|programming|software|ai|ml|computer|hackathon|robotics?)\b", re.I)),
    ("biology", re.compile(r"\b(bio|biology|medic|neuro|pre-?med|health|genome)\b", re.I)),
    ("math", re.compile(r"\b(math|olympiad|amc|aime|putnam)\b", re.I)),
    ("physics", re.compile(r"\b(physics|astro|space|quantum)\b", re.I)),
    ("engineering", re.compile(r"\b(engineer|mechanical|electrical|aero|rocket)\b", re.I)),
    ("design", re.compile(r"\b(design|art|animation|film|game\s?dev|ux|portfolio)\b", re.I)),
    ("business", re.compile(r"\b(business|entrepreneur|startup|econ|finance|investing)\b", re.I)),
    ("humanities", re.compile(r"\b(writing|journalism|debate|policy|history|essay)\b", re.I)),
    ("health", re.compile(r"\b(public\s?health|nursing|sports\s?med|nutrition|mental\s?health)\b", re.I)),
]

TYPE_HINTS: list[tuple[str, re.Pattern[str]]] = [
    ("scholarship", re.compile(r"\b(scholarship|grant|award)\b", re.I)),
    ("competition", re.compile(r"\b(competition|contest|olympiad|challenge|hackathon)\b", re.I)),
    ("journal", re.compile(r"\b(journal|publication|publish|peer[- ]?review)\b", re.I)),
    ("volunteer", re.compile(r"\b(volunteer|service|nonprofit|tutoring)\b", re.I)),
    ("internship", re.compile(r"\b(internship|intern|apprenticeship)\b", re.I)),
    ("mentorship", re.compile(r"\b(mentor|mentorship)\b", re.I)),
    ("program", re.compile(r"\b(program|fellowship|camp|course)\b", re.I)),
]


def classify(pattern_list: list[tuple[str, re.Pattern[str]]], text: str, default: str) -> str:
    for label, pattern in pattern_list:
        if pattern.search(text):
            return label
    return default


def fetch_page(
    client: Client, url: str, params: dict
) -> tuple[list[dict], str | None]:
    response = requests.get(url, params=params, headers=client.headers, timeout=20)
    response.raise_for_status()
    data = response.json().get("data", {})
    posts = [c["data"] for c in data.get("children", []) if c.get("kind") == "t3"]
    return posts, data.get("after")


def harvest_listing(client: Client, sub: str) -> list[dict]:
    """Paginate /r/{sub}/new several pages deep."""
    posts: list[dict] = []
    after: str | None = None
    for _ in range(PAGES_PER_LISTING):
        params = {"limit": 75}
        if after:
            params["after"] = after
        url = f"{client.base}/r/{sub}/new{client.suffix}"
        page, after = fetch_page(client, url, params)
        posts.extend(page)
        time.sleep(client.delay)
        if not after:
            break
    return posts


def harvest_search(client: Client, sub: str, query: str) -> list[dict]:
    """One page of subreddit-restricted search, sorted newest, past year."""
    url = f"{client.base}/r/{sub}/search{client.suffix}"
    posts, _ = fetch_page(
        client,
        url,
        {"q": query, "restrict_sr": 1, "sort": "new", "t": "year", "limit": 75},
    )
    time.sleep(client.delay)
    return posts


def to_candidate(
    post: dict,
    source: str,
    field_default: str = "interdisciplinary",
    audience: str = "high_school",
) -> dict:
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
        "field_guess": classify(FIELD_HINTS, text, field_default),
        "type_guess": classify(TYPE_HINTS, text, "program"),
        "audience_guess": audience,
        "location_guess": (
            "international"
            if re.search(r"\b(international|abroad|worldwide|global|overseas)\b", text, re.I)
            else "us"
        ),
        "needs_review": True,
    }


def looks_like_opportunity(post: dict) -> bool:
    title = post.get("title", "")
    body = post.get("selftext", "")[:2000]
    return bool(INCLUDE.search(f"{title}\n{body}")) and not EXCLUDE.search(title)


def main() -> None:
    client = build_client()

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
    blocked = 0

    def register_error(error: requests.RequestException) -> None:
        """Stop early when the public endpoints are plainly refusing us."""
        nonlocal blocked
        if "403" in str(error):
            blocked += 1
        if client.base == PUBLIC_BASE and blocked >= 3:
            sys.exit(
                "\nReddit is blocking unauthenticated .json access from this"
                " network — stopping rather than retrying against a wall.\n"
                "Next step: create the 'script' app at"
                " https://www.reddit.com/prefs/apps and put REDDIT_CLIENT_ID /"
                " REDDIT_CLIENT_SECRET in backend/.env, then re-run.\n"
                "If the OAuth token is also refused, submit the Data API"
                " access request (see this file's docstring)."
            )

    def consider(
        post: dict,
        source: str,
        field_default: str = "interdisciplinary",
        audience: str = "high_school",
    ) -> None:
        nonlocal new_count
        if not looks_like_opportunity(post):
            return
        candidate = to_candidate(post, source, field_default, audience)
        if candidate["url"] in pool:
            return
        pool[candidate["url"]] = candidate
        new_count += 1

    for sub, audience, field_default in SUBREDDITS:
        try:
            posts = harvest_listing(client, sub)
        except requests.RequestException as error:
            print(f"r/{sub}: skipped ({error})")
            register_error(error)
            continue
        before = new_count
        for post in posts:
            consider(post, f"r/{sub}", field_default, audience)
        print(f"r/{sub}: {len(posts)} posts, {new_count - before} new candidates")

    def run_searches(
        queries: list[tuple[str, str]],
        subs: list[str],
        audience: str,
    ) -> None:
        """queries: (query, field_default) pairs, swept over subs."""
        for sub in subs:
            for query, field_default in queries:
                try:
                    posts = harvest_search(client, sub, query)
                except requests.RequestException as error:
                    print(f"r/{sub} search '{query}': skipped ({error})")
                    register_error(error)
                    continue
                before = new_count
                for post in posts:
                    consider(post, f"r/{sub} search:{query}", field_default, audience)
                if new_count > before:
                    print(f"r/{sub} search '{query}': {new_count - before} new")

    run_searches(
        [(query, "interdisciplinary") for query in SEARCHES],
        SEARCH_SUBREDDITS,
        "high_school",
    )
    run_searches(
        [
            (query, field)
            for field, queries in FIELD_SEARCHES.items()
            for query in queries
        ],
        SEARCH_SUBREDDITS,
        "high_school",
    )
    run_searches(
        [(query, "interdisciplinary") for query in COLLEGE_SEARCHES],
        COLLEGE_SEARCH_SUBREDDITS,
        "college",
    )
    run_searches(
        [(query, "business") for query in FINANCE_SEARCHES],
        FINANCE_SEARCH_SUBREDDITS,
        "college",
    )
    run_searches(
        VOLUNTEER_SEARCHES,
        VOLUNTEER_SEARCH_SUBREDDITS,
        "high_school",
    )

    ordered = sorted(pool.values(), key=lambda c: c.get("score", 0), reverse=True)
    out_path.write_text(json.dumps(ordered, indent=2))

    print(f"\npool: {known} known + {new_count} new = {len(ordered)} candidates")
    print(f"-> {out_path}")
    print("Review them, fix guessed fields, then add keepers to the seed catalog.")


if __name__ == "__main__":
    main()
