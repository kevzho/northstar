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
                ),
                "deadline_guess": deadline,
                "field_guess": field_for(themes),
                "type_guess": "competition",
                # AUDIENCE IS A CONSERVATIVE GUESS, AND DELIBERATELY SO.
                #
                # Devpost's JSON gives titles, URLs, themes and deadlines — no
                # eligibility text. So there is nothing here to determine
                # whether a hackathon accepts a 15-year-old, and the verifier
                # cannot tell either: it is handed this blurb, which says only
                # "Open hackathon — themes: X, Y".
                #
                # This used to check the title alone, which is why 134 of 138
                # AI-imported rows landed on the college shelf: a title almost
                # never says "high school", even when the rules do. The signal
                # is now widened to the themes as well.
                #
                # But the DEFAULT stays college, on purpose. Of the nine seeded
                # opportunities retired after an audit, four were retired
                # precisely because high schoolers could not apply — NSF REU,
                # CERN, Jackson Lab, Broadcom MASTERS. Guessing high_school here
                # would repeat that error across 134 rows at once. Hiding a
                # hackathon a student could have entered is a real cost; sending
                # them to one that will reject them is a worse one.
                #
                # The honest fix is to capture each hackathon's eligibility text
                # and judge it. That is scraper work, tracked separately.
                "audience_guess": (
                    "high_school"
                    if any(
                        marker in haystack
                        for haystack in (title.lower(), " ".join(themes).lower())
                        for marker in ("high school", "highschool", "teen", "k-12", "grades 9")
                    )
                    else "college"
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
