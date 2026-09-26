"""
LLM opportunity verifier — screens scraped candidates before they enter
the live catalog, so the daily loop can scrape -> verify -> import
without a human in the hot path.

Design for trust (this replaces a human gate, so it must be strict):
- The model returns a structured verdict, never prose. It decides only
  whether a candidate is a real, current opportunity and extracts clean
  fields — it does NOT invent programs or deadlines.
- decide() is a PURE function (no network) that applies the guardrails:
  is_opportunity, a confidence floor, and a usable external link. Only
  candidates that clear all three auto-promote; everything else stays in
  the pool for scripts/review_candidates.py. This is the safety boundary
  and it is unit-tested.
- Every auto-promoted row is stamped added_by='ai' (migration
  20260816160000) so a bad batch is auditable and one delete away.

Provider: any OpenAI-compatible chat API. NVIDIA NIM is free and works —
set in backend/.env:
    LLM_API_BASE=https://integrate.api.nvidia.com/v1
    LLM_API_KEY=<your NIM key>
    LLM_MODEL=meta/llama-3.3-70b-instruct
Any OpenAI-compatible endpoint works the same way; production uses NVIDIA NIM.
"""

from __future__ import annotations

import json
from urllib.parse import urlparse

from .llm import LLMUnavailable, chat
from .settings import settings

FIELDS = ["cs", "biology", "math", "physics", "engineering",
          "interdisciplinary", "design", "business", "humanities", "health"]
TYPES = ["program", "scholarship", "competition", "mentorship",
         "internship", "volunteer", "journal"]

CONFIDENCE_FLOOR = 0.8

# A bare form or shortened link is not a verifiable organization — it's the
# signature of an unvetted, student-run "opportunity" the model can't judge
# from text. These never auto-import; they drop to human review, where a
# person can confirm the program is real before it reaches minors.
UNVERIFIABLE_HOSTS = (
    "forms.gle",
    "docs.google.com",
    "forms.office.com",
    "bit.ly",
    "tinyurl.com",
    "linktr.ee",
    "notion.site",
)

SYSTEM_PROMPT = """You screen scraped posts to decide whether each is a REAL, \
current opportunity a student could apply to — a program, scholarship, \
competition, internship, or fellowship — as opposed to a discussion, \
question, rant, meme, results thread, or news article.

Return ONLY a JSON object, no prose, with these keys:
  is_opportunity: boolean — true ONLY if a student could actually apply/enter
  title: string — a clean, specific title (not a reddit headline)
  host: string — the organization running it, or "" if unknown
  field: one of cs, biology, math, physics, engineering, interdisciplinary, design, business, humanities, health
  type: one of program, scholarship, competition, mentorship, internship, volunteer, journal
  entry_gate: WHO can start this, one of:
      apply     — a student can enter or apply by themselves, unaided
      qualify   — entry is by exam score or a prior round (you cannot apply directly)
      advance   — you reach it by placing at an affiliated or regional event first
      nominate  — a nomination or recommendation from someone else is required
      teacher   — a teacher, coach or other adult registers the team or applies
  entry_note: string — one short sentence on the FIRST thing a student must do,
      or "" if entry_gate is apply. Only what the text supports.
  confidence: number 0..1 — your confidence it is a real, applyable opportunity
  reason: string — one short sentence

Be strict. If it reads like a discussion or you are unsure it is a real \
applyable opportunity, set is_opportunity false and confidence low. Never \
invent details not supported by the text.

ENTRY_GATE IS NOT A FORMALITY. "Teachers apply for a $10,000 grant for a team \
of students" is entry_gate teacher, not apply: a student who waits for a student \
application form will wait forever. A national olympiad you reach by scoring on \
a qualifying exam is qualify. A science fair you reach by winning a regional is \
advance. If a competition is entered by a school team with an adult coach rather \
than by individuals, that is teacher. Only use apply when an individual student \
can genuinely start it on their own. When the text does not say, use apply and \
lower your confidence."""


# Mirrors the public.entry_gate enum in
# supabase/migrations/20260925140000_entry_gate.sql. A value outside this set
# would be rejected by Postgres and fail the whole import batch, so it is
# validated here rather than discovered at insert time.
ENTRY_GATES = frozenset({"apply", "qualify", "advance", "nominate", "teacher"})


def verifier_enabled() -> bool:
    """Whether the verifier has a provider. Checks ITS key, not the advisor's.

    These are separate credentials now: the scrape can run on Azure while
    /advisor stays on NIM, and vice versa. Reading llm_api_key here would have
    disabled the nightly import on any host that configured only VERIFIER_*.
    """
    _, key, _ = settings.verifier_provider
    return bool(key)


def _external_host(url: str) -> str:
    return urlparse(url or "").netloc.removeprefix("www.").lower()


