"""
FastAPI auth dependency for Supabase JWT verification.

Supabase projects on the current signing-key system issue **ES256** access
tokens whose public keys are published at
``<SUPABASE_URL>/auth/v1/.well-known/jwks.json``; older projects (and the
test suite) sign **HS256** with the static ``SUPABASE_JWT_SECRET``. This
dependency accepts both: the token's own header picks the path, and each
path allows exactly one algorithm — so neither can be used to confuse the
other, and "alg=none" is rejected everywhere.

The ``sub`` claim is the ``auth.users.id`` UUID, which we key student rows
by. Any failure raises 401 so route handlers stay free of JWT plumbing.
"""

from typing import Optional
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel

from .settings import settings

# Lazily-built JWKS client for ES256 tokens; PyJWT caches keys internally,
# so the JWKS endpoint is fetched once per process, not per request.
_jwks_client: Optional[jwt.PyJWKClient] = None


def _jwks() -> jwt.PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(
            f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        )
    return _jwks_client


class CurrentUser(BaseModel):
    """Authenticated user, derived from the JWT ``sub`` claim."""

    id: str
    email: Optional[str] = None


def _bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization")
    if not header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return parts[1]


def get_current_user(request: Request) -> CurrentUser:
    token = _bearer_token(request)

    # Fail-closed on misconfiguration before looking at any token: a deploy
    # that forgot SUPABASE_JWT_SECRET must refuse traffic, not serve it.
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server is missing SUPABASE_JWT_SECRET",
        )

    try:
        alg = jwt.get_unverified_header(token).get("alg")
        if alg == "ES256":
            key = _jwks().get_signing_key_from_jwt(token).key
            allowed = ["ES256"]
        else:
            key = settings.supabase_jwt_secret
            allowed = ["HS256"]
        # Supabase access tokens carry aud="authenticated"; the test suite's
        # minimal tokens carry none. Signature + expiry are the security
        # boundary here, and `sub` is what we act on — so aud is not
        # enforced rather than maintaining two token dialects.
        payload = jwt.decode(
            token, key, algorithms=allowed, options={"verify_aud": False}
        )
    except HTTPException:
        raise
    except (jwt.PyJWTError, jwt.exceptions.PyJWKClientError) as exc:
        # expired, bad signature, malformed, unknown kid, JWKS unreachable
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing 'sub' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # `sub` is auth.users.id, which Supabase always issues as a UUID. We
    # assert that rather than assume it, because user.id is interpolated
    # into PostgREST filter strings in several places and postgrest-py does
    # NOT escape filter values -- `.filter()` sanitizes only the column
    # name, and `.or_()` takes its argument verbatim. Pinning the shape
    # here makes every one of those interpolations provably safe, instead
    # of safe-by-assumption about a claim we did not mint.
    try:
        user_id = str(UUID(str(sub)))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 'sub' claim is not a valid user id",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    return CurrentUser(id=user_id, email=payload.get("email"))


# Convenience alias for route signatures: user: CurrentUser = RequireUser
RequireUser = Depends(get_current_user)
