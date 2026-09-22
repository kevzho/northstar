"""
Hermes-wired endpoint plumbing for the TF-IDF match engine. The scoring
design itself is owned by the student (ARCHITECTURE.md §2). This module
turns a student profile + catalog of opportunities into a ranked list of
MatchResult rows with scores and a human-readable explanation.

Design summary (selected by the student, see chat):
  1.  Build a text corpus: each opportunity is a "document" of
      title + blurb + description + tags + field + type.
      The student profile becomes a "query" of interests + goals.
  2.  Compute cosine similarity between the student profile vector and
      each opportunity vector using TF-IDF weighting.
  3.  Apply boosters (small additive, capped at 1.0). All six, in the
      order they are computed -- this list is the contract the /match
      explanation strings are generated from, so keep it in step with
      the code below:
      - FIELD. Two modes. With assessment field_scores the term SCALES
        with the student's interest share in that field:
        ``0.25 * share/100`` (at most +0.25). Without field_scores it
        falls back to a flat +0.15 on a keyword match.
      - BOOKMARKS. +0.02 per opportunity already bookmarked in the same
        field, capped at +0.06.
      - LOCATION. +0.05 when the student stated a location preference and
        the opportunity's scope matches it or is global.
      - GRADE. +0.10 when the student's grade is in ``[grade_min, grade_max]``
      - TAGS. +0.10 for tag overlap (intersection of tags)
      - COST. +0.05 for free opportunities (cost == 0)
  4.  ``score = clip(0.5*tfidf + boosters + collab, 0, 1)`` where
      ``collab`` is a small centered collaborative term from app/collab.py
      (ALS over logged outcomes): ``COLLAB_WEIGHT * (cf - 0.5)`` for
      students who have logged outcomes, at most ±0.075. No outcomes or
      no trained model → the term is exactly zero.
  5.  Generate a one-line ``explanation`` from the boosters that fired.

Pure stdlib, no external NLP deps. ``math`` and ``collections`` only.
"""

import math
import re
from collections import Counter
from typing import Iterable

from .collab import COLLAB_WEIGHT, collaborative_scores

# Field-keyword mapping (student interest strings → opportunity_field enum)
INTEREST_TO_FIELD = {
    "computer science": "cs",
    "cs": "cs",
    "biology": "biology",
    "biotech": "biology",
    "biotechnology": "biology",
    "mathematics": "math",
    "math": "math",
    "physics": "physics",
    "engineering": "engineering",
    "interdisciplinary": "interdisciplinary",
    "stem": "interdisciplinary",
    "research": "interdisciplinary",
    # The four fields added by 20260815170000_expand_fields.sql. That
    # migration's comment says "the frontend quiz, matcher, and scraper all
    # learn them in the same change set" -- the quiz and the enum did, this
    # table did not. Until now a student who picked Design or Business could
    # never earn the field booster, and their explanation never said the
    # field matched, for the opportunities carrying exactly those fields.
    "design": "design",
    "art": "design",
    "graphic design": "design",
    "ux": "design",
    "architecture": "design",
    "business": "business",
    "entrepreneurship": "business",
    "finance": "business",
    "economics": "business",
    "marketing": "business",
    "humanities": "humanities",
    "writing": "humanities",
    "history": "humanities",
    "philosophy": "humanities",
    "communication": "humanities",
    "journalism": "humanities",
    "policy": "humanities",
    "health": "health",
    "medicine": "health",
    "public health": "health",
    "nursing": "health",
    "neuroscience": "health",
}

