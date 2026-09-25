"""
Embed opportunities that do not have an embedding yet.

The middle of the semantic-matching loop: scrape -> verify -> import -> EMBED ->
students get semantically matched. Runs as an optional stage of the nightly
scrape so a new opportunity is searchable by meaning the day after it lands.

WHY THIS IS A CRON JOB AND NOT REQUEST-TIME WORK. nvidia/nemotron-3-embed-1b
returns 2048 dimensions and refuses any other size, so one opportunity vector is
~16 KB. Embedding at request time would mean an API call per student per load;
shipping the vectors to the app would put ~1.2 MB on every /match. Instead they
are written once here, and similarity is computed by the Postgres function
semantic_scores() which returns one float per row.

Idempotent and incremental: only rows where embedding IS NULL. On the day the
catalog grew by 60 it makes 2 batched calls; on a quiet day, none.

Usage:
    cd backend && .venv/bin/python scripts/embed_catalog.py [--limit N] [--dry-run]
"""

from __future__ import annotations

import pathlib
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.db import get_supabase  # noqa: E402
from app.embeddings import (  # noqa: E402
    BATCH,
    EmbeddingUnavailable,
    embed_passages,
    enabled,
    opportunity_document,
)

# A ceiling per run so a first backfill over a large catalog cannot spend the
# whole free pool in one night. The remainder is picked up tomorrow.
MAX_PER_RUN = 200


def main() -> int:
    dry = "--dry-run" in sys.argv
    limit = MAX_PER_RUN
    for index, arg in enumerate(sys.argv):
        if arg == "--limit" and index + 1 < len(sys.argv):
            limit = int(sys.argv[index + 1])

    if not enabled():
        sys.exit(
            "No LLM_API_KEY, so nothing can be embedded. Semantic matching "
            "stays off and lexical scoring is unaffected."
        )

    sb = get_supabase()

    pending = (
        sb.table("opportunities")
        .select("id, title, blurb, opportunity_field, type")
        .is_("embedding", "null")
        .is_("retired_at", "null")
        .limit(limit)
        .execute()
    ).data or []

    total = (
        sb.table("opportunities")
        .select("id", count="exact")
        .is_("retired_at", "null")
        .execute()
    ).count

    print(f"{len(pending)} of {total} live opportunities need an embedding.")
    if not pending:
        return 0
    if dry:
        print("dry run — nothing written.")
        return 0

    stamp = datetime.now(timezone.utc).isoformat()
    written = 0

    for start in range(0, len(pending), BATCH):
        chunk = pending[start : start + BATCH]
        try:
            vectors = embed_passages([opportunity_document(row) for row in chunk])
        except EmbeddingUnavailable as error:
            # Fail the run rather than leave a partial batch looking complete.
            # A row with no embedding is simply absent from semantic_scores(),
            # which degrades to lexical-only scoring — the safe direction.
            sys.exit(f"embedding failed after {written} rows: {error}")

        for row, vector in zip(chunk, vectors):
            sb.table("opportunities").update(
                {"embedding": vector, "embedded_at": stamp}
            ).eq("id", row["id"]).execute()
            written += 1
        print(f"  embedded {written}/{len(pending)}")

    remaining = (
        sb.table("opportunities")
        .select("id", count="exact")
        .is_("embedding", "null")
        .is_("retired_at", "null")
        .execute()
    ).count
    print(f"\nwrote {written}. Still unembedded: {remaining}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
