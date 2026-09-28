"""
Import a curated opportunity spreadsheet, verifying each row against its own page.

WHAT THE SHEET IS, AND IS NOT. stem_competitions_1000.xlsx says so itself:

    "website: filled only where the official URL is well established;
     blank means look it up before publishing"
    "Dates, deadlines, fees and eligibility change every year, so they are
     intentionally not included. Add them as you verify each entry."

So it is a leads list, not a catalog. It carries a name, a category, an
organizer and sometimes a URL — and none of deadline, grade range, cost or entry
route, which are the four fields that decide whether a student can act on a row.
Importing it as-is would add hundreds of rows that say nothing actionable, which
is the state this catalog spent a week climbing out of.

WHAT THIS DOES. For each lead it fetches the programme's own page and asks the
model to read it: is this real, does it take high schoolers, when does it close,
what does it cost, and who can enter it. A row is written only when the page
supports it. That is the same standard the landing page claims — "the hand-picked
part of the shelf is checked against each programme's own website" — applied by
machine so it can run over hundreds of rows instead of thirty-five.

Rows that fail are reported, not silently dropped: a lead whose page no longer
mentions high schoolers is worth knowing about.

The column contract, and what the last run's 24-of-2000 conversion rate was
caused by, are in northstar-docs/SHEET-SPEC.md. Read that before changing the
filters here — most of the loss is in the sheet, not in this script.

Usage:
    cd backend && .venv/bin/python scripts/import_opportunity_sheet.py \
        ~/Downloads/stem_competitions_1000.xlsx --sheet Competitions --limit 10 --dry-run
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from datetime import date, datetime, timezone

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.db import get_supabase  # noqa: E402
from app.llm import LLMUnavailable, chat  # noqa: E402
from app.settings import settings  # noqa: E402
from app.sheets import read_rows  # noqa: E402
from app.verifier import ENTRY_GATES, FIELDS, TYPES  # noqa: E402

# Only leads this product can serve: a US or global programme that admits high
# schoolers and has somewhere to send them.
AUDIENCE_TOKENS = ("HS", "Open")
COUNTRIES = ("United States", "Global")

# Above this the model's own read of the page is trusted. Deliberately higher
# than the scraper's floor: that judges a forum post, this judges a page the
# organisation wrote about itself, so there is less excuse for uncertainty.
CONFIDENCE_FLOOR = 0.75

# Every lead this importer has already judged, so a rerun does not pay to reach
# the same verdict twice. Without it, batching is broken by its own refusals:
# a refused lead is never written, so it stays in the "not in the catalog" set and
# reappears at the head of the next batch forever, and the run never advances past
# the first fifty.
#
# Also the record of what was rejected and why, which is the part worth a human's
# time — a lead whose page no longer mentions high schoolers is a fact about the
# programme, not noise.
LEDGER = pathlib.Path(__file__).parent / "scraped" / "sheet_import_ledger.json"

PAGE_CHARS = 7000
USER_AGENT = "northstar-catalog/1.0 (student nonprofit; verifying a listing before publishing it)"

EXTRACT_PROMPT = """You are reading the official page of a STEM programme to decide \
whether a high-school student can act on it, and to extract only what the page \
actually says.

Return ONLY a JSON object:
  is_real: boolean — does this page describe a real, currently-running programme?
  accepts_high_school: boolean — can a high-school student take part? false for \
university-only, graduate-only, or educator-only programmes
  grade_min: integer 6-12, the lowest US grade eligible, or null if unstated
  grade_max: integer 6-12, the highest, or null if unstated
  deadline: "YYYY-MM-DD" if the page states a FUTURE application or entry \
deadline, else null. Never guess or roll a past date forward.
  cost: integer US dollars to enter, 0 if free or unstated-and-free, null if unclear
  entry_gate: one of apply, qualify, advance, nominate, teacher
      apply    — a student enters or applies by themselves
      qualify  — entry is by exam score or a prior round
      advance  — you reach it by placing at an affiliated or regional event
      nominate — a nomination or recommendation is required
      teacher  — a teacher, coach or adult registers the team or applies
  entry_note: one short sentence on the first thing a student must do, or ""
  field: one of cs, biology, math, physics, engineering, interdisciplinary, \
design, business, humanities, health
  type: one of program, scholarship, competition, mentorship, internship, \
volunteer, journal
  blurb: one or two plain sentences a 15-year-old would find useful. No marketing.
  confidence: number 0..1
  reason: one short sentence

