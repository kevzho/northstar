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
import re
import sys
import time
from urllib.parse import urlparse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.db import get_supabase  # noqa: E402
from app.verifier import decide, verifier_enabled, verify_candidate  # noqa: E402

POOL = pathlib.Path(__file__).parent / "scraped" / "reddit_candidates.json"
MAX_VERIFY_PER_RUN = 60   # token/rate budget per daily run
REQUEST_DELAY_S = 1.0


OPP_KEYWORDS = re.compile(
    r"\b(apply|applications?|program|scholarship|fellowship|deadline|"
    r"internship|competition|hackathon|open|cohort|apprenticeship)\b",
    re.I,
)


def promising(candidate: dict) -> bool:
    """Cheap pre-filter so we don't spend a token on obvious non-starters.

    Devpost entries are real hackathons on their own domain. Otherwise the
    candidate must point at a real external site — every reddit-owned host
    (reddit.com AND the media CDNs i.redd.it / v.redd.it / redd.it) is a
    dead end for auto-import: an image or a discussion, never a program.
    """
    if candidate.get("review"):
        return False  # already judged (human or a prior auto run)
    if candidate.get("source") == "devpost":
        return True
    host = urlparse(candidate.get("url", "")).netloc.lower()
    if not host or host.endswith("redd.it") or host.endswith("reddit.com"):
        return False
    return True


def rank_key(candidate: dict) -> tuple:
    """Verify the likeliest opportunities first, not the top-upvoted memes.

    Devpost (known-real) first, then external links whose text actually
    reads like an opportunity — so the per-run token budget is spent where
    it pays off.
    """
    is_devpost = candidate.get("source") == "devpost"
    text = f"{candidate.get('title', '')} {candidate.get('blurb', '')}"
    has_keyword = bool(OPP_KEYWORDS.search(text))
    return (0 if is_devpost else 1, 0 if has_keyword else 1)


def main() -> None:
    if not verifier_enabled():
        sys.exit(
            "No LLM configured. Set LLM_API_KEY (and LLM_API_BASE / LLM_MODEL) "
            "in backend/.env. NVIDIA NIM is free: "
            "LLM_API_BASE=https://integrate.api.nvidia.com/v1"
        )

    pool = json.loads(POOL.read_text()) if POOL.exists() else []
    sb = get_supabase()

    # Optional CLI cap for calibration runs: `verify_and_import.py 10`.
    cap = MAX_VERIFY_PER_RUN
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        cap = int(sys.argv[1])

    candidates = sorted((c for c in pool if promising(c)), key=rank_key)[:cap]
    print(f"{len(candidates)} candidates to verify (cap {cap}).")

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
