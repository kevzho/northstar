"""
Spend controls on /advisor, the only user-facing feature that costs money.

The free NIM tier is a fixed pool of calls, not a monthly allowance, so
these caps are the difference between "a student burned their questions"
and "a retry loop burned the whole project's credits before the demo".

The fake below is a real in-memory table, not a mock returning canned
values: the caps are time-window counts, and a mock that ignores
created_at would pass while the windows were wrong.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app import advisor as advisor_mod
from app.advisor import (
    budget_block,
    cache_key,
    cached_answer,
    record_call,
)


class _Exec:
    def __init__(self, data, count):
        self.data = data
        self.count = count


class _Query:
    """Implements exactly the PostgREST surface advisor.py uses."""

    def __init__(self, rows: list[dict]):
        self._rows = rows
        self._eq: dict[str, object] = {}
        self._gte: dict[str, str] = {}
        self._count = False
        self._limit: int | None = None
        self._insert: dict | None = None

    def select(self, *_columns, count=None, head=None):
        self._count = count == "exact"
        return self

    def eq(self, column, value):
        self._eq[column] = value
        return self

    def gte(self, column, value):
        self._gte[column] = value
        return self

    def order(self, _column, desc=False):
        return self

    def limit(self, n):
        self._limit = n
        return self

    def insert(self, row):
        self._insert = row
        return self

    def _matching(self) -> list[dict]:
        out = []
        for row in self._rows:
            if any(row.get(k) != v for k, v in self._eq.items()):
                continue
            if any(
                row[k] < datetime.fromisoformat(v) for k, v in self._gte.items()
            ):
                continue
            out.append(row)
        return out

    def execute(self):
        if self._insert is not None:
            row = dict(self._insert)
            row["created_at"] = datetime.now(timezone.utc)
            self._rows.append(row)
            return _Exec([row], None)
        rows = sorted(self._matching(), key=lambda r: r["created_at"], reverse=True)
        if self._count:
            return _Exec(None, len(rows))
        return _Exec(rows[: self._limit] if self._limit else rows, len(rows))


class FakeSupabase:
    def __init__(self, rows: list[dict] | None = None):
        self.rows = rows or []

    def table(self, name):
        assert name == "advisor_calls", f"unexpected table {name}"
        return _Query(self.rows)


def _call(student="s1", key="k", ago_minutes=0) -> dict:
    return {
        "student": student,
        "cache_key": key,
        "question": "q",
        "answer": "a",
        "sources": [],
        "created_at": datetime.now(timezone.utc) - timedelta(minutes=ago_minutes),
    }


# --- cache key ------------------------------------------------------------


def test_cache_key_ignores_case_and_whitespace() -> None:
    sources = [{"url": "u1"}, {"url": "u2"}]
    assert cache_key("  What ROUTES fit me? ", sources) == cache_key(
        "what routes fit me?", sources
    )


def test_cache_key_changes_when_the_sources_change() -> None:
    """A stale catalog must not serve a stale answer forever."""
    assert cache_key("q", [{"url": "u1"}]) != cache_key(
        "q", [{"url": "u1"}, {"url": "u2"}]
    )


# --- cache ----------------------------------------------------------------


def test_cache_returns_a_fresh_answer() -> None:
    sb = FakeSupabase([_call(key="k1")])
    assert cached_answer(sb, "k1")["answer"] == "a"


def test_cache_ignores_an_expired_answer(monkeypatch) -> None:
    monkeypatch.setattr(advisor_mod.settings, "advisor_cache_ttl_h", 24)
    sb = FakeSupabase([_call(key="k1", ago_minutes=60 * 25)])
    assert cached_answer(sb, "k1") is None


def test_cache_misses_on_an_unknown_key() -> None:
    assert cached_answer(FakeSupabase([_call(key="k1")]), "other") is None


# --- budget ---------------------------------------------------------------


def test_no_block_when_nothing_has_been_spent() -> None:
    assert budget_block(FakeSupabase(), "s1") is None


def test_per_student_cap_blocks_only_that_student(monkeypatch) -> None:
    monkeypatch.setattr(advisor_mod.settings, "advisor_per_student_daily", 3)
    monkeypatch.setattr(advisor_mod.settings, "advisor_global_daily", 999)
    sb = FakeSupabase([_call(student="s1", ago_minutes=90) for _ in range(3)])
    assert budget_block(sb, "s1") is not None
    assert budget_block(sb, "s2") is None


def test_per_student_window_rolls_off_after_a_day(monkeypatch) -> None:
    monkeypatch.setattr(advisor_mod.settings, "advisor_per_student_daily", 2)
    old = [_call(student="s1", ago_minutes=60 * 25) for _ in range(5)]
    assert budget_block(FakeSupabase(old), "s1") is None


def test_global_daily_cap_blocks_a_fresh_student(monkeypatch) -> None:
    monkeypatch.setattr(advisor_mod.settings, "advisor_per_student_daily", 999)
    monkeypatch.setattr(advisor_mod.settings, "advisor_global_daily", 4)
    sb = FakeSupabase(
        [_call(student=f"other{i}", ago_minutes=90) for i in range(4)]
    )
    assert "shared limit" in budget_block(sb, "brand-new")


def test_burst_guard_fires_before_the_daily_caps(monkeypatch) -> None:
    """A spike should say 'try in a minute', not 'come back tomorrow'."""
    monkeypatch.setattr(advisor_mod, "GLOBAL_PER_MINUTE", 5)
    monkeypatch.setattr(advisor_mod.settings, "advisor_per_student_daily", 999)
    monkeypatch.setattr(advisor_mod.settings, "advisor_global_daily", 999)
    sb = FakeSupabase([_call(student=f"o{i}", ago_minutes=0) for i in range(5)])
    assert "minute" in budget_block(sb, "s1")


def test_burst_guard_clears_once_the_minute_passes(monkeypatch) -> None:
    monkeypatch.setattr(advisor_mod, "GLOBAL_PER_MINUTE", 5)
    monkeypatch.setattr(advisor_mod.settings, "advisor_per_student_daily", 999)
    monkeypatch.setattr(advisor_mod.settings, "advisor_global_daily", 999)
    sb = FakeSupabase([_call(student=f"o{i}", ago_minutes=2) for i in range(5)])
    assert budget_block(sb, "s1") is None


# --- ledger ---------------------------------------------------------------


def test_record_call_writes_one_billable_row() -> None:
    sb = FakeSupabase()
    record_call(sb, "s1", "k1", "question", "answer", [{"url": "u"}])
    assert len(sb.rows) == 1
    assert sb.rows[0]["student"] == "s1"
    assert cached_answer(sb, "k1")["answer"] == "answer"


def test_a_cache_hit_costs_no_quota(monkeypatch) -> None:
    """The whole point: re-asking a known question must stay free."""
    monkeypatch.setattr(advisor_mod.settings, "advisor_per_student_daily", 1)
    sb = FakeSupabase()
    record_call(sb, "s1", "k1", "q", "a", [])

    # Quota is now spent, so a *new* question would be refused...
    assert budget_block(sb, "s1") is not None
    # ...but the answer already paid for is still served, and adds no row.
    assert cached_answer(sb, "k1")["answer"] == "a"
    assert len(sb.rows) == 1


def test_record_call_never_raises_when_the_ledger_write_fails() -> None:
    """Losing the log must not lose the student an answer already paid for."""

    class Broken(FakeSupabase):
        def table(self, name):
            raise RuntimeError("postgrest down")

    record_call(Broken(), "s1", "k", "q", "a", [])  # must not raise
