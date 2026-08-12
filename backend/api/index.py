"""
Vercel serverless entrypoint.

Vercel's Python runtime builds every ``api/*.py`` file into a function and
serves the ASGI ``app`` exported here; vercel.json rewrites every path to
this function so FastAPI keeps owning the full route table (/health, /me,
/match, ...). Local dev keeps using ``uvicorn main:app`` via the sibling
``main.py`` re-export.
"""

from app.main import app  # noqa: F401  (re-export for Vercel)
