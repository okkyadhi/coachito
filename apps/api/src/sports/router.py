"""Multi-sport management endpoints (tennis-skill-framework-v0.1 §3.5).

  GET    /workspaces/me/sports                 — list a workspace's sports
  POST   /workspaces/me/sports                 — enable a sport (admin)
  DELETE /workspaces/me/sports/{sport_id}      — archive a sport (admin)
  PATCH  /athletes/{athlete_id}/sports         — set an athlete's sports
  PATCH  /memberships/{membership_id}/sports   — set a coach's sport quals (admin)

Sport availability itself is governed by ``sports.is_active`` — a workspace
can only enable a platform-active sport.  Plan limits (Solo / Club Starter =
1 sport, Club Pro = unlimited) are enforced here per doc §11.3.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.service import get_role_in_workspace
from src.deps import get_current_user_id, get_current_workspace_id
from src.middleware.rls import db_with_rls

from .service import (
    archive_sport,
    default_curriculum_for_sport,
    enable_sport,
    list_workspace_sports,
    set_athlete_sports,
    set_membership_sports,
)

router = APIRouter(tags=["sports"])

# Plans limited to a single sport at MVP (doc §11.3 / §15).
_SINGLE_SPORT_PLANS = {"solo_coach", "club_starter", "free_trial"}


class WorkspaceSportRow(BaseModel):
    sport_id: str
    sport_code: str
    name_en: str
    name_id: str
    curriculum_id: str | None
    curriculum_code: str | None
    is_active: bool


class WorkspaceSportsOut(BaseModel):
    sports: list[WorkspaceSportRow]


class PlatformSportRow(BaseModel):
    sport_id: str
    sport_code: str
    name_en: str
    name_id: str


class PlatformSportsOut(BaseModel):
    sports: list[PlatformSportRow]


class EnableSportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sport_id: UUID
    curriculum_id: UUID | None = None  # defaults to the platform curriculum


class SportIdsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sport_ids: list[UUID] = Field(min_length=1, max_length=8)


async def _require_admin(
    db: AsyncSession, user_id: UUID, workspace_id: UUID | None
) -> UUID:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No active workspace."
        )
    role = await get_role_in_workspace(db, user_id, workspace_id)
    if role != "club_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a club admin can manage sports.",
        )
    return workspace_id


# ── GET /sports (platform catalog) ───────────────────────────────


@router.get("/sports", response_model=PlatformSportsOut)
async def list_platform_sports(
    _: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> PlatformSportsOut:
    """All platform-active sports — the catalog the Sports settings panel
    offers when adding a sport."""
    rows = (
        await db.execute(
            text(
                "SELECT id::text AS sport_id, code AS sport_code, "
                "       name_en, name_id "
                "FROM sports WHERE is_active = TRUE ORDER BY display_order"
            )
        )
    ).mappings().all()
    return PlatformSportsOut(sports=[PlatformSportRow(**r) for r in rows])


# ── GET /workspaces/me/sports ────────────────────────────────────


@router.get("/workspaces/me/sports", response_model=WorkspaceSportsOut)
async def list_sports(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> WorkspaceSportsOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No active workspace."
        )
    rows = await list_workspace_sports(db, workspace_id=workspace_id)
    return WorkspaceSportsOut(sports=[WorkspaceSportRow(**r) for r in rows])


# ── POST /workspaces/me/sports ───────────────────────────────────


@router.post(
    "/workspaces/me/sports",
    response_model=WorkspaceSportsOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_sport(
    body: EnableSportIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> WorkspaceSportsOut:
    wid = await _require_admin(db, user_id, workspace_id)

    sport = (
        await db.execute(
            text("SELECT is_active FROM sports WHERE id = :sid"),
            {"sid": body.sport_id},
        )
    ).first()
    if sport is None or not sport[0]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That sport isn't available on the platform.",
        )

    # Plan gate: single-sport plans can't add a second active sport.
    plan = await db.scalar(
        text("SELECT plan FROM workspaces WHERE id = :wid"), {"wid": wid}
    )
    active_count = await db.scalar(
        text(
            "SELECT count(*) FROM workspace_sports "
            "WHERE workspace_id = :wid AND is_active AND archived_at IS NULL "
            "  AND sport_id <> :sid"
        ),
        {"wid": wid, "sid": body.sport_id},
    )
    if plan in _SINGLE_SPORT_PLANS and (active_count or 0) >= 1:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Your plan includes one sport. Upgrade to Club Pro for more.",
        )

    curriculum_id = body.curriculum_id or await default_curriculum_for_sport(
        db, sport_id=body.sport_id
    )
    await enable_sport(
        db, workspace_id=wid, sport_id=body.sport_id, curriculum_id=curriculum_id
    )
    # The admin enabling a sport gets a qualification for it, so they can coach
    # it immediately.  Other coaches are scoped explicitly via PATCH
    # /memberships/{id}/sports.
    membership_id = await db.scalar(
        text(
            "SELECT id FROM workspace_memberships "
            "WHERE workspace_id = :wid AND user_id = :uid AND archived_at IS NULL"
        ),
        {"wid": wid, "uid": user_id},
    )
    if membership_id is not None:
        await db.execute(
            text(
                """
                INSERT INTO membership_sports (workspace_id, membership_id, sport_id)
                VALUES (:wid, :mid, :sid)
                ON CONFLICT (membership_id, sport_id) DO NOTHING
                """
            ),
            {"wid": wid, "mid": membership_id, "sid": body.sport_id},
        )
    rows = await list_workspace_sports(db, workspace_id=wid)
    await db.commit()
    return WorkspaceSportsOut(sports=[WorkspaceSportRow(**r) for r in rows])


# ── DELETE /workspaces/me/sports/{sport_id} ──────────────────────


@router.delete("/workspaces/me/sports/{sport_id}", response_model=WorkspaceSportsOut)
async def remove_sport(
    sport_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> WorkspaceSportsOut:
    wid = await _require_admin(db, user_id, workspace_id)
    active = await db.scalar(
        text(
            "SELECT count(*) FROM workspace_sports "
            "WHERE workspace_id = :wid AND is_active AND archived_at IS NULL"
        ),
        {"wid": wid},
    )
    if (active or 0) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A workspace must keep at least one active sport.",
        )
    await archive_sport(db, workspace_id=wid, sport_id=sport_id)
    rows = await list_workspace_sports(db, workspace_id=wid)
    await db.commit()
    return WorkspaceSportsOut(sports=[WorkspaceSportRow(**r) for r in rows])


# ── PATCH /athletes/{athlete_id}/sports ──────────────────────────


@router.patch("/athletes/{athlete_id}/sports", status_code=status.HTTP_204_NO_CONTENT)
async def update_athlete_sports(
    athlete_id: UUID,
    body: SportIdsIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> None:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No active workspace."
        )
    athlete = await db.scalar(
        text(
            "SELECT id FROM athletes "
            "WHERE id = :aid AND workspace_id = :wid AND archived_at IS NULL"
        ),
        {"aid": athlete_id, "wid": workspace_id},
    )
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trainee not found."
        )
    await _validate_sports_enabled(db, workspace_id, body.sport_ids)
    await set_athlete_sports(
        db, workspace_id=workspace_id, athlete_id=athlete_id, sport_ids=body.sport_ids
    )
    await db.commit()


# ── PATCH /memberships/{membership_id}/sports ────────────────────


@router.patch(
    "/memberships/{membership_id}/sports", status_code=status.HTTP_204_NO_CONTENT
)
async def update_membership_sports(
    membership_id: UUID,
    body: SportIdsIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> None:
    wid = await _require_admin(db, user_id, workspace_id)
    membership = await db.scalar(
        text(
            "SELECT id FROM workspace_memberships "
            "WHERE id = :mid AND workspace_id = :wid"
        ),
        {"mid": membership_id, "wid": wid},
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found."
        )
    await _validate_sports_enabled(db, wid, body.sport_ids)
    await set_membership_sports(
        db, workspace_id=wid, membership_id=membership_id, sport_ids=body.sport_ids
    )
    await db.commit()


async def _validate_sports_enabled(
    db: AsyncSession, workspace_id: UUID, sport_ids: list[UUID]
) -> None:
    """Every sport must be active on the workspace."""
    enabled = set(
        (
            await db.execute(
                text(
                    "SELECT sport_id FROM workspace_sports "
                    "WHERE workspace_id = :wid AND is_active AND archived_at IS NULL"
                ),
                {"wid": workspace_id},
            )
        ).scalars().all()
    )
    for sid in sport_ids:
        if sid not in enabled:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Sport not enabled on this workspace.",
            )
