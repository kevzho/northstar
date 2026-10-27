"""
Behavioural tests for the TF-IDF match engine (backend/app/match.py).

These pin the properties the student can defend in the CAC interview: ranking is
driven by profile overlap, the documented boosters actually fire, the score stays
in [0, 1], and the explanation names the reason. The booster magnitudes belong to
the student (ARCHITECTURE.md §2), the tests assert relationships, not constants,
so tuning the numbers does not break the suite.
"""

from __future__ import annotations

from app.match import score_opportunities

STUDENT = {
    "id": "s1",
    "grade": "11",
    "interests": ["Computer Science"],
    "goals": "I want to build machine learning tools for hospitals.",
}


def _opp(**over) -> dict:
    base = {
        "id": "o1",
        "title": "Summer Program",
        "host": "Some University",
        "opportunity_field": "cs",
        "type": "program",
        "blurb": "",
        "description": "",
        "cost": 0,
        "grade_min": 9,
        "grade_max": 12,
        "url": "https://example.com",
        "tags": [],
    }
    base.update(over)
    return base


def test_empty_catalog_returns_empty() -> None:
    assert score_opportunities(STUDENT, []) == []


def test_student_with_no_signal_returns_empty() -> None:
    blank = {"id": "s1", "grade": "11", "interests": [], "goals": ""}
    assert score_opportunities(blank, [_opp()]) == []


