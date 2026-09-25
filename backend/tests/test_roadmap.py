"""
Tests for app/roadmap.py — the sequencer.

Pure function, no network, tested exhaustively the way app/match.py is. The
properties here are the ones that make the roadmap honest rather than merely
ordered: a 9th grader must get real work, a locked program must never be
presented as appliable, and no step may claim a date the catalog cannot
support.
"""

from __future__ import annotations

from datetime import date

from app.roadmap import (
    MIN_HORIZON_MONTHS,
    build_roadmap,
    horizon_months,
    label_for_months,
)

TODAY = date(2026, 9, 24)

SPINE = {
    "project": "Build a small thing end to end, however rough.",
    "publish": "Post a 60-second demo where builders will see it.",
    "skill": "evaluation — measuring whether it works, not whether it runs",
    "skillKey": "evaluation",
}

RESOURCES = [
    {"id": "r1", "title": "Free Course One", "effort": "a weekend"},
    {"id": "r2", "title": "Free Course Two", "effort": "2 weeks"},
    {"id": "r3", "title": "Free Book Three", "effort": "a month"},
]

MISSIONS = [
    {"id": "m1", "title": "Ship one small proof.", "description": "Do the thing."},
    {"id": "m2", "title": "Write it up.", "description": "Explain the thing."},
]


def opp(oid, title, grade_min, deadline):
    return {"opportunity": {
        "id": oid, "title": title, "grade_min": grade_min,
        "grade_max": 12, "deadline": deadline,
    }}


def test_a_ninth_grader_gets_real_work_not_a_birthday() -> None:
    """The failure the whole design exists to fix.

    Against production, a 9th grader has ONE catalog row with a future
    deadline. An opportunity-only sequencer has nothing to tell them. The
    roadmap must fill the near term with steps they can start now.
    """
    ranked = [
        opp("o1", "Locked until 11th", 11, "2027-01-15"),
        opp("o2", "Also locked", 12, "2027-02-01"),
    ]
    out = build_roadmap(
        {"grade": "9"}, SPINE, RESOURCES, ranked, MISSIONS, TODAY,
    )
    steps = [s for p in out["phases"] for s in p["steps"]]

    assert steps, "a 9th grader got an empty roadmap"
    actionable = [s for s in steps if s["category"] in ("skill", "project", "outreach")]
    assert len(actionable) >= 4, (
        f"only {len(actionable)} steps a 9th grader can start now — this is the "
        "birthday problem the design exists to avoid"
    )
    # Neither locked program may appear as an application step.
    assert not [s for s in steps if s["category"] == "application"]
    # They appear as horizon markers instead, with their unlock grade.
    assert {h["opens_at_grade"] for h in out["horizon"]} == {11, 12}


def test_a_locked_program_is_never_presented_as_appliable() -> None:
    ranked = [opp("o1", "Grade 11 only", 11, "2027-03-01")]
    for grade, expect_apply in (("9", False), ("10", False), ("11", True), ("12", True)):
        out = build_roadmap({"grade": grade}, None, [], ranked, [], TODAY)
        steps = [s for p in out["phases"] for s in p["steps"]]
        applies = [s for s in steps if s["category"] == "application"]
        assert bool(applies) is expect_apply, (
            f"grade {grade}: expected application step={expect_apply}"
        )


def test_an_expired_or_undated_opportunity_is_not_an_application_step() -> None:
    """31 of 35 dated seed rows were expired, and 33 curated rows are null on
    purpose because their real dates drift. Neither may become "apply by"."""
    ranked = [
        opp("expired", "Closed last year", 9, "2025-01-01"),
        opp("undated", "Rolling, no date", 9, None),
        opp("open", "Actually open", 9, "2027-05-01"),
    ]
    out = build_roadmap({"grade": "9"}, None, [], ranked, [], TODAY)
    steps = [s for p in out["phases"] for s in p["steps"]]
    applied = {s["opportunity_id"] for s in steps if s["category"] == "application"}
    assert applied == {"open"}


