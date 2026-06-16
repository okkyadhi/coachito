"""Demo data for local development.

Creates a single workspace + coach + 8 trainees + 5 sessions scheduled today
+ historical assessments that put each trainee at the right tier.  Sign in to
the FE with `demo@coachito.dev` via magic link to land in this workspace.

Idempotent: rerunning resets only the assessments/sessions/athletes for the
demo workspace so the FE always reflects "today" without stale data.
"""

from __future__ import annotations

import asyncio
import os
import random
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID, uuid4

import asyncpg

DEMO_EMAIL = "demo@coachito.dev"
DEMO_COACH_NAME = "Coach Novia"
DEMO_WORKSPACE_NAME = "Senayan Padel Club"

# ── Cast / roster ───────────────────────────────────────────────

# Each entry: (name, target_tier_code, has_session_today_at)
# `None` for session time means no session today (3 trainees without).
TRAINEES: list[tuple[str, str, time | None]] = [
    ("Andi Pratama",       "BRONZE",        time(8, 0)),
    ("Rina Sari",          "LOWER_BRONZE",  time(9, 30)),
    ("Budi Santoso",       "BEGINNER",      time(11, 0)),
    ("Sari Wulandari",     "BRONZE",        time(15, 0)),
    ("Joko Widodo",        "LOWER_BRONZE",  time(17, 30)),
    ("Dewi Lestari",       "BEGINNER",      None),
    ("Bambang Suryanto",   "BRONZE",        None),
    ("Sinta Anggraini",    "LOWER_BRONZE",  None),
]

# Skill levels needed to "comfortably exceed" each target tier.  We score
# every requirement of the target tier at exactly the minimum so the
# tier-calculation logic puts the trainee at that tier.  For BRONZE we score
# a couple of extras at level 3 to feel realistic.
TIER_LEVELS: dict[str, dict[str, int]] = {
    "BEGINNER": {
        # A single low score so the trainee shows up as "assessed once".
        "PADEL_TECH_FH": 1,
    },
    "LOWER_BRONZE": {
        "PADEL_TECH_FH": 2,
        "PADEL_TECH_BH": 2,
        "PADEL_TECH_SERVE": 1,
        "PADEL_TECH_RETURN": 1,
    },
    "BRONZE": {
        "PADEL_TECH_FH": 3,
        "PADEL_TECH_BH": 3,
        "PADEL_TECH_SERVE": 2,
        "PADEL_TECH_RETURN": 2,
        "PADEL_TECH_FH_VOLLEY": 2,
        "PADEL_TECH_BH_VOLLEY": 2,
        "PADEL_TECH_LOB": 2,
        "PADEL_TECH_SMASH": 2,
        "PADEL_TECH_WALL_BACK": 1,
        "PADEL_TACT_NET_POS": 2,
        "PADEL_TACT_DEF_POS": 2,
        "PADEL_PHYS_FOOTWORK": 2,
    },
}

# Trainees who don't have a session today still need at least one assessment
# so the FE has someone to render outside the "today" path; the special
# BEGINNER-with-no-assessments-yet case is handled by Budi (above) — he gets
# a single intro assessment when his session happens.
SESSION_FOCI = ["drilling", "match_play", "conditioning", "technique_focus", "general"]
COURTS = ["Court 1", "Court 2", "Court 3"]


# ── DB connection ───────────────────────────────────────────────

# Use the superuser DSN — seed bypasses RLS and FK checks.
_SUPERUSER_DSN = os.environ.get(
    "ALEMBIC_DATABASE_URL",
    "postgresql+asyncpg://coachito:coachito@postgres:5432/coachito",
).replace("postgresql+asyncpg://", "postgresql://")


async def _connect() -> asyncpg.Connection:  # type: ignore[type-arg]
    return await asyncpg.connect(_SUPERUSER_DSN)


# ── Helpers ─────────────────────────────────────────────────────


