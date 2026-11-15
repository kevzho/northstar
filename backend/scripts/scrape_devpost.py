"""
Devpost scraper, open hackathons into the candidate pool.

Second source after Reddit, and a structurally better one: Devpost's
public JSON endpoint returns titles, URLs, themes, and submission
windows, so candidates arrive with real deadlines, the field the
catalog needs most and Reddit posts almost never state.

Entries merge into the same review pool (scraped/reddit_candidates.json,
which despite the name is THE candidate pool) keyed by URL, so the
review tool picks them up with everything else and re-runs never
resurrect judged entries.

Usage:
    cd backend && .venv/bin/python scripts/scrape_devpost.py
"""

from __future__ import annotations

import html
import json
import pathlib
import sys
import re
import time
from datetime import datetime, timezone

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.urls import canonical_url  # noqa: E402

API = "https://devpost.com/api/hackathons"
USER_AGENT = "northstar-opportunity-scraper/0.2 (student project; contact: dev.thorfinn@gmail.com)"
POOL = pathlib.Path(__file__).parent / "scraped" / "reddit_candidates.json"
PAGES = 5
REQUEST_DELAY_S = 2.0

# Devpost theme names -> our opportunity fields.
THEME_FIELDS = {
    "machine learning/ai": "cs",
    "web": "cs",
    "mobile": "cs",
    "cybersecurity": "cs",
    "blockchain": "cs",
    "ar/vr": "design",
    "gaming": "design",
    "design": "design",
    "music/art": "design",
    "health": "health",
    "fintech": "business",
    "e-commerce": "business",
    "productivity": "business",
    "education": "interdisciplinary",
    "social good": "interdisciplinary",
    "communication": "humanities",
    "iot": "engineering",
    "robotic process automation": "engineering",
    "hardware": "engineering",
}


def parse_deadline(window: str) -> str | None:
    """'May 19 - Aug 17, 2026' / 'Aug 10 - 30, 2026' / 'Aug 17, 2026' -> ISO date."""
    window = (window or "").strip()
    if not window:
        return None
    end = window.split(" - ")[-1].strip()
    # Same-month ranges drop the month on the end date; borrow it.
    if re.fullmatch(r"\d{1,2}, \d{4}", end):
        start_month = window.split()[0]
        end = f"{start_month} {end}"
    try:
        return datetime.strptime(end, "%b %d, %Y").date().isoformat()
    except ValueError:
        return None


# Each hackathon page carries a "Who can participate" list Devpost builds from
# fixed settings, so the wording is stable: "Ages 13+ only", "Above legal age
# of majority in country of residence", "Students only", and so on.
ELIGIBILITY_LIST = re.compile(r'(?s)<ul id="eligibility-list"[^>]*>(.*?)</ul>')
LIST_ITEM = re.compile(r"(?s)<li>(.*?)</li>")

# A minimum age at or below this admits a ninth grader. 16+ or 17+ would admit
# only some juniors and seniors, and the shelf is per audience, not per grade.
HIGH_SCHOOL_MAX_MIN_AGE = 14

ADULT_ONLY = re.compile(r"legal age of majority|ages? (1[7-9]|[2-9]\d)\+")
MIN_AGE = re.compile(r"ages? (\d{1,2})(?:\+| to \d{1,2})")
HIGH_SCHOOL_ONLY = re.compile(r"high ?school")

# Lines that restrict entry without excluding a high schooler. Anything not
# matched here, "Georgia Tech Students Only", "Only UBC participants", is a
# restriction we cannot judge, and an unjudged restriction keeps the row off
# the high-school shelf.
HARMLESS = re.compile(
    r"^(students only"
    r"|companies/professional organizations excluded.*"
    r"|team required.*"
    r"|.*countries/territories.*"
    r"|us only)$"
)


