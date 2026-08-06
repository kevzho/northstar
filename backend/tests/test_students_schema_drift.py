"""
Guard: every column POST /students writes must exist in the SQL migrations.

Background: ``StudentProfileCreate`` has always carried an ``onboarded`` field,
``POST /students`` has always included it in the upsert payload, and
``frontend/lib/types.ts`` has always declared it — but ``public.students``
(supabase/schema.sql) never had the column. PostgREST rejects the upsert with
"column onboarded of relation students does not exist", so onboarding could
never complete. migration_006 adds it; this test keeps the three layers from
drifting apart again.

The check is textual (no live database) so it runs in CI without credentials.
"""

from __future__ import annotations

import pathlib
import re

MIGRATIONS_DIR = (
    pathlib.Path(__file__).resolve().parents[2] / "supabase" / "migrations"
)


def _students_columns() -> set[str]:
    """Columns on public.students after every migration in supabase/migrations/ is applied."""
    columns: set[str] = set()

    combined = "\n".join(
        path.read_text() for path in sorted(MIGRATIONS_DIR.glob("*.sql"))
    )
    body = re.search(
        r"create table public\.students \((?P<body>.*?)\n\);",
        combined,
        re.DOTALL | re.IGNORECASE,
    )
    assert body, "could not locate create table public.students in supabase/migrations/"
    for line in body.group("body").splitlines():
        line = line.strip()
        if not line or line.startswith("--"):
            continue
        name = line.split()[0]
        if name.lower() in {"primary", "unique", "constraint", "check", "foreign"}:
            continue
        columns.add(name)

    # ALTER TABLE ... ADD COLUMN [IF NOT EXISTS] <name>, across all migrations.
    alter = re.compile(
        r"alter\s+table\s+public\.students\s+add\s+column\s+"
        r"(?:if\s+not\s+exists\s+)?(?P<name>[a-z_]+)",
        re.IGNORECASE | re.DOTALL,
    )
    for match in alter.finditer(combined):
        columns.add(match.group("name"))

    return columns


def test_student_upsert_columns_exist_in_migrations() -> None:
    from app.schemas import StudentProfileCreate

    columns = _students_columns()
    assert "id" in columns and "interests" in columns, (
        f"parser produced a suspicious column set: {sorted(columns)}"
    )

    # POST /students sends every StudentProfileCreate field except `consent`,
    # which it translates into the `consented_at` timestamp, plus id + email
    # derived from the JWT.
    written = set(StudentProfileCreate.model_fields) - {"consent"}
    written |= {"id", "email", "consented_at"}

    missing = sorted(written - columns)
    assert not missing, (
        f"POST /students writes columns that no migration creates: {missing}. "
        f"PostgREST will reject the upsert. Add a migration under supabase/migrations/."
    )


def test_me_response_columns_exist_in_migrations() -> None:
    """Every column named in the GET /me select must be real."""
    main = (pathlib.Path(__file__).resolve().parents[1] / "app" / "main.py").read_text()
    select = re.search(
        r'\.select\("(?P<cols>id, name, email, grade, interests, goals[^"]*)"\)', main
    )
    assert select, "could not find the GET /me select in app/main.py"

    requested = {c.strip() for c in select.group("cols").split(",")}
    missing = sorted(requested - _students_columns())
    assert not missing, f"GET /me selects nonexistent columns: {missing}"


def test_onboarded_column_is_present() -> None:
    """Regression pin for the specific gap migration_006 closes."""
    assert "onboarded" in _students_columns()
