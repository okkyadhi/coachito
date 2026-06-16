"""Platform-admin guard for /admin/* endpoints.

The `users.is_platform_admin` flag is loaded fresh from Postgres on every
request (no JWT claim) so revoking admin access takes effect immediately —
no waiting for the token to expire.  Cost is one round-trip per admin call,
which is negligible relative to the cross-tenant queries those endpoints
already run.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User
from src.db.session import get_session
from src.deps import get_current_user_id


async def require_platform_admin(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> UUID:
    """Yields the admin's user_id when they have the flag; raises 404
    otherwise.  We return 404 (not 403) so unauthenticated probes don't
    confirm the endpoint exists — admin URLs are not advertised to regular
    users."""
    is_admin = (
        await db.execute(
            select(User.is_platform_admin).where(User.id == user_id)
        )
    ).scalar_one_or_none()
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found."
        )
    return user_id