def parse_eligibility(page_html: str) -> list[str]:
    """The "Who can participate" lines from one hackathon page, as plain text."""
    match = ELIGIBILITY_LIST.search(page_html or "")
    if not match:
        return []
    lines = []
    for item in LIST_ITEM.findall(match.group(1)):
        text = html.unescape(re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", item))).strip()
        if text:
            lines.append(text)
    return lines


def audience_from_eligibility(lines: list[str]) -> str | None:
    """'high_school' or 'college' from the page's own rules, None if it is silent on age."""
    lowered = [line.lower() for line in lines]
    if any(HIGH_SCHOOL_ONLY.search(line) for line in lowered):
        return "high_school"
    if any(ADULT_ONLY.search(line) for line in lowered):
        return "college"
    ages = [int(m.group(1)) for line in lowered if (m := MIN_AGE.search(line))]
    if not ages:
        return None
    if min(ages) > HIGH_SCHOOL_MAX_MIN_AGE:
        return "college"
    others = [line for line in lowered if not MIN_AGE.search(line)]
    if all(HARMLESS.match(line) for line in others):
        return "high_school"
    return "college"


def audience_from_title(title: str, themes: list[str]) -> str:
    """The fallback when the page states no age: title and theme markers, else college."""
    haystack = f"{title} {' '.join(themes)}".lower()
    markers = ("high school", "highschool", "teen", "k-12", "grades 9")
    return "high_school" if any(marker in haystack for marker in markers) else "college"


def fetch_eligibility(url: str) -> list[str]:
    """The eligibility lines for one hackathon, or [] if the page cannot be read."""
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"  {url}: eligibility unread ({error})")
        return []
    return parse_eligibility(response.text)


def field_for(themes: list[str]) -> str:
    for theme in themes:
        mapped = THEME_FIELDS.get(theme.lower())
        if mapped:
            return mapped
    return "cs"  # hackathons default: the safest single guess


def main() -> None:
    pool_entries = json.loads(POOL.read_text()) if POOL.exists() else []
    pool = {canonical_url(e["url"]): e for e in pool_entries}
    known = len(pool)
    new_count = 0

    for page in range(1, PAGES + 1):
        try:
            response = requests.get(
                API,
                params={"status[]": "open", "page": page},
                headers={"User-Agent": USER_AGENT},
                timeout=20,
            )
            response.raise_for_status()
            hackathons = response.json().get("hackathons", [])
        except (requests.RequestException, ValueError) as error:
            print(f"page {page}: skipped ({error})")
            break
        if not hackathons:
            break

        for h in hackathons:
            url = h.get("url", "")
            if not url or canonical_url(url) in pool:
                continue
            title = (h.get("title") or "").strip()
            themes = [t.get("name", "") for t in h.get("themes", [])]
            deadline = parse_deadline(h.get("submission_period_dates", ""))
            eligibility = fetch_eligibility(url)
            time.sleep(REQUEST_DELAY_S)
            pool[canonical_url(url)] = {
                "source": "devpost",
                "reddit_permalink": "",
                "posted_utc": datetime.now(timezone.utc).isoformat(),
                "score": 0,
                "title": title,
                "url": url,
                "blurb": (
                    f"Open hackathon on Devpost — themes: {', '.join(themes[:4])}."
                    + (f" Submissions close {deadline}." if deadline else "")
                    + (f" Who can participate: {'; '.join(eligibility)}." if eligibility else "")
                ),
                "deadline_guess": deadline,
                "field_guess": field_for(themes),
                "type_guess": "competition",
                # AUDIENCE COMES FROM THE PAGE'S OWN RULES WHEN IT HAS THEM.
                #
                # Devpost's JSON has no eligibility text, so this used to guess
                # from the title alone, and 134 of 138 AI-imported rows landed
                # on the college shelf: a title almost never says "high school",
                # even when the rules do. Each hackathon page does list who can
                # participate, so that list is read and judged here
                # (audience_from_eligibility). The title and themes are only the
                # fallback when the page says nothing about age.
                #
                # The DEFAULT stays college, on purpose. Of the nine seeded
                # opportunities retired after an audit, four were retired
                # precisely because high schoolers could not apply, NSF REU,
                # CERN, Jackson Lab, Broadcom MASTERS. Hiding a hackathon a
                # student could have entered is a real cost; sending them to one
                # that will reject them is a worse one. So a row reaches the
                # high-school shelf only when the page admits a ninth grader and
                # every other restriction on it is one we recognise.
                "audience_guess": (
                    audience_from_eligibility(eligibility)
                    or audience_from_title(title, themes)
                ),
                "location_guess": "global",
                "needs_review": True,
            }
            new_count += 1
        print(f"page {page}: {len(hackathons)} open hackathons scanned")
        time.sleep(REQUEST_DELAY_S)

    ordered = sorted(pool.values(), key=lambda c: c.get("score", 0), reverse=True)
    POOL.write_text(json.dumps(ordered, indent=2))
    print(f"\npool: {known} known + {new_count} new = {len(ordered)} candidates")


if __name__ == "__main__":
    main()
