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


def test_no_migration_seeds_a_placeholder_mentor() -> None:
    """Mentors are shown to students with a working mailto button.

    scripts/seed_mentors.sql used to insert 25 invented people attributed to
    MIT, Stanford, Google, CERN and the Broad, each with an RFC 2606 reserved
    address. It was folded into 20260815090000_seed_catalog.sql when the live
    database was found empty, which promoted scaffolding to production data.
    20260922090000_remove_placeholder_mentors.sql deletes those rows and adds
    a CHECK constraint; this asserts no NEW migration reintroduces the shape.

    No migration is exempt any more: the mentor INSERTs were removed from
    20260815090000_seed_catalog.sql too, so a fresh `supabase db reset` never
    creates them in the first place.
    """
    reserved = re.compile(
        r"'[^']*@[^']*\.(example|test|invalid|localhost)'"
        r"|'[^']*@example\.(com|net|org)'",
        re.IGNORECASE,
    )
    offenders = []
    for path in sorted(MIGRATIONS.glob("*.sql")):
        for match in reserved.finditer(path.read_text()):
            offenders.append(f"{path.name}: {match.group(0)}")
    assert not offenders, (
        "migration inserts a mentor at a reserved placeholder address -- that "
        "is an invented person, rendered to students with a mailto:\n  "
        + "\n  ".join(offenders)
    )


def test_placeholder_mentor_constraint_exists() -> None:
    """The durable half of the fix.

    Deleting the rows alone is reversible by a `supabase db reset`, which
    replays the historical seed. The CHECK constraint makes that replay fail
    loudly instead of silently repopulating a directory of invented people.
    """
    sql = (MIGRATIONS / "20260922090000_remove_placeholder_mentors.sql").read_text().lower()
    assert "delete from public.mentors" in sql, "the fabricated rows must be deleted"
    assert "mentors_email_not_placeholder" in sql, "the constraint must be named"
    assert "add constraint" in sql and "check" in sql
    # Order matters: the constraint cannot be added while violating rows exist.
    assert sql.index("delete from public.mentors") < sql.index("add constraint")


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
