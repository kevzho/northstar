"""
Correct grade ranges and entry gates on the seeded catalog.

Companion to retire_dead_opportunities.py. That script removed nine rows that
should not be shown at all; these twenty are real, reachable programmes that
were described wrongly. Every value below was verified against the programme's
own website on 2026-09-23, each flagged row re-checked by a second reviewer.

TWO CLASSES OF ERROR.

Grade ranges that send a student somewhere they are not eligible. RSI was listed
11-12 but takes juniors only. MIT PRIMES was 9-12 and takes sophomores and
juniors. Stanford Summer Institutes was 9-12 and is 8-11. BWSI was listed
12-12 and explicitly does NOT accept current seniors -- the one grade it was
offered to.

Entry gates: seven rows carried an application deadline for something a student
cannot apply to. You qualify for USAMO through AMC/AIME, for the Physics Team
through the F=ma exam, and you advance to ISEF from an affiliated regional fair.
A student who "applies by the deadline" to those does nothing. Lemelson-MIT is
stranger still: a TEACHER applies for a team grant.

This matters to the roadmap as well as the list. app/roadmap.py emits an
"Apply to X" step for any row that is open and grade-eligible, so without
entry_gate it would instruct a student to apply to USAMO.

Idempotent. Usage:
    cd backend && .venv/bin/python scripts/correct_opportunity_eligibility.py [--dry-run]
"""

from __future__ import annotations

import pathlib
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.db import get_supabase  # noqa: E402

