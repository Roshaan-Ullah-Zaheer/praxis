"""Optional Supabase JWT authentication.

When ``SUPABASE_JWT_SECRET`` is set, a bearer token in the Authorization header is
verified and its subject becomes the owner id. Otherwise the app runs in
single-user demo mode (the public demo needs no login), so every existing route
keeps working unchanged.
"""

from __future__ import annotations

import logging

from fastapi import Header

from . import config

logger = logging.getLogger(__name__)


def owner_from_token(authorization: str | None) -> str:
    if not config.SUPABASE_JWT_SECRET or not authorization:
        return config.DEFAULT_OWNER
    token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else authorization.strip()
    try:
        import jwt  # lazy import so the package is only needed when auth is enabled

        payload = jwt.decode(
            token,
            config.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload.get("sub") or config.DEFAULT_OWNER
    except Exception as exc:  # noqa: BLE001 - invalid token falls back to demo
        logger.warning("token verification failed: %s", exc)
        return config.DEFAULT_OWNER


def current_owner(authorization: str | None = Header(default=None)) -> str:
    """FastAPI dependency: the active owner id (demo user when auth is disabled)."""
    return owner_from_token(authorization)
