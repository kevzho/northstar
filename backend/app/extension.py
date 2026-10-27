"""
What comes after. The third direction out of a step.

The three moves, and why they are not the same question:

    break down   app/branch_generation.py   INWARD.   The moves inside this
                                                      step. "Sketch the
                                                      screens."
    diverge      app/divergence.py          SIDEWAYS. Instead of this step.
                                                      "Or build a scheduler."
    extend       here                       FORWARD.  After this. "Now put it
                                                      in front of three owners
                                                      and fix what breaks."

Two scopes, one prompt family.

    scope="branch"  Continue a breakdown. The student has three moves under
                    "build the calculator" and has run out before the thing is
                    actually finished. Appends to that list rather than
                    replacing it, because the moves already there may be done.

    scope="path"    Continue the whole plan. A roadmap ends at its application
                    steps, and a student who has shipped and applied gets
                    nothing further. This writes the next lap: harder version,
                    same direction.

WHAT IT MAY NOT DO, enforced rather than requested:

    restate         "finish the app" after "build the app" is not a next move.
    decompose       smaller pieces of the last step belong in a breakdown.
    fork            an alternative belongs in a divergence. This continues.
    write a url     an unverified link wearing the catalog's styling.
    name a programme application steps carry an opportunity_id from the
                    student's own matches. This one would not.

Growth is bounded. A list that can always take two more is an outline that
grows until nobody reads it, which is the thing the one-row-per-step design
exists to prevent.
"""

from __future__ import annotations

import json
import re

MIN_STEPS = 1
MAX_STEPS = 2
#: Hard ceiling on a single list after any number of extensions.
MAX_TOTAL = 6
MAX_TITLE = 90
MAX_DETAIL = 220

URL_PATTERN = re.compile(r"https?://|www\.|\b[a-z0-9-]+\.(com|org|net|io|edu|gov)\b", re.I)

#: An opener that means it wrote an alternative, not a continuation.
FORKING = re.compile(r"^\s*(or\b|alternatively|instead|rather than|you could also)", re.I)

SYSTEM_PROMPT = """You say what a high-school student does NEXT, after the work they have already planned.

Reply with JSON only:
{"steps": [{"title": "...", "detail": "..."}, ...]}

Rules:
- Exactly 1 or 2 steps. They come AFTER everything you were shown, in order.
- FORWARD only. Not a smaller piece of the last step, and not an alternative
  to it. If your step could be done before the ones you were shown, it is
  wrong.
- Harder than what came before, and in the same direction. The student has
  done that work; do not send them back to it.
- `title` is an imperative under 90 characters: "Put it in front of three
  owners and fix what breaks".
- `detail` is one sentence under 220 characters saying what done looks like.
- NEVER write a url, a domain, or a tool's website. Name a tool if it helps.
- NEVER tell them to apply to a named programme, competition or scholarship.
- Concrete beats encouraging. No "explore", no "consider", no "keep going".
"""


def build_prompt(
    anchor: str,
    done: list[dict],
    student: dict,
    scope: str = "branch",
    reason: str = "",
) -> str:
    """``anchor`` is the step being continued, or the plan's own direction."""
    traits = student.get("trait_scores") or {}
    trait_line = ", ".join(
        f"{name} {round(float(score))}"
        for name, score in sorted(traits.items(), key=lambda kv: -float(kv[1] or 0))[:4]
    ) or "not assessed"
    fields = student.get("field_scores") or {}
    field_line = ", ".join(
        name for name, _ in sorted(fields.items(), key=lambda kv: -float(kv[1] or 0))[:3]
    ) or "not stated"

    header = (
        f"The step being continued: {anchor}"
        if scope == "branch"
        else f"The plan being continued: {anchor}"
    )
    lines = [header, "", "Already planned, in order:"]
    lines += [f"  {i}. {s.get('title', '')}" for i, s in enumerate(done, 1)] or ["  (nothing yet)"]
    lines += [
        "",
        f"Grade: {student.get('grade') or 'unknown'}",
        f"Traits, highest first, each out of 100: {trait_line}",
        f"Fields they lean toward: {field_line}",
        "",
        "Say what they do after the last one. Do not repeat or re-cut any of "
        "the work above.",
    ]
    if reason.strip():
        lines += ["", f"What they said about where they are: {reason.strip()[:300]}"]
    return "\n".join(lines)


def parse_extension(raw: str, existing: list[dict] | None = None) -> list[dict] | None:
    """A model reply -> 1-2 clean next moves, or None to leave the plan alone.

    ``existing`` is what the list already holds, so a model that restates a
    move already planned is refused rather than appended.
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

    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list):
        return None

    seen = {str(s.get("title", "")).strip().lower() for s in (existing or [])}
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
        if URL_PATTERN.search(title) or URL_PATTERN.search(detail):
            return None
        if FORKING.match(title):
            return None
        # Already planned. Appending it would tell the student to do a thing
        # they are looking at two lines above.
        if title.lower() in seen:
            return None
        seen.add(title.lower())
        out.append({"title": title, "detail": detail})

    if not (MIN_STEPS <= len(out) <= MAX_STEPS):
        return None
    if len({s["title"].lower() for s in out}) != len(out):
        return None
    return out


def room_left(existing: list[dict] | None) -> int:
    """How many more moves this list may take before it stops being a list."""
    return max(0, MAX_TOTAL - len(existing or []))
