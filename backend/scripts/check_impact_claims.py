"""
Verify the landing page's numeric claims against the live catalog.

WHY A SCRIPT AND NOT A TEST. tests/test_impact_claims.py can only bound the
claims from above, by counting rows in the seed migrations: CI has no database
credentials, and retirement only ever removes rows, so "stated <= seeded" is the
strongest statement it can make. That is a real guard and it stays. But it
cannot see a retirement, and retirement is precisely what keeps making the copy
false:

  - nine defunct rows retired       -> the page still said 70
  - the free-share guard shipped    -> raw counts went unchecked, false in an hour
  - eight duplicates + 100 expired  -> the page still said 61

Three times, the same shape: a correctness fix to the data silently turned a
truthful sentence into a false one. The fix is to check the claim where the
credentials are — the daily scrape job, which is also the thing that changes the
numbers. Same run, same minute.

Exits non-zero and names the wrong sentence, so the failure arrives the day the
claim breaks rather than the week someone rereads the page.

Usage:
    cd backend && .venv/bin/python scripts/check_impact_claims.py
"""

from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.db import get_supabase  # noqa: E402

LANDING = (
    pathlib.Path(__file__).resolve().parents[2] / "frontend" / "app" / "page.tsx"
)


def main() -> int:
    page = " ".join(LANDING.read_text().split())
    sb = get_supabase()

    rows = (
        sb.table("opportunities")
        .select("host, opportunity_field, cost")
        .is_("retired_at", "null")
        .eq("audience", "high_school")
        .execute()
    ).data or []

    shelf = len(rows)
    orgs = len({(r.get("host") or "").strip() for r in rows if (r.get("host") or "").strip()})
    fields = len({r.get("opportunity_field") for r in rows if r.get("opportunity_field")})
    free = sum(1 for r in rows if (r.get("cost") or 0) == 0)

    # (regex, expected values, what the sentence asserts)
    checks: list[tuple[str, list[int], str]] = [
        (r"across\s+(\d+)\s+fields", [fields],
         "distinct fields on the high-school shelf"),
    ]

    failures: list[str] = []
    for pattern, actual, what in checks:
        m = re.search(pattern, page)
        if not m:
            # Absent is allowed; wrong is not. A page may stop making a claim,
            # and this job must not fail for a sentence nobody wrote.
            print(f"  n/a      {what}: the page states none (production: {actual})")
            continue
        stated = [int(g) for g in m.groups()]
        if stated != actual:
            failures.append(
                f"  WRONG    {what}: page says {stated}, production has {actual}\n"
                f"           \"{m.group(0)}\""
            )
        else:
            print(f"  ok       {what}: {stated}")

    # The shelf size is stated as a FLOOR ("more than 50"), not an exact count.
    # It was exact for about four hours: the daily scrape added two high-school
    # rows and the page was wrong the same afternoon. An exact number in static
    # copy cannot survive a catalog that grows every morning — it would redden
    # the build on any day the scraper found something, which trains people to
    # ignore the build. A floor is monotonic in the direction the catalog moves,
    # so it only fails when the shelf actually SHRINKS past it, which is a real
    # problem worth failing for.
    # An ABSENT claim is not a failure. The shelf-size sentence was removed from
    # the page on 2026-09-27; a check that demanded it would redden the nightly
    # job every night for a claim nobody makes. The rule is the other direction:
    # if the page states a number, production must support it.
    m = re.search(r"more than\s+(\d+)\s+opportunities", page, re.I)
    if not m:
        print(f"  n/a      shelf size: the page states none "
              f"(production has {shelf})")
    else:
        floor = int(m.group(1))
        if shelf <= floor:
            failures.append(
                f"  WRONG    shelf size: page claims more than {floor}, "
                f"production has {shelf}"
            )
        elif shelf >= floor * 2:
            failures.append(
                f"  STALE    page claims more than {floor} but the shelf is now "
                f"{shelf}. Not false, just needlessly modest — raise the floor."
            )
        else:
            print(f"  ok       shelf size: {shelf} clears "
                  f'"more than {floor}"')

    # The cost claim is a proportion ("more than four in five"), not a pair of
    # counts, so it cannot be compared integer-to-integer. The page states the
    # shelf size once; repeating it inside the cost sentence is what made this
    # rot before.
    FRACTIONS = {
        "three in four": 0.75, "four in five": 0.80,
        "five in six": 0.833, "nine in ten": 0.90,
    }
    share = free / shelf if shelf else 0.0
    m = re.search(
        r"More than\s+(" + "|".join(FRACTIONS) + r")\s+programs on\s+the\s+"
        r"high-school shelf cost nothing", page, re.IGNORECASE,
    )
    if not m:
        print(f"  n/a      free share: the page states none "
              f"(production is {share:.1%})")
    else:
        floor = FRACTIONS[m.group(1).lower()]
        if share <= floor:
            failures.append(
                f"  WRONG    free share: page claims more than {m.group(1)} "
                f"({floor:.0%}), production is {share:.1%} ({free}/{shelf})"
            )
        else:
            print(f"  ok       free share: {share:.1%} clears "
                  f"\"more than {m.group(1)}\" ({floor:.0%})")

    if failures:
        print("\nThe landing page states numbers the catalog does not support:\n")
        print("\n".join(failures))
        print(
            f"\nLive high-school shelf right now: {shelf} rows, {orgs} hosts, "
            f"{fields} fields, {free} free to apply.\n"
            "Update frontend/app/page.tsx to these numbers."
        )
        return 1

    print(f"\n  all claims match production ({shelf} rows, {orgs} hosts).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
