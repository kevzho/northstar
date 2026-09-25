"""
Guard: the civic-impact claims on the landing page must stay true.

The landing page now states why Northstar exists, and backs it with numbers
about the CATALOG rather than about a userbase — there are three accounts, so
any usage figure would be either embarrassing or invented. The claims are:

  - "more than four in five programs on the high-school shelf cost nothing to
    apply to"
  - "53 verified opportunities across 9 fields"
  - "No student outcomes have been logged yet"

The audit detail that used to sit beside these lives in docs/catalog-audit.md.
It was published, and should not have been: a landing page is not a defect log.

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

# The claim is "more than four in five", which IS this floor. Stated as a
# proportion rather than "45 of the 53" so the shelf size appears once on the
# page instead of twice, and so ordinary curation drift does not falsify a
# sentence about cost.
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
        f'landing page claims "more than four in five". Either re-curate toward '
        f"free programs or change the copy in frontend/app/page.tsx."
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


# --- the audit is internal now ------------------------------------------
#
# The page used to narrate the audit: nine removed, ten grade ranges, fifteen
# entry routes, eight duplicates, three accounts. Four guards pinned those
# numbers to the scripts that did the work. The numbers were true; publishing
# them was the wrong call — a marketing page is not a defect log, and a visitor
# needs to know the practice exists, not read its changelog.
#
# So the claim shrank to one sentence ("every listing is checked against the
# program's own website, and anything that does not hold up comes down"), and
# the evidence moved to northstar-docs/CATALOG-AUDIT.md. What is worth guarding changed
# with it: not the individual figures, but that the page's remaining claim is
# backed by something real, and that the record did not vanish in the edit.

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
AUDIT_RECORD = ROOT / "northstar-docs" / "CATALOG-AUDIT.md"


def test_the_verification_claim_is_backed_by_scripts_that_exist() -> None:
    """The page claims listings are checked and removed. If the machinery that
    does that is deleted or renamed, the sentence becomes marketing."""
    page = " ".join(LANDING.read_text().split())
    assert "checked against the program" in page, (
        "the landing page no longer claims listings are verified — if that is "
        "deliberate, delete this guard; do not leave it asserting nothing"
    )
    for name in (
        "retire_dead_opportunities.py",
        "correct_opportunity_eligibility.py",
        "dedupe_opportunities.py",
        "expire_opportunities.py",
    ):
        assert (SCRIPTS / name).exists(), (
            f"the page claims listings that do not hold up come down, but "
            f"scripts/{name} is gone"
        )


def test_the_audit_record_survives_internally() -> None:
    """The detail left the landing page; it must not have left the repo.

    It is the evidence for the public sentence, and the source for the
    Congressional App Challenge write-up, where describing the process IS
    appropriate. Losing it would make the claim unfalsifiable.
    """
    assert AUDIT_RECORD.exists(), (
        "northstar-docs/CATALOG-AUDIT.md is missing. The landing page's "
        "verification claim rests on it. It lives in northstar-docs/ and not "
        "docs/ because docs/ is gitignored — a record only one laptop has is "
        "not a record."
    )
    record = AUDIT_RECORD.read_text()
    # The finding that drives the whole curation policy.
    assert "1 of 35" in record, "the audit record no longer states the hit rate"
    for marker in ("retire_dead_opportunities.py", "entry_gate", "unique(title, host)"):
        assert marker in record, f"the audit record no longer covers {marker}"


def _rendered_text() -> str:
    """The landing page's prose with JSX comments removed.

    A guard about what the public can read must not look at {/* ... */} blocks:
    those are source, never sent to a browser, and this file deliberately keeps
    a comment explaining why the audit numbers are not on the page. Judging that
    comment as a leak is how a guard starts producing false failures and gets
    switched off.
    """
    raw = re.sub(r"\{/\*.*?\*/\}", " ", LANDING.read_text(), flags=re.S)
    return " ".join(raw.split())


def test_the_defect_log_did_not_creep_back_onto_the_page() -> None:
    """Not a style rule — a scope rule. These sentences were removed on purpose
    because they publish internal history. If they are wanted back, that should
    be a decision someone makes while deleting this test, not a paste."""
    page = _rendered_text()
    leaked = [
        phrase for phrase in (
            "hand-written entries",
            "turned out to be teacher training",
            "last cohort was the class of 2016",
            "three accounts",
        )
        if phrase in page
    ]
    assert not leaked, (
        f"internal audit detail is back on the landing page: {leaked}. It "
        "lives in northstar-docs/CATALOG-AUDIT.md."
    )
