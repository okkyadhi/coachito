"""Assessment v2 endpoints — draft / publish / edit / discard."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.decorators import audit_action
from src.deps import get_current_user_id, get_current_workspace_id
from src.middleware.rls import db_with_rls
from src.sports.service import SportError, SportNotQualifiedError

from .schemas import (
    AssessmentDraftIn,
    AssessmentEditIn,
    AssessmentEditOut,
    AssessmentOut,
    PublishIn,
)
from .service import (
    AssessmentNotFoundError,
    AthleteNotFoundError,
    InvalidSkillError,
    StatusConflictError,
    ValidationFailedError,
    discard_draft,
    edit_assessment,
    load_assessment,
    load_by_session,
    publish,
    upsert_draft,
)

router = APIRouter(prefix="/assessments", tags=["assessments"])


# ── POST /assessments (create/update draft) ─────────────────────


@router.post("", response_model=AssessmentOut)
@audit_action(
    "assessment.draft_saved",
    entity_type="assessment",
    extract=lambda r, _kw: {
        "assessment_id": r.id,
        "athlete_id": r.athlete_id,
        "scores": len(r.scores),
    },
)
async def save_draft(
    body: AssessmentDraftIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> AssessmentOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Switch into a workspace before saving assessments.",
        )
    try:
        result = await upsert_draft(
            db, workspace_id=workspace_id, coach_id=user_id, payload=body
        )
    except AthleteNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trainee not found."
        )
    except InvalidSkillError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more skills are not part of this curriculum.",
        )
    except StatusConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except SportNotQualifiedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except SportError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    await db.commit()
    return result


# ── GET /assessments/mine (trainee history) ─────────────────────


class TraineeAssessmentSummary(BaseModel):
    id: str
    session_id: str
    status: str
    published_at: datetime | None
    edited_at: datetime | None
    summary: str | None
    coach_display_name: str | None
    session_scheduled_at: datetime
    session_duration_min: int | None
    session_court: str | None
    session_focus: str | None
    score_count: int
    has_feedback: bool


@router.get("/mine", response_model=list[TraineeAssessmentSummary])
async def list_mine(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> list[TraineeAssessmentSummary]:
    if workspace_id is None:
        return []
    rows = (
        await db.execute(
            text(
                """
                SELECT a.id, a.session_id, a.status,
                       a.published_at, a.edited_at, a.summary,
                       u.display_name AS coach_name,
                       s.scheduled_at, s.duration_min, s.court,
                       s.focus::text AS focus,
                       (SELECT count(*) FROM assessment_scores
                         WHERE assessment_id = a.id) AS score_count,
                       EXISTS (SELECT 1 FROM feedbacks f
                         WHERE f.assessment_id = a.id
                           AND f.submitted_by_user_id = :uid
                           AND f.withdrawn_at IS NULL) AS has_feedback
                FROM assessments a
                JOIN athletes ath ON ath.id = a.athlete_id
                JOIN users u      ON u.id = a.coach_id
                JOIN sessions s   ON s.id = a.session_id
                WHERE a.workspace_id = :wid
                  AND a.status IN ('published','edited')
                  AND ath.user_id = :uid
                ORDER BY COALESCE(a.edited_at, a.published_at) DESC NULLS LAST
                LIMIT 50
                """
            ),
            {"wid": workspace_id, "uid": user_id},
        )
    ).all()
    return [
        TraineeAssessmentSummary(
            id=str(r[0]),
            session_id=str(r[1]),
            status=r[2],
            published_at=r[3],
            edited_at=r[4],
            summary=r[5],
            coach_display_name=r[6],
            session_scheduled_at=r[7],
            session_duration_min=r[8],
            session_court=r[9],
            session_focus=r[10],
            score_count=int(r[11] or 0),
            has_feedback=bool(r[12]),
        )
        for r in rows
    ]


# ── GET /assessments/mine/latest (trainee-side) ─────────────────


@router.get("/mine/latest", response_model=AssessmentOut | None)
async def latest_for_me(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> AssessmentOut | None:
    """Latest published/edited assessment whose athlete is linked to the
    caller's user.  Used by the trainee home to surface the "How was this
    session?" feedback CTA."""
    if workspace_id is None:
        return None
    row = (
        await db.execute(
            text(
                """
                SELECT a.id
                FROM assessments a
                JOIN athletes ath ON ath.id = a.athlete_id
                WHERE a.workspace_id = :wid
                  AND a.status IN ('published','edited')
                  AND ath.user_id = :uid
                ORDER BY COALESCE(a.edited_at, a.published_at) DESC NULLS LAST
                LIMIT 1
                """
            ),
            {"wid": workspace_id, "uid": user_id},
        )
    ).first()
    if row is None:
        return None
    return await load_assessment(db, assessment_id=row[0])


