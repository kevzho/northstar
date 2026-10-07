"""
Route-level smoke tests using FastAPI's TestClient.

These need no Supabase credentials: they cover the public routes and assert that
every data route fails closed with 401 when the Authorization header is absent
or invalid. That is the property that matters for a public deploy — a missing
token must never reach the service-role Supabase client.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

PROTECTED_GETS = [
    "/me",
    "/match",
    "/opportunities/00000000-0000-0000-0000-000000000000",
    "/bookmarks",
    "/outcomes",
    "/pathways",
    "/mentors",
    "/teamup/settings",
    "/teamup/candidates",
]


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch: pytest.MonkeyPatch):
    """Give the app a signing secret so rejections are 401, not the 500 the
    auth layer returns when the server itself is misconfigured."""
    from app import auth as auth_mod

    monkeypatch.setattr(auth_mod.settings, "supabase_jwt_secret", "test-jwt-secret-value")


def test_root_is_public(client: TestClient) -> None:
    res = client.get("/")
    assert res.status_code == 200
    assert res.json() == {"message": "Northstar API running"}


def test_health_is_public(client: TestClient) -> None:
    """Render's healthCheckPath points here (backend/render.yaml)."""
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    # Also reports which build answered, so "is the new code deployed?" is a
    # curl rather than a guess. "local" off Vercel; a short SHA on it.
    assert body["commit"]
    assert body["semantic"] in ("available", "unconfigured", "unavailable")
    assert body["advisor"] in ("available", "unconfigured", "unavailable")


def test_health_reports_unconfigured_when_the_llm_key_is_absent(
    client: TestClient,
) -> None:
    """The first version of /health checked whether app.embeddings IMPORTED,
    which is true on a host with no LLM_API_KEY — so it answered "available"
    for a feature that cannot run. Both /advisor and every profile embedding
    need that key, and production did not have it while the code and the
    frontend looked fine. A health check that goes green on the outage it was
    written to catch is worse than no health check."""
    from app import settings as settings_module

    original = settings_module.settings.llm_api_key
    try:
        settings_module.settings.llm_api_key = ""
        body = client.get("/health").json()
        assert body["status"] == "ok", "a missing key is not a liveness failure"
        assert body["semantic"] == "unconfigured"
        assert body["advisor"] == "unconfigured"
    finally:
        settings_module.settings.llm_api_key = original


