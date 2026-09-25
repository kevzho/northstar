"""
Guard: backend/app/spines.py must match frontend/lib/plan.ts.

The spines are authored in TypeScript and mirrored into Python so GET /roadmap
can sequence without trusting client-supplied content. Two copies of authored
prose is a drift risk, and drift here is silent: the plan page would render one
project step and the roadmap would persist a different one.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts"))

from sync_spines import parse, render  # noqa: E402

from app.spines import SPINES  # noqa: E402


def test_mirror_matches_the_typescript_source() -> None:
    parsed = parse()
    assert parsed == SPINES, (
        "backend/app/spines.py has drifted from frontend/lib/plan.ts. "
        "Regenerate: cd backend && .venv/bin/python scripts/sync_spines.py"
    )


def test_mirror_file_is_byte_identical_to_the_generator_output() -> None:
    """Catches a hand-edit that happens to parse to the same dict."""
    on_disk = (ROOT / "backend" / "app" / "spines.py").read_text()
    assert on_disk == render(parse()), (
        "spines.py was edited by hand. It is generated — "
        "run scripts/sync_spines.py instead."
    )


def test_every_spine_has_all_four_fields() -> None:
    for key, spine in SPINES.items():
        for field in ("project", "publish", "skill", "skillKey"):
            assert spine.get(field), f"{key}.{field} is empty"
