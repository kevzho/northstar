"""
Regression tests for PostgREST filter injection.

postgrest-py does not escape filter values: `.filter()` sanitizes only the
column name, and `.or_()` interpolates its argument verbatim. Before this
suite, GET /friends/{student_id}/compare took an unvalidated `str` path
parameter and interpolated it straight into the `.or_()` that was its own
authorization gate, and POST /block did the same on two DELETEs.

Every payload below is rejected at the routing or validation layer, before
any handler runs -- so these need no Supabase credentials, and a failure
here means a hostile value once again reaches a query builder.
"""

from __future__ import annotations

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import create_app

SECRET = "test-jwt-secret"
SUB = "3f1a7c4e-9b2d-4e8a-a1c6-5d0e7b2f9a31"

# PostgREST filter grammar, not SQL: the target is the or=(...) parameter.
PAYLOADS = [
    "abc),or(id.not.is.null",
    "00000000-0000-0000-0000-000000000000),or(status.eq.accepted",
    "*",
    "x,addressee.eq.y",
    'a"b',
    "(a,b)",
    "1;drop table students",
    "../../etc/passwd",
]


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch: pytest.MonkeyPatch):
    from app import auth as auth_mod

    monkeypatch.setattr(auth_mod.settings, "supabase_jwt_secret", SECRET)


def _auth() -> dict[str, str]:
    token = jwt.encode({"sub": SUB, "email": "s@example.com"}, SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("payload", PAYLOADS)
def test_compare_rejects_non_uuid_path_param(client: TestClient, payload: str) -> None:
    """The gate that was injectable. 422/404 before the handler; never 200/500."""
    res = client.get(f"/friends/{payload}/compare", headers=_auth())
    assert res.status_code in (404, 422), (
        f"{payload!r} reached the handler with {res.status_code}"
    )


@pytest.mark.parametrize("payload", PAYLOADS)
@pytest.mark.parametrize("path", ["/block", "/report", "/teamup/interest"])
def test_body_ids_reject_non_uuid(client: TestClient, path: str, payload: str) -> None:
    body = {"student_id": payload, "decision": "interested", "reason": "spam"}
    res = client.post(path, json=body, headers=_auth())
    assert res.status_code in (404, 422), (
        f"{path} accepted student_id={payload!r} with {res.status_code}"
    )


@pytest.mark.parametrize("payload", PAYLOADS)
def test_public_handle_rejects_filter_metacharacters(
    client: TestClient, payload: str
) -> None:
    """Unauthenticated, so the most exposed of the three.

    The rejection must be the SAME uniform 404 an unknown handle gets, or the
    endpoint becomes an oracle for which handles exist.
    """
    res = client.get(f"/public/{payload}")
    assert res.status_code == 404, f"{payload!r} -> {res.status_code}"

    # The anti-oracle property: a handle we reject must be indistinguishable
    # from one that simply does not exist. Payloads containing path separators
    # are normalised by the router and never match the route at all, so they
    # get FastAPI's generic 404 from a layer above this endpoint -- which
    # reveals nothing about handles either.
    if "/" not in payload:
        unknown = client.get("/public/definitely-not-a-real-handle")
        assert res.json() == unknown.json(), (
            f"{payload!r} is distinguishable from an unknown handle"
        )


@pytest.mark.parametrize(
    "path",
    [
        "/bookmarks/not-a-uuid",
        "/dismissals/not-a-uuid",
        "/opportunities/not-a-uuid",
        "/missions/not-a-uuid/complete",
        "/friends/not-a-uuid",
    ],
)
def test_id_path_params_are_uuid_typed(client: TestClient, path: str) -> None:
    """422 from FastAPI's own validation, never a 500 from the query layer."""
    method = client.post if path.endswith("/complete") else client.get
    res = method(path, headers=_auth())
    if res.status_code == 405:
        res = client.delete(path, headers=_auth())
    assert res.status_code == 422, f"{path} -> {res.status_code}"
