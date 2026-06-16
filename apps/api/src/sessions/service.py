"""Today's sessions for a coach, joined with trainee + tier metadata."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Shared CTE + SELECT + FROM used by both single-coach and all-coaches queries.
_TODAY_CTE = """
    WITH last_assessed AS (
        SELECT athlete_id,
               MAX(COALESCE(edited_at, published_at)) AS last_at
        FROM assessments
        WHERE status IN ('published','edited')
        GROUP BY athlete_id
    )
"""

_TODAY_SELECT = """
    SELECT
        s.id,
        s.scheduled_at,
        s.duration_min,
        s.court,
        s.focus,
        s.status,
        s.sport_id,
        s.coach_id,
        cu.display_name     AS coach_name,
        a.id               AS trainee_id,
        a.display_name     AS trainee_name,
        la.last_at         AS last_assessed_at,
        t.id               AS tier_id,
        t.code             AS tier_code,
        t.name_game_en     AS tier_name_game_en,
        t.name_game_id     AS tier_name_game_id
    FROM sessions s
    JOIN athletes a       ON a.id = s.athlete_id
    JOIN users cu         ON cu.id = s.coach_id
    LEFT JOIN last_assessed la ON la.athlete_id = a.id
    LEFT JOIN tiers t     ON t.id = a.current_tier_id
    WHERE s.scheduled_at::date = CURRENT_DATE
      AND s.status IN ('scheduled', 'completed')
"""

_TODAY_SQL = (
    _TODAY_CTE
    + _TODAY_SELECT
    + "  AND s.coach_id = :coach_id\n  ORDER BY s.scheduled_at ASC"
)

_TODAY_ALL_SQL = (
    _TODAY_CTE
    + _TODAY_SELECT
    + "  ORDER BY s.scheduled_at ASC"
)


async def get_today_for_coach(
    db: AsyncSession, *, coach_id: UUID
) -> list[Mapping[str, Any]]:
    result = await db.execute(text(_TODAY_SQL), {"coach_id": str(coach_id)})
    return list(result.mappings())


async def get_today_all_coaches(
    db: AsyncSession,
) -> list[Mapping[str, Any]]:
    """Return all today's sessions for the workspace (filtered by RLS)."""
    result = await db.execute(text(_TODAY_ALL_SQL))
    return list(result.mappings())
