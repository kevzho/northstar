"""
Structural checks on the seed files and migrations — no database required.

The student runs these files by hand in the Supabase SQL Editor, so a typo costs
a debugging round-trip. These assert the shape: row counts, idempotency clauses,
and enum values that actually exist in migration_002.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
SUPABASE = ROOT / "supabase"
MIGRATIONS = SUPABASE / "migrations"

FIELDS = {"cs", "biology", "math", "physics", "engineering", "interdisciplinary"}
TYPES = {"program", "scholarship", "competition", "mentorship"}


def test_opportunity_seed_is_idempotent_and_complete() -> None:
    sql = (SCRIPTS / "seed_opportunities.sql").read_text()
    inserts = sql.count("INSERT INTO public.opportunities")
    assert inserts == 35, f"expected 35 opportunity rows, found {inserts}"
    # Count the terminated clause so the prose in the header comment, which
    # names the same clause without a semicolon, is not counted as a statement.
    assert sql.count("ON CONFLICT (title, host) DO NOTHING;") == inserts, (
        "every opportunity INSERT needs ON CONFLICT so re-running is safe"
    )


def test_opportunity_seed_uses_real_enum_values() -> None:
    sql = (SCRIPTS / "seed_opportunities.sql").read_text()
    migration = (MIGRATIONS / "20250711134901_meridian_core_schema.sql").read_text()

    declared_fields = set(re.findall(r"'([a-z]+)'", re.search(
        r"create type public\.opportunity_field as enum \((?P<b>.*?)\);",
        migration, re.DOTALL).group("b")))
    declared_types = set(re.findall(r"'([a-z]+)'", re.search(
        r"create type public\.opportunity_type as enum \((?P<b>.*?)\);",
        migration, re.DOTALL).group("b")))

    assert declared_fields == FIELDS
    assert declared_types == TYPES

    used = set(re.findall(r"'(cs|biology|math|physics|engineering|interdisciplinary)'::", sql))
    if used:
        assert used <= declared_fields


def test_mentor_seed_is_idempotent_via_on_conflict() -> None:
    sql = (SCRIPTS / "seed_mentors.sql").read_text()
    inserts = sql.count("INSERT INTO public.mentors")
    assert inserts == 25, f"expected 25 mentor rows, found {inserts}"
    assert sql.count("ON CONFLICT (email) DO NOTHING;") == inserts
    assert "WHERE NOT EXISTS" not in sql


def test_mentor_seed_emails_are_unique() -> None:
    """A duplicate email inside the file would silently drop a row."""
    sql = (SCRIPTS / "seed_mentors.sql").read_text()
    emails = re.findall(r"VALUES \('[^']*', '([^']+)'", sql)
    assert len(emails) == 25
    assert len(set(emails)) == 25, "duplicate email in seed_mentors.sql"


# mentors.expertise is text[], not the opportunity_field enum, so extra tags are
# storable. They just cannot earn the field booster in app/mentors.py, which only
# credits expertise values that some student interest maps onto. Keep the
# vocabulary explicit so a new off-enum tag is a deliberate choice, not a typo.
EXPERTISE_VOCAB = FIELDS | {"chemistry"}


def test_mentor_seed_expertise_values_are_known() -> None:
    sql = (SCRIPTS / "seed_mentors.sql").read_text()
    for block in re.findall(r"ARRAY\[(.*?)\]", sql, re.DOTALL):
        for tag in re.findall(r"'([^']+)'", block):
            assert tag in EXPERTISE_VOCAB, (
                f"unknown expertise value {tag!r} in seed_mentors.sql"
            )


def test_every_mentor_has_at_least_one_boostable_expertise() -> None:
    """A mentor tagged only off-enum can never earn the expertise booster."""
    sql = (SCRIPTS / "seed_mentors.sql").read_text()
    for block in re.findall(r"ARRAY\[(.*?)\]", sql, re.DOTALL):
        tags = set(re.findall(r"'([^']+)'", block))
        assert tags & FIELDS, f"mentor expertise {sorted(tags)} maps to no field"


def test_migration_filenames_follow_cli_convention() -> None:
    """`supabase db push` only applies files named <14-digit-version>_<label>.sql."""
    names = sorted(path.name for path in MIGRATIONS.glob("*.sql"))
    assert names, "supabase/migrations/ is empty"
    versions = [
        m.group(1)
        for name in names
        if (m := re.match(r"^(\d{14})_[a-z0-9_]+\.sql$", name))
    ]
    assert len(versions) == len(names), (
        f"migration filenames must match <YYYYMMDDhhmmss>_<label>.sql: {names}"
    )
    assert len(set(versions)) == len(versions), (
        f"duplicate migration version prefix: {sorted(versions)}"
    )


def test_opportunities_unique_index_backs_the_seed_on_conflict() -> None:
    """seed_opportunities.sql's ON CONFLICT (title, host) needs the unique index."""
    sql = (MIGRATIONS / "20250711134904_opportunities_unique.sql").read_text().lower()
    assert "unique" in sql and "title" in sql and "host" in sql
