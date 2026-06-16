"""Aggregate queries powering the trainee-self Skills endpoints.

Single source of truth for category labels: server returns the canonical
EN/ID labels so the FE doesn't need a parallel mapping.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

CATEGORY_LABELS: dict[str, dict[str, str]] = {
    "technical": {"en": "Technical", "id": "Teknik"},
    "tactical":  {"en": "Tactical",  "id": "Taktik"},
    "physical":  {"en": "Physical",  "id": "Fisik"},
    "mental":    {"en": "Mental",    "id": "Mental"},
}
CATEGORY_ORDER: list[str] = ["technical", "tactical", "physical", "mental"]


async def find_my_athlete_id(
    db: AsyncSession, *, user_id: UUID, workspace_id: UUID
) -> UUID | None:
    row = (
        await db.execute(
            text(
                "SELECT id FROM athletes "
                "WHERE user_id = :uid AND workspace_id = :wid "
                "  AND archived_at IS NULL LIMIT 1"
            ),
            {"uid": user_id, "wid": workspace_id},
        )
    ).first()
    return row[0] if row else None


async def latest_per_skill(
    db: AsyncSession, *, athlete_id: UUID, sport_id: UUID | None = None
) -> list[dict[str, Any]]:
    """Latest published/edited level per skill, with the timestamp.

    Pass ``sport_id`` to scope to a single sport's assessments.
    """
    sport_filter = "AND a.sport_id = :sport_id" if sport_id is not None else ""
    rows = (
        await db.execute(
            text(
                f"""
                SELECT DISTINCT ON (sc.skill_id)
                    sc.skill_id,
                    sc.level,
                    COALESCE(a.edited_at, a.published_at) AS recorded_at
                FROM assessment_scores sc
                JOIN assessments a ON a.id = sc.assessment_id
                WHERE a.athlete_id = :aid
                  AND a.status IN ('published','edited')
                  {sport_filter}
                ORDER BY sc.skill_id,
                         COALESCE(a.edited_at, a.published_at) DESC NULLS LAST,
                         sc.updated_at DESC
                """
            ),
            {"aid": athlete_id, **({"sport_id": sport_id} if sport_id is not None else {})},
        )
    ).mappings().all()
    return [dict(r) for r in rows]


async def all_skills_for_workspace(
    db: AsyncSession, *, workspace_id: UUID, sport_id: UUID | None = None
) -> list[dict[str, Any]]:
    """Return all enabled skills for the workspace scoped to a sport.

    When ``sport_id`` is None, falls back to the legacy ``workspaces.sport_id``
    column so single-sport workspaces need no migration.
    """
    if sport_id is not None:
        sport_clause = "sport_id = :sid"
        params: dict[str, Any] = {"wid": workspace_id, "sid": sport_id}
    else:
        sport_clause = "sport_id = (SELECT sport_id FROM workspaces WHERE id = :wid)"
        params = {"wid": workspace_id}
    rows = (
        await db.execute(
            text(
                f"""
                SELECT id, code, category::text AS category,
                       name_en, name_id,
                       short_label_en, short_label_id,
                       display_order
                FROM skills
                WHERE {sport_clause}
                  AND (workspace_id = :wid OR workspace_id IS NULL)
                  AND is_enabled = TRUE
                ORDER BY display_order ASC
                """
            ),
            params,
        )
    ).mappings().all()
    return [dict(r) for r in rows]


async def recent_gains(
    db: AsyncSession,
    *,
    athlete_id: UUID,
    days: int = 14,
    limit: int = 4,
    sport_id: UUID | None = None,
) -> list[dict[str, Any]]:
    """Skills whose latest score is higher than the prior score, within
    ``days``.  Returns one entry per skill, newest first."""
    sport_filter = "AND a.sport_id = :sport_id" if sport_id is not None else ""
    rows = (
        await db.execute(
            text(
                f"""
                WITH ranked AS (
                  SELECT sc.skill_id,
                         sc.level,
                         COALESCE(a.edited_at, a.published_at) AS at,
                         ROW_NUMBER() OVER (
                           PARTITION BY sc.skill_id
                           ORDER BY COALESCE(a.edited_at, a.published_at) DESC NULLS LAST,
                                    sc.updated_at DESC
                         ) AS rn
                  FROM assessment_scores sc
                  JOIN assessments a ON a.id = sc.assessment_id
                  WHERE a.athlete_id = :aid
                    AND a.status IN ('published','edited')
                    {sport_filter}
                )
                SELECT r.skill_id,
                       r.level AS to_level,
                       COALESCE(p.level, 0) AS from_level,
                       r.at,
                       s.code, s.name_en, s.name_id
                FROM ranked r
                LEFT JOIN ranked p ON p.skill_id = r.skill_id AND p.rn = 2
                JOIN skills s ON s.id = r.skill_id
                WHERE r.rn = 1
                  AND r.at >= NOW() - make_interval(days => :win)
                  AND (p.level IS NULL OR r.level > p.level)
                ORDER BY r.at DESC
                LIMIT :lim
                """
            ),
            {
                "aid": athlete_id,
                "win": days,
                "lim": limit,
                **({"sport_id": sport_id} if sport_id is not None else {}),
            },
        )
    ).mappings().all()
    return [dict(r) for r in rows]


async def latest_note_for_skill(
    db: AsyncSession, *, athlete_id: UUID, skill_id: UUID
) -> tuple[str | None, str | None]:
    """Most recent free-text note the trainee's coach left on this skill.
    Notes don't have an EN/ID split today — coaches type in whichever
    language they speak — so we mirror the same text into both slots.
    Returns (note_en, note_id) tuple."""
    row = (
        await db.execute(
            text(
                """
                SELECT sc.note
                FROM assessment_scores sc
                JOIN assessments a ON a.id = sc.assessment_id
                WHERE a.athlete_id = :aid
                  AND sc.skill_id = :sid
                  AND sc.note IS NOT NULL AND sc.note <> ''
                  AND a.status IN ('published','edited')
                ORDER BY COALESCE(a.edited_at, a.published_at) DESC NULLS LAST,
                         sc.updated_at DESC
                LIMIT 1
                """
            ),
            {"aid": athlete_id, "sid": skill_id},
        )
    ).first()
    if row is None:
        return (None, None)
    note = row[0]
    return (note, note)


async def descriptors_for_skills(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    skill_levels: dict[UUID, int],
) -> dict[UUID, dict[str, str]]:
    """Resolve the (skill_id, level) -> {en, id} descriptor for each pair."""
    if not skill_levels:
        return {}
    out: dict[UUID, dict[str, str]] = {}
    # Group by level to keep the query count tiny (≤ 5 round trips).
    by_level: dict[int, list[UUID]] = {}
    for sid, lvl in skill_levels.items():
        by_level.setdefault(lvl, []).append(sid)
    for lvl, sids in by_level.items():
        placeholders = ", ".join(f":s{i}" for i in range(len(sids)))
        params: dict[str, Any] = {f"s{i}": sid for i, sid in enumerate(sids)}
        params.update({"wid": workspace_id, "lvl": lvl})
        rows = (
            await db.execute(
                text(
                    f"""
                    SELECT DISTINCT ON (skill_id)
                        skill_id, description_en, description_id
                    FROM skill_level_descriptors
                    WHERE level = :lvl
                      AND skill_id IN ({placeholders})
                      AND (workspace_id = :wid OR workspace_id IS NULL)
                    ORDER BY skill_id, workspace_id NULLS LAST
                    """
                ),
                params,
            )
        ).mappings().all()
        for r in rows:
            out[r["skill_id"]] = {
                "en": r["description_en"],
                "id": r["description_id"],
            }
    return out