async def _ensure_user(conn: asyncpg.Connection) -> UUID:  # type: ignore[type-arg]
    """Find-or-create the demo coach."""
    row = await conn.fetchrow(
        "SELECT id FROM users WHERE email = $1", DEMO_EMAIL
    )
    if row:
        return row["id"]
    return await conn.fetchval(
        """
        INSERT INTO users (email, display_name, preferred_locale, last_seen_at)
        VALUES ($1, $2, 'id', NOW())
        RETURNING id
        """,
        DEMO_EMAIL,
        DEMO_COACH_NAME,
    )


async def _ensure_workspace(
    conn: asyncpg.Connection, coach_id: UUID  # type: ignore[type-arg]
) -> tuple[UUID, UUID]:
    """Find-or-create the demo workspace + active club_admin membership.

    Returns (workspace_id, sport_id).
    """
    sport_id = await conn.fetchval(
        "SELECT id FROM sports WHERE code = 'padel'"
    )
    if sport_id is None:
        raise RuntimeError("padel sport not seeded — run scripts/seed.py first.")

    row = await conn.fetchrow(
        "SELECT id FROM workspaces WHERE owner_user_id = $1 AND name = $2",
        coach_id,
        DEMO_WORKSPACE_NAME,
    )
    if row:
        return row["id"], sport_id

    workspace_id = await conn.fetchval(
        """
        INSERT INTO workspaces (
            sport_id, type, name, city, brand_color, primary_locale,
            plan, trial_ends_at, owner_user_id
        ) VALUES (
            $1, 'club', $2, 'Jakarta', '#C66B47', 'id',
            'free_trial', NOW() + INTERVAL '30 days', $3
        )
        RETURNING id
        """,
        sport_id,
        DEMO_WORKSPACE_NAME,
        coach_id,
    )
    await conn.execute(
        """
        INSERT INTO workspace_memberships (
            workspace_id, user_id, role, status, invited_at, joined_at, invited_by_id
        ) VALUES ($1, $2, 'club_admin', 'active', NOW(), NOW(), $3)
        """,
        workspace_id,
        coach_id,
        coach_id,
    )
    return workspace_id, sport_id


async def _reset_tenant_data(
    conn: asyncpg.Connection, workspace_id: UUID  # type: ignore[type-arg]
) -> None:
    """Wipe assessments / sessions / athletes so the demo is deterministic."""
    await conn.execute(
        "DELETE FROM assessments WHERE workspace_id = $1", workspace_id
    )
    await conn.execute(
        "DELETE FROM sessions WHERE workspace_id = $1", workspace_id
    )
    await conn.execute(
        "DELETE FROM athletes WHERE workspace_id = $1", workspace_id
    )


async def _compute_tier_id(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    *,
    athlete_id: UUID,
    sport_id: UUID,
) -> UUID | None:
    """Pure-Python tier calculation: highest tier whose every requirement is
    met by the athlete's latest score per skill.  Returns None for athletes
    with no assessments and no matching tier (very rare — BEGINNER has zero
    requirements so it always matches)."""
    scores_rows = await conn.fetch(
        """
        SELECT DISTINCT ON (skill_id) skill_id, level
        FROM assessments
        WHERE athlete_id = $1
        ORDER BY skill_id, recorded_at DESC
        """,
        athlete_id,
    )
    scores: dict[UUID, int] = {r["skill_id"]: r["level"] for r in scores_rows}

    tiers = await conn.fetch(
        """
        SELECT id, code FROM tiers
        WHERE sport_id = $1 AND workspace_id IS NULL
        ORDER BY display_order DESC
        """,
        sport_id,
    )

    for tier in tiers:
        reqs = await conn.fetch(
            "SELECT skill_id, min_level FROM tier_requirements WHERE tier_id = $1",
            tier["id"],
        )
        if all(scores.get(r["skill_id"], 0) >= r["min_level"] for r in reqs):
            return tier["id"]
    return None