# Tiny stopword set — keeps the engine small and predictable.
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "in", "is", "it", "of", "on", "or", "that", "the", "to", "via", "with",
    "this", "these", "those",
}


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip non-word chars, drop stopwords, return tokens."""
    if not text:
        return []
    tokens = re.findall(r"[a-z0-9+-]+", text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


def _doc_for_opportunity(opp: dict) -> str:
    """Build the search-engine document for an opportunity row."""
    parts = [
        opp.get("title", ""),
        opp.get("host", ""),
        opp.get("blurb", ""),
        opp.get("description", ""),
        " ".join(opp.get("tags", []) or []),
        opp.get("opportunity_field", "") or opp.get("field", ""),
        opp.get("type", ""),
    ]
    return " ".join(parts)


def _query_for_student(student: dict) -> str:
    """Build the query string from a student profile row."""
    parts = []
    interests = student.get("interests", []) or []
    parts.extend(interests)
    parts.append(student.get("goals", "") or "")
    # Echo expanded interest keys so "Computer Science" matches "cs"
    for interest in interests:
        mapped = INTEREST_TO_FIELD.get(interest.lower(), "")
        if mapped:
            parts.append(mapped)
    return " ".join(parts)


def _tfidf_matrix(documents: list[str], query: str):
    """Return (doc_vectors, query_vector) as dict[token->weight]."""
    n = len(documents)
    if n == 0:
        return [], {}

    # document frequency: number of docs containing each token
    df: Counter = Counter()
    doc_tokens: list[list[str]] = []
    for doc in documents:
        tokens = _tokenize(doc)
        doc_tokens.append(tokens)
        for tok in set(tokens):
            df[tok] += 1

    # query tokens
    q_tokens = _tokenize(query)
    q_counter = Counter(q_tokens)
    q_tokens_set = set(q_tokens)

    idf: dict[str, float] = {}
    for tok, cf in df.items():
        idf[tok] = math.log((n + 1) / (cf + 1)) + 1.0  # smoothed

    # Only compute IDF for tokens in query (we only score docs against query);
    # tokens absent in query contribute zero to cosine anyway.
    doc_vectors = []
    for tokens in doc_tokens:
        d_counter = Counter(tokens)
        total = sum(d_counter.values()) or 1
        v = {}
        for tok, count in d_counter.items():
            if tok not in q_tokens_set:
                continue  # zero contribution to cosine
            tf = count / total
            v[tok] = tf * idf.get(tok, 0.0)
        doc_vectors.append(v)

    q_total = sum(q_counter.values()) or 1
    qv: dict[str, float] = {}
    for tok, count in q_counter.items():
        if tok not in df:
            continue  # token doesn't exist in corpus → contributes nothing
        tf = count / q_total
        qv[tok] = tf * idf.get(tok, 0.0)

    return doc_vectors, qv


def _cosine(v1: dict[str, float], v2: dict[str, float]) -> float:
    n1 = math.sqrt(sum(x * x for x in v1.values())) or 1e-9
    n2 = math.sqrt(sum(x * x for x in v2.values())) or 1e-9
    if n1 == 1e-9 or n2 == 1e-9:
        return 0.0
    # iterate over the smaller dictionary for dot product
    small, large = (v2, v1) if len(v2) < len(v1) else (v1, v2)
    dot = 0.0
    for tok, w in small.items():
        if tok in large:
            dot += w * large[tok]
    return dot / (n1 * n2)


def _explain(status_tf: float, field_note: str | None, grade_fit: bool,
             tag_overlap: int, free: bool, collab_lift: bool = False,
             bookmark_note: bool = False, location_note: str | None = None) -> str:
    bits: list[str] = []
    if status_tf > 0.3:
        bits.append("strong semantic match")
    elif status_tf > 0.1:
        bits.append("partial semantic match")
    if field_note:
        bits.append(field_note)
    if bookmark_note:
        bits.append("close to what you bookmark")
    if grade_fit:
        bits.append("eligible for your grade")
    if tag_overlap > 0:
        bits.append(f"overlaps on {tag_overlap} tag(s)")
    if free:
        bits.append("fully funded")
    if location_note:
        bits.append(location_note)
    if collab_lift:
        bits.append("students with outcomes like yours did well here")
    if not bits:
        return "Ranked as a default suggestion."
    first = bits[0].capitalize()
    rest = ("; ".join(bits[1:])).lower()
    return first + ((" — " + rest) if rest else ".")


def score_opportunities(
    student: dict,
    opportunities: Iterable[dict],
    outcomes: list[dict] | None = None,
    bookmarked_fields: dict[str, int] | None = None,
    dismissed_ids: set[str] | None = None,
) -> list[dict]:
    """Score an iterable of opportunities for one student.

    Each opportunity dict is expected to have the columns described in
    migration_002_northstar_schema.sql (title, host, opportunity_field or
    field, type, blurb, description, cost, grade_min, grade_max, tags, url).

    ``outcomes`` is the student's own logged outcome rows
    (``opportunity_id`` + ``status``); when present and a trained ALS
    artifact exists, a small centered collaborative term joins the score.

    ``bookmarked_fields`` counts the student's bookmarks per field — a
    small behavioral nudge toward fields they keep saving. ``dismissed_ids``
    are excluded outright: "not for me" means not in the list.

    Returns a list of dict with keys ``opportunity``, ``score`` where
    score itself is a dict with ``opportunity_id``, ``score``, ``explanation``.
    Returns empty list if student has no interests and no goals.
    """
    opps = list(opportunities)
    if dismissed_ids:
        opps = [o for o in opps if o.get("id") not in dismissed_ids]
    if not opps:
        return []

    # Bail-out: no signal from the student
    student_query = _query_for_student(student)
    if not _tokenize(student_query):
        return []

    documents = [_doc_for_opportunity(o) for o in opps]
    doc_vectors, qv = _tfidf_matrix(documents, student_query)

    # Resolve student's grade to int (string "11", "12", "Gap year", etc.)
    grade_str = (student.get("grade") or "").strip()
    try:
        student_grade = int(grade_str)
    except (ValueError, TypeError):
        student_grade = 99  # skip grade-mismatch penalty on unparseable

    # grade_min/grade_max describe HS grade bands (6-12); for college
    # students they carry no meaning, so the grade boost is off entirely.
    if (student.get("audience") or "high_school") == "college":
        student_grade = 99

    # Map student's interests to field enum values
    student_fields: set[str] = set()
    for interest in student.get("interests", []) or []:
        mapped = INTEREST_TO_FIELD.get(str(interest).lower())
        if mapped:
            student_fields.add(mapped)

    # Collaborative signal: {} unless the student has logged outcomes AND a
    # trained artifact exists — so the engine behaves identically to the
    # pure TF-IDF version for brand-new students.
    collab = collaborative_scores(
        outcomes or [], [o.get("id") for o in opps if o.get("id")]
    )

    # Quiz field-interest shares (0-100, sum 100), synced from the
    # assessment. When present, the field boost scales with the share
    # instead of firing flat — a 56% field pushes harder than a 12% one.
    field_scores = student.get("field_scores") or {}
    # Location preference gives a small boost, never a hard filter — an
    # 'international' preference must not empty a mostly-US catalog. Global
    # opportunities (open to all) satisfy either preference.
    location_pref = student.get("location_pref") or "either"
    field_scores = {
        k: v for k, v in field_scores.items() if isinstance(v, (int, float))
    } if isinstance(field_scores, dict) else {}

    results: list[dict] = []
    for opp, doc_v in zip(opps, doc_vectors):
        tfidf = _cosine(doc_v, qv)
        opp_field = opp.get("opportunity_field") or opp.get("field") or ""
        field_match = opp_field in student_fields

        if field_scores:
            share = float(field_scores.get(opp_field, 0))
            field_boost = 0.25 * max(0.0, min(share, 100.0)) / 100.0
            field_note = (
                f"{share:.0f}% of your interest points at this field"
                if share >= 10
                else None
            )
            field_match = field_match or share >= 10
        else:
            field_boost = 0.15 if field_match else 0.0
            field_note = "field matches an interest" if field_match else None

        bookmark_count = (bookmarked_fields or {}).get(opp_field, 0)
        bookmark_boost = min(0.02 * bookmark_count, 0.06)

        scope = opp.get("location_scope") or "us"
        location_note = None
        location_boost = 0.0
        if location_pref != "either" and scope in (location_pref, "global"):
            location_boost = 0.05
            location_note = (
                "open worldwide" if scope == "global"
                else f"{scope}-based, matching your preference"
            )

        tmin, tmax = opp.get("grade_min", 6), opp.get("grade_max", 12)
        try:
            grade_fit = (tmin <= student_grade <= tmax)
        except (TypeError, ValueError):
            grade_fit = False

        opp_tags = set(opp.get("tags", []) or [])
        student_tag_set = set()
        for interest in student.get("interests", []) or []:
            student_tag_set.add(str(interest).lower())
            student_tag_set.update(_tokenize(str(interest)))
        tag_overlap = len(opp_tags & student_tag_set) or 0

        free = (opp.get("cost", 0) or 0) == 0

        boost = field_boost + bookmark_boost + location_boost
        if grade_fit:   boost += 0.10
        if tag_overlap: boost += 0.10
        if free:        boost += 0.05

        # Centered collaborative nudge: cf 0.5 means "no opinion" → 0.0.
        cf = collab.get(opp.get("id"))
        collab_term = COLLAB_WEIGHT * (cf - 0.5) if cf is not None else 0.0

        score = max(0.0, min(0.5 * tfidf + boost + collab_term, 1.0))
        # Zero-out scores below a small noise floor so we don't surface
        # nothing-then-random entries at the very long tail.
        if tfidf == 0.0 and not field_match and not tag_overlap:
            score = min(score, 0.05)

        explanation = _explain(
            tfidf, field_note, grade_fit, tag_overlap, free,
            collab_lift=collab_term > 0.02,
            bookmark_note=bookmark_boost > 0,
            location_note=location_note,
        )
        results.append({
            "opportunity": opp,
            "score": {
                "opportunity_id": opp.get("id"),
                "score": round(score, 4),
                "explanation": explanation,
            },
        })

    results.sort(key=lambda r: r["score"]["score"], reverse=True)
    return results
