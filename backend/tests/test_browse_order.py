"""
/catalog must not open on the deadest row in the catalog.

On 2026-09-25, 123 of 186 live rows had a deadline that had already passed.
/catalog ordered by deadline ascending, which put the MOST expired row first,
and a comment excused it by claiming "the frontend filters to open
opportunities by default" — frontend/app/opportunities/page.tsx falls back to
status "all", so it does not. The first card a student saw was the worst one.

Closed rows are still returned: a sophomore needs to know RSI exists and closes
in January. They just sort last.

The sort key is extracted rather than routed through FastAPI so this needs no
Supabase credentials.
"""

from __future__ import annotations

from datetime import date

TODAY = date(2026, 9, 25)


def browse_order(opp: dict) -> tuple[int, float, str]:
    """Mirror of the key in app/main.py's /catalog route.

    Kept in step by test_browse_order_matches_the_route below, which reads the
    route's source — a copied heuristic that silently drifts is worse than none.
    """
    today_iso = TODAY.isoformat()
    raw = opp.get("deadline")
    deadline = str(raw) if raw else ""
    title = str(opp.get("title") or "")
    if not deadline:
        return (1, 0.0, title)
    try:
        ordinal = float(date.fromisoformat(deadline).toordinal())
    except ValueError:
        return (1, 0.0, title)
    if deadline < today_iso:
        return (2, -ordinal, title)
    return (0, ordinal, title)


CATALOG = [
    {"title": "Closed long ago", "deadline": "2025-11-01"},
    {"title": "Closed recently", "deadline": "2026-09-15"},
    {"title": "Rolling", "deadline": None},
    {"title": "Closes soon", "deadline": "2026-09-27"},
    {"title": "Closes later", "deadline": "2026-11-10"},
    {"title": "Malformed", "deadline": "not-a-date"},
]


def _ordered() -> list[str]:
    return [o["title"] for o in sorted(CATALOG, key=browse_order)]


def test_the_first_row_is_the_soonest_live_deadline() -> None:
    assert _ordered()[0] == "Closes soon"


def test_no_closed_row_outranks_any_open_row() -> None:
    order = _ordered()
    last_open = max(order.index("Closes later"), order.index("Rolling"))
    first_closed = min(order.index("Closed recently"), order.index("Closed long ago"))
    assert first_closed > last_open


def test_closed_rows_are_most_recent_first() -> None:
    """Descending inside the closed bucket: the one that just closed is the
    likeliest to reopen, and the least confusing to encounter."""
    order = _ordered()
    assert order.index("Closed recently") < order.index("Closed long ago")


def test_rolling_rows_sit_between_open_and_closed() -> None:
    order = _ordered()
    assert order.index("Closes later") < order.index("Rolling") < order.index("Closed recently")


def test_a_malformed_date_does_not_raise_or_outrank_live_rows() -> None:
    order = _ordered()
    assert order.index("Malformed") > order.index("Closes later")


def test_ascending_only_would_put_the_deadest_row_first() -> None:
    """The bug this file exists for. Proves the old key really was broken, so a
    future refactor back to a plain .order() cannot pass silently."""
    naive = sorted(
        [o for o in CATALOG if o["deadline"]],
        key=lambda o: str(o["deadline"]),
    )
    assert naive[0]["title"] == "Closed long ago"


def test_browse_order_matches_the_route() -> None:
    """Guard against this mirror drifting from app/main.py."""
    import pathlib

    src = pathlib.Path(__file__).resolve().parents[1] / "app" / "main.py"
    body = src.read_text()
    assert "def browse_order(opp: dict) -> tuple[int, float, str]:" in body
    assert "catalog.sort(key=browse_order)" in body
    # The three buckets, by their distinguishing return values.
    assert "return (2, -ordinal, title)" in body
    assert "return (1, 0.0, title)" in body
    assert "return (0, ordinal, title)" in body


def test_the_browse_page_is_spread_across_fields_not_owned_by_one_feed() -> None:
    """The default order is a product decision, and the old one was wrong.

    Sorting open-first-then-deadline sounds neutral and is not: it gives the top
    of the page to whichever source publishes most often. Measured 2026-10-12,
    8 of the first 10 open rows were capture-the-flag events, because ctftime
    publishes weekly and a research programme publishes once a year. On a page
    that promises "the programs you never hear about", that is the artefact
    drowning the product.
    """
    from app.catalog import interleave_by_field

    # Deadline order, as the old sort produced it: one prolific feed first.
    rows = (
        [{"id": f"ctf{i}", "field": "cs"} for i in range(8)]
        + [{"id": "bio1", "field": "biology"}]
        + [{"id": "hum1", "field": "humanities"}]
        + [{"id": f"ctf{i}", "field": "cs"} for i in range(8, 12)]
    )
    spread = interleave_by_field(rows)

    assert len(spread) == len(rows), "rows were dropped"
    assert {r["id"] for r in spread} == {r["id"] for r in rows}, "rows were changed"

    # The single most urgent row is still first — urgency is not sacrificed.
    assert spread[0] == rows[0]
    # And the first three now show three different fields instead of one.
    assert len({r["field"] for r in spread[:3]}) == 3
    # Within a field, the original order is untouched.
    assert [r["id"] for r in spread if r["field"] == "cs"] == [
        r["id"] for r in rows if r["field"] == "cs"
    ]


def test_interleaving_is_a_no_op_on_a_single_field_or_an_empty_list() -> None:
    from app.catalog import interleave_by_field

    one = [{"id": "a", "field": "cs"}, {"id": "b", "field": "cs"}]
    assert interleave_by_field(one) == one
    assert interleave_by_field([]) == []


def test_a_missing_field_does_not_lose_the_row() -> None:
    from app.catalog import interleave_by_field

    rows = [{"id": "a", "field": None}, {"id": "b", "field": "cs"}]
    assert len(interleave_by_field(rows)) == 2