Ground every field in the page text. If the page is a login wall, an error, a \
parked domain, or says nothing about the programme, set is_real false. If it \
does not mention who may enter, leave grade_min and grade_max null rather than \
assuming."""


def page_text(url: str) -> str | None:
    """The page as plain text, or None if it cannot be read."""
    try:
        response = requests.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=20, allow_redirects=True
        )
        if not response.ok:
            return None
        html = response.text[:400_000]
    except requests.RequestException:
        return None
    # Scripts and styles first: their contents are longer than the prose on many
    # pages, and would crowd the real text out of the character budget.
    html = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = (
        text.replace("&nbsp;", " ").replace("&amp;", "&")
        .replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'")
    )
    text = re.sub(r"\s+", " ", text).strip()
    return text[:PAGE_CHARS] or None


_MONTHS = {m: i + 1 for i, m in enumerate(
    "january february march april may june july august september october "
    "november december".split()
)}
_MONTHS.update({m[:3]: i for m, i in list(_MONTHS.items())})

# Only this basis licenses a forward-looking claim. The sheet's README grades
# its own timing: "Known typical annual cycle" (the programme's usual month,
# from past cycles), "Estimate based on program type" (a placeholder), and "Not
# known". The middle one is a guess about a category, not about this programme.
KNOWN_CYCLE = "known typical annual cycle"


def recurrence_month_of(row: dict) -> int | None:
    """A month for opportunities.recurrence_month, or None.

    WHY NOT deadline. `typical_deadline` is prose — "Application ~mid-December",
    "Via national team selection", "Rolling / open enrollment" — and the sheet's
    README is explicit: "None of these are verified dates for the 2026-27 cycle.
    Deadlines shift year to year and some programs change format or pause."

    opportunities.deadline is a real date that app/roadmap.py turns into "Closes
    2026-12-15 - 79 days away. Start today." Deriving that from "~mid-December"
    would put a fabricated date in front of a student and let
    expire_opportunities retire the row when the invented date passed.

    recurrence_month is the column for exactly this: 20260923120000 defines it as
    "may we make a claim about when this opens NEXT year?" — and pairs it with
    recurrence_verified_at, which stays NULL here because no human checked the
    programme's site. NULL there means the UI says "no confirmed window" instead
    of projecting a date, which is the truth about this data.
    """
    if KNOWN_CYCLE not in str(row.get("timing_basis") or "").lower():
        return None
    text = str(row.get("typical_deadline") or "").lower()
    hits = [(text.find(k), v) for k, v in _MONTHS.items() if re.search(rf"\b{k}", text)]
    return min(hits)[1] if hits else None


def host_of(url: str) -> str:
    match = re.match(r"https?://(?:www\.)?([^/]+)", str(url or ""))
    return match.group(1).lower() if match else ""


def norm_title(value: str) -> str:
    value = re.sub(r"\(.*?\)", "", str(value or "")).lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


# Scopes whose rows cannot be verified from the URL the sheet supplies.
#
# The sheet's README says it plainly: "State-level rows are rounds of a national
# program (MATHCOUNTS, Science Olympiad, TSA, HOSA, Envirothon, FIRST Tech
# Challenge)." What it does not say is that every one of those rows carries the
# NATIONAL url. So "TSA State Conference - Alabama" points at tsaweb.org, which
# describes TSA and says nothing about Alabama.
#
# Measured in batch one: the model refused all ten TSA state rows it reached, each
# for the same correct reason, at the cost of a page fetch and a completion each.
# There are 369 such rows. Verifying them needs a state-specific URL the sheet
# does not have, so they are skipped before the spend rather than after it — and
# reported, because a state round is genuinely useful once someone finds its page.
TEMPLATE_SCOPES = ("State", "Regional")


def wanted(row: dict) -> bool:
    return (
        str(row.get("country") or "") in COUNTRIES
        and any(t in str(row.get("level") or "") for t in AUDIENCE_TOKENS)
        and bool(str(row.get("website") or "").strip())
        and str(row.get("scope") or "") not in TEMPLATE_SCOPES
    )


def extract(name: str, url: str, text: str, hint: str = "") -> dict | None:
    try:
        result = chat(
            base=settings.verifier_provider[0],
            key=settings.verifier_provider[1],
            model=settings.verifier_provider[2],
            messages=[
                {"role": "system", "content": EXTRACT_PROMPT},
                {"role": "user", "content": (
                    f"Programme: {name}\nURL: {url}\n"
                    # A hint, not an answer. The sheet's own timing is
                    # unverified prose; the page is what decides. Given to the
                    # model because "applications usually close in December" makes
                    # it far likelier to find and trust a real December date on a
                    # long page than to skip past it.
                    + (f"Curator's note on its usual cycle (UNVERIFIED, do not "
                       f"copy as a date): {hint}\n" if hint else "")
                    + f"\nPage text:\n{text}"
                )},
            ],
            max_tokens=1500,
            temperature=0.0,
            response_format={"type": "json_object"},
            reasoning_effort="none",
        )
    except LLMUnavailable as error:
        print(f"      model unavailable: {error}")
        return None
    raw = result.text
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None


def note(ledger: dict, lead: dict, outcome: str, detail: str) -> None:
    ledger[str(lead.get("id"))] = {
        "name": str(lead.get("name") or "")[:120],
        "url": str(lead.get("website") or "")[:300],
        "outcome": outcome,
        "detail": detail,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def to_row(lead: dict, verdict: dict, stamp: str) -> dict | None:
    """Turn a page reading into an opportunities row, or None to refuse it."""
    if not verdict.get("is_real") or not verdict.get("accepts_high_school"):
        return None
    try:
        if float(verdict.get("confidence", 0)) < CONFIDENCE_FLOOR:
            return None
    except (TypeError, ValueError):
        return None

    field = verdict.get("field") if verdict.get("field") in FIELDS else "interdisciplinary"
    opp_type = verdict.get("type") if verdict.get("type") in TYPES else "competition"
    gate = str(verdict.get("entry_gate") or "").strip().lower()
    if gate not in ENTRY_GATES:
        gate = "apply"

    def grade(key: str, default: int) -> int:
        try:
            value = int(verdict.get(key))
        except (TypeError, ValueError):
            return default
        return value if 6 <= value <= 12 else default

    gmin, gmax = grade("grade_min", 9), grade("grade_max", 12)
    if gmin > gmax:
        gmin, gmax = 9, 12

    deadline = None
    raw_deadline = str(verdict.get("deadline") or "")[:10]
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_deadline):
        try:
            # Past deadlines are dropped rather than stored: the row is still a
            # real annual programme, and a stale date is what put 123 expired
            # listings in front of students.
            if date.fromisoformat(raw_deadline) >= date.today():
                deadline = raw_deadline
        except ValueError:
            deadline = None

    try:
        cost = max(0, int(verdict.get("cost")))
    except (TypeError, ValueError):
        cost = 0

    blurb = " ".join(str(verdict.get("blurb") or "").split())[:400] or str(lead.get("name"))
    note = " ".join(str(verdict.get("entry_note") or "").split())[:300]

    row = {
        "title": str(lead.get("name") or "").strip()[:200],
        "host": str(lead.get("organizer") or "").strip()[:200] or "Unknown",
        "opportunity_field": field,
        "type": opp_type,
        "blurb": blurb,
        "description": blurb,
        "deadline": deadline,
        "cost": cost,
        "grade_min": gmin,
        "grade_max": gmax,
        "url": str(lead.get("website") or "").strip(),
        "audience": "high_school",
        "location_scope": "us" if lead.get("country") == "United States" else "global",
        "tags": [],
        # Its own provenance. Not 'ai' (that means scraped from a forum or
        # Devpost) and not 'human' (nobody read this page personally) — a
        # curated lead, machine-verified against the programme's own site.
        "added_by": "sheet",
        "entry_gate": gate,
        "verified_at": stamp,
    }
    if note and gate != "apply":
        row["entry_note"] = note

    # The sheet's typical month, when its own basis says "known annual cycle".
    # recurrence_verified_at is deliberately NOT set: nobody has confirmed this
    # programme's site, and that column is the licence for a date claim.
    month = recurrence_month_of(lead)
    if month:
        row["recurrence_month"] = month
    return row


def load_ledger() -> dict[str, dict]:
    try:
        return json.loads(LEDGER.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_ledger(ledger: dict[str, dict]) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--sheet", default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--retry-refused", action="store_true",
        help="re-judge leads the ledger already refused (after a prompt change)",
    )
    parser.add_argument("--min-confidence", default="", help="High to take only those")
    parser.add_argument(
        "--include-known-hosts",
        action="store_true",
        help="also take leads whose host already appears in the catalog (needs review)",
    )
    args = parser.parse_args()

    all_rows = read_rows(args.path, args.sheet)
    leads = [r for r in all_rows if wanted(r)]
    skipped_template = [
        r for r in all_rows
        if str(r.get("scope") or "") in TEMPLATE_SCOPES
        and str(r.get("country") or "") in COUNTRIES
        and any(t in str(r.get("level") or "") for t in AUDIENCE_TOKENS)
        and str(r.get("website") or "").strip()
    ]
    if skipped_template:
        print(f"  skipped {len(skipped_template)} state/regional rows: they carry "
              f"the national URL, which cannot confirm a local round")
    if args.min_confidence:
        leads = [r for r in leads if r.get("confidence") == args.min_confidence]

    sb = get_supabase()
    live = (
        sb.table("opportunities").select("title, url").execute()
    ).data or []
    seen_titles = {norm_title(r["title"]) for r in live}
    seen_urls = {str(r.get("url") or "").rstrip("/") for r in live}
    seen_hosts = {host_of(r.get("url")) for r in live if r.get("url")}

    fresh = [
        r for r in leads
        if norm_title(r.get("name")) not in seen_titles
        and str(r.get("website") or "").rstrip("/") not in seen_urls
    ]
    # A SHARED HOST IS A DUPLICATE WARNING, NOT A MATCH.
    #
    # The sheet lists "Codeforces Rounds" while the feed has already imported six
    # named Codeforces contests. Neither the title nor the exact URL collides, so
    # both would land and a student would see a generic entry beside six specific
    # ones. Of 307 eligible leads, 122 share a host with something already
    # shelved — too many to wave through and too many to assume are all dupes.
    # They are held back by default and reported, because deciding between "the
    # generic row is redundant" and "this is a different programme at the same
    # university" is a judgement, not a rule.
    # Drop what has already been judged. Keeps a batch moving forward.
    ledger = load_ledger()
    if not args.retry_refused:
        before = len(fresh)
        fresh = [r for r in fresh if str(r.get("id")) not in ledger]
        if before != len(fresh):
            print(f"  ledger: skipping {before - len(fresh)} already judged "
                  f"({sum(1 for v in ledger.values() if v['outcome'] != 'written')} "
                  f"of them previously refused or unreadable)")

    collide = [r for r in fresh if host_of(r.get("website")) in seen_hosts]
    if not args.include_known_hosts:
        fresh = [r for r in fresh if host_of(r.get("website")) not in seen_hosts]

    print(f"{'DRY RUN — ' if args.dry_run else ''}{len(leads)} eligible leads, "
          f"{len(fresh)} new-host leads, taking {min(args.limit, len(fresh))}")
    if collide and not args.include_known_hosts:
        print(f"  held back: {len(collide)} leads share a host with an existing row "
              f"— review them with --include-known-hosts")
        for r in collide[:5]:
            print(f"      {str(r.get('name'))[:46]:48} {host_of(r.get('website'))}")
    print()

    stamp = datetime.now(timezone.utc).isoformat()
    written = refused = unreadable = 0
    free = 0
    for lead in fresh[: args.limit]:
        name = str(lead.get("name"))[:52]
        url = str(lead.get("website") or "").strip()
        text = page_text(url)
        if not text:
            print(f"  -- unreadable  {name:54} {url[:44]}")
            unreadable += 1
            note(ledger, lead, "unreadable", "page could not be fetched or held no text")
            continue
        hint = " / ".join(
            v for v in (lead.get("typical_deadline"), lead.get("typical_event_timing"))
            if str(v or "").strip()
        )
        verdict = extract(str(lead.get("name")), url, text, hint)
        if not verdict:
            print(f"  -- no verdict  {name:54}")
            unreadable += 1
            note(ledger, lead, "unreadable", "model returned no usable JSON")
            continue
        row = to_row(lead, verdict, stamp)
        if not row:
            print(f"  ✗  refused    {name:54} {str(verdict.get('reason'))[:56]}")
            refused += 1
            note(ledger, lead, "refused", str(verdict.get("reason") or "")[:300])
            continue
        print(f"  +  {name:54} g{row['grade_min']}-{row['grade_max']} "
              f"{row['entry_gate']:8} {row['opportunity_field']:14} "
              f"dl={row['deadline'] or '-':10} ${row['cost']}")
        if row["cost"] == 0:
            free += 1
        if not args.dry_run:
            sb.table("opportunities").upsert(row, on_conflict="title,host").execute()
            note(ledger, lead, "written", row["entry_gate"])
        written += 1

    if not args.dry_run:
        save_ledger(ledger)
    print(f"\n  {'would write' if args.dry_run else 'wrote'}: {written}   "
          f"refused: {refused}   unreadable: {unreadable}")
    if written:
        print(f"  free to apply among them: {free}/{written} ({free/written:.0%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
