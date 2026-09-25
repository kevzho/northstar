"""
Regenerate backend/app/spines.py from frontend/lib/plan.ts.

The spines are authored in TypeScript because that is where /plan renders them,
including signed-out. The backend needs them so GET /roadmap can sequence
without trusting client-supplied content — a student posting their own project
text into public.actions would destroy the provenance the foreign keys exist to
guarantee.

Two copies of authored content is a drift risk, so this is the generator and
tests/test_spines_sync.py is the alarm.

Usage:
    cd backend && .venv/bin/python scripts/sync_spines.py
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
TS = ROOT / "frontend" / "lib" / "plan.ts"
OUT = ROOT / "backend" / "app" / "spines.py"

ENTRY = re.compile(
    r'^  "([a-z0-9-]+)":\s*\{\s*\n'
    r'\s*project:\s*\n?\s*"((?:[^"\\]|\\.)*)",\s*\n'
    r'\s*publish:\s*\n?\s*"((?:[^"\\]|\\.)*)",\s*\n'
    r'\s*skill:\s*\n?\s*"((?:[^"\\]|\\.)*)",\s*\n'
    r'\s*skillKey:\s*"([a-z0-9-]+)",',
    re.MULTILINE,
)

HEADER = '''"""
Server-side mirror of the archetype spines in frontend/lib/plan.ts.

GENERATED — do not edit by hand. Regenerate with:
    cd backend && .venv/bin/python scripts/sync_spines.py

The TypeScript file stays the single source of truth because that is where the
spines are authored and where /plan renders them signed-out. This mirror exists
so GET /roadmap can sequence without the client sending its own content, which
would let a student post any project text they liked into public.actions.
tests/test_spines_sync.py fails if the two drift.
"""

from __future__ import annotations

SPINES: dict[str, dict[str, str]] = '''

FOOTER = '''


def spine_for(archetype_id: str) -> dict[str, str] | None:
    """The authored spine for an archetype, or None if there is none."""
    return SPINES.get(archetype_id)
'''


def parse() -> dict[str, dict[str, str]]:
    block = re.search(r"const SPINES[\s\S]*?\n\};", TS.read_text())
    if not block:
        sys.exit("could not find the SPINES block in frontend/lib/plan.ts")
    found = ENTRY.findall(block.group(0))
    if not found:
        sys.exit("parsed zero spines — the shape of plan.ts changed")
    unescape = lambda s: s.replace('\\"', '"')
    return {
        key: {
            "project": unescape(project),
            "publish": unescape(publish),
            "skill": unescape(skill),
            "skillKey": skill_key,
        }
        for key, project, publish, skill, skill_key in found
    }


def render(data: dict) -> str:
    return HEADER + json.dumps(data, indent=4, ensure_ascii=False) + FOOTER


def main() -> int:
    data = parse()
    OUT.write_text(render(data))
    print(f"wrote {OUT.relative_to(ROOT)} with {len(data)} spines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
