"""
Verify scraped resource candidates and import the free ones.

READS THE PAGE, NOT THE RECOMMENDATION. A reddit thread saying a resource is
free is a reason to look; it is not evidence. So each candidate's URL is
fetched, the model is shown the page text and asked to quote the sentence that
establishes the free claim, and app/resource_verifier.py then checks that quote
against the bytes that came back. A quote the page does not contain drops the
row -- which is the one check in this pipeline that a model cannot talk its way
past, and the reason every row on /learn can show its receipt.

WHY THAT IS THE STRICTEST GUARD IN THE PROJECT. public.opportunities getting a
row slightly wrong wastes an application. public.learning_resources getting one
wrong sends a student with no money to a paywall, from the page that promised
them the opposite. A shelf of twelve where every one is free is worth more to
them than a shelf of forty where three are not, because the second makes them
check all forty themselves.

Idempotent: learning_resources has `unique (url)`, and a candidate already on
the shelf is skipped before it costs a fetch or a verdict.

Usage:
    cd backend && .venv/bin/python scripts/import_resources.py --dry-run
    cd backend && .venv/bin/python scripts/import_resources.py --limit 10
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import time
from datetime import datetime, timezone

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.db import get_supabase  # noqa: E402
from app.llm import LLMUnavailable, chat  # noqa: E402
from app.resource_verifier import KINDS, decide_resource  # noqa: E402

POOL = pathlib.Path(__file__).parent / "scraped" / "resource_candidates.json"
LEDGER = pathlib.Path(__file__).parent / "scraped" / "resource_import_ledger.json"

USER_AGENT = (
    "northstar-catalog/1.0 (student nonprofit learning shelf; "
    "contact: dev.thorfinn@gmail.com)"
)
# Narrower than refresh_deadlines' 14000. The free/paid language on a course
# page is at the top, with the syllabus below it; the extra text is mostly
# lesson titles and costs tokens without changing the verdict.
PAGE_CHARS = 9000
REQUEST_DELAY_S = 1.0

# Per run. Sized against the daily job's remaining budget, and small on purpose:
# this shelf grows by verification, not by volume.
MAX_PER_RUN = 15
FAIL_FAST_AFTER = 5

# THE BAR A CANDIDATE HAS TO CLEAR BEFORE IT COSTS ANYTHING.
#
# Deliberately here rather than in the scraper: the pool remembers every link it
# sees so that agreement can accumulate across nights (see the note in
# scrape_reddit_resources.py), and this is where it is decided which of them is
# worth a page fetch and a model verdict. One stranger linking something once is
# not evidence; two separate discussions landing on the same thing is the
# cheapest real signal reddit has.
#
# Raise MIN_THREADS when the refusal counts below say the pool is the problem.
# Lower it when the queue runs dry.
MIN_THREADS = 2

SYSTEM = f"""You read one web page and decide whether it is FREE learning material a US high-school student could actually use.

Reply with JSON only:
{{"is_free": true/false,
  "free_evidence": "a sentence copied EXACTLY from the page text that establishes it is free",
  "teaches_a_skill": true/false,
  "high_school_reachable": true/false,
  "title": "what this material is called",
  "host": "the institution or person behind it",
  "kind": one of {sorted(KINDS)},
  "field": "cs|biology|math|physics|engineering|interdisciplinary|design|business|humanities|health",
  "skill_key": "a short slug for what it teaches, e.g. linear-algebra",
  "skill_label": "name — a short gloss of what that skill actually is",
  "effort": "honest time in a student's units, e.g. 'a weekend', '4 weeks at 3h/week'",
  "prerequisite": "what they need first, or 'none'",
  "why_this_one": "one sentence: why this over the alternatives",
  "confidence": 0.0-1.0}}

Rules:
- free_evidence must be COPIED from the page text, character for character. Do not
  paraphrase, do not compose a sentence, do not translate. If no sentence on the
  page establishes that the material is free, set is_free false and leave
  free_evidence empty. A quote that is not on the page is worse than no answer:
  it will be checked against the page and the row discarded.
- A free TRIAL is not free. Neither is "free with a subscription", a free first
  chapter, or free for students at one university. Those are prices.
- teaches_a_skill is false for a blog post, a news article, a product landing
  page, a syllabus with no material behind it, or a list of links.
- high_school_reachable is false for graduate-level material that assumes a
  degree. Introductory university material a motivated 15-year-old could follow
  is true.
- Lower your confidence when the page does not say, rather than guessing. A row
  below the floor is left for a human, which is the right outcome.
