"""
Contract drift gate: the committed API schema must match the live app.

frontend/lib/api-schema.json is what the frontend's generated types are
built from (npm run gen:api). If a backend change alters the OpenAPI
schema without regenerating, the frontend is silently typed against a
stale contract — this test turns that into a red build with the fix in
the message.
"""

from __future__ import annotations

import json
import pathlib

from app.main import app

SCHEMA = (
    pathlib.Path(__file__).resolve().parents[2]
    / "frontend" / "lib" / "api-schema.json"
)


def test_committed_schema_matches_live_app() -> None:
    assert SCHEMA.exists(), (
        "frontend/lib/api-schema.json is missing. Generate it: "
        "cd backend && python scripts/export_openapi.py"
    )
    committed = json.loads(SCHEMA.read_text())
    live = json.loads(json.dumps(app.openapi(), sort_keys=True))
    assert committed == live, (
        "API contract drift: the backend's OpenAPI schema no longer matches "
        "frontend/lib/api-schema.json. Regenerate both sides: "
        "cd backend && python scripts/export_openapi.py && "
        "cd ../frontend && npm run gen:api"
    )
