"""
Write a spine for each student, instead of assigning them one of twenty-four.

Reads the student, their matched opportunities and the skill keys that have
verified resources; asks the model for a project and a publish step; validates
the reply; stores it in public.generated_spines. GET /roadmap prefers that row
and falls back to the authored spine when it is absent.

WHY IT IS A SCRIPT AND NOT A CALL PER PAGE VIEW. A plan that changes between two
visits is not a plan. A student who read "build a case file on a gene-editing
trial" on Tuesday and finds something else on Thursday cannot act on either, and
the roadmap's whole claim is that its steps are in an order worth following. So
generation is deliberate: run it after an assessment changes, not on render.

REFUSAL IS A SUCCESS PATH. app/spine_generation.parse_spine returns None when
the model picks a skill key with no verified resources, writes a url, or returns
prose that will not parse. Every one of those is a case where the hand-written
spine is better, so the student simply keeps it. The counts are printed because
a refusal rate that climbs is how a prompt regression announces itself.

Usage:
    cd backend && .venv/bin/python scripts/generate_spines.py [--limit N] [--dry-run]
    cd backend && .venv/bin/python scripts/generate_spines.py --student <uuid>
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys
from datetime import datetime, timezone

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.catalog import fetch_shelf, shelf_for  # noqa: E402
from app.db import get_supabase  # noqa: E402
from app.match import score_opportunities  # noqa: E402
from app.spine_generation import SYSTEM_PROMPT, build_prompt, parse_spine  # noqa: E402

API_BASE = os.getenv("LLM_API_BASE", "").rstrip("/")
API_KEY = os.getenv("LLM_API_KEY", "")
MODEL = os.getenv("LLM_MODEL", "")
TIMEOUT_S = 90
# Low but not zero. The plan should read like it was written for one person,
# which greedy decoding tends not to do; it should not read like a different
# person each run, which is what high temperature gives.
TEMPERATURE = 0.4


def skill_catalogue(sb) -> tuple[list[dict], dict[str, str]]:
    """The skill keys that actually have verified resources behind them.

    Read from the database rather than hardcoded, so seeding a new resource
    widens what the model may choose without editing this file. On 2026-10-04
    there were 12 such keys against 24 archetypes, which is the gap this whole
    change exists to close.
    """
    rows = (
        sb.table("learning_resources")
        .select("skill_key, skill_label")
        .not_.is_("verified_at", "null")
        .execute()
    ).data or []
    labels: dict[str, str] = {}
    ordered: list[dict] = []
    for row in rows:
        key = row.get("skill_key")
        if key and key not in labels:
            labels[key] = row.get("skill_label") or ""
            ordered.append({"skill_key": key, "skill_label": labels[key]})
    return ordered, labels


def ask(prompt: str) -> str:
    response = requests.post(
        f"{API_BASE}/chat/completions",
        headers={"api-key": API_KEY, "Authorization": f"Bearer {API_KEY}",
                 "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "temperature": TEMPERATURE,
            "max_tokens": 700,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=TIMEOUT_S,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--student", default="", help="one student id")
    parser.add_argument("--dry-run", action="store_true", help="print, write nothing")
    parser.add_argument("--regenerate", action="store_true",
                        help="replace spines that already exist")
    args = parser.parse_args(argv if argv is not None else [])

    if not (API_BASE and API_KEY and MODEL):
        print("generate_spines: skipped (LLM_API_BASE/LLM_API_KEY/LLM_MODEL unset)")
        return 0

    sb = get_supabase()
    keys, labels = skill_catalogue(sb)
    if not keys:
        print("generate_spines: no verified learning resources, nothing to choose from")
        return 0
    print(f"  {len(keys)} skill rungs have verified resources: {', '.join(labels)}")

    query = sb.table("students").select(
        "id, grade, audience, interests, goals, field_scores, trait_scores, "
        "chosen_archetype, location_pref"
    )
    if args.student:
        query = query.eq("id", args.student)
    students = (query.limit(max(args.limit, 1)).execute()).data or []

    existing: set[str] = set()
    if not args.regenerate:
        try:
            existing = {
                r["user_id"]
                for r in (sb.table("generated_spines").select("user_id").execute()).data or []
            }
        except Exception:
            # Table not applied yet. Everything is "new"; the write below will
            # report the real reason once per run rather than per student.
            existing = set()

    written = refused = failed = 0
    for student in students:
        if student["id"] in existing:
            continue
        shelf = fetch_shelf(sb, shelf_for(student))
        ranked = score_opportunities(student, shelf, [])[:8]
        matches = [r["opportunity"] for r in ranked]
        try:
            raw = ask(build_prompt(student, matches, keys))
        except requests.RequestException as error:
            print(f"  !! {str(student['id'])[:8]} call failed: {error}")
            failed += 1
            continue

        spine = parse_spine(raw, labels)
        if not spine:
            # The authored spine stands. See the module docstring.
            print(f"  -- {str(student['id'])[:8]} refused, keeping the authored spine")
            refused += 1
            continue

        print(f"  +  {str(student['id'])[:8]} [{spine['skillKey']}] {spine['project'][:72]}")
        if args.dry_run:
            written += 1
            continue
        try:
            sb.table("generated_spines").upsert(
                {
                    "user_id": student["id"],
                    "project": spine["project"],
                    "publish": spine["publish"],
                    "skill": spine["skill"],
                    "skill_key": spine["skillKey"],
                    "model": MODEL,
                    "source_archetype": student.get("chosen_archetype") or None,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="user_id",
            ).execute()
            written += 1
        except Exception as error:
            print(f"  !! write failed (is 20261004120000 applied?): {error}")
            failed += 1

    print(
        f"\n  {'would write' if args.dry_run else 'wrote'}: {written}   "
        f"refused: {refused}   call/write failures: {failed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
