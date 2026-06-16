"""GET /trainees/{id}/profile — full coach-side trainee profile.

Mirrors the trainee-home shape but from the coach's perspective: stats, tier
progress with blockers, category averages, recent gains, all 27 skill levels,
recent published sessions.  Replaces the FE mock that was wired up before
the assessment v2 schema landed.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.assessments.service import recompute_tier
from src.deps import get_current_workspace_id
from src.middleware.rls import db_with_rls
from src.sports.service import SportError, resolve_sport_id

router = APIRouter(prefix="/trainees", tags=["trainees"])


# ── Schemas ─────────────────────────────────────────────────────


class TierBrief(BaseModel):
    id: str
    code: str
    name_game_en: str
    name_game_id: str


class SkillBrief(BaseModel):
    id: str
    code: str
    category: str
    name_en: str
    name_id: str
    display_order: int


class SkillScoreOut(BaseModel):
    skill: SkillBrief
    level: int | None
    last_rated_at: datetime | None


class BlockingSkillOut(BaseModel):
    skill: SkillBrief
    current_level: int
    required_level: int


class GainEntryOut(BaseModel):
    skill: SkillBrief
    from_level: int | None
    to_level: int
    recorded_at: datetime


class CoachBriefOut(BaseModel):
    id: str
    display_name: str


class SessionEntryOut(BaseModel):
    id: str
    scheduled_at: datetime
    duration_min: int
    focuses: list[str]
    summary: str | None
    skills_updated: int
    coach: CoachBriefOut
    assessment_status: str  # 'none' | 'draft' | 'published' | 'edited'


class CategoryAverageOut(BaseModel):
    category: str
    average: float
    skills_rated: int


class TraineeIdentityOut(BaseModel):
    id: str
    display_name: str
    joined_at: date
    is_minor: bool


class TraineeStatsOut(BaseModel):
    sessions_count: int
    hours_coached: float
    days_since_last_session: int | None


class TierProgressOut(BaseModel):
    current_tier: TierBrief
    next_tier: TierBrief | None
    met_count: int
    total_requirements: int
    blocking_skills: list[BlockingSkillOut]


class TraineeProfileOut(BaseModel):
    trainee: TraineeIdentityOut
    stats: TraineeStatsOut
    tier_progress: TierProgressOut
    category_averages: list[CategoryAverageOut]
    recent_gains: list[GainEntryOut]
    all_skills: list[SkillScoreOut]
    recent_sessions: list[SessionEntryOut]


# ── Endpoint ────────────────────────────────────────────────────


@router.get("/{athlete_id}/profile", response_model=TraineeProfileOut)
async def get_trainee_profile(
    athlete_id: UUID,
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
    sport_id: UUID | None = Query(default=None),
) -> TraineeProfileOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No active workspace."
        )

    identity = (
        await db.execute(
            text(
                """
                SELECT id, display_name, joined_at, is_minor
                FROM athletes
                WHERE id = :id AND workspace_id = :wid AND archived_at IS NULL
                """
            ),
            {"id": athlete_id, "wid": workspace_id},
        )
    ).mappings().first()
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trainee not found."
        )

    # Resolve sport (skill / tier scoping) — defaults to the workspace's
    # single active sport when the caller omits sport_id.
    try:
        sport_id = await resolve_sport_id(
            db, workspace_id=workspace_id, sport_id=sport_id
        )
    except SportError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e

    # ── All platform skills + the trainee's latest level per skill ──
    all_skill_rows = (
        await db.execute(
            text(
                """
                SELECT s.id, s.code, s.category::text AS category,
                       s.name_en, s.name_id, s.display_order
                FROM skills s
                WHERE s.sport_id = :sid
                  AND (s.workspace_id = :wid OR s.workspace_id IS NULL)
                  AND s.is_enabled = TRUE
                ORDER BY s.display_order
                """
            ),
            {"sid": sport_id, "wid": workspace_id},
        )
    ).mappings().all()

    latest_rows = (
        await db.execute(
            text(
                """
                SELECT DISTINCT ON (sc.skill_id)
                    sc.skill_id, sc.level,
                    COALESCE(a.edited_at, a.published_at) AS last_at
                FROM assessment_scores sc
                JOIN assessments a ON a.id = sc.assessment_id
                WHERE a.athlete_id = :aid
                  AND a.status IN ('published','edited')
                ORDER BY sc.skill_id,
                         COALESCE(a.edited_at, a.published_at) DESC NULLS LAST,
                         sc.updated_at DESC
                """
            ),
            {"aid": athlete_id},
        )
    ).mappings().all()
    latest_by_skill: dict[UUID, dict[str, Any]] = {
        r["skill_id"]: {"level": r["level"], "last_at": r["last_at"]}
        for r in latest_rows
    }

    all_skills = [
        SkillScoreOut(
            skill=SkillBrief(
                id=str(s["id"]),
                code=s["code"],
                category=s["category"],
                name_en=s["name_en"],
                name_id=s["name_id"],
                display_order=s["display_order"],
            ),
            level=(latest_by_skill[s["id"]]["level"] if s["id"] in latest_by_skill else None),
            last_rated_at=(latest_by_skill[s["id"]]["last_at"] if s["id"] in latest_by_skill else None),
        )
        for s in all_skill_rows
    ]

    # ── Tier progress (current + next + blockers) ──
    levels = {sid: data["level"] for sid, data in latest_by_skill.items()}
    tier_info = await recompute_tier(
        db,
        workspace_id=workspace_id,
        athlete_id=athlete_id,
        sport_id=sport_id,
        levels=levels,
    )

    # Look up "next tier" requirements to compute blockers.
    blockers: list[BlockingSkillOut] = []
    if tier_info["next_tier"] is not None:
        reqs = (
            await db.execute(
                text(
                    """
                    SELECT tr.skill_id, tr.min_level,
                           s.id, s.code, s.category::text AS category,
                           s.name_en, s.name_id, s.display_order
                    FROM tier_requirements tr
                    JOIN skills s ON s.id = tr.skill_id
                    WHERE tr.tier_id = :tid
                    ORDER BY tr.min_level DESC, s.display_order
                    """
                ),
                {"tid": tier_info["next_tier"].id},
            )
        ).mappings().all()
        for r in reqs:
            cur = levels.get(r["skill_id"], 0)
            if cur < r["min_level"]:
                blockers.append(
                    BlockingSkillOut(
                        skill=SkillBrief(
                            id=str(r["id"]),
                            code=r["code"],
                            category=r["category"],
                            name_en=r["name_en"],
                            name_id=r["name_id"],
                            display_order=r["display_order"],
                        ),
                        current_level=cur,
                        required_level=r["min_level"],
                    )
                )

    # Current tier may be None for trainees with zero requirements met above
    # BEGINNER — but tier_info gives us the BEGINNER row as a fallback already.
    current_brief = tier_info["current_tier"]
    if current_brief is None:
        # Beginner row fetch fallback (shouldn't trigger; defensive only).
        beg = (
            await db.execute(
                text(
                    """
                    SELECT id, code, name_game_en, name_game_id
                    FROM tiers
                    WHERE sport_id = :sid AND display_order = 1
                      AND (workspace_id = :wid OR workspace_id IS NULL)
                    LIMIT 1
                    """
                ),
                {"sid": sport_id, "wid": workspace_id},
            )
        ).mappings().first()
        current_tier_out = TierBrief(
            id=str(beg["id"]),
            code=beg["code"],
            name_game_en=beg["name_game_en"],
            name_game_id=beg["name_game_id"],
        )
    else:
        current_tier_out = TierBrief(
            id=current_brief.id,
            code=current_brief.code,
            name_game_en=current_brief.name_game_en,
            name_game_id=current_brief.name_game_id,
        )

    next_tier_out = (
        TierBrief(
            id=tier_info["next_tier"].id,
            code=tier_info["next_tier"].code,
            name_game_en=tier_info["next_tier"].name_game_en,
            name_game_id=tier_info["next_tier"].name_game_id,
        )
        if tier_info["next_tier"] is not None
        else None
    )

    tier_progress = TierProgressOut(
        current_tier=current_tier_out,
        next_tier=next_tier_out,
        met_count=tier_info["met_count"],
        total_requirements=tier_info["total_requirements"],
        blocking_skills=blockers,
    )

    # ── Category averages ──
    cat_buckets: dict[str, list[int]] = {
        "technical": [], "tactical": [], "physical": [], "mental": [],
    }
    skill_cat_lookup = {s["id"]: s["category"] for s in all_skill_rows}
    for sid, data in latest_by_skill.items():
        cat = skill_cat_lookup.get(sid)
        if cat:
            cat_buckets.setdefault(cat, []).append(data["level"])
    category_averages = [
        CategoryAverageOut(
            category=cat,
            average=round(sum(vals) / len(vals), 1) if vals else 0,
            skills_rated=len(vals),
        )
        for cat, vals in cat_buckets.items()
    ]

    # ── Recent gains ──
    gains_rows = (
        await db.execute(
            text(
                """
                WITH ranked AS (
                  SELECT sc.skill_id, sc.level,
                         COALESCE(a.edited_at, a.published_at) AS recorded_at,
                         ROW_NUMBER() OVER (
                           PARTITION BY sc.skill_id
                           ORDER BY COALESCE(a.edited_at, a.published_at) DESC NULLS LAST,
                                    sc.updated_at DESC
                         ) AS rn
                  FROM assessment_scores sc
                  JOIN assessments a ON a.id = sc.assessment_id
                  WHERE a.athlete_id = :aid
                    AND a.status IN ('published','edited')
                )
                SELECT r.skill_id, r.level AS to_level, r.recorded_at,
                       p.level AS from_level,
                       s.code, s.category::text AS category,
                       s.name_en, s.name_id, s.display_order
                FROM ranked r
                LEFT JOIN ranked p ON p.skill_id = r.skill_id AND p.rn = 2
                JOIN skills s ON s.id = r.skill_id
                WHERE r.rn = 1
                  AND (p.level IS NULL OR r.level > p.level)
                ORDER BY r.recorded_at DESC NULLS LAST
                LIMIT 5
                """
            ),
            {"aid": athlete_id},
        )
    ).mappings().all()
    recent_gains = [
        GainEntryOut(
            skill=SkillBrief(
                id=str(g["skill_id"]),
                code=g["code"],
                category=g["category"],
                name_en=g["name_en"],
                name_id=g["name_id"],
                display_order=g["display_order"],
            ),
            from_level=g["from_level"],
            to_level=g["to_level"],
            recorded_at=g["recorded_at"],
        )
        for g in gains_rows
    ]

    # ── Stats (sessions count, hours coached, days since last) ──
    stats_row = (
        await db.execute(
            text(
                """
                SELECT count(*) AS sessions_count,
                       COALESCE(SUM(duration_min), 0) AS minutes,
                       MAX(scheduled_at) AS last_at
                FROM sessions
                WHERE athlete_id = :aid AND status = 'completed'
                """
            ),
            {"aid": athlete_id},
        )
    ).mappings().first()
    sessions_count = int(stats_row["sessions_count"] or 0) if stats_row else 0
    minutes = int(stats_row["minutes"] or 0) if stats_row else 0
    last_at = stats_row["last_at"] if stats_row else None
    days_since: int | None = None
    if last_at is not None:
        from datetime import UTC as _UTC, datetime as _dt
        now = _dt.now(_UTC)
        delta = now - (last_at if last_at.tzinfo else last_at.replace(tzinfo=_UTC))
        days_since = int(delta.total_seconds() // 86400)

    stats = TraineeStatsOut(
        sessions_count=sessions_count,
        hours_coached=round(minutes / 60, 1),
        days_since_last_session=days_since,
    )

    # ── Recent sessions (with coach + assessment status + multi-focus) ──
    session_rows = (
        await db.execute(
            text(
                """
                SELECT s.id, s.scheduled_at, s.duration_min,
                       a.summary, a.status AS assessment_status,
                       s.coach_id, cu.display_name AS coach_display_name,
                       (SELECT count(*) FROM assessment_scores
                          WHERE assessment_id = a.id) AS skills_updated
                FROM sessions s
                JOIN users cu ON cu.id = s.coach_id
                LEFT JOIN assessments a ON a.session_id = s.id
                WHERE s.athlete_id = :aid
                  AND s.status IN ('completed','scheduled')
                  AND s.scheduled_at <= NOW()
                ORDER BY s.scheduled_at DESC
                LIMIT 8
                """
            ),
            {"aid": athlete_id},
        )
    ).mappings().all()
    session_ids = [s["id"] for s in session_rows]
    focuses_map: dict = {}
    if session_ids:
        placeholders = ", ".join(f":s{i}" for i in range(len(session_ids)))
        focuses_rows = (
            await db.execute(
                text(
                    f"SELECT session_id, focus FROM session_focuses "
                    f"WHERE session_id IN ({placeholders}) "
                    f"ORDER BY session_id, ordinal"
                ),
                {f"s{i}": sid for i, sid in enumerate(session_ids)},
            )
        ).all()
        for sid, focus in focuses_rows:
            focuses_map.setdefault(sid, []).append(focus)

    def _assess_status(s: dict) -> str:
        astat = s.get("assessment_status")
        if astat is None:
            return "none"
        if astat in ("published", "edited", "draft"):
            return astat
        return "none"

    recent_sessions = [
        SessionEntryOut(
            id=str(s["id"]),
            scheduled_at=s["scheduled_at"],
            duration_min=int(s["duration_min"] or 60),
            focuses=focuses_map.get(s["id"], []),
            summary=s["summary"],
            skills_updated=int(s["skills_updated"] or 0),
            coach=CoachBriefOut(
                id=str(s["coach_id"]),
                display_name=s["coach_display_name"],
            ),
            assessment_status=_assess_status(s),
        )
        for s in session_rows
    ]

    return TraineeProfileOut(
        trainee=TraineeIdentityOut(
            id=str(identity["id"]),
            display_name=identity["display_name"],
            joined_at=identity["joined_at"],
            is_minor=identity["is_minor"],
        ),
        stats=stats,
        tier_progress=tier_progress,
        category_averages=category_averages,
        recent_gains=recent_gains,
        all_skills=all_skills,
        recent_sessions=recent_sessions,
    )
