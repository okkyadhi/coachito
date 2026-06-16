"""Coach management endpoints.

  GET    /workspaces/me/members
  POST   /workspaces/me/members/invite
  PATCH  /workspaces/me/members/{membership_id}
  DELETE /workspaces/me/members/{membership_id}
  DELETE /workspaces/me/members/invites/{invite_id}

Authorization:
  - View: any active member of the workspace.
  - Mutations: only ``club_admin``.

Constraints we enforce here (not at the DB layer):
  - You cannot remove or demote the workspace owner — they keep ``club_admin``
    perpetually so the workspace always has at least one admin.
  - You cannot remove yourself via DELETE.  The club_admin who wants to leave
    needs to transfer ownership first (V1.5 — not built yet).
  - Roles allowed on coach memberships: ``coach``, ``head_coach``.
    Inviting a ``club_admin`` from this endpoint is not supported at MVP;
    additional admins live in V1.5 (multi-admin).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.decorators import audit_action
from src.auth.service import get_role_in_workspace
from src.config import settings as app_settings
from src.db.models.athlete import Athlete
from src.db.models.invite import Invite
from src.db.models.user import User
from src.db.models.workspace import Workspace, WorkspaceMembership
from src.deps import get_current_user_id, get_current_workspace_id
from src.invites.service import (
    expiry_from_now,
    generate_invite_code,
    is_invite_active,
    public_landing_url,
)
from src.middleware.rls import db_with_rls

router = APIRouter(prefix="/workspaces/me/members", tags=["workspaces"])


# ── Schemas ─────────────────────────────────────────────────────


CoachRole = Literal["coach", "head_coach"]
AnyMemberRole = Literal["club_admin", "head_coach", "coach"]


class MemberOut(BaseModel):
    id: str  # membership_id
    user_id: str
    email: str | None
    display_name: str
    role: AnyMemberRole
    joined_at: datetime | None
    is_owner: bool
    is_self: bool


class PendingInviteOut(BaseModel):
    id: str
    email: str | None
    role: AnyMemberRole
    invite_code: str
    landing_url: str
    expires_at: datetime
    invited_at: datetime


class MembersListOut(BaseModel):
    members: list[MemberOut]
    pending_invites: list[PendingInviteOut]
    coach_count: int  # active members where role in {club_admin, head_coach, coach}
    trainee_count: int  # active athletes (not archived)


class InviteCoachIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)
    role: CoachRole = "coach"


class InviteCoachOut(BaseModel):
    id: str
    email: str
    role: CoachRole
    invite_code: str
    landing_url: str
    expires_at: datetime


class MemberRolePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: CoachRole


# ── Helpers ─────────────────────────────────────────────────────


async def _require_workspace_and_admin(
    db: AsyncSession,
    user_id: UUID,
    workspace_id: UUID | None,
) -> Workspace:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No active workspace."
        )
    ws = (
        await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ).scalar_one_or_none()
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found."
        )
    role = await get_role_in_workspace(db, user_id, workspace_id)
    is_owner = ws.owner_user_id == user_id
    if role != "club_admin" and not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the workspace admin can manage coaches.",
        )
    return ws


# ── GET /workspaces/me/members ──────────────────────────────────


@router.get("", response_model=MembersListOut)
async def list_members(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> MembersListOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No active workspace."
        )
    ws = (
        await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ).scalar_one_or_none()
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found."
        )
    role = await get_role_in_workspace(db, user_id, workspace_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace.",
        )

    rows = (
        await db.execute(
            select(WorkspaceMembership, User)
            .join(User, User.id == WorkspaceMembership.user_id)
            .where(WorkspaceMembership.workspace_id == workspace_id)
            .where(WorkspaceMembership.status == "active")
            .where(WorkspaceMembership.role.in_(("club_admin", "head_coach", "coach")))
            .order_by(WorkspaceMembership.joined_at.asc().nulls_last())
        )
    ).all()

    members = [
        MemberOut(
            id=str(m.id),
            user_id=str(u.id),
            email=u.email,
            display_name=u.display_name,
            role=m.role,  # type: ignore[arg-type]
            joined_at=m.joined_at,
            is_owner=u.id == ws.owner_user_id,
            is_self=u.id == user_id,
        )
        for (m, u) in rows
    ]

    pending_rows = (
        await db.execute(
            select(Invite)
            .where(Invite.workspace_id == workspace_id)
            .where(Invite.role.in_(("club_admin", "head_coach", "coach")))
            .where(Invite.claimed_at.is_(None))
            .where(Invite.revoked_at.is_(None))
            .order_by(Invite.created_at.desc())
        )
    ).scalars().all()
    pending: list[PendingInviteOut] = []
    for inv in pending_rows:
        if not is_invite_active(inv):
            continue
        pending.append(
            PendingInviteOut(
                id=str(inv.id),
                email=inv.email,
                role=inv.role,  # type: ignore[arg-type]
                invite_code=inv.invite_code,
                landing_url=public_landing_url(inv.invite_code),
                expires_at=inv.expires_at,
                invited_at=inv.created_at,
            )
        )

    # Trainee count — active athletes in this workspace.  RLS already scopes us
    # but the explicit filter keeps the query honest if RLS is bypassed.
    trainee_count = int(
        await db.scalar(
            select(func.count(Athlete.id))
            .where(Athlete.workspace_id == workspace_id)
            .where(Athlete.archived_at.is_(None))
        )
        or 0
    )

    return MembersListOut(
        members=members,
        pending_invites=pending,
        coach_count=len(members),
        trainee_count=trainee_count,
    )


# ── POST /workspaces/me/members/invite ──────────────────────────


@router.post(
    "/invite",
    response_model=InviteCoachOut,
    status_code=status.HTTP_201_CREATED,
)
@audit_action(
    "coach.invited",
    entity_type="invite",
    extract=lambda r, kw: {"email": r.email, "role": r.role},
)
async def invite_coach(
    body: InviteCoachIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> InviteCoachOut:
    ws = await _require_workspace_and_admin(db, user_id, workspace_id)

    email_normalized = body.email.strip().lower()

    # Block dupes: if there's already an active member with this email, 409.
    existing_member = (
        await db.execute(
            select(WorkspaceMembership.id)
            .join(User, User.id == WorkspaceMembership.user_id)
            .where(WorkspaceMembership.workspace_id == ws.id)
            .where(WorkspaceMembership.status == "active")
            .where(func.lower(User.email) == email_normalized)
        )
    ).scalar_one_or_none()
    if existing_member is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email already belongs to a member of this workspace.",
        )

    # Revoke any pending invite to the same email in the same workspace so the
    # admin doesn't accumulate stale links.  Cheap to do unconditionally.
    now = datetime.now(UTC)
    await db.execute(
        Invite.__table__.update()
        .where(Invite.workspace_id == ws.id)
        .where(func.lower(Invite.email) == email_normalized)
        .where(Invite.claimed_at.is_(None))
        .where(Invite.revoked_at.is_(None))
        .values(revoked_at=now)
    )

    code = generate_invite_code(ws, body.display_name)
    invite = Invite(
        workspace_id=ws.id,
        email=email_normalized,
        phone_e164=None,
        role=body.role,
        athlete_id=None,
        invite_code=code,
        invited_by_id=user_id,
        invited_user_id=None,
        expires_at=expiry_from_now(),
    )
    db.add(invite)
    await db.flush()
    # Capture before commit closes the session.
    out = InviteCoachOut(
        id=str(invite.id),
        email=invite.email or email_normalized,
        role=body.role,
        invite_code=invite.invite_code,
        landing_url=public_landing_url(invite.invite_code),
        expires_at=invite.expires_at,
    )
    await db.commit()
    return out


# ── PATCH /workspaces/me/members/{id} ───────────────────────────


@router.patch("/{membership_id}", response_model=MemberOut)
@audit_action(
    "coach.role_changed",
    entity_type="workspace_membership",
    extract=lambda r, kw: {
        "membership_id": str(r.id),
        "new_role": r.role,
        "user_id": r.user_id,
    },
)
async def patch_member_role(
    membership_id: UUID,
    body: MemberRolePatch,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> MemberOut:
    ws = await _require_workspace_and_admin(db, user_id, workspace_id)

    row = (
        await db.execute(
            select(WorkspaceMembership, User)
            .join(User, User.id == WorkspaceMembership.user_id)
            .where(WorkspaceMembership.id == membership_id)
            .where(WorkspaceMembership.workspace_id == ws.id)
        )
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found."
        )
    mem, user = row

    if mem.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This membership is not active.",
        )
    if user.id == ws.owner_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The workspace owner's role cannot be changed.",
        )
    if mem.role == "club_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin roles can't be changed via this endpoint.",
        )

    if mem.role == body.role:
        # No-op — return the current state.
        return _to_member_out(mem, user, ws, user_id)

    mem.role = body.role
    await db.flush()
    out = _to_member_out(mem, user, ws, user_id)
    await db.commit()
    return out


# ── DELETE /workspaces/me/members/{id} ──────────────────────────


@router.delete("/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_action(
    "coach.removed",
    entity_type="workspace_membership",
    extract=lambda r, kw: {"membership_id": str(kw.get("membership_id"))},
)
async def remove_member(
    membership_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> None:
    ws = await _require_workspace_and_admin(db, user_id, workspace_id)

    row = (
        await db.execute(
            select(WorkspaceMembership, User)
            .join(User, User.id == WorkspaceMembership.user_id)
            .where(WorkspaceMembership.id == membership_id)
            .where(WorkspaceMembership.workspace_id == ws.id)
        )
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found."
        )
    mem, user = row

    if user.id == ws.owner_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The workspace owner cannot be removed.",
        )
    if user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot remove yourself. Ask another admin.",
        )
    if mem.status != "active":
        # Idempotent: already archived.
        return None

    mem.status = "archived"
    mem.archived_at = datetime.now(UTC)
    await db.flush()
    await db.commit()
    return None


# ── DELETE /workspaces/me/members/invites/{id} ──────────────────


@router.delete(
    "/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT
)
@audit_action(
    "coach.invite_revoked",
    entity_type="invite",
    extract=lambda r, kw: {"invite_id": str(kw.get("invite_id"))},
)
async def revoke_invite(
    invite_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> None:
    ws = await _require_workspace_and_admin(db, user_id, workspace_id)
    invite = (
        await db.execute(
            select(Invite)
            .where(Invite.id == invite_id)
            .where(Invite.workspace_id == ws.id)
        )
    ).scalar_one_or_none()
    if invite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found."
        )
    if invite.claimed_at is not None or invite.revoked_at is not None:
        return None
    invite.revoked_at = datetime.now(UTC)
    await db.flush()
    await db.commit()
    return None


# ── Helpers ─────────────────────────────────────────────────────


def _to_member_out(
    mem: WorkspaceMembership,
    user: User,
    ws: Workspace,
    current_user_id: UUID,
) -> MemberOut:
    return MemberOut(
        id=str(mem.id),
        user_id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        role=mem.role,  # type: ignore[arg-type]
        joined_at=mem.joined_at,
        is_owner=user.id == ws.owner_user_id,
        is_self=user.id == current_user_id,
    )


_ = app_settings  # imported for parity with other workspace modules
