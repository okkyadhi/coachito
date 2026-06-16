"""RLS context for the current request.

A FastAPI dependency that sets two Postgres GUCs on the request's session:

  - app.current_workspace_id  — from the JWT's `wsid` claim (or empty)
  - app.current_user_id       — from the JWT's `sub` claim (or empty)

The user-id GUC lets policies on cross-workspace tables (notably
`workspace_memberships`) allow a user to see their own rows without having a
workspace context.  Routes that touch tenant-scoped tables should depend on
`db_with_rls`; routes that don't read tenant data (e.g. /auth, /workspaces)
can depend on `get_session` directly.
"""

from collections.abc import AsyncGenerator
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt import decode_token
from src.db.session import get_session

_optional_bearer = HTTPBearer(auto_error=False)


def _claims_for_context(
    credentials: HTTPAuthorizationCredentials | None,
) -> dict[str, Any] | None:
    """Best-effort decode for RLS context.  Returns None on any failure so the
    request continues with empty context (the policies treat that as 'no
    workspace' / 'no user', i.e. platform-only visibility)."""
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        return None
    if payload.get("type") != "access":
        return None
    return payload


async def db_with_rls(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_optional_bearer)
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncGenerator[AsyncSession, None]:
    claims = _claims_for_context(credentials)
    wsid = claims.get("wsid") if claims else None
    sub = claims.get("sub") if claims else None
    await db.execute(
        text(
            """
            SELECT set_config('app.current_workspace_id', :wid, TRUE),
                   set_config('app.current_user_id', :uid, TRUE)
            """
        ),
        {"wid": str(wsid) if wsid else "", "uid": str(sub) if sub else ""},
    )
    yield db


async def set_user_context(db: AsyncSession, user_id: UUID) -> None:
    """Manually set app.current_user_id for auth flows that find the user
    before any JWT exists (magic-link consume, Google sign-in, refresh).

    Without this, the workspace_memberships RLS policy hides the user's own
    rows and ``get_primary_workspace_id`` returns None even when a membership
    exists.
    """
    await db.execute(
        text("SELECT set_config('app.current_user_id', :uid, TRUE)"),
        {"uid": str(user_id)},
    )
