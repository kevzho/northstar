"""
Guard: no RLS policy may grant writes to PUBLIC.

This exists because public.opportunities shipped with:

    create policy "Opportunities are insertable by service role"
      on public.opportunities for insert with check (true);
      -- service key bypasses RLS in Supabase

The comment is true and irrelevant. A `create policy` with no `to` clause
applies to PUBLIC, which includes `anon` -- and the anon key is in the
browser bundle. The name and the comment were doing the work the SQL was
supposed to do, so any visitor could write to the catalog every student
reads. Fixed in 20260921120000_rls_lockdown.sql.

The check walks every migration in filename order, replays create/drop so
only the FINAL policy set is judged, and fails any surviving write policy
that is neither scoped to a named role nor constrained by auth.uid().
"""

from __future__ import annotations

import pathlib
import re

MIGRATIONS = pathlib.Path(__file__).resolve().parents[2] / "supabase" / "migrations"

WRITE_COMMANDS = {"insert", "update", "delete", "all"}

CREATE = re.compile(
    r"create\s+policy\s+\"(?P<name>[^\"]+)\"\s+on\s+(?P<table>[\w.]+)(?P<body>.*)",
    re.IGNORECASE | re.DOTALL,
)
DROP = re.compile(
    r"drop\s+policy\s+(?:if\s+exists\s+)?\"(?P<name>[^\"]+)\"\s+on\s+(?P<table>[\w.]+)",
    re.IGNORECASE | re.DOTALL,
)
FOR_CMD = re.compile(r"\bfor\s+(select|insert|update|delete|all)\b", re.IGNORECASE)
TO_ROLES = re.compile(r"\bto\s+([\w\s,]+?)(?=\busing\b|\bwith\s+check\b|$)", re.IGNORECASE)


def _statements(sql: str) -> list[str]:
    """Split on semicolons after stripping line comments.

    Policy bodies in this repo contain no string literals with semicolons,
    so this is sufficient for a static guard.
    """
    lines = [re.sub(r"--.*$", "", line) for line in sql.splitlines()]
    return [s.strip() for s in " ".join(lines).split(";") if s.strip()]


def _final_policies() -> dict[tuple[str, str], str]:
    """(table, policy name) -> body, after replaying every create and drop."""
    policies: dict[tuple[str, str], str] = {}
    for path in sorted(MIGRATIONS.glob("*.sql")):
        for stmt in _statements(path.read_text()):
            drop = DROP.match(stmt)
            if drop:
                policies.pop((drop.group("table"), drop.group("name")), None)
                continue
            create = CREATE.match(stmt)
            if create:
                key = (create.group("table"), create.group("name"))
                policies[key] = create.group("body")
    return policies


def test_no_policy_grants_writes_to_public() -> None:
    offenders = []
    for (table, name), body in _final_policies().items():
        command = FOR_CMD.search(body)
        # `create policy` with no FOR clause defaults to ALL -- a write.
        verb = command.group(1).lower() if command else "all"
        if verb not in WRITE_COMMANDS:
            continue

        roles = TO_ROLES.search(body)
        scoped = roles is not None and "public" not in roles.group(1).lower()
        owner_checked = "auth.uid()" in body.lower()

        if not scoped and not owner_checked:
            offenders.append(f"{table}: \"{name}\" grants {verb.upper()} to PUBLIC")

    assert not offenders, (
        "RLS write policies reachable by anon (the publishable key is in the "
        "browser bundle):\n  " + "\n  ".join(offenders)
    )


def test_lockdown_migration_revokes_table_grants() -> None:
    """RLS is only the row filter; Supabase also grants table-level DML.

    Dropping the policy without revoking the grant leaves the other half of
    the hole open, so assert both halves shipped together.
    """
    sql = (MIGRATIONS / "20260921120000_rls_lockdown.sql").read_text().lower()
    for table in ("public.opportunities", "public.mentors"):
        for role in ("anon", "authenticated"):
            assert re.search(rf"revoke[^;]*on {re.escape(table)} from {role}", sql), (
                f"lockdown migration must revoke direct grants on {table} from {role}"
            )
