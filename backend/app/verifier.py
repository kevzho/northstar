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

import requests

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
  confidence: number 0..1 — your confidence it is a real, applyable opportunity
  reason: string — one short sentence

Be strict. If it reads like a discussion or you are unsure it is a real \
applyable opportunity, set is_opportunity false and confidence low. Never \
invent details not supported by the text."""


def verifier_enabled() -> bool:
    return bool(settings.llm_api_key)


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
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        # Generous on purpose. The production model (openai/gpt-oss-20b) is a
        # reasoning model: it emits its thinking before the JSON object, so a
        # 300-token ceiling truncated the reply mid-string and every retry
        # truncated it identically at temperature 0 — a deterministic failure
        # that looked like a flaky one. The verdict itself is ~80 tokens.
        "max_tokens": 1200,
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = requests.post(
                f"{settings.llm_api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=90,
            )
            response.raise_for_status()
            message = response.json()["choices"][0]["message"]

            # `content` can be null. Reasoning models (openai/gpt-oss-20b, the
            # current production model) sometimes put the answer in
            # `reasoning_content` and leave `content` None — which used to
            # raise AttributeError: 'NoneType' has no attribute 'find' here,
            # burning the candidate as an error rather than reading the reply
            # that was sitting in the next field.
            content = message.get("content") or message.get("reasoning_content") or ""
            if not content.strip():
                last_error = ValueError("model returned an empty message")
                continue

            # Some models wrap JSON in prose or fences despite instructions.
            start, end = content.find("{"), content.rfind("}")
            if start >= 0 and end > start:
                content = content[start : end + 1]
            try:
                return json.loads(content)
            except json.JSONDecodeError as error:
                # Retry rather than discard: at temperature 0 this is usually
                # a truncated reply, and the next attempt tends to complete.
                last_error = error
                continue
        except (requests.Timeout, requests.ConnectionError) as error:
            last_error = error
            continue
    raise last_error if last_error else RuntimeError("verify failed")
