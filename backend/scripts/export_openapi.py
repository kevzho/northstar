"""
Export the FastAPI OpenAPI schema to frontend/lib/api-schema.json.

That file is the single source of truth for the API contract:
``npm run gen:api`` (frontend) turns it into lib/api-types.gen.ts, and
tests/test_openapi_contract.py fails whenever the backend's live schema
no longer matches the committed file, so contract drift breaks CI
instead of breaking users.

Usage:
    cd backend && .venv/bin/python scripts/export_openapi.py
    cd frontend && npm run gen:api
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.main import app  # noqa: E402

OUT = (
    pathlib.Path(__file__).resolve().parents[2]
    / "frontend" / "lib" / "api-schema.json"
)

if __name__ == "__main__":
    OUT.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUT}")
