"""GET /trainees/me/home — trainee self-scoped home payload.

Mirrors the FE shape in apps/web/src/features/trainee-home/trainee-home-api.ts.
Trainee-scoped RLS (migration 0015) keeps this honest: even if the SQL forgot
to filter by user_id, the DB only returns the caller's own rows.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.assessments.service import recompute_tier
from src.deps import get_current_user_id, get_current_workspace_id
from src.middleware.rls import db_with_rls
from src.sports.service import resolve_sport_id

router = APIRouter(prefix="/trainees/me", tags=["trainees"])


class TierBriefOut(BaseModel):
    code: str
    name_game_en: str
    name_game_id: str


class TraineeTierProgressOut(BaseModel):
    current_tier: TierBriefOut | None
    next_tier: TierBriefOut | None
    met_count: int
    total_requirements: int


class CategoryAverageOut(BaseModel):
    category: str
    average: float
    skills_rated: int


class GainOut(BaseModel):
    skill_name_en: str
    from_level: int | None
    to_level: int
    recorded_at: datetime


class UpcomingSessionOut(BaseModel):
    id: str
    scheduled_at: datetime
    duration_min: int
    court: str | None
    focus: str | None
    coach_display_name: str


class CoachNoteOut(BaseModel):
    coach_display_name: str
    session_date: datetime
    summary: str


class TraineeHomeOut(BaseModel):
    trainee_first_name: str
    workspace_name: str
    has_assessment: bool
    tier_progress: TraineeTierProgressOut | None
    upcoming_session: UpcomingSessionOut | None
    coach_note: CoachNoteOut | None
    category_averages: list[CategoryAverageOut]
    recent_gains: list[GainOut]
    rhythm_days14: list[bool]


@router.get("/home", response_model=TraineeHomeOut)
async def get_my_home(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
    sport_id: UUID | None = Query(default=None),
) -> TraineeHomeOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active workspace.",
        )

    resolved_sport_id = await resolve_sport_id(
        db, workspace_id=workspace_id, sport_id=sport_id
    )

    athlete = (
        await db.execute(
            text(
                """
                SELECT a.id, a.display_name,
                       w.name AS workspace_name
                FROM athletes a
                JOIN workspaces w ON w.id = a.workspace_id
                WHERE a.user_id = :uid AND a.workspace_id = :wid
                LIMIT 1
                """
            ),
            {"uid": user_id, "wid": workspace_id},
        )
    ).mappings().first()
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No trainee profile linked to this account.",
        )

    athlete_id: UUID = athlete["id"]
    first_name = (athlete["display_name"] or "").split()[0] or athlete["display_name"]

    # Latest level per skill for this sport, used by tier recalc + category averages.
    level_rows = (
        await db.execute(
            text(
                """
                SELECT DISTINCT ON (s.skill_id)
                    s.skill_id, s.level,
                    COALESCE(a.edited_at, a.published_at) AS recorded_at
                FROM assessment_scores s
                JOIN assessments a ON a.id = s.assessment_id
                WHERE a.athlete_id = :aid
                  AND a.sport_id = :sport_id
                  AND a.status IN ('published','edited')
                ORDER BY s.skill_id,
                         COALESCE(a.edited_at, a.published_at) DESC NULLS LAST,
                         s.updated_at DESC
                """
            ),
            {"aid": athlete_id, "sport_id": resolved_sport_id},
        )
    ).mappings().all()
    levels: dict[UUID, int] = {r["skill_id"]: r["level"] for r in level_rows}
    has_assessment = len(levels) > 0

    tier_progress = None
    category_averages: list[CategoryAverageOut] = [
        CategoryAverageOut(category=c, average=0, skills_rated=0)
        for c in ("technical", "tactical", "physical", "mental")
    ]
    recent_gains: list[GainOut] = []

    if has_assessment:
        tier_info = await recompute_tier(
            db,
            workspace_id=workspace_id,
            athlete_id=athlete_id,
            levels=levels,
            sport_id=resolved_sport_id,
        )
        tier_progress = TraineeTierProgressOut(
            current_tier=(
                TierBriefOut(
                    code=tier_info["current_tier"].code,
                    name_game_en=tier_info["current_tier"].name_game_en,
                    name_game_id=tier_info["current_tier"].name_game_id,
                )
                if tier_info["current_tier"] is not None
                else None
            ),
            next_tier=(
                TierBriefOut(
                    code=tier_info["next_tier"].code,
                    name_game_en=tier_info["next_tier"].name_game_en,
                    name_game_id=tier_info["next_tier"].name_game_id,
                )
                if tier_info["next_tier"] is not None
                else None
            ),
            met_count=tier_info["met_count"],
            total_requirements=tier_info["total_requirements"],
        )
        category_averages = await _category_averages(
            db, workspace_id=workspace_id, levels=levels
        )
        recent_gains = await _recent_gains(
            db,
            workspace_id=workspace_id,
            athlete_id=athlete_id,
            sport_id=resolved_sport_id,
        )

    upcoming = await _upcoming_session(db, athlete_id=athlete_id)
    coach_note = await _coach_note(db, athlete_id=athlete_id)
    rhythm = await _rhythm_days14(db, athlete_id=athlete_id)

    return TraineeHomeOut(
        trainee_first_name=first_name,
        workspace_name=athlete["workspace_name"],
        has_assessment=has_assessment,
        tier_progress=tier_progress,
        upcoming_session=upcoming,
        coach_note=coach_note,
        category_averages=category_averages,
        recent_gains=recent_gains,
        rhythm_days14=rhythm,
    )


async def _category_averages(
    db: AsyncSession, *, workspace_id: UUID, levels: dict[UUID, int]
) -> list[CategoryAverageOut]:
    if not levels:
        return [
            CategoryAverageOut(category=c, average=0, skills_rated=0)
            for c in ("technical", "tactical", "physical", "mental")
        ]
    skill_ids = list(levels.keys())
    placeholders = ", ".join(f":s{i}" for i in range(len(skill_ids)))
    params: dict[str, Any] = {f"s{i}": sid for i, sid in enumerate(skill_ids)}
    params["wid"] = workspace_id
    rows = (
        await db.execute(
            text(
                f"SELECT id, category FROM skills "
                f"WHERE id IN ({placeholders}) "
                f"  AND (workspace_id = :wid OR workspace_id IS NULL)"
            ),
            params,
        )
    ).all()
    buckets: dict[str, list[int]] = {
        "technical": [], "tactical": [], "physical": [], "mental": [],
    }
    for sid, cat in rows:
        buckets.setdefault(cat, []).append(levels[sid])
    return [
        CategoryAverageOut(
            category=cat,
            average=round(sum(vals) / len(vals), 1) if vals else 0,
            skills_rated=len(vals),
        )
        for cat, vals in buckets.items()
    ]


async def _recent_gains(
    db: AsyncSession, *, workspace_id: UUID, athlete_id: UUID, sport_id: UUID
) -> list[GainOut]:
    # Latest per skill + the prior level if any.  Crosscourt simpler version:
    # any skill with a level set in the last 30 days where we can find a
    # strictly-lower prior reading.  Cap at 5 most recent.
    rows = (
        await db.execute(
            text(
                """
                WITH ranked AS (
                  SELECT sc.skill_id,
                         sc.level,
                         COALESCE(a.edited_at, a.published_at) AS recorded_at,
                         ROW_NUMBER() OVER (
                           PARTITION BY sc.skill_id
                           ORDER BY COALESCE(a.edited_at, a.published_at) DESC NULLS LAST,
                                    sc.updated_at DESC
                         ) AS rn
                  FROM assessment_scores sc
                  JOIN assessments a ON a.id = sc.assessment_id
                  WHERE a.athlete_id = :aid
                    AND a.sport_id = :sport_id
                    AND a.status IN ('published','edited')
                )
                SELECT r.skill_id, r.level AS to_level, r.recorded_at,
                       p.level         AS from_level,
                       s.name_en
                FROM ranked r
                LEFT JOIN ranked p ON p.skill_id = r.skill_id AND p.rn = 2
                JOIN skills s      ON s.id = r.skill_id
                WHERE r.rn = 1
                  AND (p.level IS NULL OR r.level > p.level)
                ORDER BY r.recorded_at DESC
                LIMIT 5
                """
            ),
            {"aid": athlete_id, "sport_id": sport_id},
        )
    ).mappings().all()
    _ = workspace_id  # already enforced by RLS on assessments
    return [
        GainOut(
            skill_name_en=r["name_en"],
            from_level=r["from_level"],
            to_level=r["to_level"],
            recorded_at=r["recorded_at"],
        )
        for r in rows
    ]


async def _upcoming_session(
    db: AsyncSession, *, athlete_id: UUID
) -> UpcomingSessionOut | None:
    row = (
        await db.execute(
            text(
                """
                SELECT s.id, s.scheduled_at, s.duration_min, s.court, s.focus::TEXT AS focus,
                       u.display_name AS coach_display_name
                FROM sessions s
                JOIN users u ON u.id = s.coach_id
                WHERE s.athlete_id = :aid
                  AND s.scheduled_at >= NOW()
                  AND s.status = 'scheduled'
                ORDER BY s.scheduled_at ASC
                LIMIT 1
                """
            ),
            {"aid": athlete_id},
        )
    ).mappings().first()
    if row is None:
        return None
    return UpcomingSessionOut(
        id=str(row["id"]),
        scheduled_at=row["scheduled_at"],
        duration_min=row["duration_min"],
        court=row["court"],
        focus=row["focus"],
        coach_display_name=row["coach_display_name"],
    )


async def _coach_note(
    db: AsyncSession, *, athlete_id: UUID
) -> CoachNoteOut | None:
    row = (
        await db.execute(
            text(
                """
                SELECT s.scheduled_at AS session_date, s.summary,
                       u.display_name AS coach_display_name
                FROM sessions s
                JOIN users u ON u.id = s.coach_id
                WHERE s.athlete_id = :aid
                  AND s.summary IS NOT NULL
                  AND s.scheduled_at <= NOW()
                ORDER BY s.scheduled_at DESC
                LIMIT 1
                """
            ),
            {"aid": athlete_id},
        )
    ).mappings().first()
    if row is None:
        return None
    return CoachNoteOut(
        coach_display_name=row["coach_display_name"],
        session_date=row["session_date"],
        summary=row["summary"],
    )


async def _rhythm_days14(
    db: AsyncSession, *, athlete_id: UUID
) -> list[bool]:
    """14-element bool array, oldest first.  True = had at least one session
    that day."""
    rows = (
        await db.execute(
            text(
                """
                SELECT DISTINCT DATE(scheduled_at AT TIME ZONE 'UTC') AS d
                FROM sessions
                WHERE athlete_id = :aid
                  AND scheduled_at >= NOW() - INTERVAL '14 days'
                  AND scheduled_at <= NOW()
                """
            ),
            {"aid": athlete_id},
        )
    ).all()
    active = {r[0] for r in rows}
    today = datetime.now(UTC).date()
    return [
        (today - timedelta(days=13 - i)) in active for i in range(14)
    ]
