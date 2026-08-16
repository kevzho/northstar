"""
Verify scraped candidates with the LLM and auto-import the clear wins.

The middle stage of the daily loop: scrape (scrape_all) -> THIS ->
students see fresh opportunities. Walks unreviewed candidates, asks the
verifier, and for each one that clears the guardrails (real opportunity,
confident, usable link) upserts it into public.opportunities stamped
added_by='ai'. Everything it rejects or is unsure about stays in the
pool for scripts/review_candidates.py — the human path still exists for
the borderline cases.

Bounded and polite: caps per run, skips obviously-unpromising posts
before spending a token on them, and stops cleanly if the LLM is
unconfigured.

Usage:
    cd backend && .venv/bin/python scripts/verify_and_import.py
"""

from __future__ import annotations

import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.db import get_supabase  # noqa: E402
from app.verifier import decide, verifier_enabled, verify_candidate  # noqa: E402

POOL = pathlib.Path(__file__).parent / "scraped" / "reddit_candidates.json"
MAX_VERIFY_PER_RUN = 60   # token/rate budget per daily run
REQUEST_DELAY_S = 1.0


def promising(candidate: dict) -> bool:
    """Cheap pre-filter so we don't spend a token on obvious non-starters."""
    if candidate.get("review"):
        return False  # already judged (human or a prior auto run)
    url = candidate.get("url", "")
    is_reddit = "reddit.com" in url or not url
    if is_reddit and candidate.get("source") != "devpost":
        return False  # no external destination -> not auto-importable anyway
    return True


def main() -> None:
    if not verifier_enabled():
        sys.exit(
            "No LLM configured. Set LLM_API_KEY (and LLM_API_BASE / LLM_MODEL) "
            "in backend/.env. NVIDIA NIM is free: "
            "LLM_API_BASE=https://integrate.api.nvidia.com/v1"
        )

    pool = json.loads(POOL.read_text()) if POOL.exists() else []
    sb = get_supabase()

    candidates = [c for c in pool if promising(c)][:MAX_VERIFY_PER_RUN]
    print(f"{len(candidates)} candidates to verify (cap {MAX_VERIFY_PER_RUN}).")

    imported = rejected = errored = 0
    for candidate in candidates:
        try:
            verdict = verify_candidate(candidate)
        except Exception as error:
            print(f"  verify failed: {str(error)[:80]}")
            errored += 1
            time.sleep(REQUEST_DELAY_S)
            continue

        row = decide(candidate, verdict)
        if row is None:
            candidate["review"] = "auto-skip"
            rejected += 1
        else:
            try:
                sb.table("opportunities").upsert(
                    row, on_conflict="title,host", returning="minimal"
                ).execute()
                candidate["review"] = "auto-kept"
                imported += 1
                print(f"  + {row['title'][:70]} [{row['opportunity_field']}]")
            except Exception as error:
                print(f"  import failed: {str(error)[:80]}")
                errored += 1
        # Save after every decision so an interruption loses nothing.
        POOL.write_text(json.dumps(pool, indent=2))
        time.sleep(REQUEST_DELAY_S)

    print(
        f"\nverified {len(candidates)}: {imported} imported, "
        f"{rejected} rejected, {errored} errors."
    )


if __name__ == "__main__":
    main()
