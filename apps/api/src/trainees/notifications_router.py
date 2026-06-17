"""GET /trainees/me/notifications — derived activity feed for the trainee.

No notifications table.  Aggregates four signals the trainee actually
cares about:
  - session_scheduled   — coach put a new session on their calendar
  - assessment_published — a coach saved a new assessment for them
  - report_ready        — a monthly / session PDF report finished
  - coach_note          — a coach added/updated a session summary

All scoped via trainee-scoped RLS (migration 0015 on athletes /
assessments / sessions; reports follow athlete RLS via athlete_id).
Returns the 30 most recent items across the last 60 days, newest first.
FE owns "unread" state via localStorage (last-seen-at) — server doesn't
track reads because there is no persistent notifications row to mark.
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
from src.middleware.rls import db_with_rls

router = APIRouter(prefix="/trainees/me", tags=["trainees", "notifications"])


NotificationKind = Literal[
    "session_scheduled",
    "assessment_published",
    "report_ready",
    "coach_note",
]


class NotificationOut(BaseModel):
    id: str
    kind: NotificationKind
    coach_name: str | None
    body: str | None
    occurred_at: datetime
    link: str | None


class NotificationsOut(BaseModel):
    items: list[NotificationOut]


def _aware(d: datetime) -> datetime:
    return d if d.tzinfo else d.replace(tzinfo=UTC)


@router.get("/notifications", response_model=NotificationsOut)
async def list_my_notifications(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> NotificationsOut:
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

    # UNION the four event sources.  Each row produces id/kind/title/body
    # ready to render — no further per-row queries.  We cap each source
    # at 20 rows before unioning so a chatty coach can't crowd the feed
    # with 50 session_scheduled entries and bury the others.
    rows = (
        await db.execute(
            text(
                """
                WITH sess AS (
                    -- session_scheduled links to the My Sessions list — there
                    -- is no per-session detail screen for upcoming sessions
                    -- (detail route takes an assessment_id, which doesn't
                    -- exist yet for a freshly-scheduled session).
                    SELECT
                        s.id::TEXT          AS source_id,
                        'session_scheduled'::TEXT AS kind,
                        u.display_name      AS coach_name,
                        s.scheduled_at      AS occurred_at,
                        s.scheduled_at      AS detail_at,
                        s.focus::TEXT       AS detail,
                        '/my-sessions'::TEXT AS link
                    FROM sessions s
                    JOIN users u ON u.id = s.coach_id
                    WHERE s.athlete_id = :aid
                      AND s.status = 'scheduled'
                      AND s.scheduled_at >= NOW() - INTERVAL '60 days'
                    ORDER BY s.scheduled_at DESC
                    LIMIT 20
                ),
                notes AS (
                    SELECT
                        s.id::TEXT          AS source_id,
                        'coach_note'::TEXT  AS kind,
                        u.display_name      AS coach_name,
                        s.scheduled_at      AS occurred_at,
                        s.scheduled_at      AS detail_at,
                        LEFT(s.summary, 140) AS detail,
                        '/my-sessions'::TEXT AS link
                    FROM sessions s
                    JOIN users u ON u.id = s.coach_id
                    WHERE s.athlete_id = :aid
                      AND s.summary IS NOT NULL
                      AND LENGTH(BTRIM(s.summary)) > 0
                      AND s.scheduled_at >= NOW() - INTERVAL '60 days'
                    ORDER BY s.scheduled_at DESC
                    LIMIT 20
                ),
                ass AS (
                    SELECT
                        a.id::TEXT          AS source_id,
                        'assessment_published'::TEXT AS kind,
                        u.display_name      AS coach_name,
                        COALESCE(a.edited_at, a.published_at) AS occurred_at,
                        COALESCE(a.edited_at, a.published_at) AS detail_at,
                        NULL::TEXT          AS detail,
                        ('/my-sessions/' || a.id::TEXT) AS link
                    FROM assessments a
                    JOIN users u ON u.id = a.coach_id
                    WHERE a.athlete_id = :aid
                      AND a.status IN ('published','edited')
                      AND COALESCE(a.edited_at, a.published_at) >= NOW() - INTERVAL '60 days'
                    ORDER BY COALESCE(a.edited_at, a.published_at) DESC
                    LIMIT 20
                ),
                rpts AS (
                    SELECT
                        r.id::TEXT          AS source_id,
                        'report_ready'::TEXT AS kind,
                        u.display_name      AS coach_name,
                        r.generated_at      AS occurred_at,
                        r.period_start::TIMESTAMPTZ AS detail_at,
                        to_char(r.period_start, 'FMMon YYYY') AS detail,
                        '/me/reports'::TEXT AS link
                    FROM reports r
                    JOIN users u ON u.id = r.coach_id
                    WHERE r.athlete_id = :aid
                      AND r.status = 'completed'
                      AND r.pdf_url IS NOT NULL
                      AND r.generated_at >= NOW() - INTERVAL '60 days'
                    ORDER BY r.generated_at DESC
                    LIMIT 20
                )
                SELECT * FROM sess
                UNION ALL SELECT * FROM notes
                UNION ALL SELECT * FROM ass
                UNION ALL SELECT * FROM rpts
                ORDER BY occurred_at DESC NULLS LAST
                LIMIT 30
                """
            ),
            {"aid": athlete_id},
        )
    ).mappings().all()

    items: list[NotificationOut] = []
    for r in rows:
        kind: NotificationKind = r["kind"]  # type: ignore[assignment]
        items.append(
            NotificationOut(
                id=f"{kind}:{r['source_id']}",
                kind=kind,
                coach_name=r["coach_name"],
                body=r["detail"],
                occurred_at=_aware(r["occurred_at"]),
                link=r["link"],
            )
        )
    return NotificationsOut(items=items)
