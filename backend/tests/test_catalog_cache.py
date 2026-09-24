"""
Guards on app/catalog.py — the shared, cached, audience-filtered accessor.

GET /match is called from three frontend pages. It used to select("*") the
whole 144-row catalog and filter by audience in Python: 106 KB per call,
~318 KB per student session, 9.8 GB/month of Supabase egress at 1,000
students against a 5 GB free tier. These assert the three properties that
make the fix safe rather than merely smaller.
"""

from __future__ import annotations

import pytest

from app import catalog


class FakeTable:
    """Records the filters a chain applied, so the test can assert on them."""

    def __init__(self, rows: list[dict], log: list[dict]):
        self._rows, self._log = rows, log
        self._call: dict = {"select": None, "eq": {}, "is_": {}, "limit": None}

    def select(self, cols):
        self._call["select"] = cols
        return self

    def eq(self, col, val):
        self._call["eq"][col] = val
        return self

    def is_(self, col, val):
        self._call["is_"][col] = val
        return self

    def limit(self, n):
        self._call["limit"] = n
        return self

    def execute(self):
        self._log.append(dict(self._call))
        eq = self._call["eq"]
        rows = [r for r in self._rows if all(r.get(k) == v for k, v in eq.items())]
        for col, want in self._call["is_"].items():
            if want == "null":
                rows = [r for r in rows if r.get(col) is None]
        return type("R", (), {"data": rows})()


class FakeSB:
    def __init__(self, rows):
        self.rows, self.queries = rows, []

    def table(self, name):
        assert name == "opportunities"
        return FakeTable(self.rows, self.queries)


ROWS = [
    {"id": "1", "audience": "high_school", "opportunity_field": "cs",
     "title": "HS thing", "description": "x" * 900, "retired_at": None},
    {"id": "2", "audience": "college", "opportunity_field": "math",
     "title": "College thing", "description": "y" * 900, "retired_at": None},
    {"id": "3", "audience": "high_school", "opportunity_field": "biology",
     "title": "Another HS thing", "description": "z" * 900, "retired_at": None},
    # A program that ended. Gates Millennium Scholars shaped: real row, real
    # history hanging off it, must never be ranked or shown again.
    {"id": "4", "audience": "high_school", "opportunity_field": "cs",
     "title": "Ended program", "description": "w" * 900,
     "retired_at": "2026-09-23T00:00:00Z"},
]


@pytest.fixture(autouse=True)
def _clear():
    catalog.clear_cache()
    yield
    catalog.clear_cache()


def test_audience_filter_is_pushed_into_postgres() -> None:
    """The filter must be a DB predicate, not a Python comprehension.

    That is the half of the saving that reduces bytes on the wire; filtering
    after the fact moves the college shelf across the network to discard it.
    """
    sb = FakeSB(ROWS)
    rows = catalog.fetch_shelf(sb, "high_school")

    assert len(sb.queries) == 1
    assert sb.queries[0]["eq"] == {"audience": "high_school"}, (
        "audience must be filtered by the database, not in Python"
    )
    assert sb.queries[0]["limit"] == catalog.MAX_CATALOG_ROWS
    assert {r["id"] for r in rows} == {"1", "3"}


def test_cache_collapses_repeat_reads_within_the_ttl() -> None:
    sb = FakeSB(ROWS)
    for _ in range(3):                      # the three pages that call /match
        catalog.fetch_shelf(sb, "high_school")
    assert len(sb.queries) == 1, "a warm instance must read the catalog once"


def test_cache_is_keyed_by_audience() -> None:
    """A college student must never be served the high-school shelf."""
    sb = FakeSB(ROWS)
    hs = catalog.fetch_shelf(sb, "high_school")
    co = catalog.fetch_shelf(sb, "college")
    assert {r["id"] for r in hs} == {"1", "3"}
    assert {r["id"] for r in co} == {"2"}
    assert len(sb.queries) == 2


def test_unknown_audience_falls_back_rather_than_reaching_a_filter() -> None:
    """postgrest-py does not escape filter criteria (see app/params.py)."""
    sb = FakeSB(ROWS)
    catalog.fetch_shelf(sb, "high_school'),or(id.not.is.null")
    assert sb.queries[0]["eq"] == {"audience": catalog.DEFAULT_AUDIENCE}


def test_shelf_for_validates_against_the_enum() -> None:
    assert catalog.shelf_for({"audience": "college"}) == "college"
    assert catalog.shelf_for({"audience": None}) == "high_school"
    assert catalog.shelf_for({}) == "high_school"
    assert catalog.shelf_for({"audience": "graduate"}) == "high_school"


def test_public_view_drops_description_but_scoring_keeps_it() -> None:
    """description is 23% of the payload and no list view renders it —
    but app/match.py feeds it into the TF-IDF corpus, so the ROW must keep it.
    """
    sb = FakeSB(ROWS)
    rows = catalog.fetch_shelf(sb, "high_school")
    assert all("description" in r for r in rows), (
        "scoring input must retain description or ranking silently degrades"
    )

    view = catalog.public_view(rows[0])
    assert "description" not in view
    assert view["field"] == "cs" and "opportunity_field" not in view
    assert rows[0].get("description"), "public_view must not mutate the cached row"
    assert "opportunity_field" in rows[0]


def test_retired_rows_never_reach_a_student() -> None:
    """A retired program is filtered in Postgres, not hidden in the UI.

    The seeded catalog contained a scholarship whose final cohort was the class
    of 2016, a competition re-scoped to middle school, and two programs that
    never accepted high schoolers. They are stamped rather than deleted because
    outcomes/bookmarks/matches/dismissals cascade from opportunities(id) — so
    the read path is what has to exclude them.
    """
    sb = FakeSB(ROWS)
    rows = catalog.fetch_shelf(sb, "high_school")

    assert sb.queries[0]["is_"] == {"retired_at": "null"}, (
        "retired_at must be filtered by the database"
    )
    assert "4" not in {r["id"] for r in rows}, "a retired program was served"
    assert {r["id"] for r in rows} == {"1", "3"}
