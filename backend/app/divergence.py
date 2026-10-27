"""
Other directions out of the same step.

What this is not. app/branch_generation.py goes INWARD: it takes "build a
web app that calculates break-even" and returns the moves inside it. This goes
SIDEWAYS. From the same point in the plan, what else could this student do
instead? Not a smaller piece of the step, and not the next step after it, but
a different thing to make with the same skill and the same hour.

Why a plan needs it. A generated path is one route, written once, from a
twenty-question profile. It is a guess. A student who reads it and thinks
"that is not quite me" previously had two options: accept it, or regenerate
the whole thing and lose the parts that were right. Divergence is the third:
keep the path, and ask what else this particular step could have been.

What the model may not do, enforced here rather than requested in the prompt:

    decompose           "sketch the screens" is a sub-step, not an
                        alternative. If it only makes sense AFTER the step it
                        came from, it is a breakdown and belongs in the other
                        module.
    write a url         a model-supplied link is an unverified one wearing the
                        styling of the catalog's verified ones.
    name a programme    application steps come from the student's ranked
                        matches and carry an opportunity_id. An invented
                        "apply to X" would put an unverified programme in a
                        plan whose whole claim is that it does not do that.
    drift               an alternative to a statistics project is another
                        statistics project, not "learn the guitar". Same
                        skill, same field, different artefact.

A divergence is drawn as a dotted edge, the weakest one the tree has, because
nothing here is required and nobody has measured that students take it. It is
an option, and it is labelled as one.
"""

from __future__ import annotations

import json
import re

MIN_PATHS = 2
MAX_PATHS = 3
MAX_TITLE = 90
MAX_DETAIL = 220

URL_PATTERN = re.compile(r"https?://|www\.|\b[a-z0-9-]+\.(com|org|net|io|edu|gov)\b", re.I)

# Openers that mean the model wrote a sub-step instead of an alternative.
# "First, sketch the screens" is a breakdown however it is dressed up.
SEQUENCING = re.compile(
    r"^\s*(first|then|next|after that|finally|start by|begin by|once you)\b", re.I
)

SYSTEM_PROMPT = """You suggest OTHER DIRECTIONS a high-school student could take from one step of their plan.

Reply with JSON only:
{"paths": [{"title": "...", "detail": "..."}, ...]}

Rules:
- Exactly 2 or 3. Each is a DIFFERENT thing the student could make or do
  INSTEAD of the step you were given, from the same point in their plan.
- NOT smaller pieces of that step. If your suggestion only makes sense after
  doing the original step, it is wrong. "Sketch the screens" is wrong.
- NOT the next step either. Do not continue the plan, fork it.
- Same skill and same field as the original. An alternative to a statistics
  project is a different statistics project, not a different subject.
- `title` is an imperative under 90 characters, and reads as a real
  alternative: "Build a shift scheduler for the same business".
- `detail` is one sentence under 220 characters saying what makes this a
  different direction and who it suits.
- NEVER write a url, a domain, or a tool's website. Name a tool if it helps.
- NEVER tell them to apply to a named programme, competition or scholarship.
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
        f"The step they want alternatives to ({step_category}): {step_title}",
        "",
        f"Grade: {student.get('grade') or 'unknown'}",
        f"Traits, highest first, each out of 100: {trait_line}",
        f"Fields they lean toward: {field_line}",
        "",
        "Give other things they could make from this same point, not the "
        "pieces of the step above and not what comes after it.",
    ]
    if reason.strip():
        lines += ["", f"Why the current step does not fit: {reason.strip()[:300]}"]
    return "\n".join(lines)


def parse_divergence(raw: str) -> list[dict] | None:
    """A model reply -> 2-3 clean alternatives, or None to leave the plan alone.

    Returning None is a success path, same as the breakdown parser: the step
    the student already has beats a bad alternative to it.
    """
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

    raw_paths = data.get("paths")
    if not isinstance(raw_paths, list):
        return None

    out: list[dict] = []
    for item in raw_paths:
        if not isinstance(item, dict):
            return None
        title = str(item.get("title") or "").strip()
        detail = str(item.get("detail") or "").strip()
        if not title or not detail:
            return None
        if len(title) > MAX_TITLE or len(detail) > MAX_DETAIL:
            return None
        if URL_PATTERN.search(title) or URL_PATTERN.search(detail):
            return None
        # A sequenced opener means it wrote a breakdown, which the other
        # module already does properly.
        if SEQUENCING.match(title):
            return None
        out.append({"title": title, "detail": detail})

    if not (MIN_PATHS <= len(out) <= MAX_PATHS):
        return None
    if len({p["title"].lower() for p in out}) != len(out):
        return None
    return out
