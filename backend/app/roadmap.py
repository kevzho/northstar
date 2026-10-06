"""
Build one student's roadmap: an ordered sequence of concrete steps.

Northstar ranked opportunities. This sequences them, and — more importantly —
fills the space in front of them with things a student can do this week.

WHY THE TIME AXIS IS GRADE, NOT DEADLINE. Measured against production:

    grade   eligible   with a future deadline
      9       36/61             1
     10       44/61             1
     11       55/61             1
     12       61/61             4

A 9th grader has ONE thing in the whole catalog they can apply to today. A
sequencer anchored on deadlines has nothing to say to them, and the only
"unlock" it can offer is a birthday -- which three independent reviewers of an
earlier design called its fatal flaw. So the horizon comes from months to
graduation, and the near term is filled with work that is available now:
a free resource to learn from, the spine's project, the publish step. An
application appears as a step only when it is genuinely open.

The chain is learn -> build -> publish -> apply, and every arrow is a real
dependency rather than a calendar tick.

WHAT THIS MODULE DOES NOT DO. No network, no database, no model. It takes data
and returns a list of dicts, so it can be tested exhaustively the way
app/match.py is. Persistence and fetching live in the route.

HONEST LABELLING. Every step carries an ``edge_reason``. Two of them --
``eligibility`` and ``window`` -- are computed calendar facts. Three --
``artifact``, ``ladder``, ``evidence`` -- are authored generalisations about how
students get from one thing to the next, backed by 24 hand-written spines and no
outcome data at all (public.outcomes has 0 rows). The UI words those as "a
common route", never "required", because claiming a causal chain we have not
measured would be the same class of error as the catalog rows that had to be
retired.
"""

from __future__ import annotations

from datetime import date

# A school year a student is "in the fall of" -- used for phase labels. Northern
# hemisphere academic year; a student in grade 11 in the autumn is 11 all year
# for our purposes, which is accurate enough for a horizon marker and avoids
# inventing a month.
TERMS = ("Fall", "Spring")

# How many steps a phase may hold. A roadmap that lists twenty things for this
# month is a list again. Named because it is a judgement call, not a finding.
STEPS_PER_PHASE = 3

# Longest horizon we will plan over, in months. A freshman gets three and a bit
# years; beyond that the catalog's own shape is guesswork.
MAX_HORIZON_MONTHS = 42
MIN_HORIZON_MONTHS = 6

GRADUATION_MONTH = 6  # June

# The academic year turns over in July: a student is "in" their grade from then
# until the following June.
ACADEMIC_YEAR_START_MONTH = 7

# entry_gate -> (step wording, fallback note). The note is only used when the
# row has no entry_note of its own, so a curated explanation always wins.
# What a student actually DOES first, when a gate stands in front of a
# programme.
#
# The gate was already surfaced as a footnote on the application step: "You
# cannot apply directly -- entry is by qualifying score or exam." True, and
# useless on its own. A roadmap whose answer to "I want Math Prize for Girls"
# is a caveat has told the student they are blocked and stopped there.
#
# So a gated programme now gets a step of its own, placed BEFORE the
# application. The wording comes from opportunities.entry_note where there is
# one -- a sentence a human wrote after reading the programme's page, saying
# what the qualifier actually is ("Qualification is by AMC score", "Entry is
# through your ACS local section exam") -- and falls back to the generic line
# only when there is none. Measured 2026-10-05: all 18 gated high-school rows
# carry a note, so the generic fallback is the rare case, not the common one.
#
# Nothing here is invented. The step says what the catalog was already told.
GATE_PREP: dict[str, str] = {
    "qualify": "Work toward the qualifier for {title}",
    "advance": "Enter the affiliated fair that leads to {title}",
    "nominate": "Line up a nomination for {title}",
    "teacher": "Find the teacher or coach who can enter {title} with you",
}

GATE_STEP: dict[str, tuple[str, str]] = {
    "apply": ("Apply to {title}.", ""),
    "qualify": (
        "Qualify for {title}.",
        "You cannot apply directly — entry is by qualifying score or exam.",
    ),
    "advance": (
        "Advance to {title} from an affiliated fair.",
        "Entry is by winning at an affiliated regional or state fair first.",
    ),
    "nominate": (
        "Get nominated for {title}.",
        "Entry needs a nomination or recommendation — ask early, not late.",
    ),
    "teacher": (
        "Find a teacher to enter {title} with you.",
        "An adult applies or registers the team, not a student individually.",
    ),
}



