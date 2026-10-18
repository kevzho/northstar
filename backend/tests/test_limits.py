"""
The ceilings on actions that cost a person something.

These exist because of who uses this product. A friend-request loop aimed at a
fifteen-year-old is not a performance problem, and "decline" does not undo
having received two hundred of them.
"""

from __future__ import annotations

from app.limits import GLOBAL_PER_WINDOW, POLICIES, limit_block, record_event


class _Query:
    def __init__(self, counts, log):
        self.counts, self.log = counts, log
        self.action = None
        self.student = None

    def select(self, *a, **k):
        return self

    def eq(self, column, value):
        if column == "action":
            self.action = value
        if column == "student_id":
            self.student = value
        return self

    def gte(self, *a, **k):
        return self

    def execute(self):
        key = (self.action, self.student)
        return type("R", (), {"count": self.counts.get(key, 0), "data": []})()

    def insert(self, row):
        self.log.append(row)
        return self


class _SB:
    def __init__(self, counts=None):
        self.counts = counts or {}
        self.log: list[dict] = []

    def table(self, name):
        assert name == "rate_events"
        return _Query(self.counts, self.log)


def test_ordinary_use_never_meets_a_ceiling() -> None:
    """The limits are for abuse, not for rationing. A student having an
    enthusiastic evening should not be told to slow down."""
    sb = _SB({("friend_request", "me"): 12, ("friend_request", None): 50})
    assert limit_block(sb, "friend_request", "me") is None


def test_a_friend_request_loop_is_stopped_and_told_why() -> None:
    limit, _, _ = POLICIES["friend_request"]
    sb = _SB({("friend_request", "me"): limit})
    message = limit_block(sb, "friend_request", "me")
    assert message is not None
    # Names the student's own behaviour rather than scolding them about load.
    assert "connection requests" in message


def test_the_global_ceiling_catches_what_no_single_account_would() -> None:
    """One account under its own limit, the platform over its total — a
    distributed burst that a per-student count cannot see."""
    sb = _SB({
        ("friend_request", "me"): 1,
        ("friend_request", None): GLOBAL_PER_WINDOW["friend_request"],
    })
    message = limit_block(sb, "friend_request", "me")
    assert message is not None
    assert "busier than usual" in message


def test_an_unauthenticated_action_is_limited_globally() -> None:
    """POST /mentors/apply takes no account, so there is no student to count.
    It is the only write the open internet can reach."""
    per_student, _, _ = POLICIES["mentor_apply"]
    assert per_student is None
    sb = _SB({("mentor_apply", None): GLOBAL_PER_WINDOW["mentor_apply"]})
    assert limit_block(sb, "mentor_apply", None) is not None
    assert limit_block(_SB(), "mentor_apply", None) is None


def test_an_unknown_action_is_not_silently_limited() -> None:
    assert limit_block(_SB(), "something-new", "me") is None


def test_every_policy_has_a_global_ceiling_behind_it() -> None:
    """A per-student limit alone is a limit per account, and accounts are free."""
    for action in POLICIES:
        assert action in GLOBAL_PER_WINDOW, action


def test_a_limiter_that_cannot_write_does_not_break_the_endpoint() -> None:
    """A safeguard that can 500 the thing it protects is an outage. The failure
    mode of not counting one event is one extra request getting through."""

    class _Broken:
        def table(self, name):
            raise RuntimeError("database unavailable")

    record_event(_Broken(), "friend_request", "me")  # must not raise


def test_an_event_is_recorded_with_its_action_and_student() -> None:
    sb = _SB()
    record_event(sb, "report", "me")
    assert sb.log == [{"action": "report", "student_id": "me"}]
