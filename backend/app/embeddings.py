"""
Embedding client for semantic matching.

app/match.py scores lexically, which cannot connect "I want to help people with
cancer" to "Stanford Institutes of Medicine Summer Research", no shared tokens.
Measured on the live catalog, TF-IDF pins every row after the first at the
booster floor of 0.050, i.e. no signal at all. Embeddings surface the medicine
programme TF-IDF never reaches.

WHAT THIS IS NOT. Not a replacement for the deterministic engine. The semantic
term is one capped booster among seven, so every score still decomposes into
named reasons, which is the product's whole position on explainability, and a
score a student cannot interrogate only helps someone who already has an adult
to interpret it.

MODEL. nvidia/nemotron-3-embed-1b on NVIDIA NIM's free tier, on the same key the
verifier uses. Four other NIM embedding models return 404 for this account
(nv-embedqa-mistral-7b-v2, arctic-embed-l, embed-qa-4, llama-3.2-nv-embedqa-1b),
so this is not a preference. It returns 2048 dimensions and refuses any other
size: "dimensions must be one of 2048".

ASYMMETRY MATTERS. This model distinguishes queries from passages. A student
profile is a QUERY; an opportunity is a PASSAGE. Embedding both the same way
measurably degrades retrieval, so the two helpers below are separate rather than
one function with a flag nobody remembers to set.

COST. Opportunities are embedded once, on the nightly cron, only where the
column is NULL, about 60 calls on the day the catalog grows by 60, and 2 on a
normal day. A student profile is embedded when it changes. Request time makes no
API call at all: the similarity is a Postgres function (semantic_scores).
"""

from __future__ import annotations

import requests

from .settings import settings

MODEL = "nvidia/nemotron-3-embed-1b"
DIMENSIONS = 2048

# The provider batches, but a large batch is one slow request that a timeout
# then discards entirely. 32 keeps a retry cheap.
BATCH = 32
TIMEOUT_S = 90
RETRIES = 2


class EmbeddingUnavailable(RuntimeError):
    """The provider could not be reached, or returned an unusable response.

    Raised rather than returning a zero vector: a zero vector would be silently
    equidistant from everything and would quietly poison ranking, which is the
    failure mode this codebase has already paid for once.
    """


def enabled() -> bool:
    return bool(settings.llm_api_key)


def _post(texts: list[str], input_type: str) -> list[list[float]]:
    last: Exception | None = None
    for _ in range(RETRIES + 1):
        try:
            response = requests.post(
                f"{settings.llm_api_base.rstrip('/')}/embeddings",
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "input": texts,
                    "input_type": input_type,
                    "encoding_format": "float",
                },
                timeout=TIMEOUT_S,
            )
            response.raise_for_status()
            rows = response.json().get("data") or []
            vectors = [row.get("embedding") for row in rows]
            if len(vectors) != len(texts) or any(
                not v or len(v) != DIMENSIONS for v in vectors
            ):
                raise EmbeddingUnavailable(
                    f"expected {len(texts)} vectors of {DIMENSIONS} dims, "
                    f"got {[len(v) if v else 0 for v in vectors]}"
                )
            return vectors  # type: ignore[return-value]
        except (requests.Timeout, requests.ConnectionError) as error:
            last = error
            continue
        except requests.HTTPError as error:
            # A 4xx will not improve on retry; a 5xx might.
            status = error.response.status_code if error.response is not None else 0
            if 400 <= status < 500:
                raise EmbeddingUnavailable(
                    f"HTTP {status}: {error.response.text[:200] if error.response else ''}"
                ) from error
            last = error
            continue
    raise EmbeddingUnavailable(str(last) if last else "embedding request failed")


def embed_passages(texts: list[str]) -> list[list[float]]:
    """Embed opportunity documents. Batched; order is preserved."""
    out: list[list[float]] = []
    for start in range(0, len(texts), BATCH):
        out.extend(_post(texts[start : start + BATCH], "passage"))
    return out


def embed_query(text: str) -> list[float]:
    """Embed one student profile."""
    return _post([text], "query")[0]


def opportunity_document(opp: dict) -> str:
    """What gets embedded for an opportunity.

    Title plus blurb only. `description` is excluded deliberately: many rows
    carry a scraped 220-character excerpt of someone else's Reddit post there,
    which says more about the poster than the programme.
    """
    parts = [
        (opp.get("title") or "").strip(),
        (opp.get("blurb") or "").strip(),
        (opp.get("opportunity_field") or "").strip(),
        (opp.get("type") or "").strip(),
    ]
    return ". ".join(p for p in parts if p)[:2000]


def student_query(student: dict) -> str:
    """What gets embedded for a student.

    Their own words first. `goals` is free text the student wrote and is the
    only part of the profile that can express "help people with cancer";
    interests are a fixed vocabulary of ten options and cannot.
    """
    goals = (student.get("goals") or "").strip()
    interests = ", ".join(str(i) for i in (student.get("interests") or []))
    parts = [goals, f"Interested in: {interests}" if interests else ""]
    return ". ".join(p for p in parts if p)[:2000]


def semantic_scores(sb, student_id: str) -> dict[str, float]:
    """Cosine similarity per opportunity, computed in Postgres.

    Calls public.semantic_scores(), which keeps the 2048-float vectors in the
    database and returns one float per row. Returns {} when the student has no
    profile embedding, when nothing is embedded yet, or on any error, and
    scoring then falls back to exactly the lexical behaviour that shipped
    before embeddings existed.
    """
    try:
        rows = sb.rpc("semantic_scores", {"p_student": student_id}).execute().data or []
    except Exception:
        return {}
    out: dict[str, float] = {}
    for row in rows:
        oid, sim = row.get("opportunity_id"), row.get("similarity")
        if oid is not None and isinstance(sim, (int, float)):
            out[oid] = float(sim)
    return out


def refresh_student_embedding(sb, student_id: str, student: dict) -> bool:
    """Re-embed a student profile after it changes. Best effort.

    Called from the routes that alter a scoring input, the profile itself and
    the assessment sync. One call per edit, not per request: three students
    today means roughly three calls a week.

    Never raises. A stale or missing profile embedding costs precision in
    ranking; a 500 on saving a profile costs the student their onboarding.
    """
    from datetime import datetime, timezone

    if not enabled():
        return False
    text = student_query(student)
    if not text.strip():
        return False
    try:
        vector = embed_query(text)
    except EmbeddingUnavailable:
        return False
    try:
        sb.table("students").update({
            "profile_embedding": vector,
            "profile_embedded_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", student_id).execute()
        return True
    except Exception:
        return False