# ── GET /assessments/by-session/{id} ────────────────────────────


@router.get("/by-session/{session_id}", response_model=AssessmentOut | None)
async def by_session(
    session_id: UUID,
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> AssessmentOut | None:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active workspace.",
        )
    return await load_by_session(db, session_id=session_id)


# ── GET /assessments/{id} ───────────────────────────────────────


@router.get("/{assessment_id}", response_model=AssessmentOut)
async def get_one(
    assessment_id: UUID,
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> AssessmentOut:
    try:
        return await load_assessment(db, assessment_id=assessment_id)
    except AssessmentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found."
        )


# ── POST /assessments/{id}/publish ──────────────────────────────


@router.post("/{assessment_id}/publish", response_model=AssessmentOut)
@audit_action(
    "assessment.published",
    entity_type="assessment",
    extract=lambda r, kw: {
        "assessment_id": r.id,
        "scores": len(r.scores),
    },
)
async def publish_assessment(
    assessment_id: UUID,
    body: PublishIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> AssessmentOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No active workspace."
        )
    try:
        result = await publish(
            db,
            workspace_id=workspace_id,
            coach_id=user_id,
            assessment_id=assessment_id,
            force_empty=body.force_empty,
        )
    except AssessmentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found."
        )
    except StatusConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationFailedError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": e.errors},
        )
    await db.commit()
    return result


# ── PATCH /assessments/{id} (edit published) ────────────────────


@router.patch("/{assessment_id}", response_model=AssessmentOut)
@audit_action(
    "assessment.edited",
    entity_type="assessment",
    extract=lambda r, _kw: {
        "assessment_id": r.id,
        "status": r.status,
    },
)
async def patch_assessment(
    assessment_id: UUID,
    body: AssessmentEditIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> AssessmentOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No active workspace."
        )
    try:
        result = await edit_assessment(
            db,
            workspace_id=workspace_id,
            coach_id=user_id,
            assessment_id=assessment_id,
            patch=body,
        )
    except AssessmentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found."
        )
    except InvalidSkillError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more skills are not part of this curriculum.",
        )
    except StatusConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    await db.commit()
    return result


# ── DELETE /assessments/{id} (discard draft) ────────────────────


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_action(
    "assessment.draft_discarded",
    entity_type="assessment",
    extract=lambda r, kw: {"assessment_id": str(kw.get("assessment_id"))},
)
async def delete_draft(
    assessment_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> None:
    try:
        await discard_draft(db, coach_id=user_id, assessment_id=assessment_id)
    except AssessmentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found."
        )
    except StatusConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    await db.commit()
    return None


# ── POST /assessments/{id}/view ─────────────────────────────────


@router.post("/{assessment_id}/view", status_code=status.HTTP_204_NO_CONTENT)
async def mark_viewed(
    assessment_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> None:
    """Trainee marks an assessment as viewed.  Idempotent: first view wins,
    subsequent calls are no-ops so the timestamp reflects "first opened"."""
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active workspace.",
        )
    # Allow only the linked trainee user.  Coaches reading the assessment
    # should not register as the trainee's view.
    r = (
        await db.execute(
            text(
                """
                SELECT a.id
                FROM assessments a
                JOIN athletes ath ON ath.id = a.athlete_id
                WHERE a.id = :aid
                  AND a.workspace_id = :wid
                  AND a.status IN ('published','edited')
                  AND ath.user_id = :uid
                """
            ),
            {"aid": assessment_id, "wid": workspace_id, "uid": user_id},
        )
    ).first()
    if r is None:
        # Either not found or the caller isn't the linked trainee.  We don't
        # want to leak the difference — quietly return.
        return None
    await db.execute(
        text(
            """
            UPDATE assessments
               SET trainee_viewed_at = COALESCE(trainee_viewed_at, NOW())
             WHERE id = :aid
            """
        ),
        {"aid": assessment_id},
    )
    await db.commit()
    return None


# ── GET /assessments/{id}/edits ─────────────────────────────────


@router.get("/{assessment_id}/edits", response_model=list[AssessmentEditOut])
async def edits_history(
    assessment_id: UUID,
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> list[AssessmentEditOut]:
    rows = (
        await db.execute(
            text(
                """
                SELECT e.id, e.edited_by_id, u.display_name,
                       e.edited_at, e.changes_jsonb, e.reason
                FROM assessment_edits e
                JOIN users u ON u.id = e.edited_by_id
                WHERE e.assessment_id = :aid
                ORDER BY e.edited_at DESC
                """
            ),
            {"aid": assessment_id},
        )
    ).all()
    return [
        AssessmentEditOut(
            id=str(r[0]),
            edited_by_id=str(r[1]),
            edited_by_display_name=r[2],
            edited_at=r[3],
            changes=r[4],
            reason=r[5],
        )
        for r in rows
    ]
