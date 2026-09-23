"""
Route advisor — exploration, grounded in the verified catalog.

The clearpolicy.org pattern: a conversational answer that is only allowed
to lean on sources we can show. The advisor receives the student's
deterministic profile (traits, field shares, goals) plus their actual
matched opportunities as numbered sources, and answers questions like
"what unusual routes fit how I think?" — citing sources by number.

Boundaries, deliberately hard:
- The advisor NEVER produces fit percentages or rankings; that authority
  stays with the explainable engine in app/match.py.
- Every response returns the source list so the UI can render "backed
  by" links; the model is instructed to cite [n] and to say plainly when
  the catalog has nothing relevant.
- No key configured -> 503 and the frontend renders the feature as off.

Provider: any OpenAI-compatible chat API. Production uses NVIDIA NIM's free
tier (LLM_API_BASE / LLM_MODEL / LLM_API_KEY in backend/.env).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

import requests

from .settings import settings

# --- Spend control -------------------------------------------------------
#
# Every model call here costs a credit from a fixed pool, so the ledger and
# the cache are one table (public.advisor_calls): one row per BILLED call,
# no row for a cache hit. That makes count(rows) mean "credits spent".
#
# A cache hit is checked before the budget and never consumes quota — the
# point of the cache is that re-asking a known question is free.

# The provider's free tier allows 40 requests/minute across everything using
# the key, and the nightly verifier shares it. Leave that real headroom.
GLOBAL_PER_MINUTE = 20


def cache_key(question: str, sources: list[dict]) -> str:
    """Same question over the same sources and model -> same answer.

    The sources are part of the key, not just the question: once the catalog
    behind an answer changes, the old answer is stale and deserves a fresh
    call. Whitespace and case are normalized so trivial retypings hit.
    """
    basis = json.dumps(
        {
            "q": " ".join(question.lower().split()),
            "s": [s.get("url") or s.get("title", "") for s in sources],
            "m": settings.llm_model,
        },
        sort_keys=True,
    )
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def _since(**delta: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(**delta)).isoformat()


def cached_answer(sb, key: str) -> dict | None:
    """The newest unexpired answer for this key, or None."""
    rows = (
        sb.table("advisor_calls")
        .select("answer, sources")
        .eq("cache_key", key)
        .gte("created_at", _since(hours=settings.advisor_cache_ttl_h))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    ).data or []
    return rows[0] if rows else None


def _spent(sb, since: str, student: str | None = None) -> int:
    """How many billed calls since `since`, optionally for one student."""
    query = (
        sb.table("advisor_calls")
        .select("id", count="exact", head=True)
        .gte("created_at", since)
    )
    if student is not None:
        query = query.eq("student", student)
    return query.execute().count or 0


def budget_block(sb, student: str) -> str | None:
    """Why this call must be refused, or None to let it through.

    Ordered cheapest-to-explain first, and burst before daily so a spike
    gets "try again in a minute" rather than "come back tomorrow".
    """
    if _spent(sb, _since(minutes=1)) >= GLOBAL_PER_MINUTE:
        return "The advisor is busy right now — try again in a minute."
    if _spent(sb, _since(days=1), student) >= settings.advisor_per_student_daily:
        return (
            f"You have used your {settings.advisor_per_student_daily} advisor "
            "questions for today. This resets 24 hours after your first one."
        )
    if _spent(sb, _since(days=1)) >= settings.advisor_global_daily:
        return "The advisor has reached today's shared limit. Try again tomorrow."
    return None


def record_call(
    sb, student: str, key: str, question: str, answer: str, sources: list[dict]
) -> None:
    """Log a billed call. This row is both the ledger entry and the cache."""
    try:
        sb.table("advisor_calls").insert(
            {
                "student": student,
                "cache_key": key,
                "question": question[:1000],
                "answer": answer,
                "sources": sources,
            }
        ).execute()
    except Exception:
        # Never lose the student an answer we already paid for. The cost is
        # that this call goes uncounted against the quota, which is the
        # cheaper failure next to a 500 on a successful completion.
        pass

SYSTEM_PROMPT = """You are Northstar's route advisor for students. You help them \
explore unusual, interdisciplinary, and non-obvious directions.

Rules you never break:
1. Ground every concrete claim in the numbered sources provided, citing like [2]. \
If the sources do not support an answer, say so plainly and suggest what kind of \
opportunity to look for instead.
2. Never invent programs, deadlines, or statistics. Never state fit percentages \
or predict what the student "will" become — you explore, the matching engine ranks.
3. Speak plainly to a student. Two short paragraphs maximum, then up to three \
cited suggestions as a list.
"""


def advisor_enabled() -> bool:
    return bool(settings.llm_api_key)


def build_sources(matches: list[dict], limit: int = 12) -> list[dict]:
    """Numbered, verifiable source entries from the student's own matches."""
    sources = []
    for entry in matches[:limit]:
        opp = entry.get("opportunity", entry)
        sources.append({
            "n": len(sources) + 1,
            "title": opp.get("title", ""),
            "field": opp.get("field") or opp.get("opportunity_field", ""),
            "type": opp.get("type", ""),
            "deadline": opp.get("deadline"),
            "url": opp.get("url", ""),
        })
    return sources


def ask_advisor(question: str, profile: dict, sources: list[dict]) -> str:
    """One grounded chat completion; raises requests exceptions upward."""
    source_lines = "\n".join(
        f"[{s['n']}] {s['title']} — {s['field']}/{s['type']}"
        + (f", deadline {s['deadline']}" if s.get("deadline") else "")
        for s in sources
    ) or "(no matched opportunities yet)"

    profile_lines = (
        f"Traits (0-100): {profile.get('trait_scores')}\n"
        f"Field interest shares: {profile.get('field_scores')}\n"
        f"Stated interests: {profile.get('interests')}\n"
        f"Goals, in their words: {profile.get('goals') or '(none written)'}"
    )

    response = requests.post(
        f"{settings.llm_api_base}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Student profile:\n{profile_lines}\n\n"
                        f"Verified sources (their matched opportunities):\n{source_lines}\n\n"
                        f"Question: {question[:1000]}"
                    ),
                },
            ],
            "max_tokens": 700,
            "temperature": 0.7,
        },
        timeout=45,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
