"""
Write one student's spine instead of assigning them one of twenty-four.

WHAT A SPINE IS. app/roadmap.py sequences learn -> build -> publish -> apply.
The middle three rungs come from a "spine": a starter project, a way to publish
it, and a skill to sprint on. Until now a spine was looked up by archetype in
frontend/lib/plan.ts -- twenty-four of them, hand-written, one per archetype.

WHY CHANGE IT. Two measured problems.

    1. Twenty-four buckets is not a plan, it is a genre. Two students who both
       land on "applied-ai-builder" get the same sentence about a study-note
       summariser whether they are a ninth grader who has never shipped anything
       or a twelfth grader with three projects and a biology obsession.

    2. Half of them are hollow. Each spine names a skillKey that joins to
       public.learning_resources, and on 2026-10-04 twelve of the twenty-four
       pointed at a key with NO resource behind it -- argument-mapping,
       playtesting, public-records, causal-inference and nine more. Those
       students' roadmaps render the learn rung as nothing at all, silently.

WHAT THE MODEL DECIDES, AND WHAT IT MAY NOT. It writes the project and the
publish step, in the student's own context: their traits, their grade, their
field, and the opportunities actually matched to them. It does NOT invent the
skill rung. It CHOOSES one from the keys that currently have verified resources,
because a rung with nothing behind it is the bug above, not a feature. The list
is read from the database at call time rather than hardcoded, so adding
resources widens the model's choices without touching this file.

Three things are rejected outright, because each is a way for a generated plan
to make a claim the catalog has not earned:

    a url            the learn rung links to curated, verified resources; a
                     model-supplied link is an unverified one wearing the same
                     styling.
    an unknown key   it would render an empty learn rung -- the exact defect
                     this is meant to fix.
    empty prose      a blank project step is worse than the authored fallback.

On any rejection the caller falls back to the authored spine. A student always
has a plan; what varies is whether it was written for them.

PROVENANCE IS NOT COSMETIC. roadmap.py already separates edges that are computed
calendar facts from edges that are authored generalisations, and the UI words
the second kind as "a common route, not a requirement". A generated spine is a
third thing, and calling it "a common route" would be false: no human wrote it
and no outcome data supports it. It carries source="generated" so the UI can say
what it actually is.
"""

from __future__ import annotations

import json
import re

# Caps, not style preferences: this text renders inside a roadmap step, and a
# 600-word "project" is a wall a student scrolls past.
MAX_PROJECT = 400
MAX_PUBLISH = 300
MAX_SKILL = 200

URL_PATTERN = re.compile(r"https?://|www\.", re.I)

SYSTEM_PROMPT = """You plan a single high-school student's next three months.

You will be given one student and the opportunities already matched to them.
Write three things:

  project  One concrete thing they could build or do in 2-4 weeks, starting from
           what they have now. Specific to THIS student: their traits, their
           grade, their field. Not a genre of project.
  publish  One way to put that work where someone else can see it. Concrete.
And choose one skill_key from the allowed list: the one whose resources would
most help this student do the project you just wrote.

Do not write the skill sentence. It is supplied by the catalog, from the key you
pick.

Rules:
- Never include a URL, a link, or a programme name that is not in the matches
  you were given.
- Never promise an outcome ("this will get you into..."). Describe the work.
- A 9th grader with no projects and a 12th grader with three get different
  plans. Use the grade and the trait scores.
- Plain language. No jargon, no exclamation marks, no "leverage" or "journey".

Reply with JSON only:
{"project": "...", "publish": "...", "skill_key": "..."}"""


def build_prompt(student: dict, matches: list[dict], skill_keys: list[dict]) -> str:
    """The user half of the request. Only data the catalog already holds."""
    traits = student.get("trait_scores") or {}
    trait_line = ", ".join(
        f"{name} {round(float(score) * 100)}%" for name, score in sorted(
            traits.items(), key=lambda kv: -float(kv[1] or 0)
        )[:6]
    ) or "not assessed"
    fields = student.get("field_scores") or {}
    field_line = ", ".join(
        name for name, _ in sorted(fields.items(), key=lambda kv: -float(kv[1] or 0))[:3]
    ) or "not stated"

    lines = [
        f"Grade: {student.get('grade') or 'unknown'}",
        f"Archetype they landed on: {student.get('chosen_archetype') or 'none'}",
        f"Traits (highest first): {trait_line}",
        f"Fields they lean toward: {field_line}",
        "",
        "Opportunities already matched to them (the only programmes you may name):",
    ]
    for match in matches[:8]:
        when = match.get("deadline") or "rolling"
        lines.append(
            f"  - {match.get('title', '')[:90]} "
            f"[{match.get('opportunity_field', '')}, closes {when}]"
        )
    if not matches:
        lines.append("  (none yet — write a project that needs no programme)")

    lines += ["", "Allowed skill_key values, with what each teaches:"]
    for row in skill_keys:
        lines.append(f"  - {row['skill_key']}: {str(row.get('skill_label') or '')[:110]}")
    return "\n".join(lines)


def parse_spine(raw: str, skill_labels: dict[str, str]) -> dict | None:
    """A model reply -> a usable spine, or None to fall back.

    Every rejection here is a case where the authored spine is better than what
    came back, so returning None is a success path, not an error path.

    THE SKILL SENTENCE IS NOT THE MODEL'S TO WRITE. It comes from
    learning_resources.skill_label for the key the model picked. The first
    version let the model phrase it, and a test student got the sentence
    "Rigor — a bioethics case file is only as strong as its sources" attached to
    the key `regulatory-literacy`: roadmap.py would have printed that sentence
    and then linked four resources about something else. The label is already
    human-written and already matches the resources, so taking it from there
    removes the whole class of mismatch rather than trying to detect it.
    """
    text = (raw or "").strip()
    # Models wrap JSON in prose or fences often enough to be worth handling.
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        text = fenced.group(1)
    else:
        braces = re.search(r"\{.*\}", text, re.S)
        if braces:
            text = braces.group(0)
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None

    project = str(data.get("project") or "").strip()[:MAX_PROJECT]
    publish = str(data.get("publish") or "").strip()[:MAX_PUBLISH]
    key = str(data.get("skill_key") or "").strip()

    if not project or not publish:
        return None
    # A key with nothing behind it renders an empty learn rung, which is the
    # defect this module exists to fix.
    if key not in skill_labels:
        return None
    skill = str(skill_labels[key] or "").strip()[:MAX_SKILL]
    if not skill:
        return None
    # The learn rung links to curated, verified resources. A model-supplied link
    # would sit in the same styling with none of that behind it.
    if any(URL_PATTERN.search(part) for part in (project, publish)):
        return None

    return {
        "project": project,
        "publish": publish,
        "skill": skill,
        "skillKey": key,
        # Not cosmetic. roadmap.py words authored edges as "a common route",
        # which would be a lie about a sentence no human wrote.
        "source": "generated",
    }
