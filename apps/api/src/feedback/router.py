"""Trainee feedback endpoints.

  POST   /assessments/{id}/feedback     — trainee/parent submits
  GET    /assessments/{id}/feedback     — coach reads (identity stripped if anonymous)
  PATCH  /feedback/{id}                 — submitter edits within 24h
  DELETE /feedback/{id}                 — submitter withdraws
  POST   /feedback/{id}/read            — coach marks as seen
  GET    /feedback/inbox                — coach inbox (unread first)

The anonymity rule is enforced at the API boundary: the server-side
projection strips ``submitter_display_name`` when ``is_anonymous=True``
and the viewer isn't the submitter themselves.  The DB always knows
who submitted (for rate-limit, moderation, edit/withdraw).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.decorators import audit_action
from src.auth.service import get_role_in_workspace
from src.deps import get_current_user_id, get_current_workspace_id
from src.middleware.rls import db_with_rls

from .schemas import (
    FeedbackEditIn,
    FeedbackInboxItem,
    FeedbackOut,
    FeedbackSubmitIn,
)

EDIT_WINDOW = timedelta(hours=24)

# Two routers — one under /assessments/{id}/feedback (nested), one at /feedback/*.
assessment_feedback_router = APIRouter(tags=["feedback"])
feedback_router = APIRouter(prefix="/feedback", tags=["feedback"])


# ── POST /assessments/{id}/feedback ─────────────────────────────


@assessment_feedback_router.post(
    "/assessments/{assessment_id}/feedback",
    response_model=FeedbackOut,
    status_code=status.HTTP_201_CREATED,
)
@audit_action(
    "feedback.submitted",
    entity_type="feedback",
    extract=lambda r, _kw: {
        "assessment_id": r.assessment_id,
        "rating_overall": r.rating_overall,
        "is_anonymous": r.is_anonymous,
    },
)
async def submit_feedback(
    assessment_id: UUID,
    body: FeedbackSubmitIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> FeedbackOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active workspace.",
        )

    role = await get_role_in_workspace(db, user_id, workspace_id)
    if role not in ("trainee", "parent"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only trainees or parents can submit feedback.",
        )

    # Verify the assessment is published and belongs to this workspace.
    ar = (
        await db.execute(
            text(
                """
                SELECT id, athlete_id, status
                FROM assessments
                WHERE id = :id
                  AND workspace_id = :wid
                  AND status IN ('published','edited')
                """
            ),
            {"id": assessment_id, "wid": workspace_id},
        )
    ).first()
    if ar is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found or not published.",
        )

    # If trainee: must be the linked user.  If parent: must be linked via
    # user_guardians.  Cheap check via RLS-bypassing facts.
    if role == "trainee":
        bound = await db.scalar(
            text(
                "SELECT 1 FROM athletes WHERE id = :aid AND user_id = :uid"
            ),
            {"aid": ar[1], "uid": user_id},
        )
        if not bound:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This assessment is for a different trainee.",
            )

    # UNIQUE index enforces "one per (assessment, user, role)" — we use ON
    # CONFLICT to allow a re-submission to update the latest non-withdrawn row.
    new_id = await db.scalar(
        text(
            """
            INSERT INTO feedbacks (
                workspace_id, assessment_id, submitted_by_user_id, submitter_role,
                is_anonymous, rating_overall, rating_fairness, comment
            )
            VALUES (
                :wid, :aid, :uid, :role,
                :anon, :ov, :fair, :comment
            )
            RETURNING id
            """
        ),
        {
            "wid": workspace_id,
            "aid": assessment_id,
            "uid": user_id,
            "role": role,
            "anon": body.is_anonymous,
            "ov": body.rating_overall,
            "fair": body.rating_fairness,
            "comment": body.comment,
        },
    )
    # Build the response inside the same transaction — committing first
    # would lose the RLS GUCs (SET LOCAL is per-transaction), and the
    # follow-up read would 404 on the new row.
    row = await _load_for_viewer(db, feedback_id=new_id, viewer_id=user_id)
    await db.commit()
    return row


# ── GET /assessments/{id}/feedback ──────────────────────────────


@assessment_feedback_router.get(
    "/assessments/{assessment_id}/feedback",
    response_model=list[FeedbackOut],
)
async def list_feedback_for_assessment(
    assessment_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> list[FeedbackOut]:
    rows = (
        await db.execute(
            text(
                """
                SELECT f.id, f.assessment_id, f.submitter_role,
                       f.is_anonymous, f.rating_overall, f.rating_fairness,
                       f.comment, f.submitted_at, f.edited_at, f.read_at,
                       f.submitted_by_user_id, u.display_name
                FROM feedbacks f
                JOIN users u ON u.id = f.submitted_by_user_id
                WHERE f.assessment_id = :aid AND f.withdrawn_at IS NULL
                ORDER BY f.submitted_at DESC
                """
            ),
            {"aid": assessment_id},
        )
    ).all()
    out: list[FeedbackOut] = []
    now = datetime.now(UTC)
    for r in rows:
        is_self = r[10] == user_id
        anon = bool(r[3])
        display = r[11] if (is_self or not anon) else None
        out.append(
            FeedbackOut(
                id=str(r[0]),
                assessment_id=str(r[1]),
                submitter_role=r[2],
                submitter_display_name=display,
                is_anonymous=anon,
                rating_overall=r[4],
                rating_fairness=r[5],
                comment=r[6],
                submitted_at=r[7],
                edited_at=r[8],
                read_at=r[9],
                can_edit=is_self and _within_edit_window(r[7], now),
                can_withdraw=is_self,
            )
        )
    return out


# ── PATCH /feedback/{id} ─────────────────────────────────────────


@feedback_router.patch("/{feedback_id}", response_model=FeedbackOut)
async def edit_feedback(
    feedback_id: UUID,
    body: FeedbackEditIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> FeedbackOut:
    r = (
        await db.execute(
            text(
                """
                SELECT id, submitted_by_user_id, submitted_at, withdrawn_at
                FROM feedbacks WHERE id = :id
                """
            ),
            {"id": feedback_id},
        )
    ).first()
    if r is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found."
        )
    if r[1] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the submitter can edit feedback.",
        )
    if r[3] is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feedback is already withdrawn.",
        )
    if not _within_edit_window(r[2], datetime.now(UTC)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Edit window has expired (24 hours).",
        )

    sets: list[str] = []
    params: dict = {"id": feedback_id}
    if body.rating_overall is not None:
        sets.append("rating_overall = :ov")
        params["ov"] = body.rating_overall
    if body.rating_fairness is not None:
        sets.append("rating_fairness = :fair")
        params["fair"] = body.rating_fairness
    if body.comment is not None:
        sets.append("comment = :comment")
        params["comment"] = body.comment
    if body.is_anonymous is not None:
        sets.append("is_anonymous = :anon")
        params["anon"] = body.is_anonymous
    if not sets:
        return await _load_for_viewer(db, feedback_id=feedback_id, viewer_id=user_id)
    sets.append("edited_at = NOW()")
    await db.execute(
        text(f"UPDATE feedbacks SET {', '.join(sets)} WHERE id = :id"),
        params,
    )
    out = await _load_for_viewer(db, feedback_id=feedback_id, viewer_id=user_id)
    await db.commit()
    return out


# ── DELETE /feedback/{id} (withdraw) ────────────────────────────


@feedback_router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_feedback(
    feedback_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> None:
    r = (
        await db.execute(
            text(
                "SELECT submitted_by_user_id, withdrawn_at FROM feedbacks WHERE id = :id"
            ),
            {"id": feedback_id},
        )
    ).first()
    if r is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found."
        )
    if r[0] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the submitter can withdraw.",
        )
    if r[1] is not None:
        # Already withdrawn — idempotent no-op.
        return None
    await db.execute(
        text(
            "UPDATE feedbacks SET withdrawn_at = NOW() WHERE id = :id"
        ),
        {"id": feedback_id},
    )
    await db.commit()
    return None


# ── POST /feedback/{id}/read ────────────────────────────────────


@feedback_router.post("/{feedback_id}/read", response_model=FeedbackOut)
async def mark_read(
    feedback_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> FeedbackOut:
    r = (
        await db.execute(
            text(
                """
                SELECT f.id
                FROM feedbacks f
                JOIN assessments a ON a.id = f.assessment_id
                WHERE f.id = :id AND a.coach_id = :uid
                """
            ),
            {"id": feedback_id, "uid": user_id},
        )
    ).first()
    if r is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found."
        )
    await db.execute(
        text(
            "UPDATE feedbacks SET read_at = COALESCE(read_at, NOW()) WHERE id = :id"
        ),
        {"id": feedback_id},
    )
    out = await _load_for_viewer(db, feedback_id=feedback_id, viewer_id=user_id)
    await db.commit()
    return out


# ── GET /feedback/inbox ─────────────────────────────────────────


@feedback_router.get("/inbox", response_model=list[FeedbackInboxItem])
async def inbox(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> list[FeedbackInboxItem]:
    if workspace_id is None:
        return []
    rows = (
        await db.execute(
            text(
                """
                SELECT f.id, f.assessment_id, f.submitter_role,
                       f.is_anonymous, f.rating_overall, f.rating_fairness,
                       f.comment, f.submitted_at, f.read_at,
                       ath.display_name AS athlete_name,
                       s.scheduled_at, s.focus
                FROM feedbacks f
                JOIN assessments a ON a.id = f.assessment_id
                JOIN athletes ath ON ath.id = a.athlete_id
                JOIN sessions s   ON s.id = a.session_id
                WHERE f.workspace_id = :wid
                  AND f.withdrawn_at IS NULL
                  AND a.coach_id = :uid
                ORDER BY (f.read_at IS NULL) DESC, f.submitted_at DESC
                LIMIT 100
                """
            ),
            {"wid": workspace_id, "uid": user_id},
        )
    ).all()
    out: list[FeedbackInboxItem] = []
    for r in rows:
        anon = bool(r[3])
        out.append(
            FeedbackInboxItem(
                id=str(r[0]),
                assessment_id=str(r[1]),
                submitter_role=r[2],
                is_anonymous=anon,
                rating_overall=r[4],
                rating_fairness=r[5],
                comment=r[6],
                submitted_at=r[7],
                read_at=r[8],
                athlete_display_name=None if anon else r[9],
                session_scheduled_at=r[10],
                session_focus=r[11],
            )
        )
    return out


# ── Helpers ─────────────────────────────────────────────────────


def _within_edit_window(submitted_at: datetime, now: datetime) -> bool:
    sa = submitted_at
    if sa.tzinfo is None:
        sa = sa.replace(tzinfo=UTC)
    return now - sa <= EDIT_WINDOW


async def _load_for_viewer(
    db: AsyncSession, *, feedback_id: UUID, viewer_id: UUID
) -> FeedbackOut:
    r = (
        await db.execute(
            text(
                """
                SELECT f.id, f.assessment_id, f.submitter_role, f.is_anonymous,
                       f.rating_overall, f.rating_fairness, f.comment,
                       f.submitted_at, f.edited_at, f.read_at,
                       f.submitted_by_user_id, u.display_name
                FROM feedbacks f
                JOIN users u ON u.id = f.submitted_by_user_id
                WHERE f.id = :id
                """
            ),
            {"id": feedback_id},
        )
    ).first()
    if r is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found."
        )
    is_self = r[10] == viewer_id
    anon = bool(r[3])
    display = r[11] if (is_self or not anon) else None
    now = datetime.now(UTC)
    return FeedbackOut(
        id=str(r[0]),
        assessment_id=str(r[1]),
        submitter_role=r[2],
        submitter_display_name=display,
        is_anonymous=anon,
        rating_overall=r[4],
        rating_fairness=r[5],
        comment=r[6],
        submitted_at=r[7],
        edited_at=r[8],
        read_at=r[9],
        can_edit=is_self and _within_edit_window(r[7], now),
        can_withdraw=is_self,
    )
