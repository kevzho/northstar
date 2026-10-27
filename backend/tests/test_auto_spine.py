"""
The first thing in this product that spends money on its own initiative.

/plan asks for a spine when nobody ever wrote the student one. That is the
right behaviour -- without it a plan is three application steps and a cold
email, with no project in it -- and it is also the shape that runs up a bill if
any of its gates is wrong. Every test here is a gate.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.db
from app.auth import get_current_user
from app.main import create_app

STUDENT = {
    "id": "11111111-1111-1111-1111-111111111111",
    "grade": 11,
    "audience": "high_school",
    "interests": ["Biology"],
    "goals": "public health",
    "field_scores": {"biology": 40},
    "trait_scores": {"builder": 60},
    "chosen_archetype": None,
    "location_pref": None,
}


class _Table:
    def __init__(self, parent, name):
        self.parent, self.name = parent, name
        self._filters = {}

    def select(self, *a, **k):
        return self

    def eq(self, column, value):
        self._filters[column] = value
        return self

    def gte(self, *a, **k):
        return self

    @property
    def not_(self):
        # postgrest chains `.not_.is_(...)`, so not_ is a PROPERTY returning
        # something with is_ on it, not a method.
        return self

    def is_(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def maybe_single(self):
        return self

    def insert(self, row):
        self.parent.writes.append((self.name, row))
        return self

    def upsert(self, row, **k):
        self.parent.writes.append((self.name, row))
        return self

    def execute(self):
        data = self.parent.data.get(self.name, [])
        if self.name == "rate_events":
            return type("R", (), {"data": data, "count": self.parent.rate_count})()
        if self.name == "students":
            return type("R", (), {"data": STUDENT, "count": 0})()
        return type("R", (), {"data": data, "count": len(data)})()


class _SB:
    def __init__(self, **kw):
        self.data = {
            "generated_spines": kw.get("generated_spines", []),
            "learning_resources": kw.get("learning_resources",
                                         [{"skill_key": "statistics",
                                           "skill_label": "statistics — tests"}]),
            "opportunities": [],
            "outcomes": [],
            "advisor_calls": [],
            "rate_events": [],
        }
        self.rate_count = kw.get("rate_count", 0)
        self.writes: list[tuple] = []

    def table(self, name):
        return _Table(self, name)


def _client(sb, monkeypatch, archetype=None):
    STUDENT["chosen_archetype"] = archetype
    api = create_app()

    class _User:
        id = STUDENT["id"]
        email = "s@example.com"

    api.dependency_overrides[get_current_user] = lambda: _User()
    monkeypatch.setattr(app.db, "get_supabase", lambda: sb)
    return TestClient(api)


def test_a_student_who_already_has_a_spine_costs_nothing(monkeypatch) -> None:
    """Idempotent by construction: the plan page may call this on every mount,
    and only a genuinely empty plan may reach the provider."""
    sb = _SB(generated_spines=[{
        "project": "p", "publish": "q", "skill": "s", "skill_key": "statistics",
    }])
    called: list[int] = []
    monkeypatch.setattr("app.llm.chat", lambda **kw: called.append(1))
    response = _client(sb, monkeypatch).post("/roadmap/spine/auto")
    assert response.status_code == 200
    body = response.json()
    assert body["generated"] is False and body["reason"] == "already-written"
    assert body["project"] == "p"
    assert called == [], "a model was called for a student who already had a spine"


def test_a_student_who_charted_a_path_is_left_alone(monkeypatch) -> None:
    """They answered the question on /futures. Writing over their authored
    spine would be answering one they did not ask."""
    sb = _SB()
    called: list[int] = []
    monkeypatch.setattr("app.llm.chat", lambda **kw: called.append(1))
    response = _client(sb, monkeypatch, archetype="social-entrepreneur").post(
        "/roadmap/spine/auto"
    )
    assert response.json()["reason"] == "has-authored-path"
    assert called == []


def test_the_per_student_ceiling_refuses_before_spending(monkeypatch) -> None:
    """Three per thirty days. A profile the model keeps refusing would
    otherwise retry on every page load for a month."""
    from app.limits import POLICIES

    limit, _, _ = POLICIES["auto_spine"]
    sb = _SB(rate_count=limit)
    called: list[int] = []
    monkeypatch.setattr("app.llm.chat", lambda **kw: called.append(1))
    body = _client(sb, monkeypatch).post("/roadmap/spine/auto").json()
    assert body["generated"] is False and body["reason"] == "rate-limited"
    assert called == []


def test_the_attempt_is_counted_before_the_call_not_after_success(monkeypatch) -> None:
    """THE RUNAWAY THIS PREVENTS. Counting only successes makes a persistently
    failing generation free, and therefore infinite."""
    sb = _SB()

    class _Result:
        text = "this is not json and never will be"
        prompt_tokens = completion_tokens = total_tokens = 10

    monkeypatch.setattr("app.llm.chat", lambda **kw: _Result())
    body = _client(sb, monkeypatch).post("/roadmap/spine/auto").json()
    assert body["generated"] is False and body["reason"] == "unusable"
    counted = [w for w in sb.writes if w[0] == "rate_events"]
    assert counted, "a failed generation was not counted and would retry forever"
    assert counted[0][1]["action"] == "auto_spine"


def test_a_provider_outage_is_silent_rather_than_an_error_on_the_plan(monkeypatch) -> None:
    """The student did not ask for this, so it must not become their problem."""
    from app.llm import LLMUnavailable

    sb = _SB()

    def _boom(**kw):
        raise LLMUnavailable("provider down")

    monkeypatch.setattr("app.llm.chat", _boom)
    response = _client(sb, monkeypatch).post("/roadmap/spine/auto")
    assert response.status_code == 200
    assert response.json()["reason"] == "unavailable"


def test_it_refuses_when_no_skill_rung_has_resources_behind_it(monkeypatch) -> None:
    """A spine naming a rung with nothing behind it renders an empty learn
    step, which is the defect the whole module exists to avoid."""
    sb = _SB(learning_resources=[])
    called: list[int] = []
    monkeypatch.setattr("app.llm.chat", lambda **kw: called.append(1))
    assert _client(sb, monkeypatch).post("/roadmap/spine/auto").json()["reason"] == (
        "no-resources"
    )
    assert called == []


def test_a_good_reply_is_stored_once(monkeypatch) -> None:
    sb = _SB()

    class _Result:
        text = (
            '{"project": "Build a thing", "publish": "Put it somewhere", '
            '"skill_key": "statistics"}'
        )
        prompt_tokens = completion_tokens = total_tokens = 10

    monkeypatch.setattr("app.llm.chat", lambda **kw: _Result())
    body = _client(sb, monkeypatch).post("/roadmap/spine/auto").json()
    assert body["generated"] is True
    assert body["project"] == "Build a thing"
    stored = [w for w in sb.writes if w[0] == "generated_spines"]
    assert len(stored) == 1
    assert stored[0][1]["skill_key"] == "statistics"


def test_it_requires_an_account() -> None:
    assert TestClient(create_app()).post("/roadmap/spine/auto").status_code in (401, 403)
