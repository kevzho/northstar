"""
Team-up matching — candidate ranking and block-wall behavior, no database.

A tiny chainable fake stands in for the Supabase client: the functions
under test only ever chain select/eq/or_/limit and read ``.data`` off
execute(), so one stub covers both queries.
"""

from types import SimpleNamespace

from app.social import blocked_ids, teamup_candidates


class FakeQuery:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args):
        return self

    def or_(self, *_args):
        return self

    def limit(self, *_args):
        return self

    def execute(self):
        return SimpleNamespace(data=self._rows)


class FakeSB:
    def __init__(self, rows_by_table: dict[str, list[dict]]):
        self._rows = rows_by_table

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self._rows.get(name, []))


ME = {
    "id": "me",
    "audience": "high_school",
    "field_scores": {"cs": 60, "math": 30},
    "chosen_archetype": "applied-ai-builder",
}


def student(sid: str, **overrides) -> dict:
    row = {
        "id": sid,
        "name": f"{sid.title()} Person",
        "handle": sid,
        "grade": 11,
        "field_scores": {"cs": 50},
        "chosen_archetype": None,
        "chosen_kind": None,
        "teamup_pitch": "building things",
        "public_profile": True,
    }
    row.update(overrides)
    return row


def test_ranks_by_affinity_and_excludes_self_and_excluded() -> None:
    sb = FakeSB({
        "students": [
            student("me"),
            student("stranger", field_scores={"humanities": 90}),
            student("twin", field_scores={"cs": 70, "math": 40},
                    chosen_archetype="applied-ai-builder"),
            student("excluded"),
        ]
    })
    out = teamup_candidates(sb, ME, exclude_ids={"excluded"})
    ids = [c["student_id"] for c in out]
    assert "me" not in ids and "excluded" not in ids
    assert ids[0] == "twin"  # shared fields + same path ranks first


def test_zero_affinity_candidates_stay_in_the_deck() -> None:
    # Unlike discover, the pitch is signal the score can't see — a student
    # with no field overlap must still be shown, ranked last.
    sb = FakeSB({"students": [student("different", field_scores={"design": 80})]})
    out = teamup_candidates(sb, ME, exclude_ids=set())
    assert [c["student_id"] for c in out] == ["different"]


def test_private_profiles_never_leak_their_handle() -> None:
    sb = FakeSB({"students": [student("shy", public_profile=False)]})
    out = teamup_candidates(sb, ME, exclude_ids=set())
    assert out[0]["handle"] is None
    assert out[0]["name"] == "Shy"  # first name only, like everywhere social


def test_limit_caps_the_deck() -> None:
    sb = FakeSB({"students": [student(f"s{i}") for i in range(20)]})
    assert len(teamup_candidates(sb, ME, exclude_ids=set(), limit=5)) == 5


def test_blocked_ids_covers_both_directions() -> None:
    sb = FakeSB({
        "blocks": [
            {"blocker": "me", "blocked": "them"},
            {"blocker": "other", "blocked": "me"},
        ]
    })
    assert blocked_ids(sb, "me") == {"them", "other"}
