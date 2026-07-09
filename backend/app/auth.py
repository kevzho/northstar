"""
FastAPI auth dependency for Supabase JWT verification.

Supabase Auth signs its JWTs HS256 with ``SUPABASE_JWT_SECRET`` (Dashboard ->
Project Settings -> API -> JWT Secret). The ``sub`` claim is the
``auth.users.id`` UUID, which we key student rows by.

Exposes :func:`get_current_user` — a FastAPI dependency that reads the
``Authorization: Bearer <token>`` header, verifies it with PyJWT, and returns
a :class:`CurrentUser` (id + optional email). Any failure raises 401 so
route handlers stay free of JWT plumbing.
"""

from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel

from .settings import settings

# Supabase uses HS256 for project JWTs. Hard-coding the algorithm list is
# deliberate: PyJWT only accepts algorithms you name here, so listing only
# HS256 blocks "alg=none" / algorithm-confusion bypasses.
_ALG = ["HS256"]


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

    secret = settings.supabase_jwt_secret
    if not secret:
        # Fail-closed: a backend without the secret must not accept traffic.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server is missing SUPABASE_JWT_SECRET",
        )

    try:
        payload = jwt.decode(token, secret, algorithms=_ALG)
    except jwt.PyJWTError as exc:  # expired, bad signature, malformed
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
    return CurrentUser(id=str(sub), email=payload.get("email"))


# Convenience alias for route signatures: user: CurrentUser = RequireUser
RequireUser = Depends(get_current_user)