def decide(candidate: dict, verdict: dict) -> dict | None:
    """Pure guardrail: turn a verdict into an opportunity row, or None.

    Auto-promotes ONLY when the model says it's an opportunity, is
    confident enough, AND the candidate has a usable link that isn't just
    a reddit permalink (a real opportunity lives on its own site; Devpost
    entries are already vetted hackathons and pass on their own domain).
    """
    if not verdict.get("is_opportunity"):
        return None
    try:
        confidence = float(verdict.get("confidence", 0))
    except (TypeError, ValueError):
        return None
    if confidence < CONFIDENCE_FLOOR:
        return None

    url = candidate.get("url", "")
    host = _external_host(url)
    is_reddit = host.endswith("reddit.com") or not host
    is_devpost = candidate.get("source") == "devpost"
    if is_reddit and not is_devpost:
        # No real destination to send a student to — leave for a human.
        return None
    if any(host == h or host.endswith("." + h) for h in UNVERIFIABLE_HOSTS):
        # A form/shortener alone can't establish the program is real.
        return None

    field = verdict.get("field")
    if field not in FIELDS:
        field = candidate.get("field_guess", "interdisciplinary")
    opp_type = verdict.get("type")
    if opp_type not in TYPES:
        opp_type = candidate.get("type_guess", "program")

    # ENTRY GATE. Twenty-two catalog rows were corrected by hand because they
    # carried an application deadline for something a student cannot apply to:
    # you qualify for USAMO by exam score, you advance to ISEF from a regional
    # fair, and a TEACHER applies for a Lemelson-MIT InvenTeam grant. app/
    # roadmap.py reads this column to pick the step verb, so without it the plan
    # says "Apply to USAMO" — a step no student can take, in the one place this
    # product promises to say what to do next.
    #
    # The verifier had no notion of it, so every AI-imported row took the column
    # default. Tested against Azure gpt-5.6, it accepted the Lemelson grant as a
    # student opportunity at 0.98 confidence — so the scraper could quietly
    # reintroduce the whole class of defect the hand corrections removed.
    #
    # An unrecognised or missing value falls back to "apply", which is both the
    # column default and the common case. That is a deliberate floor, not a
    # guess: the prompt tells the model to lower its confidence when the text
    # does not say, and CONFIDENCE_FLOOR then keeps the unclear ones out.
    gate = str(verdict.get("entry_gate") or "").strip().lower()
    if gate not in ENTRY_GATES:
        gate = "apply"
    note = str(verdict.get("entry_note") or "").strip()[:300]

    title = (verdict.get("title") or candidate.get("title") or "").strip()[:200]
    if not title:
        return None

    return {
        "title": title,
        "host": (verdict.get("host") or host or "Community-sourced")[:200],
        "opportunity_field": field,
        "type": opp_type,
        "blurb": (candidate.get("blurb") or title)[:400],
        "description": candidate.get("blurb", ""),
        "deadline": candidate.get("deadline_guess"),
        "cost": 0,
        "entry_gate": gate,
        # Only stored when it says something. An empty note would displace the
        # generic per-gate wording in roadmap.py, which is better than nothing.
        **({"entry_note": note} if note and gate != "apply" else {}),
        "url": url,
        "audience": candidate.get("audience_guess", "high_school"),
        "location_scope": candidate.get("location_guess", "us"),
        "tags": [],
        "added_by": "ai",
    }


def verify_candidate(candidate: dict, retries: int = 2) -> dict:
    """One LLM verdict for a candidate. Raises on network/parse failure.

    Retries on read timeouts — free hosted tiers (NIM) cold-start slowly,
    so a single timeout shouldn't drop an otherwise-fine candidate.
    """
    text = f"Title: {candidate.get('title', '')}\n\n{candidate.get('blurb', '')[:1500]}"
    base, key, model = settings.verifier_provider
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            content = chat(
                base=base,
                key=key,
                model=model,
                messages=messages,
                # Generous on purpose. Reasoning models emit their thinking
                # before the JSON object, so a 300-token ceiling truncated the
                # reply mid-string and every retry truncated it identically at
                # temperature 0 — a deterministic failure that looked flaky. The
                # verdict itself is ~80 tokens.
                max_tokens=1200,
                # DETERMINISM IS BEST-EFFORT, NOT GUARANTEED. NIM honours
                # temperature 0; Azure gpt-5.6 refuses any value but its default
                # of 1 ("Unsupported value: 'temperature' does not support 0.0"),
                # so app/llm.py drops the parameter for that provider. On Azure
                # the same candidate can therefore get different verdicts on
                # different runs. Acceptable here — decide() re-checks every
                # verdict against hard guardrails (confidence floor, usable link,
                # non-reddit host), so a wobbly verdict cannot import anything
                # the rules would reject. It does mean the JSON-truncation retry
                # below is now genuinely a retry rather than a repeat.
                temperature=0.0,
                # Verified working on Azure gpt-5.6 and on NIM. Notably NOT
                # supported by DeepSeek-R1, which is why that plan was dropped.
                response_format={"type": "json_object"},
                timeout=90,
            )

            # Some models wrap JSON in prose or fences despite instructions.
            start, end = content.find("{"), content.rfind("}")
            if start >= 0 and end > start:
                content = content[start : end + 1]
            try:
                return json.loads(content)
            except json.JSONDecodeError as error:
                # Retry rather than discard: at temperature 0 this is usually a
                # truncated reply, and the next attempt tends to complete.
                last_error = error
                continue
        except LLMUnavailable as error:
            last_error = error
            continue

    raise last_error if last_error else RuntimeError("verify failed")
