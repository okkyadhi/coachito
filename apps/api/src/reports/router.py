"""Reports HTTP surface.

* GET /reports          — list this workspace's reports (newest first).
* POST /reports         — enqueue a one-off generation.  Returns 202 with the
                          row pre-inserted in status='pending' so the FE can
                          poll it immediately.
* GET /reports/{id}     — status / url poll for the FE.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from redis import Redis as SyncRedis
from rq import Queue
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.audit.decorators import audit_action
from src.auth.service import get_role_in_workspace
from src.deps import get_current_user_id, get_current_workspace_id
from src.middleware.rls import db_with_rls

router = APIRouter(prefix="/reports", tags=["reports"])


# ── Schemas ──────────────────────────────────────────────────────


class ReportOut(BaseModel):
    id: str
    athlete_id: str
    trainee_name: str
    period_start: date
    period_end: date
    status: str
    generated_at: datetime | None
    pdf_url: str | None
    view_count: int
    error_message: str | None = None


class ReportListOut(BaseModel):
    reports: list[ReportOut]


class ReportCreateIn(BaseModel):
    athlete_id: UUID
    # When `session_id` is provided the BE derives period_start/end from the
    # session's scheduled date; the FE can omit them.
    session_id: UUID | None = None
    period_start: date | None = None
    period_end: date | None = None


class ReportCreateOut(BaseModel):
    report: ReportOut
    job_id: str


# ── Helpers ──────────────────────────────────────────────────────


def _enqueue(report_id: str) -> str:
    conn = SyncRedis.from_url(settings.redis_url)
    queue = Queue("default", connection=conn)
    # The string path keeps the worker import lazy — the API container has
    # the same module layout so this resolves identically on the worker side.
    job = queue.enqueue(
        "src.reports.jobs.generate_report_pdf",
        report_id,
        job_timeout=120,
    )
    return job.id


# ── Routes ───────────────────────────────────────────────────────


@router.get("", response_model=ReportListOut)
async def list_reports(
    _user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> ReportListOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No active workspace."
        )
    rows = (
        await db.execute(
            text(
                """
                SELECT r.id, r.athlete_id, a.display_name AS trainee_name,
                       r.period_start, r.period_end, r.status::text AS status,
                       r.generated_at, r.pdf_url, r.view_count, r.error_message
                FROM reports r
                JOIN athletes a ON a.id = r.athlete_id
                ORDER BY COALESCE(r.generated_at, NOW()) DESC, r.period_end DESC
                LIMIT 100
                """
            )
        )
    ).mappings().all()
    return ReportListOut(
        reports=[
            ReportOut(
                id=str(r["id"]),
                athlete_id=str(r["athlete_id"]),
                trainee_name=r["trainee_name"],
                period_start=r["period_start"],
                period_end=r["period_end"],
                status=r["status"],
                generated_at=r["generated_at"],
                pdf_url=r["pdf_url"],
                view_count=int(r["view_count"]),
                error_message=r["error_message"],
            )
            for r in rows
        ]
    )


@router.post("", response_model=ReportCreateOut, status_code=status.HTTP_202_ACCEPTED)
@audit_action(
    "report.requested",
    entity_type="report",
    extract=lambda r, _kw: {"job_id": r.job_id, "athlete_id": r.report.athlete_id},
)
async def create_report(
    body: ReportCreateIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> ReportCreateOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No active workspace."
        )

    # Authorization (checked before the athlete lookup so a trainee role
    # gets 403 rather than a 404 from RLS hiding the athlete).
    #   - trainee / parent / no-membership → 403 (they receive reports, not create them)
    #   - coach → must have coached ≥1 session with this trainee
    #   - club_admin / head_coach → unrestricted (oversight, customer support)
    role = await get_role_in_workspace(db, user_id, workspace_id)
    if role in ("trainee", "parent") or role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only coaches can generate reports.",
        )
    if role == "coach":
        has_session = await db.scalar(
            text(
                """
                SELECT 1 FROM sessions
                WHERE workspace_id = :wid
                  AND athlete_id = :aid
                  AND coach_id = :uid
                LIMIT 1
                """
            ),
            {"wid": workspace_id, "aid": body.athlete_id, "uid": user_id},
        )
        if not has_session:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only generate reports for trainees you've coached.",
            )

    # Athlete must exist in this workspace (RLS already filters).
    athlete = (
        await db.execute(
            text(
                "SELECT id, display_name FROM athletes "
                "WHERE id = :aid AND archived_at IS NULL"
            ),
            {"aid": body.athlete_id},
        )
    ).mappings().first()
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trainee not found."
        )

    period_start = body.period_start
    period_end = body.period_end
    if body.session_id is not None:
        session_row = (
            await db.execute(
                text(
                    "SELECT scheduled_at::date AS d FROM sessions "
                    "WHERE id = :sid AND athlete_id = :aid"
                ),
                {"sid": body.session_id, "aid": body.athlete_id},
            )
        ).mappings().first()
        if session_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found."
            )
        period_start = session_row["d"]
        period_end = session_row["d"]

    if period_start is None or period_end is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="period_start and period_end are required for monthly reports.",
        )
    if period_end < period_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="period_end must be on or after period_start.",
        )

    report_id = uuid4()
    await db.execute(
        text(
            """
            INSERT INTO reports (
                id, workspace_id, athlete_id, coach_id, session_id,
                period_start, period_end, status,
                generation_type, generated_by_id
            )
            VALUES (:id, :wid, :aid, :uid, :sid, :ps, :pe,
                    'pending', 'manual', :uid)
            """
        ),
        {
            "id": report_id,
            "wid": workspace_id,
            "aid": body.athlete_id,
            "uid": user_id,
            "sid": body.session_id,
            "ps": period_start,
            "pe": period_end,
        },
    )
    await db.commit()

    job_id = _enqueue(str(report_id))

    return ReportCreateOut(
        report=ReportOut(
            id=str(report_id),
            athlete_id=str(body.athlete_id),
            trainee_name=athlete["display_name"],
            period_start=period_start,
            period_end=period_end,
            status="pending",
            generated_at=None,
            pdf_url=None,
            view_count=0,
        ),
        job_id=job_id,
    )


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(
    report_id: UUID,
    _user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> ReportOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No active workspace."
        )
    row = (
        await db.execute(
            text(
                """
                SELECT r.id, r.athlete_id, a.display_name AS trainee_name,
                       r.period_start, r.period_end, r.status::text AS status,
                       r.generated_at, r.pdf_url, r.view_count, r.error_message
                FROM reports r
                JOIN athletes a ON a.id = r.athlete_id
                WHERE r.id = :rid
                """
            ),
            {"rid": report_id},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Report not found."
        )
    return ReportOut(
        id=str(row["id"]),
        athlete_id=str(row["athlete_id"]),
        trainee_name=row["trainee_name"],
        period_start=row["period_start"],
        period_end=row["period_end"],
        status=row["status"],
        generated_at=row["generated_at"],
        pdf_url=row["pdf_url"],
        view_count=int(row["view_count"]),
        error_message=row["error_message"],
    )


@router.post("/{report_id}/view", status_code=status.HTTP_204_NO_CONTENT)
async def record_view(
    report_id: UUID,
    _user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> Response:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No active workspace."
        )
    await db.execute(
        text("UPDATE reports SET view_count = view_count + 1 WHERE id = :rid"),
        {"rid": report_id},
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