def test_scores_are_bounded_and_sorted() -> None:
    catalog = [
        _opp(id="a", title="Machine Learning for Hospitals", description="machine learning"),
        _opp(id="b", opportunity_field="physics", title="Particle Physics Camp"),
        _opp(id="c", title="Robotics Build Season", opportunity_field="engineering"),
    ]
    results = score_opportunities(STUDENT, catalog)

    assert len(results) == len(catalog)
    scores = [r["score"]["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 <= s <= 1.0 for s in scores)


def test_semantic_overlap_outranks_unrelated() -> None:
    catalog = [
        _opp(id="match", title="Machine Learning in Medicine",
             description="Students build machine learning tools for hospitals."),
        _opp(id="other", opportunity_field="physics", title="Astronomy Night",
             description="Telescope observation of distant galaxies."),
    ]
    results = score_opportunities(STUDENT, catalog)
    assert results[0]["score"]["opportunity_id"] == "match"


def test_field_booster_fires_for_mapped_interest() -> None:
    """"Computer Science" must map onto the `cs` field enum."""
    on_field = score_opportunities(STUDENT, [_opp(id="x", opportunity_field="cs")])[0]
    off_field = score_opportunities(STUDENT, [_opp(id="x", opportunity_field="physics")])[0]

    assert on_field["score"]["score"] > off_field["score"]["score"]
    assert "field matches" in on_field["score"]["explanation"].lower()


def test_grade_booster_respects_range() -> None:
    eligible = score_opportunities(STUDENT, [_opp(grade_min=9, grade_max=12)])[0]
    too_senior = score_opportunities(STUDENT, [_opp(grade_min=6, grade_max=8)])[0]

    assert eligible["score"]["score"] > too_senior["score"]["score"]
    assert "grade" in eligible["score"]["explanation"].lower()


def test_unparseable_grade_does_not_crash() -> None:
    student = dict(STUDENT, grade="Gap year")
    results = score_opportunities(student, [_opp()])
    assert 0.0 <= results[0]["score"]["score"] <= 1.0


def test_cost_booster_prefers_free() -> None:
    free = score_opportunities(STUDENT, [_opp(cost=0)])[0]
    paid = score_opportunities(STUDENT, [_opp(cost=4500)])[0]

    assert free["score"]["score"] > paid["score"]["score"]
    assert "funded" in free["score"]["explanation"].lower()


def test_tag_overlap_boosts_and_is_explained() -> None:
    tagged = score_opportunities(STUDENT, [_opp(tags=["computer", "science"])])[0]
    untagged = score_opportunities(STUDENT, [_opp(tags=["welding"])])[0]

    assert tagged["score"]["score"] > untagged["score"]["score"]
    assert "tag" in tagged["score"]["explanation"].lower()


def test_field_key_accepts_either_column_name() -> None:
    """Rows come back as `opportunity_field` from Postgres, `field` from the API."""
    a = score_opportunities(STUDENT, [_opp(id="x", opportunity_field="cs")])[0]
    row = _opp(id="x")
    del row["opportunity_field"]
    row["field"] = "cs"
    b = score_opportunities(STUDENT, [row])[0]

    assert a["score"]["score"] == b["score"]["score"]


def test_every_result_carries_an_explanation() -> None:
    results = score_opportunities(STUDENT, [_opp(id="a"), _opp(id="b", cost=100)])
    for r in results:
        assert r["score"]["explanation"].strip()
        assert r["score"]["opportunity_id"]


# ---------------------------------------------------------------------------
# Evolving-profile signals: proportional field boost, bookmarks, dismissals.
# ---------------------------------------------------------------------------


def test_field_scores_make_boost_proportional() -> None:
    """A 60% field pushes harder than a 10% one; both beat 0%."""
    student = {**STUDENT, "field_scores": {"cs": 60, "biology": 10, "math": 0}}
    results = score_opportunities(
        student,
        [
            _opp(id="cs", opportunity_field="cs"),
            _opp(id="bio", opportunity_field="biology"),
            _opp(id="math", opportunity_field="math"),
        ],
    )
    by_id = {r["score"]["opportunity_id"]: r["score"]["score"] for r in results}
    assert by_id["cs"] > by_id["bio"] > by_id["math"]


def test_field_share_appears_in_explanation() -> None:
    student = {**STUDENT, "field_scores": {"cs": 56}}
    (result,) = score_opportunities(student, [_opp(opportunity_field="cs")])
    assert "56% of your interest" in result["score"]["explanation"]


def test_without_field_scores_flat_boost_still_fires() -> None:
    """Old behavior is the fallback: stated interest -> flat boost."""
    (result,) = score_opportunities(STUDENT, [_opp(opportunity_field="cs")])
    assert "field matches" in result["score"]["explanation"].lower()


def test_dismissed_opportunities_are_excluded() -> None:
    results = score_opportunities(
        STUDENT,
        [_opp(id="keep"), _opp(id="gone")],
        dismissed_ids={"gone"},
    )
    ids = [r["score"]["opportunity_id"] for r in results]
    assert ids == ["keep"]


def test_bookmarked_field_nudges_and_is_explained() -> None:
    plain = score_opportunities(STUDENT, [_opp()])
    nudged = score_opportunities(STUDENT, [_opp()], bookmarked_fields={"cs": 2})
    assert nudged[0]["score"]["score"] > plain[0]["score"]["score"]
    assert "bookmark" in nudged[0]["score"]["explanation"].lower()


def test_malformed_field_scores_do_not_crash() -> None:
    student = {**STUDENT, "field_scores": {"cs": "not-a-number", "math": None}}
    results = score_opportunities(student, [_opp(opportunity_field="cs")])
    assert len(results) == 1  # falls back cleanly, no boost from junk


def test_location_preference_boosts_matching_scope() -> None:
    us_pref = {**STUDENT, "location_pref": "us"}
    results = score_opportunities(
        us_pref,
        [
            _opp(id="us", location_scope="us"),
            _opp(id="intl", location_scope="international"),
        ],
    )
    by_id = {r["score"]["opportunity_id"]: r["score"]["score"] for r in results}
    assert by_id["us"] > by_id["intl"]
    us_result = next(r for r in results if r["score"]["opportunity_id"] == "us")
    assert "us-based" in us_result["score"]["explanation"].lower()


def test_global_opportunities_satisfy_any_preference() -> None:
    intl_pref = {**STUDENT, "location_pref": "international"}
    (result,) = score_opportunities(intl_pref, [_opp(location_scope="global")])
    assert "worldwide" in result["score"]["explanation"].lower()


def test_either_preference_gives_no_location_boost() -> None:
    either = {**STUDENT, "location_pref": "either"}
    (result,) = score_opportunities(either, [_opp(location_scope="us")])
    assert "matching your preference" not in result["score"]["explanation"]


def test_matcher_knows_every_field_in_the_enum() -> None:
    """INTEREST_TO_FIELD must cover the whole opportunity_field enum.

    20260815170000_expand_fields.sql added design, business, humanities and
    health, and its comment says "the frontend quiz, matcher, and scraper all
    learn them in the same change set." The quiz and the enum did; this table
    did not, for five weeks. A student who picked Design never earned the
    field booster, and their explanation never said the field matched, for
    exactly the opportunities carrying that field.

    Ground truth is the migrations, not a hand-copied list, so adding a fifth
    field to the enum without teaching the matcher fails here.
    """
    import pathlib
    import re

    from app.match import INTEREST_TO_FIELD

    migrations = pathlib.Path(__file__).resolve().parents[2] / "supabase" / "migrations"
    declared: set[str] = set()
    for path in sorted(migrations.glob("*.sql")):
        sql = path.read_text()
        block = re.search(
            r"create type public\.opportunity_field as enum \((?P<b>.*?)\)",
            sql,
            re.DOTALL | re.IGNORECASE,
        )
        if block:
            declared |= set(re.findall(r"'([a-z_]+)'", block.group("b")))
        declared |= set(
            re.findall(
                r"alter type public\.opportunity_field add value if not exists '([a-z_]+)'",
                sql,
                re.IGNORECASE,
            )
        )

    assert declared, "no opportunity_field enum values found in the migrations"
    missing = declared - set(INTEREST_TO_FIELD.values())
    assert not missing, (
        "app/match.py INTEREST_TO_FIELD cannot reach these opportunity_field "
        f"values, so no student interest can ever boost them: {sorted(missing)}"
    )


# ---------------------------------------------------------------------------
# Semantic booster. TF-IDF is lexical: measured on the live catalog, a student
# who writes "I want to help people with cancer" gets every row after the first
# pinned at the 0.05 noise floor, and Stanford Institutes of Medicine Summer
# Research, the one relevant programme, sits at rank 33. With the semantic
# term and assessment field scores present it reaches rank 1, and Broad Summer
# Scholars moves 9 -> 4 while a maths camp moves 27 -> 20.
# ---------------------------------------------------------------------------

SEM_STUDENT = {
    "id": "s1",
    "grade": "11",
    "interests": ["Health"],
    "goals": "I want to help people with cancer",
    "audience": "high_school",
    "location_pref": "either",
    "field_scores": {"health": 60},
}


def _sem_opp(oid, title, field="health", blurb=""):
    return {
        "id": oid, "title": title, "host": "H", "opportunity_field": field,
        "type": "program", "blurb": blurb, "description": "", "cost": 0,
        "grade_min": 9, "grade_max": 12, "tags": [], "url": "https://e.org",
        "location_scope": "us",
    }


def test_absent_semantic_scores_change_nothing() -> None:
    """The feature must degrade to exactly the previous behaviour.

    A missing profile embedding, an unembedded catalog, or an unreachable
    provider all produce {}, and none of them may alter a score.
    """
    opps = [_sem_opp("a", "Alpha Research"), _sem_opp("b", "Beta Program", "cs")]
    base = score_opportunities(SEM_STUDENT, opps, [])
    for empty in (None, {}):
        got = score_opportunities(SEM_STUDENT, opps, [], semantic=empty)
        assert [r["score"]["score"] for r in got] == [
            r["score"]["score"] for r in base
        ], f"semantic={empty!r} altered the scoring"


def test_a_flat_similarity_set_is_ignored_not_amplified() -> None:
    """Every row equally similar carries no information.

    Min-max normalising a flat set would divide by zero or promote everything
    uniformly; neither is a ranking signal.
    """
    opps = [_sem_opp("a", "Alpha"), _sem_opp("b", "Beta"), _sem_opp("c", "Gamma")]
    base = score_opportunities(SEM_STUDENT, opps, [])
    flat = score_opportunities(
        SEM_STUDENT, opps, [], semantic={"a": 0.2, "b": 0.2, "c": 0.2}
    )
    assert [r["score"]["score"] for r in flat] == [
        r["score"]["score"] for r in base
    ]


def test_a_strong_semantic_match_escapes_the_lexical_noise_floor() -> None:
    """The floor is what made embeddings pointless without this exemption.

    A row with no shared words, no field match and no tag overlap is capped at
    0.05. That cap is what buried Stanford SIMR at rank 33, the semantic term
    was computed and then discarded.
    """
    # Nothing lexical in common with the student, and a field they did not pick.
    far = _sem_opp("far", "Zzzz Qqqq", field="math")
    near = _sem_opp("near", "Wwww Vvvv", field="math")
    opps = [far, near]

    without = {r["opportunity"]["id"]: r["score"]["score"]
               for r in score_opportunities(SEM_STUDENT, opps, [])}
    assert without["near"] <= 0.05 and without["far"] <= 0.05, without

    with_sem = {r["opportunity"]["id"]: r["score"]["score"]
                for r in score_opportunities(
                    SEM_STUDENT, opps, [], semantic={"far": 0.05, "near": 0.90})}
    assert with_sem["near"] > 0.05, (
        "a strong semantic match is still capped by the lexical floor"
    )
    assert with_sem["far"] <= 0.05, "a weak match should stay at the floor"


def test_a_floored_row_does_not_claim_a_semantic_lift() -> None:
    """The explanation must not describe a contribution the floor discarded.

    Before this, 28 rows read "close in meaning to what you wrote" while
    scoring 0.050, an unfalsifiable reason attached to a non-result.
    """
    opps = [_sem_opp("a", "Zzzz Qqqq", field="math"), _sem_opp("b", "Wwww Vvvv", field="math")]
    results = score_opportunities(
        SEM_STUDENT, opps, [], semantic={"a": 0.30, "b": 0.31}
    )
    for r in results:
        if r["score"]["score"] <= 0.05:
            assert "close in meaning" not in r["score"]["explanation"].lower(), (
                f"floored row claims a semantic lift: {r['score']}"
            )


def test_the_semantic_term_is_capped() -> None:
    """A booster, never a replacement. The deterministic engine keeps
    authority over the score, which is what keeps every result explainable."""
    from app.match import SEMANTIC_WEIGHT

    opps = [_sem_opp("a", "Alpha Research"), _sem_opp("b", "Beta Research")]
    low = score_opportunities(SEM_STUDENT, opps, [], semantic={"a": 0.0, "b": 0.0})
    high = score_opportunities(SEM_STUDENT, opps, [], semantic={"a": 0.0, "b": 1.0})
    lift = max(r["score"]["score"] for r in high) - max(
        r["score"]["score"] for r in low
    )
    assert lift <= SEMANTIC_WEIGHT + 1e-6, (
        f"semantic lifted a score by {lift:.3f}, above the {SEMANTIC_WEIGHT} cap"
    )


def test_tfidf_is_no_longer_described_as_semantic() -> None:
    """It is lexical. Calling it "semantic match" was always inaccurate and
    became actively confusing once a real semantic term existed."""
    opps = [_sem_opp("a", "cancer research program", blurb="cancer research")]
    student = dict(SEM_STUDENT, goals="cancer research program")
    text = score_opportunities(student, opps, [])[0]["score"]["explanation"].lower()
    assert "semantic match" not in text, text
