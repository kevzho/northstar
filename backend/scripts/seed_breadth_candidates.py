"""
A hand-written list of non-CS opportunities, pushed through the same verifier.

WHY A LIST AND NOT A SCRAPER. Every structured feed that is free and needs no
auth is computer science, ctftime, codeforces, devpost, and scrape_ctftime's
own docstring says so: "balance comes from curating non-CS competitions, which
no API provides." Pathways to Science and the fair directory fixed science; they
did nothing for history, writing, debate, economics or the arts, because those
fields have no equivalent directory.

Measured 2026-10-08, the high-school shelf:

    cs                52 rows
    interdisciplinary 48
    math              20
    engineering       15
    biology           10   (3 open)
    humanities         4   (0 open)
    physics            3   (0 open)
    health             2   (0 open)
    business           2   (1 open)

A student who writes, argues, or studies the past opened this catalog and found
four things, none of them open. That is not a ranking problem, it is an absence.

NOTHING HERE IS INSERTED BY HAND. These are leads, not rows: a title and the
organiser's own url, written into the candidate pool so verify_and_import
fetches each page, reads it, and refuses anything it cannot confirm, the same
bar every scraped row clears. A list typed from memory is exactly the kind of
unverified content this catalog removes, so it does not get a shortcut.

Usage:
    cd backend && .venv/bin/python scripts/seed_breadth_candidates.py
"""

from __future__ import annotations

import json
import pathlib
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.urls import canonical_url  # noqa: E402

POOL = pathlib.Path(__file__).parent / "scraped" / "reddit_candidates.json"

# (title, url, field, type, one line a student would want)
LEADS: list[tuple[str, str, str, str, str]] = [
    # --- history and social science -------------------------------------
    ("National History Day", "https://www.nhd.org/", "humanities", "competition",
     "Research a historical topic and present it as a paper, exhibit, documentary, performance or website. Runs through school, regional and state contests."),
    ("The Concord Review", "https://www.tcr.org/", "humanities", "journal",
     "The only quarterly journal in the world publishing academic history papers by secondary students. Submissions accepted year-round."),
    ("National Economics Challenge", "https://www.councilforeconed.org/national-economics-challenge/", "business", "competition",
     "Team economics competition for high schoolers, run by the Council for Economic Education, with state rounds feeding a national final."),
    ("Profile in Courage Essay Contest", "https://www.jfklibrary.org/learn/education/profile-in-courage-essay-contest", "humanities", "competition",
     "Write about an act of political courage by a US elected official. Run by the JFK Library; open to US high-school students."),
    ("Harvard International Review Academic Writing Contest", "https://hir.harvard.edu/writing-contest/", "humanities", "competition",
     "Write an international-affairs essay judged by the Harvard International Review's editorial board."),
    ("National Speech and Debate Tournament", "https://www.speechanddebate.org/nationals/", "humanities", "competition",
     "The national championship for speech and debate, entered through a school chapter and district qualifying tournaments."),
    ("Bill of Rights Institute MyImpact Challenge", "https://billofrightsinstitute.org/myimpact-challenge", "humanities", "competition",
     "Describe a civic project you ran in your own community. Scholarship awards; open to US students 14-19."),

    # --- writing and the arts -------------------------------------------
    ("Scholastic Art and Writing Awards", "https://www.artandwriting.org/", "design", "competition",
     "The longest-running recognition programme for creative teenagers in the US — writing and art, regional juries feeding national medals."),
    ("YoungArts", "https://youngarts.org/apply/", "design", "competition",
     "National awards across writing, visual art, music, theatre and film for 15-18 year olds, with cash awards and a winners' week."),
    ("Poetry Out Loud", "https://www.poetryoutloud.org/", "humanities", "competition",
     "A national recitation contest run through schools: memorise and perform poems, advancing from class to state to national finals."),
    ("Bennington Young Writers Awards", "https://www.bennington.edu/events/young-writers-awards", "humanities", "competition",
     "Poetry, fiction and non-fiction prizes for students in grades 9-12, judged by Bennington's writing faculty."),
    ("The Adroit Prizes for Poetry and Prose", "https://theadroitjournal.org/adroit-prizes-for-poetry-and-prose/", "humanities", "competition",
     "Prizes for secondary and undergraduate writers, judged by an established writer and published in The Adroit Journal."),
    ("Patricia Grodd Poetry Prize", "https://kenyonreview.org/contests/patricia-grodd/", "humanities", "competition",
     "A poetry prize for high-school sophomores and juniors, run by the Kenyon Review; winners receive a full scholarship to its writers workshop."),

    # --- chemistry, biology, neuroscience, health -----------------------
    ("USA Brain Bee", "https://www.thebrainbee.org/", "biology", "competition",
     "A neuroscience competition for 13-19 year olds: local chapters feed a national contest and the international championship."),
    ("Genes in Space", "https://www.genesinspace.org/", "biology", "competition",
     "Design a DNA experiment to be carried out aboard the International Space Station. Open to US students in grades 7-12."),
    ("ACS ChemClub", "https://www.acs.org/education/students/highschool/chemistryclubs.html", "biology", "program",
     "An American Chemical Society programme for high-school chemistry clubs, with activities, grants and a national community."),
    ("Regeneron Biomedical Science Talent Search", "https://www.societyforscience.org/regeneron-sts/", "health", "competition",
     "The oldest science and mathematics competition for US high-school seniors, judged on an independent research project."),
    ("HOSA Future Health Professionals", "https://hosa.org/competitive-events/", "health", "competition",
     "Competitive events across clinical, health-science and leadership categories, entered through a school chapter."),
]


def main() -> int:
    pool = json.loads(POOL.read_text()) if POOL.exists() else []
    seen = {canonical_url(e.get("url")) for e in pool if e.get("url")}
    now = datetime.now(timezone.utc).isoformat()

    added = 0
    for title, url, field, kind, blurb in LEADS:
        if canonical_url(url) in seen:
            print(f"  -- already in the pool: {title[:50]}")
            continue
        pool.append({
            "source": "curated-breadth",
            "reddit_permalink": "",
            "posted_utc": now,
            "score": 0,
            "title": title,
            "url": url,
            "blurb": blurb,
            # No date is asserted. Every one of these is an annual programme
            # whose cycle the organiser publishes; refresh_deadlines reads it
            # off their page, and inventing one here is the mistake this
            # catalog has already made and undone.
            "deadline_guess": "",
            "field_guess": field,
            "type_guess": kind,
            "audience_guess": "high_school",
            "location_guess": "us",
            "needs_review": True,
        })
        seen.add(canonical_url(url))
        added += 1
        print(f"  +  {field:14} {title[:52]}")

    POOL.write_text(json.dumps(pool, indent=2) + "\n")
    print(f"\nadded {added} leads of {len(LEADS)} (pool {len(pool)})")
    print("Run verify_and_import next — nothing here reaches the catalog unverified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
