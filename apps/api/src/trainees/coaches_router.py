"""GET /trainees/me/coaches — list of every coach who has coached this
trainee, most recent first.  Read-only, trainee-self scoped via RLS.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.deps import get_current_user_id, get_current_workspace_id
from src.memberships.bio_schemas import coerce_bio
from src.middleware.rls import db_with_rls

router = APIRouter(prefix="/trainees/me", tags=["trainees", "coaches"])


class CoachListEntry(BaseModel):
    coach_id: str
    display_name: str
    avatar_url: str | None
    headline: str | None
    session_count: int
    last_coached_at: datetime | None
    next_session_at: datetime | None


class CoachListOut(BaseModel):
    coaches: list[CoachListEntry]


def _as_aware(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=UTC)


@router.get("/coaches", response_model=CoachListOut)
async def list_my_coaches(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> CoachListOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active workspace.",
        )

    athlete_id = (
        await db.execute(
            text(
                "SELECT id FROM athletes "
                "WHERE user_id = :uid AND workspace_id = :wid "
                "  AND archived_at IS NULL LIMIT 1"
            ),
            {"uid": user_id, "wid": workspace_id},
        )
    ).scalar_one_or_none()
    if athlete_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No trainee profile linked to this account.",
        )

    rows = (
        await db.execute(
            text(
                """
                SELECT
                    s.coach_id,
                    u.display_name,
                    u.avatar_url,
                    COALESCE(m.bio, '{}'::jsonb) AS bio,
                    COUNT(*) FILTER (WHERE s.status IN ('completed','scheduled'))
                        AS session_count,
                    MAX(s.scheduled_at) FILTER (
                        WHERE s.status IN ('completed','scheduled')
                          AND s.scheduled_at <= NOW()
                    ) AS last_coached_at,
                    MIN(s.scheduled_at) FILTER (
                        WHERE s.status = 'scheduled'
                          AND s.scheduled_at > NOW()
                    ) AS next_session_at
                FROM sessions s
                JOIN users u ON u.id = s.coach_id
                LEFT JOIN workspace_memberships m
                    ON m.workspace_id = s.workspace_id
                   AND m.user_id = s.coach_id
                WHERE s.athlete_id = :aid
                GROUP BY s.coach_id, u.display_name, u.avatar_url, m.bio
                """
            ),
            {"aid": athlete_id},
        )
    ).mappings().all()

    now = datetime.now(UTC)
    cutoff_soon = now.timestamp() + 7 * 86400

    entries: list[CoachListEntry] = []
    for r in rows:
        bio = coerce_bio(r["bio"])
        entries.append(
            CoachListEntry(
                coach_id=str(r["coach_id"]),
                display_name=r["display_name"],
                avatar_url=r["avatar_url"],
                headline=bio.headline,
                session_count=int(r["session_count"] or 0),
                last_coached_at=_as_aware(r["last_coached_at"]),
                next_session_at=_as_aware(r["next_session_at"]),
            )
        )

    def _sort_key(e: CoachListEntry) -> tuple[int, float]:
        # Bucket 0: upcoming session within 7 days, sorted soonest first.
        # Bucket 1: by most-recent last_coached_at.
        if e.next_session_at and e.next_session_at.timestamp() <= cutoff_soon:
            return (0, e.next_session_at.timestamp())
        last_ts = e.last_coached_at.timestamp() if e.last_coached_at else 0.0
        return (1, -last_ts)

    entries.sort(key=_sort_key)
    return CoachListOut(coaches=entries)
