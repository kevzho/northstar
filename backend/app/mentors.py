"""
Hermes-wired mentor matching engine.

For the MVP we reuse the same TF-IDF / cosine machinery as
``app/match.py`` so the two ranking surfaces in Meridian feel consistent.
Production can swap the sparse TF-IDF for real sentence-transformer
embeddings once the bio_embedding column is populated (the schema +
SQL functions already support the vector(384) column).

Design:
  1.  Student query = interests + goals
  2.  Mentor doc   = name + bio + flattened expertise
  3.  TF-IDF cosine similarity produces a [0, 1] score
  4.  Boosters layer on top:
        +0.15 when any mentor.expertise matches a student interest's
              mapped field enum (see INTEREST_TO_FIELD in app/match)
        +0.05 when the mentor takes multiple expertise tags (breadth)
  5.  ``score = min(0.5*tfidf + boosters, 1.0)``
  6.  Explanation: which expertise overlaps the student interests, plus
      a sentence about the bio keyword overlap.

Why stdlib only: keeps the cold-start path fast and avoids a model
download on Render. pgvector is still used for the column itself.
"""

from typing import Iterable

from .match import _doc_for_opportunity, _query_for_student, _tfidf_matrix, _cosine
from .match import _tokenize, INTEREST_TO_FIELD


def _mentor_doc(mentor: dict) -> str:
    """Build the search corpus entry for a mentor row."""
    parts = [
        mentor.get("name", ""),
        mentor.get("bio", ""),
        mentor.get("email", ""),  # helps when looking up by name
    ]
    expertise = mentor.get("expertise", []) or []
    # Echo each expertise tag twice so it counts more than incidental
    # mentions in the bio. This stops "engineer" in a bio from drowning
    # out the explicit expertise field.
    parts.extend(expertise)
    parts.extend(expertise)
    return " ".join(parts)


def _explain_overlap(student: dict, mentor: dict) -> str:
    """Compose a 1-line reason for ranking this mentor for this student."""
    student_interests = [str(s).lower() for s in student.get("interests", []) or []]
    expertise = [str(t).lower() for t in mentor.get("expertise", []) or []]

    fields = {INTEREST_TO_FIELD[i] for i in student_interests if i in INTEREST_TO_FIELD}
    overlap_fields = [e for e in expertise if e in fields]

    shared_words: list[str] = []
    bio_tokens = set(_tokenize(mentor.get("bio", "") or ""))
    for interest in student_interests:
        shared_words.extend(set(_tokenize(interest)) & bio_tokens)

    bits = []
    if overlap_fields:
        bits.append(f"expertise matches your {', '.join(sorted(set(overlap_fields)))} interest")
    if shared_words:
        unique = sorted(set(shared_words))[:3]
        bits.append(f"bio mentions your interest in {', '.join(unique)}")
    if len(expertise) >= 3:
        bits.append(f"versatile across {len(expertise)} fields")

    if not bits:
        return "Default suggestion based on profile."
    first = bits[0].capitalize()
    rest = "; ".join(bits[1:]).lower()
    return first + ((" — " + rest) if rest else ".")


def score_mentors(student: dict, mentors: Iterable[dict]) -> list[dict]:
    """Score an iterable of mentor rows for one student.

    Returns a list of dicts with keys ``mentor``, ``score``
    (``{mentor_id, score, explanation}``) sorted by score desc.
    """

    rows = list(mentors)
    if not rows:
        return []

    student_query = _query_for_student(student)
    if not _tokenize(student_query):
        return []

    student_interests = [str(s).lower() for s in student.get("interests", []) or []]
    fields = {INTEREST_TO_FIELD[i] for i in student_interests if i in INTEREST_TO_FIELD}

    documents = [_mentor_doc(m) for m in rows]
    doc_vectors, qv = _tfidf_matrix(documents, student_query)

    results: list[dict] = []
    for mentor, doc_v in zip(rows, doc_vectors):
        tfidf = _cosine(doc_v, qv)

        expertise = mentor.get("expertise", []) or []
        expertise_match = sum(1 for e in expertise if str(e).lower() in fields)

        boost = 0.0
        if expertise_match:
            boost += 0.15
        if len(expertise) >= 3:
            boost += 0.05

        score = min(0.5 * tfidf + boost, 1.0)
        if tfidf == 0.0 and expertise_match == 0:
            score = min(score, 0.10)

        results.append({
            "mentor": mentor,
            "score": {
                "mentor_id": mentor.get("id"),
                "score": round(score, 4),
                "explanation": _explain_overlap(student, mentor),
            },
        })

    results.sort(key=lambda r: r["score"]["score"], reverse=True)
    return results