def _int_grade(raw: object) -> int | None:
    """students.grade is free text -- onboarding offers '8' through '12' and
    'Gap year'. Anything unparseable means we cannot place a student on the
    time axis, and the caller falls back to an undated plan rather than
    guessing a grade and producing confidently wrong unlock dates."""
    try:
        grade = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return grade if 6 <= grade <= 12 else None


def horizon_months(grade: int, today: date) -> int:
    """Months until this student graduates, clamped."""
    years_left = max(0, 12 - grade)
    months = years_left * 12 + max(0, GRADUATION_MONTH - today.month)
    return max(MIN_HORIZON_MONTHS, min(MAX_HORIZON_MONTHS, months))


def label_for_months(months: float, grade: int | None, today: date) -> str:
    """A phase label derived from WHEN its steps fall, not from its index.

    Index-based labelling put a scholarship closing in 30 days under "Spring of
    grade 12" and the build steps under "After graduation". A heading has to
    come from the time axis or it contradicts the steps beneath it.

    Never a month name: the catalog cannot support that precision. Four of 61
    high-school rows carry a usable future deadline and 33 are deliberately
    undated because their real dates drift.
    """
    if months < 1:
        return "Now"
    if grade is None:
        return "Next few months" if months < 4 else "Later"

    # ACADEMIC years, not calendar years. A step five months out from
    # September lands in February — still the same school year, still the same
    # grade. Counting calendar years rolled it over and told a senior their
    # February deadline fell "After graduation".
    total = today.month - 1 + int(round(months))
    landing_year = today.year + total // 12
    landing_month = total % 12 + 1

    def academic_start(year: int, month: int) -> int:
        """The calendar year the academic year containing (year, month) began."""
        return year if month >= ACADEMIC_YEAR_START_MONTH else year - 1

    years_out = academic_start(landing_year, landing_month) - academic_start(
        today.year, today.month
    )
    target = grade + years_out
    if target > 12:
        return "After graduation"

    term = "Fall" if landing_month >= ACADEMIC_YEAR_START_MONTH else "Spring"
    return f"{term} of grade {target}"


def _unlock_grade(opp: dict) -> int:
    try:
        return int(opp.get("grade_min") or 6)
    except (TypeError, ValueError):
        return 6


def _is_open(opp: dict, today: date) -> bool:
    """Only a row with a future deadline is presented as appliable now.

    A null deadline is NOT treated as open: 33 curated rows carry null on
    purpose because their real dates drift, and the seed migration's own header
    says not to fabricate them.
    """
    deadline = opp.get("deadline")
    if not deadline:
        return False
    try:
        return date.fromisoformat(str(deadline)) >= today
    except ValueError:
        return False


# How many "apply to this" steps a plan may contain.
#
# A plan is a sequence, not an inbox. Ten applications in the Now phase is a
# list of links with a deadline attached — the thing this product exists to
# replace. Four is enough to be useful and few enough to be a decision.
MAX_APPLICATION_STEPS = 4


def _worth_applying(result: dict, already: int) -> bool:
    """Whether a ranked row earns a place in the plan.

    TWO RULES, AND THE FIRST IS THE IMPORTANT ONE.

    Respect the matcher's own verdict. app/match.py pins a row at NOISE_FLOOR
    when it matched nothing at all — no shared words, no field, no tag, no
    semantic signal. The roadmap used to iterate every open, grade-eligible row
    regardless of score, so a biology-focused 10th grader's personalised learning
    path was nine capture-the-flag security competitions, each scored 0.0500,
    each presented as "Apply to this. Start today." The matcher had already
    called them noise; the roadmap simply did not ask.

    That bug was latent while only four rows were open. Adding recurring
    competition feeds made it visible, which is the useful kind of regression:
    the plan was always willing to do this, it just never had the material.

    Then cap the count, because a plan with ten applications is not a plan.
    ``ranked`` arrives sorted by score, so the cap keeps the best matches.
    """
    from .match import NOISE_FLOOR

    if already >= MAX_APPLICATION_STEPS:
        return False
    score = (result.get("score") or {}).get("score")
    if score is None:
        return True  # no score available (tests, older callers) — do not hide it
    return score > NOISE_FLOOR


