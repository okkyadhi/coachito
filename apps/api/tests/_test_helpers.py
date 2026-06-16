"""Shared test helpers for endpoints that need a fully-set-up tenant.

Workspaces tests already exercise the create/membership path via the real
API; here we just need a way to: sign in as a user, create a workspace, and
optionally inject athletes/sessions/assessments directly via asyncpg.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from typing import Any

import asyncpg
from httpx import AsyncClient

# Superuser DSN — bypasses RLS for setup/teardown
SUPERUSER_DSN = "postgresql://coachito:coachito@postgres:5432/coachito"


async def superuser_conn() -> asyncpg.Connection:  # type: ignore[type-arg]
    return await asyncpg.connect(SUPERUSER_DSN)


async def sign_in(
    client: AsyncClient, email: str, captured: list[dict[str, str]]
) -> dict[str, Any]:
    """Run magic-link request + consume, return the full token payload."""
    await client.post("/auth/magic/request", json={"email": email})
    link = captured[-1]["link"]
    token = link.split("token=", 1)[1]
    r = await client.get("/auth/magic/consume", params={"token": token})
    assert r.status_code == 200, r.text
    return r.json()


async def create_workspace(
    client: AsyncClient,
    access_token: str,
    *,
    name: str,
    type_: str = "club",
) -> dict[str, Any]:
    r = await client.post(
        "/workspaces",
        json={"type": type_, "name": name, "primary_locale": "id"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def insert_athlete(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    *,
    workspace_id: str,
    coach_id: str,
    display_name: str,
) -> str:
    """Returns the new athlete id as a string."""
    aid = await conn.fetchval(
        """
        INSERT INTO athletes (workspace_id, display_name, joined_at, created_by_id)
        VALUES ($1, $2, CURRENT_DATE, $3)
        RETURNING id::text
        """,
        workspace_id,
        display_name,
        coach_id,
    )
    return aid


async def insert_assessment(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    *,
    workspace_id: str,
    athlete_id: str,
    coach_id: str,
    skill_code: str = "PADEL_TECH_FH",
    level: int = 2,
    days_ago: int = 1,
) -> None:
    skill_id = await conn.fetchval(
        "SELECT id FROM skills WHERE code = $1 AND workspace_id IS NULL",
        skill_code,
    )
    # Test helper: create a synthetic completed session + published
    # assessment + score so tests that need "historical assessments" can keep
    # using insert_assessment(...) without knowing about the v2 shape.
    session_id = await conn.fetchval(
        """
        INSERT INTO sessions (
            workspace_id, sport_id, athlete_id, coach_id, scheduled_at,
            duration_min, focus, status, completed_at
        ) VALUES ($1, (SELECT sport_id FROM workspaces WHERE id = $1),
                  $2, $3, NOW() - make_interval(days => $4),
                  60, 'general', 'completed',
                  NOW() - make_interval(days => $4))
        RETURNING id
        """,
        workspace_id, athlete_id, coach_id, days_ago,
    )
    assessment_id = await conn.fetchval(
        """
        INSERT INTO assessments (
            workspace_id, sport_id, session_id, athlete_id, coach_id,
            status, published_at, saved_at
        ) VALUES ($1, (SELECT sport_id FROM workspaces WHERE id = $1),
                  $2, $3, $4, 'published',
                  NOW() - make_interval(days => $5),
                  NOW() - make_interval(days => $5))
        RETURNING id
        """,
        workspace_id, session_id, athlete_id, coach_id, days_ago,
    )
    await conn.execute(
        """
        INSERT INTO assessment_scores (assessment_id, skill_id, level)
        VALUES ($1, $2, $3)
        """,
        assessment_id, skill_id, level,
    )


async def insert_session_today(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    *,
    workspace_id: str,
    athlete_id: str,
    coach_id: str,
    hour: int = 9,
    minute: int = 0,
    court: str = "Court 1",
    focus: str = "drilling",
) -> str:
    today = datetime.now(UTC).date()
    scheduled = datetime.combine(today, time(hour, minute), tzinfo=UTC)
    sid = await conn.fetchval(
        """
        INSERT INTO sessions (workspace_id, sport_id, athlete_id, coach_id,
                              scheduled_at, duration_min, court, focus, status)
        VALUES ($1, (SELECT sport_id FROM workspaces WHERE id = $1),
                $2, $3, $4, 60, $5, $6::session_focus, 'scheduled')
        RETURNING id::text
        """,
        workspace_id,
        athlete_id,
        coach_id,
        scheduled,
        court,
        focus,
    )
    return sid


__all__ = [
    "SUPERUSER_DSN",
    "create_workspace",
    "insert_assessment",
    "insert_athlete",
    "insert_session_today",
    "sign_in",
    "superuser_conn",
]
