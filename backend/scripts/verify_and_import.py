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

# Sources that come from a structured API of real, dated events rather than from
# somebody's post about one. These are trusted enough to skip the reddit-host
# screen and to be verified before the open-ended pool.
KNOWN_REAL_SOURCES = frozenset(
    {
        "devpost",
        "ctftime",
        "codeforces",
        # Added 2026-10-04 with the scrapers that emit them. They belong here
        # for the same reason the three above do -- a directory listing is not
        # somebody's post about one -- and they would hit the exact failure
        # rank_key's docstring describes if they were left out: both write
        # score 0, so inside the generic tier they sort below ten thousand
        # upvoted reddit threads and would never be reached by a 60-verdict
        # budget. The scrape would succeed daily and import nothing.
        "pathwaystoscience",
        "sciencefairs",
        # A hand-written list of non-CS leads (scripts/seed_breadth_candidates.py).
        # Trusted to reach the verifier first, NOT trusted to skip it: every one
        # still has its page fetched and read, and is refused if it cannot be
        # confirmed. Without this it would queue behind ten thousand reddit
        # threads and never be judged at all.
        "curated-breadth",
        # The same arrangement for the access list
        # (scripts/seed_access_candidates.py): programmes that exist because of
        # who is missing from STEM. Measured 2026-10-24, only 13 of 180 live
        # high-school rows served those students explicitly, and the honest fix
        # was to go and find more rather than to describe the catalog as
        # something it was not. Trusted to be REACHED, not trusted to be right:
        # each page is still fetched and read, and refused if it cannot be
        # confirmed.
        "curated-access",
    }
)
MAX_VERIFY_PER_RUN = 60   # token/rate budget per daily run
FAIL_FAST_AFTER = 5       # consecutive errors that mean the provider, not the data

# Wall-clock ceiling for the verify loop. Measured against NVIDIA NIM's free
# tier on openai/gpt-oss-20b, a single verdict takes anywhere from 24s to 83s
# — free capacity is shared and cold-starts are not rare. verify_candidate
# retries twice on timeout, so a worst-case candidate can occupy several
# minutes on its own, and a fixed count of 60 says nothing useful about how
# long the run will take.
#
# The GitHub job allows 90 minutes and the scrape stage uses roughly 12, so
# 55 leaves real headroom. Stopping on time imports fewer today and every
# subsequent day; overrunning imports nothing and reports a timeout.
TIME_BUDGET_S = 55 * 60
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
    if candidate.get("source") in KNOWN_REAL_SOURCES:
        return True
    host = urlparse(candidate.get("url", "")).netloc.lower()
    if not host or host.endswith("redd.it") or host.endswith("reddit.com"):
        return False
    return True


def rank_key(candidate: dict) -> tuple:
    """Verify the likeliest opportunities first, not the top-upvoted memes.

    Structured-feed candidates first, then external links whose text actually
    reads like an opportunity — so the per-run token budget is spent where it
    pays off.

    KNOWN_REAL_SOURCES, not just devpost. When the ctftime and codeforces feeds
    were added they inherited the generic tier, which sounds harmless and is
    not: the pool holds 9,000+ reddit candidates, the per-run cap is 60, and
    ordering inside a tier falls back to pool order, which is score-descending
    — and a structured feed has no upvotes, so its entries sort last of all.
    The feeds would have run daily, written candidates nobody ever verified,
    and imported nothing, which is indistinguishable from working.
    """
    known_real = candidate.get("source") in KNOWN_REAL_SOURCES
    text = f"{candidate.get('title', '')} {candidate.get('blurb', '')}"
    has_keyword = bool(OPP_KEYWORDS.search(text))
    # Soonest deadline first within a tier: a contest starting tomorrow is worth
    # a token before one three months out.
    deadline = candidate.get("deadline_guess") or "9999-12-31"
    return (0 if known_real else 1, 0 if has_keyword else 1, deadline)


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
    consecutive_failures = 0
    first_error = ""
    started = time.monotonic()
    for candidate in candidates:
        elapsed = time.monotonic() - started
        if elapsed > TIME_BUDGET_S:
            print(
                f"\nstopping at the {TIME_BUDGET_S // 60}-minute budget after "
                f"{imported + rejected + errored} candidates — the rest stay in "
                "the pool for tomorrow."
            )
            break
        try:
            verdict = verify_candidate(candidate)
            consecutive_failures = 0
        except Exception as error:
            print(f"  verify failed: {str(error)[:120]}")
            errored += 1
            consecutive_failures += 1
            first_error = first_error or str(error)
            # A handful of consecutive failures is not bad luck with one
            # posting -- it is the endpoint, the key, or the model. Stop
            # rather than spending the rest of the run proving it 57 more
            # times. This is how a retired model cost 28 days of imports:
            # every call 410'd, each was logged and skipped, and the run
            # still finished "successfully".
            if consecutive_failures >= FAIL_FAST_AFTER:
                print(
                    f"\n{consecutive_failures} consecutive verify failures — "
                    "treating this as a systemic fault, not bad candidates."
                )
                break
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

    attempted = imported + rejected + errored
    print(
        f"\nverified {attempted}: {imported} imported, "
        f"{rejected} rejected, {errored} errors."
    )

    # Exit non-zero when nothing could be judged. Silence has to be louder
    # than success here: the pool grows every day regardless, and the daily
    # commit of that pool made a dead verifier look like a working one for
    # four weeks.
    if attempted and errored == attempted:
        sys.exit(
            f"every one of {attempted} verify attempts failed — the catalog "
            f"imported nothing. First error: {first_error[:200]}"
        )


if __name__ == "__main__":
    main()