def build_roadmap(
    student: dict,
    spine: dict | None,
    resources: list[dict],
    ranked: list[dict],
    missions: list[dict],
    today: date,
) -> dict:
    """Return {"horizon_months", "phases": [{label, steps: [...]}], "notes"}.

    ``spine`` is SPINES[archetype] from frontend/lib/plan.ts, mirrored server
    side: {project, publish, skill, skillKey}. None means the student has not
    charted a path, and the roadmap is then resources + open applications only.
    ``ranked`` is score_opportunities() output.
    """
    grade = _int_grade(student.get("grade"))
    steps: list[dict] = []

    def add(
        category: str,
        title: str,
        *,
        step_key: str,
        edge_reason: str,
        edge_note: str = "",
        opportunity_id: str | None = None,
        resource_id: str | None = None,
        mission_id: str | None = None,
        timeframe: str = "month",
        due_in_months: float | None = None,
    ) -> None:
        # due_in_months places a step on the time axis. A deadline sets it; the
        # authored ladder rungs take their sequence position instead, so learn
        # precedes build precedes publish. Without it, phasing chunked by
        # insertion order and a senior was told a scholarship closing in three
        # days fell "After graduation".
        steps.append({
            "due_in_months": (
                due_in_months if due_in_months is not None else float(len(steps))
            ),
            "category": category,
            "title": title,
            "step_key": step_key,
            "edge_reason": edge_reason,
            "edge_note": edge_note,
            "opportunity_id": opportunity_id,
            "resource_id": resource_id,
            "mission_id": mission_id,
            "timeframe": timeframe,
        })

    # 1. LEARN. First, because it is the only rung available to every student
    #    regardless of grade, and because the spine's skill rung used to be an
    #    instruction with nowhere to go.
    if spine and resources:
        first = resources[0]
        add(
            "skill",
            f"Start {first['title']} — {first.get('effort', 'a weekend')}.",
            step_key=f"learn:{first['id']}",
            edge_reason="ladder",
            edge_note=(
                f"This is the skill rung of your path: {spine.get('skill', '')}. "
                "Free, and it is the thing that makes the rest possible."
            ),
            resource_id=first["id"],
            timeframe="month",
        )
        for extra in resources[1:3]:
            add(
                "skill",
                f"Then {extra['title']} — {extra.get('effort', 'a weekend')}.",
                step_key=f"learn:{extra['id']}",
                edge_reason="ladder",
                edge_note="Same skill, a different angle. Free.",
                resource_id=extra["id"],
            )

    # 2. BUILD, then 3. PUBLISH. Labelled by who actually wrote them.
    #
    # "A common route" is a claim about what students generally do, and it is
    # true of the twenty-four authored spines because a person wrote each one
    # after looking at the field. It is NOT true of a spine the model wrote for
    # one student this week: nobody has seen anyone follow it, and
    # public.outcomes still has no rows. Giving both the same sentence would
    # launder a guess into a pattern, which is the same error as a deadline no
    # human confirmed being shown as though one had.
    if spine:
        written_for_you = spine.get("source") == "generated"
        add(
            "project",
            spine["project"],
            step_key="spine:project",
            edge_reason="artifact",
            edge_note=(
                "Written for you from your assessment and your matches — a "
                "suggestion, not a route anyone has walked."
                if written_for_you
                else "A common route: the thing you make is what an application asks about."
            ),
        )
        add(
            "project",
            spine["publish"],
            step_key="spine:publish",
            edge_reason="evidence",
            edge_note=(
                "Written for you. Work nobody can see is hard to point at later."
                if written_for_you
                else "A common route: work nobody can see is hard to point at later."
            ),
        )

    # Missions, ordered so the one matching the student's strongest trait lands
    # early (an early win) -- the only genuinely per-student mechanic the
    # existing plan had.
    for index, mission in enumerate(missions[:2]):
        add(
            "project",
            mission.get("title", ""),
            step_key=f"mission:{mission.get('id')}",
            edge_reason="artifact",
            edge_note=mission.get("description", "")[:200],
            mission_id=mission.get("id"),
            # Explicit ladder position. Inheriting the insertion index pushed
            # these past a senior's horizon and scheduled work they could start
            # today for "After graduation".
            due_in_months=3.0 + index,
        )

    # 4. APPLY -- only what is actually open, and only what the student is
    #    eligible for. Everything else becomes a horizon marker, not a step.
    #
    #    A row carrying an application deadline is not automatically a row you
    #    can apply to. You qualify for USAMO by AMC score; you advance to ISEF
    #    from an affiliated regional fair; a TEACHER applies for a Lemelson
    #    InvenTeam grant. Telling a student to "Apply to USAMO" is not a wording
    #    slip, it is a step they cannot take, in the one place this product
    #    promises to say what to do next. See opportunities.entry_gate
    #    (20260925140000_entry_gate.sql).
    horizon: list[dict] = []
    applications = 0
    for result in ranked:
        opp = result.get("opportunity") or {}
        opp_id = opp.get("id")
        if not opp_id:
            continue
        unlock = _unlock_grade(opp)
        eligible = grade is None or unlock <= grade

        if eligible and _is_open(opp, today) and _worth_applying(result, applications):
            days = (date.fromisoformat(str(opp["deadline"])) - today).days
            soon = days <= 30
            title = opp.get("title", "this program")
            gate = (opp.get("entry_gate") or "apply").strip() or "apply"
            verb, gate_note = GATE_STEP.get(gate, GATE_STEP["apply"])

            # The preparation step, before the application it unlocks.
            #
            # Placed a hair earlier on the time axis so it always sorts above
            # the thing it is a prerequisite for -- a plan that lists "apply"
            # above "qualify first" is a plan in the wrong order.
            prep = GATE_PREP.get(gate)
            if prep:
                note = (opp.get("entry_note") or "").strip() or gate_note
                add(
                    "skill",
                    prep.format(title=title) + ".",
                    step_key=f"prep:{opp_id}",
                    # Not "ladder": this is a stated requirement of the
                    # programme, not a generalisation about what students
                    # usually do. It belongs with the computed facts.
                    edge_reason="gate",
                    edge_note=(
                        note
                        + (" " if note else "")
                        + f"Do this before the {opp.get('deadline')} deadline, "
                        "not after it."
                    ).strip(),
                    opportunity_id=opp_id,
                    timeframe="month",
                    due_in_months=max(0.0, float(days) / 30.0 - 0.01),
                )

            # The gate is the binding constraint when there is one; the closing
            # date only matters once you are allowed through it.
            add(
                "application",
                verb.format(title=title),
                step_key=f"{gate}:{opp_id}",
                edge_reason="window" if gate == "apply" else "gate",
                # Once a preparation step exists it has already said HOW you
                # get in, in the programme's own words. Repeating that sentence
                # here made a student read the same instruction twice in a row,
                # directly under itself. The application step keeps only what is
                # its own: when the window shuts.
                edge_note=(
                    ("" if prep else (opp.get("entry_note") or gate_note or "").strip() + " ")
                    + f"Closes {opp.get('deadline')} — {days} days away. "
                    + ("Start today." if soon else "Open now.")
                ).strip(),
                opportunity_id=opp_id,
                timeframe="week" if soon else "month",
                # Placed by its deadline, so a step closing this month cannot
                # land in a phase after one closing next year.
                due_in_months=max(0.0, days / 30.0),
            )
            applications += 1
        elif not eligible:
            horizon.append({
                "title": opp.get("title", ""),
                "opens_at_grade": unlock,
                "opportunity_id": opp_id,
                "edge_reason": "eligibility",
                "edge_note": (
                    f"Opens when you reach grade {unlock}. Not yet — which is "
                    "what the work above is for."
                ),
            })

    add(
        "outreach",
        "Email two people doing work you want to do. One specific question each, not for generic advice.",
        step_key="outreach:cold-email",
        edge_reason="ladder",
        edge_note="A common route: most students never send the email.",
        # Explicitly near-term. Added last, so without this it inherited its
        # insertion index as a time position and landed under "After
        # graduation" — advice to send an email in three years.
        due_in_months=2.0,
    )

    # Chunk into phases and stamp ordering.
    months = horizon_months(grade, today) if grade is not None else MIN_HORIZON_MONTHS

    steps.sort(key=lambda s: (s["due_in_months"], s["step_key"]))

    phase_count = max(1, min(6, -(-len(steps) // STEPS_PER_PHASE)))
    phases: list[dict] = []
    ordinal = 0
    used: set[str] = set()
    for index in range(phase_count):
        chunk = steps[index * STEPS_PER_PHASE : (index + 1) * STEPS_PER_PHASE]
        if not chunk:
            continue
        # Labelled from the EARLIEST step in the phase, so the heading never
        # postdates anything beneath it.
        label = label_for_months(chunk[0]["due_in_months"], grade, today)
        if label in used:
            label = f"{label} — continued"
        used.add(label)
        for step in chunk:
            step["phase_index"] = index
            step["phase_label"] = label
            step["ordinal"] = ordinal
            ordinal += 1
        phases.append({"label": label, "steps": chunk})

    return {
        "horizon_months": months,
        "grade": grade,
        "phases": phases,
        "horizon": sorted(horizon, key=lambda h: h["opens_at_grade"])[:12],
        "notes": {
            "dated_steps": sum(
                1 for s in steps if s["edge_reason"] in ("window", "gate")
            ),
            "authored_edges": sum(
                1 for s in steps if s["edge_reason"] in ("artifact", "ladder", "evidence")
            ),
            "outcomes_logged": 0,
        },
    }
