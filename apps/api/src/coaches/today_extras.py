"""GET /coaches/me/today-extras — the data behind the Today screen's
"empty day" surfaces: this-week stats + a small recent-activity feed.

Both are derived from existing tables (sessions, assessments, athletes,
reports) so no schema change is needed.  All counts are scoped to the
caller — sessions they coached, assessments they published, etc.  Athlete
mentions in the activity feed are anchored to the caller's coaching, not
the entire workspace, so the feed reads like "what I just did" rather
than a workspace audit log.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.deps import get_current_user_id, get_current_workspace_id
from src.middleware.rls import db_with_rls

router = APIRouter(prefix="/coaches/me", tags=["coaches", "today"])


ActivityKind = Literal[
    "assessment_published",
    "session_coached",
    "report_generated",
    "trainee_joined",
]


class WeekStats(BaseModel):
    sessions: int
    hours_coached: float
    assessments_published: int
    trainees_coached: int


class ActivityItem(BaseModel):
    id: str
    kind: ActivityKind
    trainee_name: str | None
    detail: str | None
    occurred_at: datetime


class TodayExtrasOut(BaseModel):
    week_stats: WeekStats
    recent_activity: list[ActivityItem]


@router.get("/today-extras", response_model=TodayExtrasOut)
async def get_today_extras(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> TodayExtrasOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active workspace.",
        )

    # Week = the last 7 days inclusive of today. Calendar weeks would force
    # a "what week is it" decision the coach doesn't care about — a rolling
    # window stays useful all the time.
    week_start = datetime.utcnow() - timedelta(days=7)

    stats_row = (
        await db.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM sessions
                       WHERE coach_id = :uid
                         AND scheduled_at >= :ws
                         AND scheduled_at <= NOW()
                         AND status NOT IN ('cancelled', 'no_show')
                    ) AS sessions,
                    (SELECT COALESCE(SUM(duration_min), 0) FROM sessions
                       WHERE coach_id = :uid
                         AND scheduled_at >= :ws
                         AND scheduled_at <= NOW()
                         AND status NOT IN ('cancelled', 'no_show')
                    ) AS minutes,
                    (SELECT COUNT(*) FROM assessments
                       WHERE coach_id = :uid
                         AND status IN ('published', 'edited')
                         AND COALESCE(edited_at, published_at) >= :ws
                    ) AS published,
                    (SELECT COUNT(DISTINCT athlete_id) FROM sessions
                       WHERE coach_id = :uid
                         AND scheduled_at >= :ws
                         AND scheduled_at <= NOW()
                         AND status NOT IN ('cancelled', 'no_show')
                    ) AS trainees
                """
            ),
            {"uid": user_id, "ws": week_start},
        )
    ).mappings().first()
    sessions_count = int((stats_row or {}).get("sessions") or 0)
    minutes = int((stats_row or {}).get("minutes") or 0)
    week_stats = WeekStats(
        sessions=sessions_count,
        hours_coached=round(minutes / 60, 1),
        assessments_published=int((stats_row or {}).get("published") or 0),
        trainees_coached=int((stats_row or {}).get("trainees") or 0),
    )

    # Recent activity feed.  UNION across four event sources, cap each
    # source at 6 rows before unioning so one chatty type doesn't drown
    # the others, then take the 8 most recent overall.  60-day window to
    # avoid empty feeds when the coach takes time off.
    feed_start = datetime.utcnow() - timedelta(days=60)
    rows = (
        await db.execute(
            text(
                """
                WITH pub AS (
                    SELECT a.id::TEXT AS id,
                           'assessment_published'::TEXT AS kind,
                           ath.display_name AS trainee_name,
                           NULL::TEXT AS detail,
                           COALESCE(a.edited_at, a.published_at) AS occurred_at
                    FROM assessments a
                    JOIN athletes ath ON ath.id = a.athlete_id
                    WHERE a.coach_id = :uid
                      AND a.status IN ('published','edited')
                      AND COALESCE(a.edited_at, a.published_at) >= :ws
                    ORDER BY COALESCE(a.edited_at, a.published_at) DESC
                    LIMIT 6
                ),
                sess AS (
                    SELECT s.id::TEXT AS id,
                           'session_coached'::TEXT AS kind,
                           ath.display_name AS trainee_name,
                           s.focus::TEXT AS detail,
                           s.scheduled_at AS occurred_at
                    FROM sessions s
                    JOIN athletes ath ON ath.id = s.athlete_id
                    WHERE s.coach_id = :uid
                      AND s.status NOT IN ('cancelled','no_show')
                      AND s.scheduled_at >= :ws
                      AND s.scheduled_at <= NOW()
                    ORDER BY s.scheduled_at DESC
                    LIMIT 6
                ),
                rpt AS (
                    SELECT r.id::TEXT AS id,
                           'report_generated'::TEXT AS kind,
                           ath.display_name AS trainee_name,
                           NULL::TEXT AS detail,
                           r.generated_at AS occurred_at
                    FROM reports r
                    JOIN athletes ath ON ath.id = r.athlete_id
                    WHERE r.coach_id = :uid
                      AND r.status = 'completed'
                      AND r.generated_at >= :ws
                    ORDER BY r.generated_at DESC
                    LIMIT 6
                ),
                joined AS (
                    SELECT ath.id::TEXT AS id,
                           'trainee_joined'::TEXT AS kind,
                           ath.display_name AS trainee_name,
                           NULL::TEXT AS detail,
                           ath.joined_at::TIMESTAMPTZ AS occurred_at
                    FROM athletes ath
                    WHERE ath.workspace_id = :wid
                      AND ath.archived_at IS NULL
                      AND ath.joined_at::TIMESTAMPTZ >= :ws
                      AND EXISTS (
                          SELECT 1 FROM sessions s2
                          WHERE s2.athlete_id = ath.id AND s2.coach_id = :uid
                      )
                    ORDER BY ath.joined_at DESC
                    LIMIT 6
                )
                SELECT * FROM pub
                UNION ALL SELECT * FROM sess
                UNION ALL SELECT * FROM rpt
                UNION ALL SELECT * FROM joined
                ORDER BY occurred_at DESC NULLS LAST
                LIMIT 8
                """
            ),
            {"uid": user_id, "wid": workspace_id, "ws": feed_start},
        )
    ).mappings().all()

    activity = [
        ActivityItem(
            id=f"{r['kind']}:{r['id']}",
            kind=r["kind"],
            trainee_name=r["trainee_name"],
            detail=r["detail"],
            occurred_at=r["occurred_at"],
        )
        for r in rows
    ]

    return TodayExtrasOut(week_stats=week_stats, recent_activity=activity)
