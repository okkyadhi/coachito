"""GET /trainees/me/coaches — trainee's club roster + every active coach in
their workspace, with session enrichment for the ones who have coached
them.  Read-only, trainee-self scoped via RLS.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.deps import get_current_user_id, get_current_workspace_id
from src.memberships.bio_schemas import coerce_bio
from src.middleware.rls import db_with_rls

router = APIRouter(prefix="/trainees/me", tags=["trainees", "coaches"])


class WorkspaceBrief(BaseModel):
    id: str
    name: str
    type: Literal["club", "personal"]
    city: str | None
    logo_url: str | None
    brand_color: str | None


class CoachListEntry(BaseModel):
    coach_id: str
    display_name: str
    avatar_url: str | None
    headline: str | None
    role: str
    session_count: int
    last_coached_at: datetime | None
    next_session_at: datetime | None


class CoachListOut(BaseModel):
    workspace: WorkspaceBrief
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

    # Resolve the athlete + workspace brief in one round trip.  We need the
    # athlete row anyway to enrich session counts; pulling the workspace
    # branding alongside keeps the page render single-query from FE side.
    head = (
        await db.execute(
            text(
                """
                SELECT a.id           AS athlete_id,
                       w.id           AS workspace_id,
                       w.name         AS workspace_name,
                       w.type         AS workspace_type,
                       w.city         AS workspace_city,
                       w.logo_url     AS workspace_logo_url,
                       w.brand_color  AS workspace_brand_color
                FROM athletes a
                JOIN workspaces w ON w.id = a.workspace_id
                WHERE a.user_id = :uid
                  AND a.workspace_id = :wid
                  AND a.archived_at IS NULL
                LIMIT 1
                """
            ),
            {"uid": user_id, "wid": workspace_id},
        )
    ).mappings().first()
    if head is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No trainee profile linked to this account.",
        )

    athlete_id: UUID = head["athlete_id"]

    # Every active coach-tier member of this workspace + an outer join on
    # the trainee's sessions so we get session_count / last / next for the
    # subset that has actually coached them.  Brand-new club trainees see
    # all coaches with 0 sessions instead of an empty list.
    rows = (
        await db.execute(
            text(
                """
                SELECT
                    m.user_id                                       AS coach_id,
                    u.display_name,
                    u.avatar_url,
                    m.role,
                    COALESCE(m.bio, '{}'::jsonb)                    AS bio,
                    COALESCE(sc.session_count, 0)                   AS session_count,
                    sc.last_coached_at,
                    sc.next_session_at
                FROM workspace_memberships m
                JOIN users u ON u.id = m.user_id
                LEFT JOIN LATERAL (
                    SELECT
                        COUNT(*) FILTER (WHERE s.status IN ('completed','scheduled'))
                            AS session_count,
                        MAX(s.scheduled_at) FILTER (
                            WHERE s.status IN ('completed','scheduled')
                              AND s.scheduled_at <= NOW()
                        )                                            AS last_coached_at,
                        MIN(s.scheduled_at) FILTER (
                            WHERE s.status = 'scheduled'
                              AND s.scheduled_at > NOW()
                        )                                            AS next_session_at
                    FROM sessions s
                    WHERE s.athlete_id = :aid
                      AND s.coach_id = m.user_id
                ) sc ON TRUE
                WHERE m.workspace_id = :wid
                  AND m.status = 'active'
                  AND m.role IN ('club_admin','head_coach','coach')
                """
            ),
            {"aid": athlete_id, "wid": workspace_id},
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
                role=r["role"],
                session_count=int(r["session_count"] or 0),
                last_coached_at=_as_aware(r["last_coached_at"]),
                next_session_at=_as_aware(r["next_session_at"]),
            )
        )

    def _sort_key(e: CoachListEntry) -> tuple[int, float, str]:
        # Bucket 0: upcoming session within 7 days, soonest first.
        # Bucket 1: coaches who have actually coached this trainee, most
        #           recent first.
        # Bucket 2: rest of the workspace coaches (alphabetical) — so the
        #           directory is stable for new trainees.
        if e.next_session_at and e.next_session_at.timestamp() <= cutoff_soon:
            return (0, e.next_session_at.timestamp(), "")
        if e.last_coached_at is not None:
            return (1, -e.last_coached_at.timestamp(), "")
        return (2, 0.0, e.display_name.lower())

    entries.sort(key=_sort_key)
    return CoachListOut(
        workspace=WorkspaceBrief(
            id=str(head["workspace_id"]),
            name=head["workspace_name"],
            type=head["workspace_type"],
            city=head["workspace_city"],
            logo_url=head["workspace_logo_url"],
            brand_color=head["workspace_brand_color"],
        ),
        coaches=entries,
    )
