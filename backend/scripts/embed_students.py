"""
Backfill profile embeddings for students who predate semantic matching.

THE BUG THIS FIXES, which nothing would have reported. The catalog side of
semantic matching worked: 293 of 293 live opportunities carry a 2048-float
nemotron vector, written nightly by embed_catalog.py. The student side is
written by app/embeddings.py#refresh_student_embedding, which fires on profile
save and on assessment sync -- correct for every profile edited AFTER the
feature shipped, and silent for every account that already existed.

Result, measured 2026-10-18: 0 of 6 students had a profile embedding, so
public.semantic_scores() returned zero rows for everybody, so app/match.py
computed its semantic term over an empty dict and fell back to pure TF-IDF on
every single request. The feature was built, wired, migrated, indexed and
tested, and had never once influenced a ranking in production. Nothing was
broken enough to notice: the matcher degrades silently by design, because a
missing embedding should cost precision rather than the whole response.

Idempotent and incremental, like embed_catalog.py: only rows where
profile_embedding is null, unless --all is passed.

Usage:
    cd backend && .venv/bin/python scripts/embed_students.py --dry-run
    cd backend && .venv/bin/python scripts/embed_students.py
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.db import get_supabase  # noqa: E402
from app.embeddings import (  # noqa: E402
    enabled,
    refresh_student_embedding,
    student_query,
)

# One embedding call each. Small because the population is small; the ceiling
# exists so a future backfill over thousands cannot spend the pool in one run.
MAX_PER_RUN = 200


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--all", action="store_true",
                        help="re-embed every student, not only the missing ones")
    parser.add_argument("--limit", type=int, default=MAX_PER_RUN)
    args = parser.parse_args(argv or [])

    if not enabled():
        print("embed_students: skipped (embeddings not configured)")
        return 0

    sb = get_supabase()
    rows = (
        sb.table("students")
        .select("id, interests, goals, audience, profile_embedding")
        .execute()
    ).data or []

    todo = [
        r for r in rows
        if (args.all or not r.get("profile_embedding"))
        and student_query(r).strip()
    ]
    skipped = len(rows) - len(todo)
    todo = todo[: args.limit]
    print(f"{len(rows)} students, {len(todo)} to embed, {skipped} skipped "
          "(already embedded, or nothing to embed from)")

    if args.dry_run:
        for row in todo:
            print(f"  would embed {row['id']}: {student_query(row)[:70]!r}")
        return 0

    done = 0
    for row in todo:
        if refresh_student_embedding(sb, row["id"], row):
            done += 1
            print(f"  embedded {row['id']}")
        else:
            # refresh_student_embedding never raises; a False is a provider
            # refusal or a write failure, and the next run picks it up.
            print(f"  FAILED   {row['id']} (will retry next run)")

    print(f"\n{done}/{len(todo)} embedded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
