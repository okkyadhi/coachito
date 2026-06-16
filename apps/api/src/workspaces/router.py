"""Workspace endpoints: create, list mine, switch."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.service import issue_and_register_token_pair
from src.db.models.workspace import Workspace
from src.deps import get_current_user_id, get_redis
from src.middleware.rls import db_with_rls
from src.sports.service import list_workspace_sports

from .schemas import (
    TokenBundle,
    WorkspaceCreateIn,
    WorkspaceCreateOut,
    WorkspaceMembershipOut,
    WorkspaceOut,
    WorkspacesListOut,
    WorkspaceSportOut,
)
from .service import (
    create_workspace_with_owner,
    find_active_membership,
    list_workspaces_for_user,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


async def _to_workspace_out(db: AsyncSession, ws: Workspace) -> WorkspaceOut:
    sports = await list_workspace_sports(db, workspace_id=ws.id)
    return WorkspaceOut(
        id=str(ws.id),
        sport_id=str(ws.sport_id),
        sports=[WorkspaceSportOut(**s) for s in sports],
        type=ws.type,
        name=ws.name,
        slug=ws.slug,
        city=ws.city,
        brand_color=ws.brand_color,
        logo_url=ws.logo_url,
        tier_style=ws.tier_style,
        primary_locale=ws.primary_locale,
        plan=ws.plan,
        trial_ends_at=ws.trial_ends_at,
        active_trainee_quota=ws.active_trainee_quota,
        owner_user_id=str(ws.owner_user_id),
        created_at=ws.created_at,
        archived_at=ws.archived_at,
    )


# ── POST /workspaces ─────────────────────────────────────────────


@router.post("", response_model=WorkspaceCreateOut, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    body: WorkspaceCreateIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    redis: Annotated[Redis, Depends(get_redis)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> WorkspaceCreateOut:
    workspace = await create_workspace_with_owner(
        db,
        owner_user_id=user_id,
        type_=body.type,
        name=body.name,
        primary_locale=body.primary_locale,
        city=body.city,
        brand_color=body.brand_color,
    )
    tokens = await issue_and_register_token_pair(
        user_id=user_id, workspace_id=workspace.id, redis=redis
    )
    # Build the response (which reads workspace_sports under RLS) BEFORE
    # commit, while the request's SET LOCAL GUCs are still in scope — after
    # commit the GUCs are gone and RLS would hide the freshly-created rows.
    workspace_out = await _to_workspace_out(db, workspace)
    await db.commit()

    return WorkspaceCreateOut(
        workspace=workspace_out,
        tokens=TokenBundle(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
            workspace_id=str(workspace.id),
        ),
    )


# ── GET /workspaces/mine ─────────────────────────────────────────


@router.get("/mine", response_model=WorkspacesListOut)
async def list_my_workspaces(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> WorkspacesListOut:
    rows = await list_workspaces_for_user(db, user_id)
    return WorkspacesListOut(
        workspaces=[
            WorkspaceMembershipOut(
                workspace=await _to_workspace_out(db, ws),
                role=mem.role,
                status=mem.status,
                joined_at=mem.joined_at,
            )
            for ws, mem in rows
        ]
    )


# ── POST /workspaces/{id}/switch ─────────────────────────────────


@router.post("/{workspace_id}/switch", response_model=TokenBundle)
async def switch_workspace(
    workspace_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    redis: Annotated[Redis, Depends(get_redis)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> TokenBundle:
    membership = await find_active_membership(
        db, user_id=user_id, workspace_id=workspace_id
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace.",
        )
    tokens = await issue_and_register_token_pair(
        user_id=user_id, workspace_id=workspace_id, redis=redis
    )
    return TokenBundle(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        workspace_id=str(workspace_id),
    )
