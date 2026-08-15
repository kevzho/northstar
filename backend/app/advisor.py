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

Provider: any OpenAI-compatible chat API. Defaults target DeepSeek
(LLM_API_BASE / LLM_MODEL / LLM_API_KEY in backend/.env).
"""

from __future__ import annotations

import requests

from .settings import settings

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
