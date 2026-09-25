"""
Guard: the civic-impact claims on the landing page must stay true.

The landing page now states why Northstar exists, and backs it with numbers
about the CATALOG rather than about a userbase — there are three accounts, so
any usage figure would be either embarrassing or invented. The claims are:

  - "almost nine in ten programs on the high-school shelf cost nothing to
    apply to"
  - "70 verified opportunities ... from 60 different organizations, across
    9 fields"
  - "No student outcomes have been logged yet"

The catalog grows daily from the scrape cron, so these drift on their own.
That is exactly the failure this repo has already had once, at scale: six
different wrong question counts shipped because copy stated a number no test
could see. These assert the claims against the migrations, so a curation
change that makes the equity claim false fails here instead of on the landing
page a judge is reading.

Seeded rows only — the live catalog needs credentials and CI has none. The
seed is what a fresh clone gets, and it is the floor the claim rests on.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "supabase" / "migrations"
LANDING = ROOT / "frontend" / "app" / "page.tsx"

# The claim is "almost nine in ten". Assert a floor with headroom, so ordinary
# curation drift is fine and a real reversal is not.
FREE_SHARE_FLOOR = 0.80


def _seeded_high_school_rows() -> list[tuple[str, int]]:
    """(host, cost) for every seeded high_school opportunity."""
    rows: list[tuple[str, int]] = []

    seed = (MIGRATIONS / "20260815090000_seed_catalog.sql").read_text()
    # INSERT INTO ... VALUES ('title', 'host', ..., deadline, cost, ...)
    for match in re.finditer(
        r"VALUES \('(?:[^']|'')*', '((?:[^']|'')*)'.*?, '[\d-]{10}', (\d+),", seed
    ):
        rows.append((match.group(1), int(match.group(2))))

    curated = (MIGRATIONS / "20260816190000_curated_noncs_seed.sql").read_text()
    for line in curated.splitlines():
        # ('Title', 'Host', 'field', 'type',
        m = re.match(r"\s*\('(?:[^']|'')*', '((?:[^']|'')*)', '[a-z]+', '[a-z]+',", line)
        if m:
            cost = 0
            cm = re.search(r",\s*(\d+),\s*\d+,\s*\d+,", line)
            if cm:
                cost = int(cm.group(1))
            rows.append((m.group(1), cost))
    return rows


def test_most_of_the_shelf_is_free_to_apply_to() -> None:
    """The equity claim. If curation drifts paid-heavy, the copy becomes false."""
    rows = _seeded_high_school_rows()
    assert len(rows) >= 30, f"parsed only {len(rows)} seeded rows — the parser drifted"

    free = [r for r in rows if r[1] == 0]
    share = len(free) / len(rows)
    assert share >= FREE_SHARE_FLOOR, (
        f"only {share:.0%} of seeded opportunities are free to apply to, but the "
        f'landing page claims "almost nine in ten". Either re-curate toward free '
        f"programs or change the copy in frontend/app/page.tsx."
    )


def test_landing_page_does_not_claim_usage_it_cannot_prove() -> None:
    """No invented userbase, and the pre-pilot admission must survive edits.

    Three accounts, zero logged outcomes. A judge respects a stated zero; an
    inflated number is the kind of thing that loses a competition on integrity
    rather than on engineering.
    """
    # Collapse whitespace: JSX wraps prose across lines, so a sentence is
    # rarely a contiguous substring of the source.
    page_raw = LANDING.read_text()
    page = " ".join(page_raw.split())

    assert "No student outcomes have been logged yet" in page, (
        "the landing page must keep stating that no outcomes exist yet — "
        "remove it only when outcomes actually exist"
    )

    # Catch the shapes an inflated claim would take.
    forbidden = re.findall(
        r"\b\d[\d,]*\+?\s+(?:students|users|schools|teachers|districts)\b",
        page,
        re.IGNORECASE,
    )
    assert not forbidden, (
        "the landing page states a userbase figure: "
        f"{forbidden}. There are 3 accounts — verify it against "
        "public.students before shipping a number."
    )


def test_mission_is_actually_on_the_page() -> None:
    """The civic frame was absent entirely until 2026-09-23.

    A grep for nonprofit/equity/underrepresented across the whole frontend
    returned nothing but a placeholder in a discarded form field, while the
    project's entire reason for existing is access. This keeps it present.
    """
    page = " ".join(LANDING.read_text().split())
    assert "Minorities in STEM" in page
    assert "fiscally sponsored" in page


def test_stated_catalog_counts_match_the_seed_floor() -> None:
    """The counts on the page must not exceed what the catalog can support.

    This guard had a hole, and it showed up within the hour: it checked the
    free-share percentage and the no-usage claim, but not the raw counts. Then
    nine rows were retired, the high-school shelf went 70 -> 61, and the page
    still said 70 — a false claim introduced by a correctness fix.

    CI has no database credentials, so the live count cannot be read here. What
    CAN be asserted is the direction of the error that actually happened: the
    page must not claim MORE opportunities than the seed migrations define,
    since retirement only ever removes rows. A page claiming fewer than the
    seed is fine and expected — that is what retirement looks like.
    """
    page = " ".join(LANDING.read_text().split())

    claimed = re.search(r"(\d+)\s+verified opportunities", page)
    assert claimed, "the landing page no longer states a verified-opportunity count"
    stated = int(claimed.group(1))

    seeded = len(_seeded_high_school_rows())
    curated = (MIGRATIONS / "20260816190000_curated_noncs_seed.sql").read_text()
    curated_rows = len(re.findall(r"^\s*\('", curated, re.MULTILINE))
    ceiling = seeded + curated_rows

    assert stated <= ceiling, (
        f"the landing page claims {stated} verified opportunities, but the seed "
        f"migrations define at most {ceiling} on the high-school shelf. Retiring "
        f"rows lowers the real number — re-count against production and update "
        f"frontend/app/page.tsx."
    )
    assert stated > 0


# --- prose counts about the audit ----------------------------------------
#
# The mission paragraph now narrates the audit: nine removed, ten grade ranges
# corrected, fifteen entry routes corrected, eight duplicates. Those are all
# derivable from the scripts that did the work, with no database — so unlike the
# shelf size, they CAN be pinned here. Without this, the paragraph is four more
# numbers that rot the next time the catalog is corrected.

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"

NUMBER_WORDS = {
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "eight": 8, "seven": 7,
}


def _correction_entries() -> list[tuple[str, str]]:
    """(title, body) for each entry in the CORRECTIONS dict."""
    src = (SCRIPTS / "correct_opportunity_eligibility.py").read_text()
    body = src[src.index("CORRECTIONS: dict"):]
    entries = re.findall(r'\n    "([^"]+)": \{(.*?)\n    \},', body, re.S)
    assert len(entries) >= 15, f"parsed only {len(entries)} corrections — parser drifted"
    return entries


def _stated(pattern: str) -> int:
    page = " ".join(LANDING.read_text().split())
    m = re.search(pattern, page)
    assert m, f"the landing page no longer contains {pattern!r}"
    raw = m.group(1)
    return NUMBER_WORDS[raw.lower()] if raw.lower() in NUMBER_WORDS else int(raw)


def test_the_page_states_the_real_number_of_retired_rows() -> None:
    src = (SCRIPTS / "retire_dead_opportunities.py").read_text()
    listed = len(re.findall(r'^\s{4}\(\s*$', src, re.MULTILINE)) or len(
        re.findall(r'^\s{4}\(\n\s+"', src, re.MULTILINE)
    )
    assert listed > 0, "could not count the RETIRE list — parser drifted"
    assert _stated(r"removed\s+(\w+)\s*(?:&mdash;|—)") == listed


def test_the_page_states_the_real_number_of_grade_corrections() -> None:
    fixed = [t for t, b in _correction_entries()
             if "grade_min" in b or "grade_max" in b]
    assert _stated(r"grade range on\s+(\w+)\s+more") == len(fixed), (
        f"the page claims a different count than the {len(fixed)} rows whose "
        "grade range correct_opportunity_eligibility.py actually changes"
    )


def test_the_page_states_the_real_number_of_gate_corrections() -> None:
    gated = [t for t, b in _correction_entries() if "entry_gate" in b]
    assert _stated(r"the entry route on\s+(\w+)\b") == len(gated)


def test_the_page_states_the_real_number_of_duplicates() -> None:
    """Exact-title duplicates are found at runtime, so only the explicitly
    listed alias pairs can be counted statically. The page's figure must be at
    least those, and the sentence must not overstate what the script can do."""
    src = (SCRIPTS / "dedupe_opportunities.py").read_text()
    aliases = re.findall(r'^\s{4}\("([^"]+)",\s*$', src, re.MULTILINE)
    assert len(aliases) >= 3, f"parsed {len(aliases)} alias pairs — parser drifted"
    assert _stated(r"(\w+)\s+programs were listed twice") >= len(aliases)