def test_every_step_carries_an_honest_edge_reason() -> None:
    out = build_roadmap({"grade": "10"}, SPINE, RESOURCES,
                        [opp("o", "Open", 9, "2027-01-01")], MISSIONS, TODAY)
    steps = [s for p in out["phases"] for s in p["steps"]]
    computed = {"eligibility", "window"}
    authored = {"artifact", "ladder", "evidence"}
    for s in steps:
        assert s["edge_reason"] in computed | authored, s
    # The counts are reported so the UI can say which is which.
    assert out["notes"]["authored_edges"] > 0
    assert out["notes"]["dated_steps"] == 1


def test_provenance_is_always_an_id_never_a_bare_string() -> None:
    """A step naming a program or course must reference it, so the FK can
    refuse a row that names something not in the catalog."""
    out = build_roadmap({"grade": "11"}, SPINE, RESOURCES,
                        [opp("o1", "Open now", 9, "2027-01-01")], MISSIONS, TODAY)
    steps = [s for p in out["phases"] for s in p["steps"]]
    for s in steps:
        if s["category"] == "application":
            assert s["opportunity_id"], "application step with no opportunity_id"
        if s["step_key"].startswith("learn:"):
            assert s["resource_id"], "learning step with no resource_id"
        if s["step_key"].startswith("mission:"):
            assert s["mission_id"]


def test_step_keys_are_unique_and_stable() -> None:
    """Regeneration merges on step_key. A duplicate would collide on the
    unique index; an unstable one would lose a completed step."""
    args = ({"grade": "10"}, SPINE, RESOURCES,
            [opp("o1", "Open", 9, "2027-01-01")], MISSIONS)
    first = build_roadmap(*args, TODAY)
    second = build_roadmap(*args, TODAY)
    keys = [s["step_key"] for p in first["phases"] for s in p["steps"]]
    assert len(keys) == len(set(keys)), f"duplicate step_key: {keys}"
    assert keys == [s["step_key"] for p in second["phases"] for s in p["steps"]]


def test_unparseable_grade_does_not_invent_unlock_dates() -> None:
    """students.grade is free text and onboarding offers 'Gap year'. A bad
    grade must not silently become 99 and unlock everything, which is what
    match.py's booster does."""
    ranked = [opp("o1", "Grade 12 only", 12, "2027-01-01")]
    out = build_roadmap({"grade": "Gap year"}, SPINE, RESOURCES, ranked, [], TODAY)
    assert out["grade"] is None
    assert out["horizon_months"] == MIN_HORIZON_MONTHS
    steps = [s for p in out["phases"] for s in p["steps"]]
    # Unknown grade means we cannot say they are ineligible, so it may appear —
    # but it must still respect the deadline gate.
    assert all(s["edge_reason"] != "eligibility" for s in steps)


def test_horizon_shrinks_as_a_student_advances() -> None:
    assert horizon_months(9, TODAY) > horizon_months(11, TODAY)
    assert horizon_months(12, TODAY) == MIN_HORIZON_MONTHS
    for g in range(6, 13):
        assert MIN_HORIZON_MONTHS <= horizon_months(g, TODAY) <= 42


def test_phase_labels_are_grade_terms_not_fabricated_months() -> None:
    months_names = ("January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November",
                    "December")
    for m in (0.2, 1.5, 6, 14, 30, 60):
        for grade in (9, 10, 11, 12, None):
            label = label_for_months(m, grade, TODAY)
            assert label.strip(), (m, grade)
            assert not any(name in label for name in months_names), label

    assert label_for_months(0.1, 10, TODAY) == "Now"
    # A senior cannot have a phase inside school 30 months out.
    assert label_for_months(30, 12, TODAY) == "After graduation"


