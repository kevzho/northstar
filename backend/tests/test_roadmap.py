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


# --- entry gates ---------------------------------------------------------
#
# A row carrying an application deadline is not automatically a row you can
# apply to. Seven catalog rows are gated: you qualify for USAMO by AMC score,
# you advance to ISEF from an affiliated fair, and a TEACHER applies for a
# Lemelson InvenTeam grant. The sequencer read the deadline and ignored the
# gate, so it emitted "Apply to USAMO" — a step no student can take, in the one
# place the product promises to say what to do next.


def gated(oid, title, gate, note=None, deadline="2026-11-01"):
    row = {"id": oid, "title": title, "grade_min": 9, "grade_max": 12,
           "deadline": deadline, "entry_gate": gate}
    if note:
        row["entry_note"] = note
    return {"opportunity": row}


def _application_steps(plan):
    return [s for phase in plan["phases"] for s in phase["steps"]
            if s["category"] == "application"]


def test_a_qualify_row_is_never_phrased_as_an_application() -> None:
    plan = build_roadmap(
        {"grade": "11"}, SPINE, RESOURCES,
        [gated("o1", "USA Mathematical Olympiad (USAMO)", "qualify")],
        MISSIONS, TODAY,
    )
    steps = _application_steps(plan)
    assert steps, "an open, eligible row must still produce a step"
    titles = " ".join(s["title"] for s in steps)
    assert "Apply to USA Mathematical Olympiad" not in titles
    assert "Qualify for USA Mathematical Olympiad (USAMO)." in titles


def test_every_gate_produces_an_actionable_verb() -> None:
    """No gate may fall through to 'Apply', and none may produce empty text."""
    for gate, expected in [
        ("apply", "Apply to"),
        ("qualify", "Qualify for"),
        ("advance", "Advance to"),
        ("nominate", "Get nominated for"),
        # Deliberately NOT "Find a teacher": the prep step for this gate already
        # says that, and printing both two lines apart reads as a stutter rather
        # than as two steps. Finding the adult is the prerequisite; this is the
        # step that finishes it.
        ("teacher", "Get your teacher to submit"),
    ]:
        plan = build_roadmap(
            {"grade": "11"}, SPINE, RESOURCES, [gated("o1", "Some Program", gate)], MISSIONS, TODAY,
        )
        steps = _application_steps(plan)
        assert len(steps) == 1, f"{gate} produced {len(steps)} steps"
        assert steps[0]["title"].startswith(expected), (
            f"gate {gate!r} produced {steps[0]['title']!r}"
        )


def test_a_gated_step_never_repeats_its_own_prep_step() -> None:
    """Two steps, two different instructions.

    Seen on a real plan: "Find the teacher or coach who can enter ACS ChemClub
    with you" followed two lines later by "Find a teacher to enter ACS ChemClub
    with you". The prep step and the application step were the same sentence
    twice, which reads as a bug in the plan rather than as a route through it.
    """
    for gate in ("qualify", "advance", "nominate", "teacher"):
        plan = build_roadmap(
            {"grade": "11"}, SPINE, RESOURCES,
            [gated("o1", "Some Program", gate)], MISSIONS, TODAY,
        )
        titles = [s["title"] for p in plan["phases"] for s in p["steps"]
                  if s["opportunity_id"] == "o1"]
        assert len(titles) == 2, f"{gate} should produce a prep and an application"
        prep, application = titles
        # Compare on the leading verb phrase, which is what a reader actually
        # sees differ; the programme name is the same in both by design.
        first_words = lambda t: " ".join(t.split()[:3]).lower().rstrip(".")
        assert first_words(prep) != first_words(application), (
            f"gate {gate!r} says the same thing twice: {prep!r} then {application!r}"
        )


def test_a_curated_entry_note_wins_over_the_generic_one() -> None:
    """The audit wrote a specific sentence per row; it must not be discarded.

    It now lands on the PREPARATION step rather than the application, because
    that is the step it is an instruction for — "Qualify by score on the AMC 10
    or AMC 12" tells you what to do, and the thing you do it before is the
    application. Printing it on both made a student read the same sentence
    twice, directly under itself.
    """
    curated = "You cannot apply. Qualify by score on the AMC 10 or AMC 12."
    plan = build_roadmap(
        {"grade": "11"}, SPINE, RESOURCES, [gated("o1", "USAMO", "qualify", note=curated)], MISSIONS, TODAY,
    )
    steps = {s["step_key"]: s for p in plan["phases"] for s in p["steps"]}

    prep = steps["prep:o1"]
    assert curated in prep["edge_note"], "the audit's sentence was dropped"
    assert "entry is by qualifying score or exam" not in prep["edge_note"].lower()

    # The deadline is still stated -- a gate does not excuse dropping the date.
    assert "2026-11-01" in steps["qualify:o1"]["edge_note"]


