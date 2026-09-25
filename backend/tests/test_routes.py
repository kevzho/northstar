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