"""


def page_text(url: str) -> str | None:
    """The page as plain text, or None if it cannot be read.

    The text returned here is what the quote is checked against, so it must be
    the same transformation on both sides -- see resource_verifier.normalise,
    which is applied to this string and to the quote identically.
    """
    try:
        response = requests.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=20, allow_redirects=True
        )
        if not response.ok:
            return None
        html = response.text[:400_000]
    except requests.RequestException:
        return None
    html = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    return (re.sub(r"\s+", " ", text).strip()[:PAGE_CHARS]) or None


def read_page(url: str, text: str) -> dict | None:
    try:
        result = chat(
            base=os.getenv("LLM_API_BASE", ""),
            key=os.getenv("LLM_API_KEY", ""),
            model=os.getenv("LLM_MODEL", ""),
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"URL: {url}\n\nPage text:\n{text}"},
            ],
            max_tokens=900,
            temperature=0.0,
        )
    except LLMUnavailable:
        return None
    body = result.text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", body, re.S)
    if fenced:
        body = fenced.group(1)
    else:
        brace = re.search(r"\{.*\}", body, re.S)
        if brace:
            body = brace.group(0)
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return None


def load_ledger() -> dict:
    try:
        return json.loads(LEDGER.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def rank_key(candidate: dict) -> tuple:
    """Most-agreed-on first.

    Distinct threads before raw mentions, because ten replies in one thread is
    one thread agreeing -- see tally() in scrape_reddit_resources.py.
    """
    return (
        -int(candidate.get("thread_count") or 0),
        -int(candidate.get("mentions") or 0),
        -int(candidate.get("upvotes") or 0),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=MAX_PER_RUN)
    parser.add_argument("--dry-run", action="store_true",
                        help="verify and print, insert nothing")
    args = parser.parse_args(argv or [])

    if not POOL.exists():
        print("import_resources: no candidate pool; run scrape_reddit_resources.py first")
        return 0
    if not (os.getenv("LLM_API_BASE") and os.getenv("LLM_API_KEY") and os.getenv("LLM_MODEL")):
        print("import_resources: skipped (LLM not configured)")
        return 0

    candidates = json.loads(POOL.read_text())
    sb = get_supabase()

    # Already on the shelf, or already judged and refused. Skipped before they
    # cost a fetch or a verdict.
    on_shelf = {
        row["url"]
        for row in (sb.table("learning_resources").select("url").execute().data or [])
    }
    ledger = load_ledger()

    queue = [
        c for c in candidates
        if c.get("url") not in on_shelf
        and c.get("review") != "drop"
        and c["url"] not in ledger
        and (
            int(c.get("thread_count") or 0) >= MIN_THREADS
            # A human who marked it "keep" outranks the counter.
            or c.get("review") == "keep"
        )
    ]
    queue.sort(key=rank_key)
    queue = queue[: args.limit]
    agreed = sum(1 for c in candidates if int(c.get("thread_count") or 0) >= MIN_THREADS)
    print(
        f"{len(candidates)} candidates, {agreed} recommended in {MIN_THREADS}+ "
        f"threads, {len(on_shelf)} already on the shelf, {len(ledger)} already "
        f"judged — reading {len(queue)}."
    )

    imported = 0
    refused: dict[str, int] = {}
    consecutive_errors = 0

    for candidate in queue:
        url = candidate["url"]
        agreement = f"{candidate.get('thread_count', 0)} threads"
        text = page_text(url)
        time.sleep(REQUEST_DELAY_S)
        if not text:
            refused["unreachable"] = refused.get("unreachable", 0) + 1
            ledger[url] = {"at": datetime.now(timezone.utc).isoformat(), "why": "unreachable"}
            print(f"  unreachable  {url[:70]}")
            continue

        verdict = read_page(url, text)
        if verdict is None:
            consecutive_errors += 1
            print(f"  no verdict   {url[:70]}")
            if consecutive_errors >= FAIL_FAST_AFTER:
                print(
                    f"\n{FAIL_FAST_AFTER} verdicts in a row failed. That is the "
                    "provider, not the data — stopping so the run goes red "
                    "rather than quietly importing nothing for a month."
                )
                return 1
            continue
        consecutive_errors = 0

        row = decide_resource(candidate, verdict, text)
        if row is None:
            # Name the reason, because "refused 14" tells a maintainer nothing
            # about whether the prompt or the pool is the problem.
            why = (
                "not free" if not verdict.get("is_free")
                else "quote not on page"
                if not verdict.get("free_evidence")
                or verdict.get("free_evidence") not in text
                else "teaches nothing" if not verdict.get("teaches_a_skill")
                else "not reachable" if verdict.get("high_school_reachable") is False
                else "low confidence"
            )
            refused[why] = refused.get(why, 0) + 1
            ledger[url] = {"at": datetime.now(timezone.utc).isoformat(), "why": why}
            print(f"  {why:<18} {url[:60]}")
            continue

        if args.dry_run:
            print(f"  WOULD IMPORT ({agreement})  {row['title'][:48]} — {row['host'][:22]}")
            print(f"       {row['kind']} · {row['skill_key']} · \"{row['free_evidence'][:70]}\"")
            imported += 1
            continue

        try:
            sb.table("learning_resources").insert(row).execute()
        except Exception as error:  # noqa: BLE001 — postgrest raises broadly
            print(f"  insert failed {url[:60]}: {error}")
            continue
        ledger[url] = {"at": datetime.now(timezone.utc).isoformat(), "why": "imported"}
        imported += 1
        print(f"  imported ({agreement})  {row['title'][:48]} — {row['skill_key']}")

    if not args.dry_run:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        LEDGER.write_text(json.dumps(ledger, indent=2) + "\n")

    print(f"\n{imported} imported, {sum(refused.values())} refused.")
    for why, count in sorted(refused.items(), key=lambda kv: -kv[1]):
        print(f"  {count:>3}  {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
