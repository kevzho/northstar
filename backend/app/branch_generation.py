"""
Break one step of a plan into the two or three moves that make it up.

WHY. The roadmap tells a student to "Build a simple web app that lets a local
business calculate break-even". For someone who has never shipped anything that
is one instruction with a cliff in the middle. Until now the plan could only be
accepted or regenerated whole -- there was nothing between "this is my path"
and "write me a different path".

A branch is that middle. Point at any step, get the moves inside it, written
from the same profile and the same matched opportunities as the step itself.

WHAT THE MODEL MAY NOT DO, enforced here rather than asked for in the prompt:

    write a url          a model-supplied link is an unverified one wearing
                         the styling of the catalog's verified ones. The learn
                         rungs link to resources this project checked; a branch
                         step does not get to look like that.
    name a programme     the plan's application steps come from the student's
                         ranked matches and carry an opportunity_id. A branch
                         inventing "apply to X" would put an unverified
                         programme inside a plan whose whole claim is that it
                         does not do that.
    pad the list         one step is not a breakdown and six is a new plan.
    write an essay       this renders inside a node on a diagram.

Pure functions and one chat call. Same shape as spine_generation, and
deliberately the same refusal stance: returning None is a success path, because
the step the student already had is better than a bad decomposition of it.
"""

from __future__ import annotations

import json
import re

MIN_STEPS = 2
MAX_STEPS = 3
MAX_TITLE = 90
MAX_DETAIL = 220

URL_PATTERN = re.compile(r"https?://|www\.|\b[a-z0-9-]+\.(com|org|net|io|edu|gov)\b", re.I)

SYSTEM_PROMPT = """You break ONE step of a high-school student's plan into the smaller moves it is made of.

Reply with JSON only:
{"steps": [{"title": "...", "detail": "..."}, ...]}

Rules:
- Exactly 2 or 3 steps. Each one is a thing the student does, in order.
- `title` is an imperative under 90 characters: "Sketch the three screens on paper".
- `detail` is one sentence under 220 characters saying what done looks like.
- These are the INSIDE of the step you were given. Do not restate it, do not go
  past it, and do not invent a new direction.
- NEVER write a url, a domain, or a tool's website. Name a tool if it helps.
- NEVER tell them to apply to a named programme, competition or scholarship.
  Applications come from their verified matches, not from you.
- Concrete beats encouraging. No "explore", no "consider", no "dive into".
"""


def build_prompt(step_title: str, step_category: str, student: dict, reason: str = "") -> str:
    traits = student.get("trait_scores") or {}
    trait_line = ", ".join(
        f"{name} {round(float(score))}"
        for name, score in sorted(traits.items(), key=lambda kv: -float(kv[1] or 0))[:4]
    ) or "not assessed"
    fields = student.get("field_scores") or {}
    field_line = ", ".join(
        name for name, _ in sorted(fields.items(), key=lambda kv: -float(kv[1] or 0))[:3]
    ) or "not stated"

    lines = [
        f"The step to break down ({step_category}): {step_title}",
        "",
        f"Grade: {student.get('grade') or 'unknown'}",
        f"Traits, highest first, each out of 100: {trait_line}",
        f"Fields they lean toward: {field_line}",
    ]
    if reason.strip():
        lines += ["", f"What they said they are stuck on: {reason.strip()[:300]}"]
    return "\n".join(lines)


def parse_branch(raw: str) -> list[dict] | None:
    """A model reply -> 2-3 clean sub-steps, or None to leave the plan alone."""
    text = (raw or "").strip()
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

    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list):
        return None

    out: list[dict] = []
    for item in raw_steps:
        if not isinstance(item, dict):
            return None
        title = str(item.get("title") or "").strip()
        detail = str(item.get("detail") or "").strip()
        if not title or not detail:
            return None
        if len(title) > MAX_TITLE or len(detail) > MAX_DETAIL:
            return None
        # A link here would sit in a plan whose learn rungs link only to
        # resources this project opened and read.
        if URL_PATTERN.search(title) or URL_PATTERN.search(detail):
            return None
        out.append({"title": title, "detail": detail})

    if not (MIN_STEPS <= len(out) <= MAX_STEPS):
        return None
    # Two identical moves is not a breakdown.
    if len({s["title"].lower() for s in out}) != len(out):
        return None
    return out
