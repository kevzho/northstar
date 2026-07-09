"""
Thin uvicorn entrypoint module.

Keeps the historical ``uvicorn main:app`` command working unchanged while the
real FastAPI app, settings, and Pydantic schemas live under ``backend/app/``.
See PROMPTS.md #4 for the targeted structure this preserves.
"""

from app.main import app  # noqa: F401  (re-export for uvicorn)
