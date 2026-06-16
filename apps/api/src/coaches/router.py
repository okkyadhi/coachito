"""GET /coaches/:coach_id — public-within-workspace coach bio.

Returns 404 if the caller doesn't share at least one workspace with the
coach.  No PII beyond what the coach put in their bio.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.deps import get_current_user_id, get_current_workspace_id
from src.memberships.bio_schemas import CoachBio, coerce_bio
from src.middleware.rls import db_with_rls

router = APIRouter(prefix="/coaches", tags=["coaches"])


class CoachBioOut(BaseModel):
    coach_id: str
    display_name: str
    avatar_url: str | None
    bio: CoachBio
    member_since: datetime
    coached_trainees_count: int


@router.get("/{coach_id}", response_model=CoachBioOut)
async def get_coach_bio(
    coach_id: UUID,
    _user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> CoachBioOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active workspace.",
        )

    # Coach + their membership in the *current* workspace.  If they don't
    # have one here, 404 — preserves the workspace-scoped privacy boundary.
    row = (
        await db.execute(
            text(
                """
                SELECT u.id, u.display_name, u.avatar_url,
                       COALESCE(m.bio, '{}'::jsonb) AS bio,
                       m.joined_at, m.invited_at
                FROM users u
                JOIN workspace_memberships m
                  ON m.user_id = u.id
                 AND m.workspace_id = :wid
                 AND m.role IN ('coach','head_coach','club_admin')
                 AND m.status = 'active'
                WHERE u.id = :cid
                """
            ),
            {"cid": coach_id, "wid": workspace_id},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Coach not found."
        )

    coached = await db.scalar(
        text(
            """
            SELECT COUNT(DISTINCT athlete_id)
            FROM sessions
            WHERE workspace_id = :wid AND coach_id = :cid
            """
        ),
        {"wid": workspace_id, "cid": coach_id},
    )

    member_since = row["joined_at"] or row["invited_at"]
    return CoachBioOut(
        coach_id=str(row["id"]),
        display_name=row["display_name"],
        avatar_url=row["avatar_url"],
        bio=coerce_bio(row["bio"]),
        member_since=member_since,
        coached_trainees_count=int(coached or 0),
    )
