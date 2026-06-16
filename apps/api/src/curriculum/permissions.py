"""Centralised authorization helpers for curriculum endpoints.

The shape (admin role OR workspace owner) repeats across every PATCH
endpoint — extract once so we don't drift.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.service import get_role_in_workspace
from src.db.models.workspace import Workspace

# Plans allowed to mutate curriculum (enable/disable skills, edit descriptors,
# rename tiers).  Club Starter coaches see read-only curriculum + an upsell.
_PLANS_THAT_CAN_EDIT = {"club_pro", "solo_coach", "free_trial"}
# Roles allowed to mutate.  Owners always pass via the ownership check below.
_EDITOR_ROLES = {"club_admin"}


async def load_workspace_or_404(
    db: AsyncSession, workspace_id: UUID | None
) -> Workspace:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active workspace.",
        )
    ws = (
        await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ).scalar_one_or_none()
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found."
        )
    return ws


async def require_workspace_member(
    db: AsyncSession, user_id: UUID, workspace_id: UUID | None
) -> Workspace:
    """Any active member (or owner) — used for read endpoints."""
    ws = await load_workspace_or_404(db, workspace_id)
    if ws.owner_user_id == user_id:
        return ws
    role = await get_role_in_workspace(db, user_id, ws.id)
    if role not in {"club_admin", "head_coach", "coach"}:
        # Trainees/parents don't see the curriculum admin surface — they get
        # skills via /skills which already gates by membership.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to the curriculum.",
        )
    return ws


async def require_curriculum_admin(
    db: AsyncSession, user_id: UUID, workspace_id: UUID | None
) -> Workspace:
    """Admin role OR workspace owner — used for write endpoints.

    Also enforces the plan gate: Club Starter cannot edit even if the caller
    is the admin.  402 (Payment Required) signals the FE to surface the
    upsell.
    """
    ws = await load_workspace_or_404(db, workspace_id)
    is_owner = ws.owner_user_id == user_id
    role = await get_role_in_workspace(db, user_id, ws.id)
    if role not in _EDITOR_ROLES and not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the workspace admin can edit the curriculum.",
        )
    if ws.plan not in _PLANS_THAT_CAN_EDIT:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Customizing the curriculum requires Club Pro.",
        )
    return ws


async def require_feedback_sender(
    db: AsyncSession, user_id: UUID, workspace_id: UUID | None
) -> Workspace:
    """Coaches send feedback to admin.  Admin/owner can't send to themselves
    — surfaces a 409 so the FE can hide the affordance for them."""
    ws = await load_workspace_or_404(db, workspace_id)
    if ws.owner_user_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You own this workspace — there's no separate admin to send feedback to.",
        )
    role = await get_role_in_workspace(db, user_id, ws.id)
    if role not in {"head_coach", "coach"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only coaches can send curriculum feedback.",
        )
    return ws
