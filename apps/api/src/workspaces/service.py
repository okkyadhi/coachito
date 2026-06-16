"""Workspace + membership operations."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.sport import Sport
from src.db.models.workspace import Workspace, WorkspaceMembership
from src.sports.service import (
    default_curriculum_for_sport,
    enable_sport,
    set_membership_sports,
)

TRIAL_DAYS = 30


async def _get_padel_sport_id(db: AsyncSession) -> UUID:
    result = await db.execute(select(Sport.id).where(Sport.code == "padel"))
    sport_id = result.scalar_one_or_none()
    if sport_id is None:
        raise RuntimeError("padel sport row is missing — run the seed.")
    return sport_id


async def create_workspace_with_owner(
    db: AsyncSession,
    *,
    owner_user_id: UUID,
    type_: str,
    name: str,
    primary_locale: str,
    city: str | None = None,
    brand_color: str | None = None,
    sport_ids: list[UUID] | None = None,
    plan: str = "free_trial",
    trial_days: int = TRIAL_DAYS,
) -> Workspace:
    """Create a workspace and the owner's active membership in one transaction.

    Caller commits.

    ``sport_ids`` controls multi-sport enrollment. When omitted, defaults to
    just padel — keeps existing single-sport callers working unchanged. The
    first sport in the list also seeds the legacy ``workspaces.sport_id`` /
    ``curriculum_id`` columns during the dual-write window.
    """
    if not sport_ids:
        sport_ids = [await _get_padel_sport_id(db)]
    primary_sport_id = sport_ids[0]
    now = datetime.now(UTC)

    workspace = Workspace(
        sport_id=primary_sport_id,
        type=type_,
        name=name,
        city=city,
        brand_color=brand_color,
        primary_locale=primary_locale,
        plan=plan,
        trial_ends_at=now + timedelta(days=trial_days),
        owner_user_id=owner_user_id,
    )
    db.add(workspace)
    await db.flush()

    membership = WorkspaceMembership(
        workspace_id=workspace.id,
        user_id=owner_user_id,
        role="club_admin" if type_ == "club" else "coach",
        status="active",
        invited_at=now,
        joined_at=now,
        invited_by_id=owner_user_id,
    )
    db.add(membership)
    await db.flush()

    # Multi-sport dual-write: register each sport + the owner's qualification.
    # Legacy workspaces.sport_id stays in lockstep with the first sport during
    # the migration window.
    for sid in sport_ids:
        curriculum_id = await default_curriculum_for_sport(db, sport_id=sid)
        await enable_sport(
            db, workspace_id=workspace.id, sport_id=sid, curriculum_id=curriculum_id
        )
    await set_membership_sports(
        db,
        workspace_id=workspace.id,
        membership_id=membership.id,
        sport_ids=sport_ids,
    )
    return workspace


async def list_workspaces_for_user(
    db: AsyncSession, user_id: UUID
) -> list[tuple[Workspace, WorkspaceMembership]]:
    """All active, non-archived workspaces the user belongs to, newest first."""
    result = await db.execute(
        select(Workspace, WorkspaceMembership)
        .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
        .where(WorkspaceMembership.user_id == user_id)
        .where(WorkspaceMembership.status == "active")
        .where(Workspace.archived_at.is_(None))
        .order_by(WorkspaceMembership.joined_at.desc().nulls_last())
    )
    return list(result.all())


async def find_active_membership(
    db: AsyncSession, *, user_id: UUID, workspace_id: UUID
) -> WorkspaceMembership | None:
    result = await db.execute(
        select(WorkspaceMembership)
        .where(WorkspaceMembership.user_id == user_id)
        .where(WorkspaceMembership.workspace_id == workspace_id)
        .where(WorkspaceMembership.status == "active")
    )
    return result.scalar_one_or_none()
