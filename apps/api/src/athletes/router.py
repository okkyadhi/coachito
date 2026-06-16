"""Trainees endpoints: list, create-with-invite, update, soft-delete."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.decorators import audit_action
from src.db.models.athlete import Athlete
from src.deps import get_current_user_id, get_current_workspace_id
from src.invites.service import public_landing_url
from src.middleware.rls import db_with_rls

from .create import create_athlete_with_invite
from .schemas import (
    AthleteListOut,
    AthleteOut,
    InviteBrief,
    LinkedUserBrief,
    TierBrief,
    TraineeCreateIn,
    TraineeCreateOut,
    TraineeUpdateIn,
)
from .service import DEFAULT_LIMIT, MAX_LIMIT, list_athletes

router = APIRouter(prefix="/trainees", tags=["trainees"])


def _athlete_to_out(athlete: Athlete) -> AthleteOut:
    return AthleteOut(
        id=str(athlete.id),
        display_name=athlete.display_name,
        date_of_birth=athlete.date_of_birth,
        is_minor=athlete.is_minor,
        joined_at=athlete.joined_at,
        last_assessed_at=None,
        current_tier=None,
        archived_at=athlete.archived_at,
        created_at=athlete.created_at,
    )


# ── GET /trainees ────────────────────────────────────────────────


@router.get("", response_model=AthleteListOut)
async def list_trainees(
    _: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    cursor: str | None = Query(default=None),
) -> AthleteListOut:
    rows, next_cursor = await list_athletes(db, q=q, limit=limit, cursor=cursor)
    return AthleteListOut(
        athletes=[
            AthleteOut(
                id=str(r["id"]),
                display_name=r["display_name"],
                date_of_birth=r["date_of_birth"],
                is_minor=r["is_minor"],
                joined_at=r["joined_at"],
                last_assessed_at=r["last_assessed_at"],
                current_tier=(
                    TierBrief(
                        id=str(r["tier_id"]),
                        code=r["tier_code"],
                        name_game_en=r["tier_name_game_en"],
                        name_game_id=r["tier_name_game_id"],
                    )
                    if r["tier_id"] is not None
                    else None
                ),
                archived_at=r["archived_at"],
                created_at=r["created_at"],
            )
            for r in rows
        ],
        next_cursor=next_cursor,
    )


# ── POST /trainees ───────────────────────────────────────────────


@router.post("", response_model=TraineeCreateOut, status_code=status.HTTP_201_CREATED)
@audit_action("trainee.created", entity_type="athlete")
async def create_trainee(
    body: TraineeCreateIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> TraineeCreateOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Switch into a workspace before adding trainees.",
        )

    athlete, invite, extras = await create_athlete_with_invite(
        db,
        workspace_id=workspace_id,
        coach_id=user_id,
        name=body.name,
        phone_e164=body.phone_e164,
        date_of_birth=body.date_of_birth,
        parent_phone_e164=body.parent_phone_e164,
    )
    await db.commit()

    linked_payload = extras.get("linked_user")
    linked_user = (
        LinkedUserBrief(**linked_payload)
        if isinstance(linked_payload, dict)
        else None
    )

    return TraineeCreateOut(
        trainee=_athlete_to_out(athlete),
        invite=InviteBrief(
            id=str(invite.id),
            code=invite.invite_code,
            phone_e164=invite.phone_e164,
            expires_at=invite.expires_at,
            landing_url=extras["landing_url"],
        ),
        linked_user=linked_user,
    )


# ── PATCH /trainees/{id} ─────────────────────────────────────────


@router.patch("/{athlete_id}", response_model=AthleteOut)
@audit_action(
    "trainee.updated",
    entity_type="athlete",
    extract=lambda _r, kw: {"athlete_id": str(kw.get("athlete_id"))},
)
async def update_trainee(
    athlete_id: UUID,
    body: TraineeUpdateIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> AthleteOut:
    athlete = (
        await db.execute(select(Athlete).where(Athlete.id == athlete_id))
    ).scalar_one_or_none()
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trainee not found."
        )

    changed = False
    if body.display_name is not None and body.display_name != athlete.display_name:
        athlete.display_name = body.display_name.strip()
        changed = True
    if body.date_of_birth is not None and body.date_of_birth != athlete.date_of_birth:
        from .create import _is_minor
        athlete.date_of_birth = body.date_of_birth
        athlete.is_minor = _is_minor(body.date_of_birth)
        changed = True
    if body.notes is not None and body.notes != athlete.notes:
        athlete.notes = body.notes
        changed = True

    if changed:
        athlete.updated_at = datetime.now(UTC)
        await db.flush()
        await db.commit()

    return _athlete_to_out(athlete)


# ── DELETE /trainees/{id} ────────────────────────────────────────


@router.delete("/{athlete_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_action(
    "trainee.archived",
    entity_type="athlete",
    extract=lambda _r, kw: {"athlete_id": str(kw.get("athlete_id"))},
)
async def delete_trainee(
    athlete_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> Response:
    """Soft-delete via archived_at.  Hard-delete (cascade) is reserved for
    the "Danger Zone" admin flow (post-MVP)."""
    athlete = (
        await db.execute(select(Athlete).where(Athlete.id == athlete_id))
    ).scalar_one_or_none()
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trainee not found."
        )

    if athlete.archived_at is None:
        athlete.archived_at = datetime.now(UTC)
        athlete.updated_at = datetime.now(UTC)
        await db.flush()
        await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── GET /trainees/{id}/sessions ──────────────────────────────────


from pydantic import BaseModel
from sqlalchemy import text as sa_text


class TraineeSessionOut(BaseModel):
    id: str
    scheduled_at: datetime
    duration_min: int
    court: str | None
    focus: str | None
    summary: str | None
    status: str


class TraineeSessionsOut(BaseModel):
    sessions: list[TraineeSessionOut]


@router.get("/{athlete_id}/sessions", response_model=TraineeSessionsOut)
async def list_trainee_sessions(
    athlete_id: UUID,
    _: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
    limit: int = 20,
) -> TraineeSessionsOut:
    """Recent sessions for one trainee, newest first.  Used by the report
    picker so the coach can choose "per session" instead of "per month"."""
    rows = (
        await db.execute(
            sa_text(
                """
                SELECT id, scheduled_at, duration_min, court,
                       focus::TEXT AS focus, summary, status
                FROM sessions
                WHERE athlete_id = :aid
                ORDER BY scheduled_at DESC
                LIMIT :limit
                """
            ),
            {"aid": athlete_id, "limit": max(1, min(limit, 100))},
        )
    ).mappings().all()
    return TraineeSessionsOut(
        sessions=[
            TraineeSessionOut(
                id=str(r["id"]),
                scheduled_at=r["scheduled_at"],
                duration_min=int(r["duration_min"]) if r["duration_min"] else 60,
                court=r["court"],
                focus=r["focus"],
                summary=r["summary"],
                status=r["status"],
            )
            for r in rows
        ]
    )


# Silence "imported but only used in branch" warnings.
_ = public_landing_url
