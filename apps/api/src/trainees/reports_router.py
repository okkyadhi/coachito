"""GET /trainees/me/reports — completed reports for the signed-in trainee.

RLS-scoped via ``athletes.user_id``: trainee A can never see B's reports
even if the WHERE clause forgot to filter.  Coaches don't hit this route —
they have ``GET /reports`` under the coach shell.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.deps import get_current_user_id, get_current_workspace_id
from src.middleware.rls import db_with_rls

router = APIRouter(prefix="/trainees/me", tags=["trainees", "reports"])


class TraineeReportOut(BaseModel):
    id: str
    period_start: date
    period_end: date
    is_session_report: bool
    generated_at: datetime
    pdf_url: str
    view_count: int
    coach_display_name: str


class TraineeReportsListOut(BaseModel):
    reports: list[TraineeReportOut]


_PRIVATE_30S = "private, max-age=30"


@router.get("/reports", response_model=TraineeReportsListOut)
async def list_my_reports(
    response: Response,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> TraineeReportsListOut:
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
                SELECT r.id, r.period_start, r.period_end,
                       r.session_id IS NOT NULL AS is_session_report,
                       r.generated_at, r.pdf_url, r.view_count,
                       u.display_name AS coach_display_name
                FROM reports r
                JOIN users u ON u.id = r.coach_id
                WHERE r.athlete_id = :aid
                  AND r.status = 'completed'
                  AND r.pdf_url IS NOT NULL
                ORDER BY r.generated_at DESC
                """
            ),
            {"aid": athlete_id},
        )
    ).mappings().all()

    response.headers["Cache-Control"] = _PRIVATE_30S
    return TraineeReportsListOut(
        reports=[
            TraineeReportOut(
                id=str(r["id"]),
                period_start=r["period_start"],
                period_end=r["period_end"],
                is_session_report=bool(r["is_session_report"]),
                generated_at=r["generated_at"],
                pdf_url=r["pdf_url"],
                view_count=int(r["view_count"] or 0),
                coach_display_name=r["coach_display_name"],
            )
            for r in rows
        ],
    )
