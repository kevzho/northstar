"""
Hand-written leads for programmes that exist because of who is missing from STEM.

WHY THIS LIST. Measured 2026-10-24, of 180 live high-school rows only 13 (7%)
explicitly serve students who are underrepresented in STEM. That is not a claim
this catalog should be making loudly, and the honest fix is to go and find the
programmes rather than to describe the catalog as something it is not.

It is also the gap that matters most for the organisation sponsoring this. A
student who is the first in their family to consider research does not need a
longer list of general programmes; they need the ones built on the assumption
that nobody told them, which are usually also the ones that are free, cover
travel, and do not require a teacher to nominate them.

WHAT IS AND IS NOT CLAIMED. These programmes state an access mission on their
own pages -- a named community, a first-generation focus, a no-cost guarantee,
or a stipend. None of them is restricted in a way a student could fall foul of
without being told: the verifier reads each page and writes the eligibility it
finds, so a programme that turns out to be narrower than this list assumes is
corrected by its own words rather than by mine.

NOTHING HERE IS INSERTED BY HAND. Leads only -- a title and the organiser's own
url -- written into the candidate pool so verify_and_import fetches each page,
reads it, and refuses whatever it cannot confirm. A list typed from memory is
exactly the kind of unverified content this catalog exists to remove, so it
gets no shortcut. Expect some of these to be rejected; that is the system
working, not failing.

Usage:
    cd backend && .venv/bin/python scripts/seed_access_candidates.py
    cd backend && .venv/bin/python scripts/verify_and_import.py
"""

from __future__ import annotations

import json
import pathlib
import sys
from datetime import datetime, timezone

POOL = pathlib.Path(__file__).parent / "scraped" / "reddit_candidates.json"

# (title, url, field, type, one line a student would want)
LEADS: list[tuple[str, str, str, str, str]] = [
    # --- free summer research and enrichment ----------------------------
    ("MIT MOSTEC", "https://oeop.mit.edu/programs/mostec", "cs", "program",
     "A free six-month online STEM programme from MIT for rising seniors, with a focus on students from underrepresented or underserved backgrounds."),
    ("Telluride Association Summer Seminar (TASS)", "https://www.tellurideassociation.org/our-programs/high-school-students/", "humanities", "program",
     "A free six-week college-level seminar on critical black studies and social justice for high schoolers. Tuition, room and board are covered."),
    ("LEDA Career Institute", "https://www.ledascholars.org/", "interdisciplinary", "program",
     "A free summer institute and multi-year college-access programme for high-achieving students from under-resourced backgrounds."),
    ("SMASH Academy", "https://www.smash.org/", "cs", "program",
     "A free three-year STEM programme on a university campus for students of colour, run by the Kapor Foundation."),
    ("Project SEED (American Chemical Society)", "https://www.acs.org/education/students/highschool/seed.html", "biology", "program",
     "A paid summer research placement in a chemistry lab for high-school students from economically disadvantaged families."),
    ("Stanford SHTEM Summer Internships", "https://compression.stanford.edu/outreach/shtem-summer-internships-high-schoolers-and-community-college-students", "interdisciplinary", "internship",
     "Free remote research internships at Stanford for high schoolers and community-college students, explicitly open to those with no prior research access."),
    ("NASA MUREP Programs", "https://www.nasa.gov/learning-resources/minority-university-research-education-project/", "engineering", "program",
     "NASA's Minority University Research and Education Project, funding STEM opportunities at minority-serving institutions."),

    # --- girls and women in STEM ----------------------------------------
    ("Kode With Klossy", "https://www.kodewithklossy.com/", "cs", "program",
     "Free two-week coding camps for girls, trans and non-binary teens aged 13-18, with laptops and materials provided."),
    ("Girls Who Code Summer Immersion Program", "https://girlswhocode.com/programs/summer-immersion-program", "cs", "program",
     "A free virtual summer programme in computer science for students who identify as girls or non-binary, in grades 9-11."),
    ("AI4ALL Summer Programs", "https://ai-4-all.org/", "cs", "program",
     "University-run summer AI programmes for high schoolers from groups underrepresented in artificial intelligence."),
    ("NCWIT Award for Aspirations in Computing", "https://www.aspirations.org/", "cs", "competition",
     "A national award recognising high-school students who identify as women, genderqueer or non-binary for their computing aspirations."),
    ("Technovation Girls", "https://www.technovation.org/challenges/girls/", "cs", "competition",
     "A global technology entrepreneurship competition where girls build a mobile app to solve a community problem."),

    # --- scholarships and college access --------------------------------
    ("The Gates Scholarship", "https://www.thegatesscholarship.org/", "interdisciplinary", "scholarship",
     "A full last-dollar scholarship for exceptional minority high-school seniors from low-income households."),
    ("Jack Kent Cooke Young Scholars Program", "https://www.jkcf.org/our-scholarships/young-scholars-program/", "interdisciplinary", "scholarship",
     "A five-year pre-college scholarship for high-achieving 7th graders with financial need, carrying advising and summer funding."),
    ("Hispanic Scholarship Fund", "https://www.hsf.net/scholarship", "interdisciplinary", "scholarship",
     "Scholarships and career support for students of Hispanic heritage, from high-school seniors through graduate study."),
    ("The Posse Foundation", "https://www.possefoundation.org/", "interdisciplinary", "scholarship",
     "Full-tuition leadership scholarships; students are nominated and go to college together as a supportive cohort."),
    ("American Indian Science and Engineering Society (AISES)", "https://www.aises.org/students/pre-college", "engineering", "program",
     "Pre-college programming, scholarships and a national conference for Native American students in STEM."),
    ("Society of Hispanic Professional Engineers (SHPE) Jr. Chapters", "https://shpe.org/students/pre-college/", "engineering", "program",
     "Pre-college chapters, competitions and scholarships for Hispanic students pursuing engineering."),
    ("NSBE Jr.", "https://nsbe.org/pre-college/", "engineering", "program",
     "The National Society of Black Engineers' pre-college programme: chapters, competitions and a national convention."),

    # --- paid, no-cost-to-you pathways ----------------------------------
    ("Genesys Works", "https://genesysworks.org/", "cs", "internship",
     "A paid year-long corporate internship and training programme for high-school seniors from low-income communities."),
    ("The Hidden Genius Project", "https://www.hiddengeniusproject.org/", "cs", "program",
     "A free intensive programme training Black male youth in software development, entrepreneurship and leadership."),
    ("Minds Matter", "https://www.mindsmatter.org/", "interdisciplinary", "program",
     "A free three-year college-readiness programme pairing low-income high schoolers with volunteer mentors."),
    ("SEO Scholars", "https://www.seo-usa.org/scholars/", "interdisciplinary", "program",
     "A free eight-year academic programme for public-school students, from high school through college graduation."),
]


def main() -> int:
    pool = json.loads(POOL.read_text()) if POOL.exists() else []
    seen = {row.get("url") for row in pool}
    now = datetime.now(timezone.utc).isoformat()

    added = 0
    for title, url, field, kind, blurb in LEADS:
        if url in seen:
            continue
        pool.append({
            "source": "curated-access",
            "reddit_permalink": "",
            "posted_utc": now,
            "score": 0,
            "title": title,
            "url": url,
            "blurb": blurb,
            "field_guess": field,
            "type_guess": kind,
            "audience_guess": "high_school",
            "location_guess": "us",
            "needs_review": False,
        })
        added += 1

    POOL.write_text(json.dumps(pool, indent=2) + "\n")
    print(f"{len(LEADS)} leads, {added} new, pool now {len(pool)}")
    print("Next: .venv/bin/python scripts/verify_and_import.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
