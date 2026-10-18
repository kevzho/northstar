"""
One cached, audience-filtered accessor for public.opportunities.

Three routes used to do the same thing independently: ``select("*")`` over the
whole catalog, then filter to the student's audience shelf in Python. That is
GET /match (called from three separate frontend pages with no client cache),
POST /advisor, and GET /pathways.

The cost, measured at 144 live rows: 106 KB per call. One student session
touching the dashboard, /opportunities and /plan issues three /match calls and
moves ~318 KB of catalog to score twelve visible cards. At 1,000 students that
is 9.8 GB/month of Supabase egress against a 5 GB free tier -- so the product
runs out of free database before it runs out of anything else.

Three changes here, none of which touch the scoring engine:

1. The audience filter moves into Postgres. ``opportunities.audience`` is
   ``not null default 'high_school'`` (20260815120000_audience.sql), and there
   are zero NULL rows, so ``.eq()`` is exactly equivalent to the Python
   comprehension it replaces -- while halving the rows on the wire, since the
   catalog is currently 70 high_school / 74 college.

2. A short TTL cache. The catalog changes at most once a day, from the scrape
   cron. Functions are per-instance on Vercel so this is not a shared cache,
   but a warm instance serving one student's three /match calls reads the
   catalog once instead of three times. Same pattern as app/projects.py.

3. ``public_view()`` strips ``description`` from what is RETURNED. It stays in
   what is SCORED -- app/match.py feeds it straight into the TF-IDF corpus, so
   dropping it from the query would silently gut ranking. It is 23% of the
   payload and no list view renders it; GET /opportunities/{id} serves it to
   the one page that does.
"""

from __future__ import annotations

import time

# The audience enum, mirrored from 20260815120000_audience.sql. Used to
# validate before the value reaches a PostgREST filter: postgrest-py does not
# escape filter criteria (see app/params.py), and this one originates in a row
# rather than a request, which is a reason to check it rather than a reason not
# to.
AUDIENCES = frozenset({"high_school", "college"})
DEFAULT_AUDIENCE = "high_school"

CACHE_TTL_S = 300

# A hard ceiling so a runaway catalog cannot turn one request into a multi-
# megabyte response. Generously above the current 144 rows; if it is ever hit,
# the fix is pagination, not a bigger number.
MAX_CATALOG_ROWS = 2_000

_cache: dict[str, tuple[float, list[dict]]] = {}


def shelf_for(student: dict) -> str:
    """The audience shelf a student's recommendations come from."""
    shelf = (student or {}).get("audience") or DEFAULT_AUDIENCE
    return shelf if shelf in AUDIENCES else DEFAULT_AUDIENCE


def fetch_shelf(sb, audience: str, *, force: bool = False) -> list[dict]:
    """Every opportunity on one audience shelf, cached for CACHE_TTL_S.

    Returns the rows as stored, ``description`` included, because the scoring
    engine needs it. Callers must not mutate them -- they are shared with the
    cache. Use ``public_view()`` to build anything that goes over the wire.
    """
    shelf = audience if audience in AUDIENCES else DEFAULT_AUDIENCE

    if not force:
        cached = _cache.get(shelf)
        if cached and time.time() - cached[0] < CACHE_TTL_S:
            return cached[1]

    rows = (
        sb.table("opportunities")
        .select("*")
        .eq("audience", shelf)
        # Retired rows never reach a student. An audit of the seeded catalog
        # against each program's own site found programs that had ENDED (Gates
        # Millennium, final cohort 2016), been renamed and re-scoped to middle
        # school (Broadcom MASTERS), or never accepted high schoolers at all
        # (a fabricated "NSF REU High School Track"; CERN, which requires
        # university enrolment). They are stamped rather than deleted, because
        # outcomes/bookmarks/matches/dismissals all cascade from
        # opportunities(id) and a DELETE would take a student's logged history
        # with it. See 20260923120000_opportunity_verification.sql.
        .is_("retired_at", "null")
        .limit(MAX_CATALOG_ROWS)
        .execute()
    ).data or []

    _cache[shelf] = (time.time(), rows)
    return rows


def public_view(opp: dict) -> dict:
    """The shape a list response should carry.

    Renames ``opportunity_field`` to ``field`` (the DB column vs what
    frontend/lib/types.ts expects) and drops ``description``, which only
    GET /opportunities/{id} needs.
    """
    out = {k: v for k, v in opp.items() if k != "description"}
    if "opportunity_field" in out:
        out["field"] = out.pop("opportunity_field")
    return out


def clear_cache() -> None:
    """Drop the cache. For tests, and for a post-import cron step."""
    _cache.clear()


def interleave_by_field(rows: list[dict], field_key: str = "field") -> list[dict]:
    """Round-robin the browse list across fields, soonest-first inside each.

    WHY THE DEFAULT ORDER NEEDED CHANGING. /opportunities sorted open-first then
    by deadline, which sounds neutral and is not: it hands the top of the list
    to whichever feed is most prolific. Measured 2026-10-12, 8 of the first 10
    open rows were capture-the-flag events and 40% of all open rows were CTF or
    competitive programming -- because ctftime and codeforces publish weekly
    while a research programme publishes once a year. A student arriving at a
    page that promises "the programs you never hear about" met a wall of
    hacking competitions.

    That is a ranking artefact, not a fact about opportunity. This page's job is
    BREADTH -- it is the browse surface, not the matcher -- so it shows the
    soonest biology thing next to the soonest humanities thing next to the
    soonest CS thing, and only then the second of each.

    Nothing is hidden, dropped or down-weighted: every row is still here, the
    filters are unchanged, and within a field the deadline order is exactly what
    it was. A student who wants only CTFs filters for them and gets all of them.

    Fields enter the rotation ordered by their own soonest deadline, so the
    single most urgent thing in the catalog is still first on the page.
    """
    from collections import OrderedDict

    buckets: "OrderedDict[str, list[dict]]" = OrderedDict()
    for row in rows:
        buckets.setdefault(row.get(field_key) or "", []).append(row)

    # A field's place in the rotation is its best row's place in the old order,
    # so "most urgent first" survives the change.
    order = sorted(buckets, key=lambda f: rows.index(buckets[f][0]))

    out: list[dict] = []
    index = 0
    while len(out) < len(rows):
        taken = False
        for field in order:
            bucket = buckets[field]
            if index < len(bucket):
                out.append(bucket[index])
                taken = True
        if not taken:
            break
        index += 1
    return out