# title -> fields to set. Only what the audit could evidence.
CORRECTIONS: dict[str, dict] = {
    # --- grade ranges ---------------------------------------------------
    "Congressional App Challenge": {
        "grade_min": 6, "grade_max": 12,
        "_why": 'eligibility is "middle or high school student", not 9-12',
    },
    "Davidson Fellows Scholarship": {
        "grade_min": 8, "grade_max": 12,
        "_why": "eligibility is by age (18 or younger), not grade",
    },
    "MIT PRIMES": {
        "grade_min": 10, "grade_max": 11,
        "_why": "sophomores and juniors only, US residents",
    },
    "NASA High School Aerospace Scholars (HAS)": {
        "grade_min": 11, "grade_max": 11,
        "_why": "the open track is juniors only",
    },
    "Research Science Institute (RSI)": {
        "grade_min": 11, "grade_max": 11,
        "_why": "juniors only — exactly one year before graduation, 16 by July 1",
    },
    "Stanford Summer Institutes": {
        "grade_min": 8, "grade_max": 11,
        "_why": "8-11, not 9-12",
    },
    "STEM Enhancement in Earth Science (SEES) Internship": {
        "grade_min": 10, "grade_max": 11,
        "_why": "sophomores or juniors only, 16 by the July start, US citizen",
    },

    # --- entry gates (and the grade fixes that came with them) ----------
    "USA Mathematical Olympiad (USAMO)": {
        "entry_gate": "qualify",
        "entry_note": (
            "You cannot apply. Qualify by score on the AMC 10 or AMC 12, then "
            "the AIME. Start with the AMC in the autumn."
        ),
        "url": "https://maa.org/math-competitions/",
        "_why": "qualification-gated; the old maa.org/usamo/ URL 404s",
    },
    # "Physics Olympiad Summer Camp (US Physics Team)" was here. It is not a
    # programme you enter at all -- it is the camp the top ~20 USAPhO scorers
    # are invited to -- and it duplicated "U.S. Physics Team (USAPhO)".
    # dedupe_opportunities.py retires it; correcting it would have kept a door
    # on the shelf that does not open.
    "Regeneron International Science and Engineering Fair (ISEF)": {
        "entry_gate": "advance",
        "entry_note": (
            "You cannot enter directly. Advance from a Society-affiliated "
            "regional or state fair — find yours first, its deadline is earlier."
        ),
        "_why": "entry is by advancing from an affiliated fair",
    },
    "Math Prize for Girls": {
        "grade_min": 8, "grade_max": 11,
        "entry_gate": "qualify",
        "entry_note": (
            "Qualification is by AMC score, and you must be in 11th grade or "
            "below on 1 March — seniors are not eligible."
        ),
        "_why": "AMC-gated, and 12th graders were wrongly included",
    },
    "Simons Summer Research Program": {
        "grade_min": 11, "grade_max": 11,
        "entry_gate": "nominate",
        "entry_note": (
            "Juniors only, and highly competitive — a teacher recommendation "
            "carries it. Ask a science teacher before the deadline, not after."
        ),
        "_why": "juniors only; recommendation-driven",
    },
    "MIT Beaver Works Summer Institute (BWSI)": {
        "grade_min": 10, "grade_max": 11,
        "entry_gate": "qualify",
        "entry_note": (
            "Selection is by prior coursework and an admissions process, and "
            "current seniors are explicitly not accepted."
        ),
        "_why": 'listed 12-12, but it does NOT accept "current seniors"',
    },
    "Lemelson-MIT InvenTeams": {
        "entry_gate": "teacher",
        "entry_note": (
            "A teacher applies for the team grant, not a student. Find a "
            "teacher willing to lead it — that is the real first step."
        ),
        "_why": "the applicant is an educator, not a student",
    },

    # --- team entry: a student cannot register alone -------------------
    #
    # A second pass over the rows still marked "apply" found nine more. These
    # are not obscure: they are the best-known competitions on the shelf, and
    # every one of them told a student to do something they cannot do by
    # themselves. A 9th grader reading "Apply to FIRST Robotics" and finding no
    # application form concludes the product is wrong, and they are right.
    "FIRST Robotics Competition (FRC)": {
        "entry_gate": "teacher",
        "entry_note": (
            "Teams register, not individuals, and a team needs adult mentors. "
            "Join your school's team — or ask a teacher to start one."
        ),
        "_why": "team registration with adult mentors, not an individual application",
    },
    "FIRST Tech Challenge (FTC)": {
        "entry_gate": "teacher",
        "entry_note": (
            "Teams register, not individuals. Cheaper and smaller than FRC, so "
            "it is the realistic one to start at a school with no team yet."
        ),
        "_why": "team registration, not an individual application",
    },
    "VEX Robotics Competition": {
        "entry_gate": "teacher",
        "entry_note": (
            "A team registers with the REC Foundation and needs an adult coach. "
            "Find the coach first; the registration is the easy part."
        ),
        "_why": "team registration with an adult coach",
    },
    "Team America Rocketry Challenge (TARC)": {
        "entry_gate": "teacher",
        "entry_note": (
            "Teams of 3-10 students enter with an adult advisor, usually "
            "through a school or club. You cannot enter on your own."
        ),
        "_why": "team entry requires an adult advisor",
    },
    "Science Olympiad": {
        "entry_gate": "teacher",
        "entry_note": (
            "Your school fields a team and a coach registers it. If there is "
            "no team, starting one is the actual first step."
        ),
        "_why": "school-team entry, registered by a coach",
    },
    "American Mathematics Competitions (AMC)": {
        "entry_gate": "teacher",
        "entry_note": (
            "You cannot register yourself. A school or registered host site "
            "orders the exam — ask a math teacher well before the autumn "
            "ordering deadline, because the site must be set up in advance."
        ),
        "_why": "ordered by a school or host site, never by a student",
    },

    # --- qualification ladders -----------------------------------------
    "U.S. Physics Team (USAPhO)": {
        "entry_gate": "qualify",
        "entry_note": (
            "You cannot apply. Take the F=ma exam first; qualifying scores "
            "advance to USAPhO, and the top scorers are invited to camp."
        ),
        "_why": "F=ma exam is the entry point, not an application",
    },
    "U.S. National Chemistry Olympiad (USNCO)": {
        "entry_gate": "qualify",
        "entry_note": (
            "Entry is through your ACS local section exam, which your school "
            "arranges — top local scorers are nominated for the national exam."
        ),
        "_why": "local section exam and nomination, not an application",
    },
    "USA Biology Olympiad (USABO)": {
        "entry_gate": "qualify",
        "entry_note": (
            "Start with the Open Exam, which your school or a registered "
            "centre signs you up for; the top scorers advance to the Semifinal."
        ),
        "_why": "Open Exam ladder, registered through a school",
    },
}


def main() -> int:
    dry = "--dry-run" in sys.argv
    sb = get_supabase()
    stamp = datetime.now(timezone.utc).isoformat()

    print(f"{'DRY RUN — ' if dry else ''}correcting {len(CORRECTIONS)} opportunities\n")
    changed = missing = 0

    for title, fields in CORRECTIONS.items():
        why = fields.pop("_why", "")
        found = (
            sb.table("opportunities")
            .select("id, title, grade_min, grade_max, entry_gate")
            .eq("title", title)
            .is_("retired_at", "null")
            .execute()
        ).data or []

        if not found:
            print(f"  ?? not found: {title[:58]}")
            missing += 1
            continue

        for row in found:
            before = f"g{row['grade_min']}-{row['grade_max']} gate={row.get('entry_gate')}"
            after = (
                f"g{fields.get('grade_min', row['grade_min'])}"
                f"-{fields.get('grade_max', row['grade_max'])} "
                f"gate={fields.get('entry_gate', row.get('entry_gate'))}"
            )
            print(f"  {row['title'][:52]}")
            print(f"      {before}  ->  {after}   ({why})")
            if dry:
                continue
            sb.table("opportunities").update(
                {**fields, "verified_at": stamp}
            ).eq("id", row["id"]).execute()
            changed += 1

    print(f"\n  updated: {changed}   not found: {missing}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