@pytest.mark.parametrize("path", PROTECTED_GETS)
def test_protected_get_requires_auth(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("path", PROTECTED_GETS)
def test_protected_get_rejects_garbage_token(client: TestClient, path: str) -> None:
    res = client.get(path, headers={"Authorization": "Bearer not-a-jwt"})
    assert res.status_code == 401


def test_protected_writes_require_auth(client: TestClient) -> None:
    assert client.post("/students", json={}).status_code == 401
    assert client.post("/bookmarks", json={"opportunity_id": "x"}).status_code == 401
    assert client.post("/outcomes", json={"opportunity_id": "x", "status": "accepted"}).status_code == 401
    assert client.delete("/bookmarks/x").status_code == 401


def test_server_without_jwt_secret_fails_closed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A deploy that forgot SUPABASE_JWT_SECRET must refuse traffic, not serve it."""
    from app import auth as auth_mod

    monkeypatch.setattr(auth_mod.settings, "supabase_jwt_secret", "")
    res = client.get("/me", headers={"Authorization": "Bearer anything"})
    assert res.status_code == 500
    assert "SUPABASE_JWT_SECRET" in res.json()["detail"]


def test_every_route_except_public_ones_declares_auth() -> None:
    """No route may be added later without the RequireUser dependency."""
    app = create_app()
    public = {
        "/", "/health", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc",
        # Deliberately public: serves opt-in highlight data only, uniform
        # 404 for private/unknown handles (see app/main.py public_profile).
        "/public/{handle}",
        # Deliberately public: the high-school shelf, so a visitor who has not
        # made an account sees opportunities rather than an empty page. Every
        # catalog route was gated until 2026-10-05, and /opportunities,
        # /discover and /plan each rendered zero rows signed out while the API
        # answered 401 — which reads as broken rather than as gated.
        #
        # It is a separate route from /catalog precisely so this entry is not a
        # loophole: /catalog returns the whole row including added_by,
        # verified_at and retired_reason, while this one serves an allowlist of
        # fields. A column added to the table later stays private until someone
        # adds it there on purpose.
        #
        # Under /catalog/ and not /public/ because `/public/{handle}` matches
        # any string and is registered first, so `/public/catalog` was being
        # served as a profile lookup and 404ing.
        "/catalog/public",
    }

    for route in app.routes:
        path = getattr(route, "path", None)
        if path is None or path in public:
            continue
        dependant = getattr(route, "dependant", None)
        if dependant is None:
            continue
        names = {d.call.__name__ for d in dependant.dependencies if d.call is not None}
        assert "get_current_user" in names, f"{path} is not auth-gated"


def test_public_catalog_serves_an_allowlist_not_the_row() -> None:
    """The open internet gets what a student needs to judge an opportunity, and
    nothing about how it got here.

    /catalog returns dict(row), which carries added_by, verified_at,
    retired_reason and the recurrence columns. None of that is secret and all of
    it is curation bookkeeping. This route exists so that distinction is
    enforced by construction rather than by remembering.
    """
    import ast
    import inspect
    import textwrap

    from app import main as main_mod

    src = inspect.getsource(main_mod.create_app)
    start = src.index('@app.get("/catalog/public")')
    body = src[start : src.index('@app.get("/catalog")', start)]

    # Parse the allowlist rather than grep the text: this function's own
    # docstring NAMES the columns it withholds, and a substring check would
    # punish the explanation instead of the behaviour.
    tree = ast.parse(textwrap.dedent(body.split("\n", 1)[1]))
    fields: tuple[str, ...] = ()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", "") == "PUBLIC_FIELDS" for t in node.targets
        ):
            fields = tuple(
                el.value for el in node.value.elts if isinstance(el, ast.Constant)
            )
    assert fields, "PUBLIC_FIELDS not found; the shape must stay an allowlist"

    for withheld in ("added_by", "verified_at", "retired_at", "retired_reason",
                     "recurrence_month", "recurrence_verified_at", "description"):
        assert withheld not in fields, (
            f"the public catalog would expose {withheld}, which is curation "
            "bookkeeping, not something a visitor needs"
        )
    # And it must still carry the things that make a row actionable.
    for needed in ("title", "host", "url", "deadline", "cost"):
        assert needed in fields, f"the public catalog omits {needed}"

    # Retired rows are never browsable, and this is the high-school shelf.
    assert 'is_("retired_at", "null")' in body
    assert '"high_school"' in body


def test_locality_is_the_one_thing_recall_cannot_give_and_must_survive() -> None:
    """Measured 2026-10-05: a frontier model with no web access, asked to recall
    24 curated catalog rows, knew all 24 existed. The catalog's existence claim
    is therefore not a differentiator. Locality is: no model can say which of
    Alabama's four ISEF-affiliated fairs serves Bullock County.

    That fact was already being scraped and then dropped. scrape_sciencefairs.py
    extracts each fair's territory and passes "Bullock County, AL";
    app/verifier.py collapsed it into location_scope — an enum of three values —
    and every regional fair in the catalog read location=NULL.
    """
    import ast
    import inspect
    import textwrap

    from app import main as main_mod
    from app.verifier import parse_locality

    src = inspect.getsource(main_mod.create_app)
    start = src.index('@app.get("/catalog/public")')
    body = src[start : src.index('@app.get("/catalog")', start)]
    tree = ast.parse(textwrap.dedent(body.split("\n", 1)[1]))
    fields = ()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", "") == "PUBLIC_FIELDS" for t in node.targets
        ):
            fields = tuple(e.value for e in node.value.elts if isinstance(e, ast.Constant))
    for needed in ("state", "location"):
        assert needed in fields, (
            f"the public catalog drops {needed}, which is the only field in it a "
            "chat model cannot produce from memory"
        )

    # Conservative by design: a wrong state is worse than none, because it drops
    # the row out of the filter for the student it belongs to.
    assert parse_locality("Bullock County, AL") == ("Bullock County", "AL")
    assert parse_locality("Woods Hole, MA") == ("Woods Hole", "MA")
    assert parse_locality("Some Place, ZZ") == ("Some Place, ZZ", None)
    # A scope word is not a place. Three rows were written location='us' on the
    # first backfill before this was tightened.
    for scope_word in ("us", "USA", "global", "online", "Various", "international"):
        assert parse_locality(scope_word) == (None, None), f"{scope_word} became a place"
