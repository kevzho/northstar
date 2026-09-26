"""
The verifier must carry entry_gate, not leave it to the column default.

Twenty-two catalog rows were corrected by hand because they carried an
application deadline for something a student cannot apply to: you qualify for
USAMO by exam score, you advance to ISEF from a regional fair, and a TEACHER
applies for a Lemelson-MIT InvenTeam grant. app/roadmap.py reads the column to
choose the step verb, so a wrong gate produces "Apply to USAMO" — a step no
student can take, in the one place this product promises to say what to do next.

The verifier had no notion of it, so every AI-imported row took the default.
Tested against Azure gpt-5.6, it accepted the Lemelson grant as a student
opportunity at 0.98 confidence. The scraper could therefore reintroduce, nightly
and unattended, the entire class of defect the hand corrections removed.

These tests cover the validation boundary, which is where a model's freedom to
say anything meets a Postgres enum that will reject the whole batch.
"""

from __future__ import annotations

import pytest

from app.verifier import ENTRY_GATES, decide

CANDIDATE = {
    "title": "Some Program",
    "blurb": "A real thing students do.",
    "url": "https://example.org/program",
    "source": "reddit",
}


def verdict(**over) -> dict:
    base = {
        "is_opportunity": True,
        "title": "Some Program",
        "host": "Example Org",
        "field": "engineering",
        "type": "competition",
        "confidence": 0.95,
        "reason": "real",
    }
    base.update(over)
    return base


def test_the_enum_matches_the_migration() -> None:
    """A value Postgres rejects fails the whole import batch, so the set here
    must equal the one in 20260925140000_entry_gate.sql."""
    import pathlib
    import re

    sql = (pathlib.Path(__file__).resolve().parents[2] / "supabase" / "migrations"
           / "20260925140000_entry_gate.sql").read_text()
    declared = set(re.findall(r"'([a-z]+)'", sql.split("create type")[1].split(")")[0]))
    assert declared == set(ENTRY_GATES), (
        f"verifier gates {sorted(ENTRY_GATES)} != migration {sorted(declared)}"
    )


@pytest.mark.parametrize("gate", sorted(ENTRY_GATES))
def test_every_valid_gate_is_passed_through(gate: str) -> None:
    row = decide(CANDIDATE, verdict(entry_gate=gate))
    assert row is not None
    assert row["entry_gate"] == gate


@pytest.mark.parametrize("bad", ["", None, "APPLY ", "lottery", "audition", 7, [], "teacher;drop"])
def test_an_unusable_gate_falls_back_to_apply(bad) -> None:
    """Not a guess — the floor. The prompt tells the model to lower its
    confidence when the text does not say, and CONFIDENCE_FLOOR keeps the
    unclear ones out, so the fallback only ever applies to rows that were
    already confident about everything else."""
    row = decide(CANDIDATE, verdict(entry_gate=bad))
    assert row is not None
    assert row["entry_gate"] == "apply"


def test_case_and_whitespace_are_tolerated() -> None:
    """Models emit "Teacher" and " qualify" — rejecting those would silently
    downgrade a correct answer to the default."""
    assert decide(CANDIDATE, verdict(entry_gate="Teacher"))["entry_gate"] == "teacher"
    assert decide(CANDIDATE, verdict(entry_gate="  QUALIFY "))["entry_gate"] == "qualify"


def test_a_note_is_stored_only_when_it_adds_something() -> None:
    row = decide(CANDIDATE, verdict(entry_gate="teacher",
                                    entry_note="A teacher applies for the grant."))
    assert row["entry_note"] == "A teacher applies for the grant."

    # An empty note must not be stored: roadmap.py falls back to per-gate
    # wording, and "" would displace it with nothing.
    row = decide(CANDIDATE, verdict(entry_gate="teacher", entry_note="   "))
    assert "entry_note" not in row

    # Nor on an ungated row, where a note has nothing to explain.
    row = decide(CANDIDATE, verdict(entry_gate="apply", entry_note="Just apply."))
    assert "entry_note" not in row


def test_a_gated_row_is_still_imported() -> None:
    """The point is honesty, not exclusion. Lemelson-MIT is a real thing a
    student can pursue by finding a teacher, and roadmap.py turns the gate into
    "Find a teacher to enter X with you". Dropping gated rows would hide real
    opportunities; mislabelling them is the actual harm."""
    row = decide(CANDIDATE, verdict(entry_gate="teacher"))
    assert row is not None and row["entry_gate"] == "teacher"


def test_the_gate_cannot_rescue_a_row_the_guardrails_reject() -> None:
    """Gate handling runs after the confidence and link checks, not instead."""
    assert decide(CANDIDATE, verdict(entry_gate="teacher", confidence=0.1)) is None
    assert decide(CANDIDATE, verdict(entry_gate="teacher", is_opportunity=False)) is None
    reddit = {**CANDIDATE, "url": "https://www.reddit.com/r/x/comments/y/"}
    assert decide(reddit, verdict(entry_gate="teacher")) is None
