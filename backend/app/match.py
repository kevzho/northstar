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
  3.  Apply boosters (small additive, capped at 1.0):
      - +0.15 when the opportunity's field aligns with a student
        interest keyword (e.g. "Computer Science" → ``cs``)
      - +0.10 when the student's grade is in ``[grade_min, grade_max]``
      - +0.10 for tag overlap (intersection of tags)
      - +0.05 for free opportunities (cost == 0)
  4.  ``score = clip(0.5*tfidf + boosters, 0, 1)``
  5.  Generate a one-line ``explanation`` from the boosters that fired.

Pure stdlib, no external NLP deps. ``math`` and ``collections`` only.
"""

import math
import re
from collections import Counter
from typing import Iterable

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


def _explain(status_tf: float, field_match: bool, grade_fit: bool,
             tag_overlap: int, free: bool) -> str:
    bits: list[str] = []
    if status_tf > 0.3:
        bits.append("strong semantic match")
    elif status_tf > 0.1:
        bits.append("partial semantic match")
    if field_match:
        bits.append("field matches an interest")
    if grade_fit:
        bits.append("eligible for your grade")
    if tag_overlap > 0:
        bits.append(f"overlaps on {tag_overlap} tag(s)")
    if free:
        bits.append("fully funded")
    if not bits:
        return "Ranked as a default suggestion."
    first = bits[0].capitalize()
    rest = ("; ".join(bits[1:])).lower()
    return first + ((" — " + rest) if rest else ".")


def score_opportunities(student: dict, opportunities: Iterable[dict]) -> list[dict]:
    """Score an iterable of opportunities for one student.

    Each opportunity dict is expected to have the columns described in
    migration_002_meridian_schema.sql (title, host, opportunity_field or
    field, type, blurb, description, cost, grade_min, grade_max, tags, url).

    Returns a list of dict with keys ``opportunity``, ``score`` where
    score itself is a dict with ``opportunity_id``, ``score``, ``explanation``.
    Returns empty list if student has no interests and no goals.
    """
    opps = list(opportunities)
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

    # Map student's interests to field enum values
    student_fields: set[str] = set()
    for interest in student.get("interests", []) or []:
        mapped = INTEREST_TO_FIELD.get(str(interest).lower())
        if mapped:
            student_fields.add(mapped)

    results: list[dict] = []
    for opp, doc_v in zip(opps, doc_vectors):
        tfidf = _cosine(doc_v, qv)
        opp_field = opp.get("opportunity_field") or opp.get("field") or ""
        field_match = opp_field in student_fields

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

        boost = 0.0
        if field_match: boost += 0.15
        if grade_fit:   boost += 0.10
        if tag_overlap: boost += 0.10
        if free:        boost += 0.05
        score = min(0.5 * tfidf + boost, 1.0)
        # Zero-out scores below a small noise floor so we don't surface
        # nothing-then-random entries at the very long tail.
        if tfidf == 0.0 and not field_match and not tag_overlap:
            score = min(score, 0.05)

        explanation = _explain(tfidf, field_match, grade_fit, tag_overlap, free)
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
