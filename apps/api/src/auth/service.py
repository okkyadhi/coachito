"""User find-or-create, workspace membership lookup, token issuance helper."""

from datetime import UTC, datetime
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt import TokenPairOut, issue_token_pair
from src.auth.magic import register_refresh_jti
from src.db.models.user import User
from src.db.models.workspace import WorkspaceMembership


def _name_from_email(email: str) -> str:
    return email.split("@", 1)[0].replace(".", " ").replace("_", " ").title() or email


async def find_or_create_user_by_email(
    db: AsyncSession, email: str, display_name: str | None = None
) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is not None:
        return user
    user = User(
        email=email,
        display_name=display_name or _name_from_email(email),
    )
    db.add(user)
    await db.flush()
    return user


async def find_or_create_user_by_google(
    db: AsyncSession,
    *,
    google_sub: str,
    email: str,
    display_name: str,
) -> User:
    # Match by google_sub first (the stable identifier)
    result = await db.execute(select(User).where(User.google_sub == google_sub))
    user = result.scalar_one_or_none()
    if user is not None:
        # Refresh email/name in case they changed
        if email and user.email != email:
            user.email = email
        if display_name and user.display_name != display_name:
            user.display_name = display_name
        await db.flush()
        return user

    # Fall back to email — link the google_sub to an existing magic-link user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is not None:
        user.google_sub = google_sub
        if display_name and not user.display_name:
            user.display_name = display_name
        await db.flush()
        return user

    user = User(
        email=email,
        google_sub=google_sub,
        display_name=display_name or _name_from_email(email),
    )
    db.add(user)
    await db.flush()
    return user


async def get_primary_workspace_id(
    db: AsyncSession, user_id: UUID
) -> UUID | None:
    """Returns the most recently joined active workspace for the user, or None."""
    result = await db.execute(
        select(WorkspaceMembership.workspace_id)
        .where(WorkspaceMembership.user_id == user_id)
        .where(WorkspaceMembership.status == "active")
        .order_by(WorkspaceMembership.joined_at.desc().nulls_last())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_role_in_workspace(
    db: AsyncSession, user_id: UUID, workspace_id: UUID | None
) -> str | None:
    """Role string for the membership row tying user to workspace.  None if
    there is no workspace yet."""
    if workspace_id is None:
        return None
    result = await db.execute(
        select(WorkspaceMembership.role)
        .where(WorkspaceMembership.user_id == user_id)
        .where(WorkspaceMembership.workspace_id == workspace_id)
        .where(WorkspaceMembership.status == "active")
        .limit(1)
    )
    return result.scalar_one_or_none()


async def touch_last_seen(db: AsyncSession, user: User) -> None:
    user.last_seen_at = datetime.now(UTC)
    await db.flush()


async def issue_and_register_token_pair(
    *,
    user_id: UUID,
    workspace_id: UUID | None,
    redis: Redis,
) -> TokenPairOut:
    """Mint an access+refresh pair and register the refresh jti for rotation."""
    tokens = issue_token_pair(user_id, workspace_id)
    ttl_seconds = max(int(tokens.refresh_exp.timestamp() - datetime.now(UTC).timestamp()), 1)
    await register_refresh_jti(
        redis,
        user_id=str(user_id),
        jti=tokens.refresh_jti,
        ttl_seconds=ttl_seconds,
    )
    return tokens
