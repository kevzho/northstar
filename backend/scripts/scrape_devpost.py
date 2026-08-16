"""
Devpost scraper — open hackathons into the candidate pool.

Second source after Reddit, and a structurally better one: Devpost's
public JSON endpoint returns titles, URLs, themes, and submission
windows, so candidates arrive with real deadlines — the field the
catalog needs most and Reddit posts almost never state.

Entries merge into the same review pool (scraped/reddit_candidates.json,
which despite the name is THE candidate pool) keyed by URL, so the
review tool picks them up with everything else and re-runs never
resurrect judged entries.

Usage:
    cd backend && .venv/bin/python scripts/scrape_devpost.py
"""

from __future__ import annotations

import json
import pathlib
import re
import time
from datetime import datetime, timezone

import requests

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


def field_for(themes: list[str]) -> str:
    for theme in themes:
        mapped = THEME_FIELDS.get(theme.lower())
        if mapped:
            return mapped
    return "cs"  # hackathons default: the safest single guess


def main() -> None:
    pool_entries = json.loads(POOL.read_text()) if POOL.exists() else []
    pool = {e["url"]: e for e in pool_entries}
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
            if not url or url in pool:
                continue
            title = (h.get("title") or "").strip()
            themes = [t.get("name", "") for t in h.get("themes", [])]
            deadline = parse_deadline(h.get("submission_period_dates", ""))
            pool[url] = {
                "source": "devpost",
                "reddit_permalink": "",
                "posted_utc": datetime.now(timezone.utc).isoformat(),
                "score": 0,
                "title": title,
                "url": url,
                "blurb": (
                    f"Open hackathon on Devpost — themes: {', '.join(themes[:4])}."
                    + (f" Submissions close {deadline}." if deadline else "")
                ),
                "deadline_guess": deadline,
                "field_guess": field_for(themes),
                "type_guess": "competition",
                "audience_guess": (
                    "high_school" if "high school" in title.lower() else "college"
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