async def _seed_trainees(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    *,
    workspace_id: UUID,
    coach_id: UUID,
    sport_id: UUID,
) -> None:
    today = datetime.now(UTC).date()
    rng = random.Random(42)  # deterministic seed for reproducible demos

    # Lookup map: skill code → id
    skill_rows = await conn.fetch(
        "SELECT id, code FROM skills WHERE sport_id = $1 AND workspace_id IS NULL",
        sport_id,
    )
    skill_by_code: dict[str, UUID] = {r["code"]: r["id"] for r in skill_rows}

    for trainee_name, tier_code, session_time in TRAINEES:
        athlete_id = await conn.fetchval(
            """
            INSERT INTO athletes (
                workspace_id, display_name, joined_at, created_by_id
            ) VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            workspace_id,
            trainee_name,
            today - timedelta(days=rng.randint(7, 120)),
            coach_id,
        )

        # Stagger assessment timestamps so "last_assessed_at" varies.  Days
        # ago is sampled uniformly; lighter-weight trainees get fewer skills.
        levels = TIER_LEVELS[tier_code]
        days_offset = rng.randint(1, 30)
        for skill_code, level in levels.items():
            await conn.execute(
                """
                INSERT INTO assessments (
                    workspace_id, athlete_id, coach_id, skill_id, level,
                    recorded_at
                ) VALUES ($1, $2, $3, $4, $5, NOW() - make_interval(days => $6))
                """,
                workspace_id,
                athlete_id,
                coach_id,
                skill_by_code[skill_code],
                level,
                days_offset,
            )

        # Cache the computed tier
        tier_id = await _compute_tier_id(
            conn, athlete_id=athlete_id, sport_id=sport_id
        )
        if tier_id is not None:
            await conn.execute(
                "UPDATE athletes SET current_tier_id = $1 WHERE id = $2",
                tier_id,
                athlete_id,
            )

        # Today's session, if any
        if session_time is not None:
            session_dt = datetime.combine(today, session_time, tzinfo=UTC)
            await conn.execute(
                """
                INSERT INTO sessions (
                    workspace_id, sport_id, athlete_id, coach_id, scheduled_at,
                    duration_min, court, focus, status
                ) VALUES ($1, (SELECT sport_id FROM workspaces WHERE id = $1),
                          $2, $3, $4, $5, $6, $7::session_focus, 'scheduled')
                """,
                workspace_id,
                athlete_id,
                coach_id,
                session_dt,
                rng.choice([45, 60, 90]),
                rng.choice(COURTS),
                rng.choice(SESSION_FOCI),
            )


async def main() -> None:
    conn = await _connect()
    try:
        coach_id = await _ensure_user(conn)
        workspace_id, sport_id = await _ensure_workspace(conn, coach_id)

        await _reset_tenant_data(conn, workspace_id)
        await _seed_trainees(
            conn,
            workspace_id=workspace_id,
            coach_id=coach_id,
            sport_id=sport_id,
        )

        athletes_n: int = await conn.fetchval(
            "SELECT count(*) FROM athletes WHERE workspace_id = $1", workspace_id
        )
        sessions_n: int = await conn.fetchval(
            "SELECT count(*) FROM sessions WHERE workspace_id = $1 "
            "AND scheduled_at::date = CURRENT_DATE",
            workspace_id,
        )
        assessments_n: int = await conn.fetchval(
            "SELECT count(*) FROM assessments WHERE workspace_id = $1",
            workspace_id,
        )
        print(f"Demo seeded into workspace {workspace_id}")
        print(f"  athletes:           {athletes_n}")
        print(f"  sessions today:     {sessions_n}")
        print(f"  assessments:        {assessments_n}")
        print(f"  sign in as:         {DEMO_EMAIL}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())


# Silence unused-import warning for `uuid4` (kept for future inline UUID needs)
_ = uuid4
_: Any = None