def test_the_instruction_is_not_printed_twice() -> None:
    """It was, briefly: the prep step and the application beneath it carried the
    same sentence, so the plan repeated itself line to line."""
    curated = "Qualification is by AMC score."
    plan = build_roadmap(
        {"grade": "11"}, SPINE, RESOURCES, [gated("o1", "USAMO", "qualify", note=curated)], MISSIONS, TODAY,
    )
    notes = [
        s["edge_note"] for p in plan["phases"] for s in p["steps"]
        if s["step_key"] in ("prep:o1", "qualify:o1")
    ]
    assert sum(curated in n for n in notes) == 1


def test_a_gated_step_still_counts_as_dated() -> None:
    """notes.dated_steps drives the 'is this roadmap real?' display. A gated
    step has a real deadline, so excluding it would understate the plan.

    Two now, not one: a gated programme produces the preparation step AND the
    application it unlocks. Both are grounded in the same calendar fact and in a
    requirement the programme itself states, so counting both is the honest
    reading — this metric separates computed facts from authored guesses, and
    neither of these is a guess.
    """
    plan = build_roadmap(
        {"grade": "11"}, SPINE, RESOURCES, [gated("o1", "USAMO", "qualify")], MISSIONS, TODAY,
    )
    assert plan["notes"]["dated_steps"] == 2


def test_the_preparation_step_comes_before_the_thing_it_unlocks() -> None:
    """The whole point of the step.

    Telling a student to qualify for USAMO is useless underneath "Apply to
    USAMO" — a plan in the wrong order is not a plan. The prep step is placed a
    hair earlier on the time axis so it can never sort below its application.
    """
    plan = build_roadmap(
        {"grade": "11"}, SPINE, RESOURCES, [gated("o1", "USAMO", "qualify")], MISSIONS, TODAY,
    )
    keys = [
        step["step_key"]
        for phase in plan["phases"]
        for step in phase["steps"]
    ]
    assert "prep:o1" in keys, "a gated programme must say what to do first"
    assert keys.index("prep:o1") < keys.index("qualify:o1")


def test_an_ungated_application_gets_no_preparation_step() -> None:
    """A programme you can simply apply to has nothing standing in front of it,
    and inventing a hurdle would be as wrong as hiding a real one."""
    plan = build_roadmap(
        {"grade": "11"}, SPINE, RESOURCES, [gated("o1", "Open Thing", "apply")], MISSIONS, TODAY,
    )
    keys = [s["step_key"] for p in plan["phases"] for s in p["steps"]]
    assert "prep:o1" not in keys


def test_the_preparation_step_uses_the_programmes_own_words() -> None:
    """Measured 2026-10-05: all 18 gated high-school rows carry an entry_note a
    human wrote after reading the programme's page — "Qualification is by AMC
    score", "Entry is through your ACS local section exam". That sentence is
    the specific instruction a student needs, and the generic gate line is only
    the fallback when there is none."""
    row = gated("o1", "Math Prize for Girls", "qualify")
    row["opportunity"]["entry_note"] = "Qualification is by AMC score."
    plan = build_roadmap({"grade": "11"}, SPINE, RESOURCES, [row], MISSIONS, TODAY)
    prep = next(
        s for p in plan["phases"] for s in p["steps"] if s["step_key"] == "prep:o1"
    )
    assert "AMC score" in prep["edge_note"]
    assert "cannot apply directly" not in prep["edge_note"], (
        "the generic line should give way to the programme's own"
    )


def test_a_missing_or_unknown_gate_falls_back_to_apply() -> None:
    """Every row predating 20260925140000_entry_gate.sql, and any value a
    future migration adds, must still produce a usable step."""
    for row in (
        {"id": "o1", "title": "Old Row", "grade_min": 9, "grade_max": 12,
         "deadline": "2026-11-01"},                      # column absent
        {"id": "o2", "title": "Null Row", "grade_min": 9, "grade_max": 12,
         "deadline": "2026-11-01", "entry_gate": None},  # column null
        {"id": "o3", "title": "Future Row", "grade_min": 9, "grade_max": 12,
         "deadline": "2026-11-01", "entry_gate": "lottery"},  # unknown value
    ):
        plan = build_roadmap(
            {"grade": "11"}, SPINE, RESOURCES, [{"opportunity": row}], MISSIONS, TODAY,
        )
        steps = _application_steps(plan)
        assert len(steps) == 1
        assert steps[0]["title"].startswith("Apply to")


# --- the plan is not an inbox -------------------------------------------
#
# app/match.py pins a row at NOISE_FLOOR when nothing matched: no shared words,
# no field, no tag, no semantic signal. build_roadmap used to iterate every open,
# grade-eligible row regardless of score, so a biology-focused 10th grader's
# personalised learning path was nine capture-the-flag competitions at 0.0500
# each, every one captioned "Start today." The matcher had already called them
# noise; the roadmap never asked.
#
# Latent while four rows were open. Adding recurring competition feeds made it
# visible — the plan was always willing to do this, it just lacked the material.


