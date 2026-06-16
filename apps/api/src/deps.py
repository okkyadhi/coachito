"""Shared FastAPI dependencies: redis client + auth claims/user-id/wsid.

RLS context (setting app.current_workspace_id / app.current_user_id GUCs) lives
in src/middleware/rls.py — depend on `db_with_rls` from there when a route
touches tenant-scoped tables.
"""

from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis

from src.auth.jwt import decode_token
from src.config import settings

# ── Redis client (singleton; closed in main.py lifespan) ─────────

_redis_client: Redis | None = None


def get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


# ── Auth dependencies ────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=False)


def _claims_from_credentials(
    credentials: HTTPAuthorizationCredentials | None,
    *,
    expected_type: str,
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )
    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired."
        ) from e
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token."
        ) from e
    if payload.get("type") != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Expected a {expected_type} token.",
        )
    return payload


def get_access_claims(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ],
) -> dict[str, Any]:
    return _claims_from_credentials(credentials, expected_type="access")


def get_refresh_claims(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ],
) -> dict[str, Any]:
    return _claims_from_credentials(credentials, expected_type="refresh")


def get_current_user_id(
    claims: Annotated[dict[str, Any], Depends(get_access_claims)],
) -> UUID:
    return UUID(claims["sub"])


def get_current_workspace_id(
    claims: Annotated[dict[str, Any], Depends(get_access_claims)],
) -> UUID | None:
    wsid = claims.get("wsid")
    return UUID(wsid) if wsid else None


