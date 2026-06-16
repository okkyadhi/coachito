"""POST /assessments/{id}/draft-summary — Gemini-drafted assessment summary.

Authorization:
  - assessment's coach OR head_coach OR club_admin in the workspace → 200
  - other coach in the workspace → 403
  - trainee / parent / no membership → 403
  - assessment not in this workspace → 404 (RLS hides it)
  - assessment has zero scored skills → 409

Caller's coach `summary_style` and `preferred_locale` shape the draft.  The
response is text only; nothing is written to the DB.  Every call is audited
via ``ai.draft_generated`` (no draft text, no trainee data — just metadata).
"""

from __future__ import annotations

import json
import logging
import time
from typing import Annotated, Any
from uuid import UUID

import asyncpg
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.draft_summary import (
    SkillInput,
    SummaryLocale,
    SummaryStyle,
    draft_assessment_summary,
)
from src.ai.gemini_client import GeminiError
from src.auth.service import get_role_in_workspace
from src.config import settings
from src.deps import get_current_user_id, get_current_workspace_id
from src.invites.og_landing import _superuser_dsn
from src.middleware.rls import db_with_rls

log = logging.getLogger(__name__)

router = APIRouter(prefix="/assessments", tags=["assessments", "ai"])

# Shared httpx client — one connection pool across requests, closed on app
# shutdown via main.py's lifespan.  Lazy-instantiated so tests can override.
_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=settings.gemini_timeout_s)
    return _http_client


async def close_http_client() -> None:
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


class DraftSummaryOut(BaseModel):
    draft: str
    model: str


_PRIVILEGED_ROLES = ("club_admin", "head_coach")


async def _record_audit(
    *,
    workspace_id: UUID,
    user_id: UUID,
    assessment_id: UUID,
    metadata: dict[str, Any],
) -> None:
    """Append-only audit row.  Uses its own asyncpg connection (RLS-bypass)
    so a logging failure can never roll back the user-visible response."""
    try:
        conn = await asyncpg.connect(_superuser_dsn())
        try:
            await conn.execute(
                """
                INSERT INTO audit_log (
                    workspace_id, user_id, action,
                    entity_type, entity_id, metadata
                )
                VALUES ($1, $2, 'ai.draft_generated',
                        'assessment', $3, $4::jsonb)
                """,
                workspace_id,
                user_id,
                assessment_id,
                json.dumps(metadata),
            )
        finally:
            await conn.close()
    except Exception:  # pragma: no cover - audit must never break a route
        log.exception("audit_log_failed", extra={"action": "ai.draft_generated"})


@router.post(
    "/{assessment_id}/draft-summary",
    response_model=DraftSummaryOut,
)
async def draft_summary_endpoint(
    assessment_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
    http: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> DraftSummaryOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active workspace.",
        )

    # ── Auth: role gate ──────────────────────────────────────────
    role = await get_role_in_workspace(db, user_id, workspace_id)
    if role in ("trainee", "parent") or role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only coaches can draft assessment summaries.",
        )

    # ── Load the assessment (RLS scopes to this workspace) ───────
    assessment_row = (
        await db.execute(
            text(
                """
                SELECT a.id, a.coach_id, a.session_id, a.athlete_id,
                       ath.display_name AS trainee_display_name,
                       s.focus::text AS session_focus
                FROM assessments a
                JOIN athletes ath ON ath.id = a.athlete_id
                LEFT JOIN sessions s ON s.id = a.session_id
                WHERE a.id = :aid
                """
            ),
            {"aid": assessment_id},
        )
    ).mappings().first()
    if assessment_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found."
        )

    # ── Auth: ownership gate for plain coaches ───────────────────
    if role == "coach" and assessment_row["coach_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned coach can draft this summary.",
        )

    # ── Load the coach's voice + locale preference ───────────────
    coach_prefs = (
        await db.execute(
            text(
                "SELECT preferred_locale, summary_style FROM users "
                "WHERE id = :uid"
            ),
            {"uid": user_id},
        )
    ).mappings().first()
    locale: SummaryLocale = (
        "id"
        if coach_prefs and coach_prefs["preferred_locale"] == "id"
        else "en"
    )
    style: SummaryStyle = (
        coach_prefs["summary_style"]
        if coach_prefs
        and coach_prefs["summary_style"] in ("encouraging", "direct", "warm")
        else "encouraging"
    )

    # ── Assemble the skill list (uses coach's locale for names) ──
    name_col = "name_id" if locale == "id" else "name_en"
    skill_rows = (
        await db.execute(
            text(
                f"""
                SELECT sk.{name_col} AS name, sc.level, sc.note
                FROM assessment_scores sc
                JOIN skills sk ON sk.id = sc.skill_id
                WHERE sc.assessment_id = :aid
                ORDER BY sk.display_order
                """
            ),
            {"aid": assessment_id},
        )
    ).mappings().all()
    if not skill_rows:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Score at least one skill before drafting a summary.",
        )
    skills: list[SkillInput] = [
        {
            "name": r["name"],
            "score": int(r["level"]),
            "note": (r["note"] or None),
        }
        for r in skill_rows
    ]

    # ── Focuses (multi-focus rows if present, else legacy single) ──
    focus_rows = (
        await db.execute(
            text(
                """
                SELECT focus::text AS focus FROM session_focuses
                WHERE session_id = :sid
                ORDER BY ordinal
                """
            ),
            {"sid": assessment_row["session_id"]},
        )
    ).all()
    focuses: list[str] = [r[0] for r in focus_rows]
    if not focuses and assessment_row["session_focus"]:
        focuses = [assessment_row["session_focus"]]

    # ── Trainee first name (only PII sent to Gemini) ─────────────
    full = (assessment_row["trainee_display_name"] or "").strip()
    first_name = full.split()[0] if full else "the trainee"

    # ── Call Gemini ──────────────────────────────────────────────
    started = time.perf_counter()
    try:
        draft = await draft_assessment_summary(
            trainee_first_name=first_name,
            locale=locale,
            style=style,
            focuses=focuses,
            skills=skills,
            http=http,
        )
    except GeminiError:
        # NB: GeminiError subclasses RuntimeError, so this except clause
        # MUST come before the generic RuntimeError catch below.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service is temporarily unavailable, try again.",
        ) from None
    except RuntimeError:
        # Missing key — deploy isn't configured for AI.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI drafting is not configured for this deploy.",
        ) from None
    latency_ms = int((time.perf_counter() - started) * 1000)

    await _record_audit(
        workspace_id=workspace_id,
        user_id=user_id,
        assessment_id=assessment_id,
        metadata={
            "style": style,
            "locale": locale,
            "skill_count": len(skills),
            "latency_ms": latency_ms,
        },
    )

    return DraftSummaryOut(draft=draft, model=settings.gemini_model)