def scored(oid, title, score, deadline="2026-11-01", grade_min=9):
    return {
        "opportunity": {"id": oid, "title": title, "grade_min": grade_min,
                        "grade_max": 12, "deadline": deadline},
        "score": {"score": score, "opportunity_id": oid, "explanation": ""},
    }


def test_a_row_the_matcher_called_noise_never_becomes_a_step() -> None:
    from app.match import NOISE_FLOOR

    plan = build_roadmap(
        {"grade": "10"}, SPINE, RESOURCES,
        [scored(f"o{i}", f"Irrelevant CTF {i}", NOISE_FLOOR) for i in range(9)],
        MISSIONS, TODAY,
    )
    apps = [s for p in plan["phases"] for s in p["steps"]
            if s["category"] == "application"]
    assert apps == [], (
        f"{len(apps)} noise-floor rows became application steps: "
        f"{[s['title'] for s in apps][:3]}"
    )
    # And the student still gets real work rather than an empty page.
    actionable = [s for p in plan["phases"] for s in p["steps"]
                  if s["category"] in ("skill", "project", "outreach")]
    assert actionable, "filtering noise must not empty the plan"


def test_applications_are_capped_so_a_plan_stays_a_plan() -> None:
    from app.roadmap import MAX_APPLICATION_STEPS

    plan = build_roadmap(
        {"grade": "10"}, SPINE, RESOURCES,
        [scored(f"o{i}", f"Good Match {i}", 0.5 - i * 0.01) for i in range(12)],
        MISSIONS, TODAY,
    )
    apps = [s for p in plan["phases"] for s in p["steps"]
            if s["category"] == "application"]
    assert len(apps) == MAX_APPLICATION_STEPS, (
        f"expected {MAX_APPLICATION_STEPS} application steps, got {len(apps)}"
    )


def test_the_cap_keeps_the_best_matches_not_the_first_ones() -> None:
    """``ranked`` arrives sorted by score, so the cap must preserve that order —
    otherwise the plan's four applications are arbitrary."""
    ranked = [scored("best", "Best Match", 0.90),
              scored("mid", "Middling Match", 0.50),
              scored("low", "Weak Match", 0.20),
              scored("low2", "Weaker Match", 0.15),
              scored("low3", "Weakest Match", 0.10)]
    plan = build_roadmap({"grade": "10"}, SPINE, RESOURCES, ranked, MISSIONS, TODAY)
    titles = [s["title"] for p in plan["phases"] for s in p["steps"]
              if s["category"] == "application"]
    assert any("Best Match" in t for t in titles)
    assert not any("Weakest Match" in t for t in titles)


def test_a_result_without_a_score_is_still_shown() -> None:
    """Older callers and tests pass bare {"opportunity": ...}. Silently hiding
    those would be a worse failure than showing them."""
    plan = build_roadmap(
        {"grade": "10"}, SPINE, RESOURCES,
        [{"opportunity": {"id": "o1", "title": "Unscored", "grade_min": 9,
                          "grade_max": 12, "deadline": "2026-11-01"}}],
        MISSIONS, TODAY,
    )
    apps = [s for p in plan["phases"] for s in p["steps"]
            if s["category"] == "application"]
    assert len(apps) == 1


def test_a_student_with_no_archetype_still_gets_build_and_publish_steps() -> None:
    """The "none of these are me" path.

    A student who declines all three suggested careers has no archetype, so
    spine_for("") returns None and the roadmap used to come back with no build
    or publish rung at all — the plan for someone who rejected the framing was
    thinner than the plan for someone who accepted it, which is backwards.

    Their spine comes from the model instead, written against their traits,
    grade, fields and real matched opportunities. Verified live on 2026-10-08: a
    10th grader with no archetype got a sampling-discipline rung, a home
    microbiology project, and a 12-step roadmap carrying real verified learning
    resources and a real USABO deadline.
    """
    generated = {
        "project": "Run a small microbiology experiment you can do at home.",
        "publish": "Write it up as a short illustrated report.",
        "skill": "sampling discipline — why the boring schedule is the whole experiment",
        "skillKey": "sampling-discipline",
        "source": "generated",
    }
    plan = build_roadmap(
        {"grade": "10"},                      # no chosen_archetype at all
        generated, RESOURCES, [], MISSIONS, TODAY,
    )
    keys = [s["step_key"] for p in plan["phases"] for s in p["steps"]]
    assert "spine:project" in keys, "a declined archetype must not cost the build step"
    assert "spine:publish" in keys

    notes = [
        s["edge_note"] for p in plan["phases"] for s in p["steps"]
        if s["step_key"].startswith("spine:")
    ]
    # And it must still be labelled as a model's suggestion rather than
    # inheriting the wording reserved for the hand-authored spines.
    assert any("Written for you" in n for n in notes)
    assert not any("A common route" in n for n in notes)
