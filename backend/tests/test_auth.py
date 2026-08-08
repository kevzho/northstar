"""JWT verification tests for backend/app/auth.py."""

from __future__ import annotations

import datetime as dt

import jwt
import pytest
from fastapi import HTTPException

from app import auth as auth_mod

SECRET = "test-jwt-secret"


class _FakeRequest:
    def __init__(self, header: str | None):
        self.headers = {} if header is None else {"Authorization": header}


@pytest.fixture(autouse=True)
def _secret(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(auth_mod.settings, "supabase_jwt_secret", SECRET)


def _token(**claims) -> str:
    payload = {"sub": "user-123", "email": "student@example.com"}
    payload.update(claims)
    return jwt.encode(payload, SECRET, algorithm="HS256")


def test_valid_token_yields_user() -> None:
    user = auth_mod.get_current_user(_FakeRequest(f"Bearer {_token()}"))
    assert user.id == "user-123"
    assert user.email == "student@example.com"


@pytest.mark.parametrize(
    "header",
    [None, "", "Bearer", "Token abc", "Bearer ", "Bearer a b"],
)
def test_malformed_authorization_header_is_401(header: str | None) -> None:
    with pytest.raises(HTTPException) as excinfo:
        auth_mod.get_current_user(_FakeRequest(header))
    assert excinfo.value.status_code == 401


def test_wrong_signature_is_401() -> None:
    bad = jwt.encode({"sub": "user-123"}, "not-the-secret", algorithm="HS256")
    with pytest.raises(HTTPException) as excinfo:
        auth_mod.get_current_user(_FakeRequest(f"Bearer {bad}"))
    assert excinfo.value.status_code == 401


def test_expired_token_is_401() -> None:
    past = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
    with pytest.raises(HTTPException) as excinfo:
        auth_mod.get_current_user(_FakeRequest(f"Bearer {_token(exp=past)}"))
    assert excinfo.value.status_code == 401


def test_token_without_sub_is_401() -> None:
    token = jwt.encode({"email": "x@example.com"}, SECRET, algorithm="HS256")
    with pytest.raises(HTTPException) as excinfo:
        auth_mod.get_current_user(_FakeRequest(f"Bearer {token}"))
    assert excinfo.value.status_code == 401


def test_alg_none_token_is_rejected() -> None:
    """PyJWT must not accept an unsigned token even though `sub` is present."""
    unsigned = jwt.encode({"sub": "user-123"}, key="", algorithm="none")
    with pytest.raises(HTTPException) as excinfo:
        auth_mod.get_current_user(_FakeRequest(f"Bearer {unsigned}"))
    assert excinfo.value.status_code == 401


def test_missing_server_secret_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_mod.settings, "supabase_jwt_secret", "")
    with pytest.raises(HTTPException) as excinfo:
        auth_mod.get_current_user(_FakeRequest(f"Bearer {_token()}"))
    assert excinfo.value.status_code == 500