def test_a_phase_label_never_postdates_its_own_steps() -> None:
    """The bug: "Spring of grade 12" headed a step closing in 30 days, and
    "After graduation" headed the build steps."""
    ranked = [
        opp("soon", "Closes in a week", 9, "2026-10-01"),
        opp("far", "Closes in 14 months", 9, "2027-11-20"),
    ]
    out = build_roadmap({"grade": "12"}, SPINE, RESOURCES, ranked, MISSIONS, TODAY)
    first = out["phases"][0]
    assert first["label"] == "Now", first["label"]
    # Any step due within the month must be in the "Now" phase.
    for phase in out["phases"]:
        for step in phase["steps"]:
            if step["due_in_months"] < 1:
                assert phase["label"] == "Now", (
                    f"step due in {step['due_in_months']:.1f}mo sits under "
                    f"{phase['label']!r}"
                )


def test_no_spine_still_produces_a_usable_roadmap() -> None:
    """12 of 24 archetypes had no spine for five weeks, and a student who has
    not charted a path has none either. Neither may get an empty page."""
    out = build_roadmap({"grade": "11"}, None, [],
                        [opp("o1", "Open", 9, "2027-01-01")], [], TODAY)
    steps = [s for p in out["phases"] for s in p["steps"]]
    assert steps, "no spine produced an empty roadmap"


def test_an_imminent_deadline_is_never_placed_after_a_distant_one() -> None:
    """The bug a dry run against production caught.

    Phasing chunked steps by insertion order, so a grade-12 student was shown
    QuestBridge (closing in 3 days) and Coca-Cola (6 days) in a phase labelled
    "After graduation", behind learning steps. A roadmap that misorders the one
    thing with a real deadline is worse than a list.
    """
    ranked = [
        opp("far", "Closes in a year", 9, "2027-09-01"),
        opp("soon", "Closes in three days", 9, "2026-09-27"),
        opp("mid", "Closes in two months", 9, "2026-11-24"),
    ]
    out = build_roadmap({"grade": "12"}, SPINE, RESOURCES, ranked, MISSIONS, TODAY)
    steps = [s for p in out["phases"] for s in p["steps"]]

    order = [s["opportunity_id"] for s in steps if s["category"] == "application"]
    assert order == ["soon", "mid", "far"], (
        f"application steps are out of deadline order: {order}"
    )

    by_key = {s["step_key"]: s for s in steps}
    assert by_key["apply:soon"]["ordinal"] < by_key["apply:far"]["ordinal"]
    # The imminent one must be in the first phase and marked as a week task.
    assert by_key["apply:soon"]["phase_index"] == 0
    assert by_key["apply:soon"]["timeframe"] == "week"
    assert "Start today" in by_key["apply:soon"]["edge_note"]
    assert by_key["apply:far"]["timeframe"] == "month"


def test_every_phase_has_a_label() -> None:
    """A senior's last phase rendered with an empty label, because
    phase_labels broke out of its loop on reaching graduation."""
    ranked = [opp(f"o{i}", f"Program {i}", 9, f"2027-0{i}-01") for i in range(1, 6)]
    for grade in ("9", "10", "11", "12"):
        out = build_roadmap({"grade": grade}, SPINE, RESOURCES, ranked, MISSIONS, TODAY)
        for phase in out["phases"]:
            assert phase["label"].strip(), f"grade {grade}: unlabelled phase"
            for step in phase["steps"]:
                assert step["phase_label"].strip()


def test_no_authored_step_is_pushed_past_the_horizon() -> None:
    """Steps that are available now must be scheduled now.

    The outreach step was added last and inherited its insertion index as a
    time position, so a senior was advised to send two emails "After
    graduation". Nothing a student could do this week belongs there.
    """
    ranked = [opp("far", "Closes in a year", 9, "2027-09-01")]
    for grade in ("9", "12"):
        out = build_roadmap({"grade": grade}, SPINE, RESOURCES, ranked, MISSIONS, TODAY)
        for phase in out["phases"]:
            for step in phase["steps"]:
                if step["category"] in ("skill", "project", "outreach"):
                    assert phase["label"] != "After graduation", (
                        f'grade {grade}: "{step["title"][:40]}" ({step["category"]}) '
                        f"scheduled after graduation, but it is available now"
                    )
