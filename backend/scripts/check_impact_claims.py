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

    # (regex, capture index -> actual value, what the sentence asserts)
    checks: list[tuple[str, list[int], str]] = [
        (r"(\d+)\s+verified opportunities", [shelf],
         "size of the high-school shelf"),
        (r"from\s+(\d+)\s+different\s+organizations", [orgs],
         "distinct hosts on the high-school shelf"),
        (r"across\s+(\d+)\s+fields", [fields],
         "distinct fields on the high-school shelf"),
        (r"(\d+)\s+of the\s+(\d+)\s+programs on the\s+high-school shelf cost nothing",
         [free, shelf], "free-to-apply count and shelf size"),
    ]

    failures: list[str] = []
    for pattern, actual, what in checks:
        m = re.search(pattern, page)
        if not m:
            failures.append(
                f"  MISSING  the sentence stating the {what} is gone from "
                f"page.tsx (pattern: {pattern!r}). If the claim was removed on "
                "purpose, remove this check too — do not leave it unmatched."
            )
            continue
        stated = [int(g) for g in m.groups()]
        if stated != actual:
            failures.append(
                f"  WRONG    {what}: page says {stated}, production has {actual}\n"
                f"           \"{m.group(0)}\""
            )
        else:
            print(f"  ok       {what}: {stated}")

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
