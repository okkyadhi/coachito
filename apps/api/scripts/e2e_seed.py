"""End-to-end test data seed.

Wipes all tenant data + users, then creates a deterministic cast for
manual E2E testing:

  Users (all password: ``password123``)
    admin@coachito.dev     — club_admin in Club
    head@coachito.dev     — head_coach in Club
    coach1@coachito.dev    — coach in Club
    coach2@coachito.dev    — coach in Club
    hybrid@coachito.dev   — coach in Club + owner of Personal workspace
    solo@coachito.dev     — owner of Personal workspace only

  Workspaces
    Senayan Padel Club      (club, owner=admin@coachito.dev)
    Coach Hybrid Personal   (personal, owner=hybrid@coachito.dev)
    Coach Solo Personal     (personal, owner=solo@coachito.dev)

  Trainees in the club workspace (5):
    Andi Pratama       — un-assessed (no tier)
    Rina Sari          — BEGINNER
    Budi Santoso       — LOWER_BRONZE
    Sari Wulandari     — BRONZE
    Joko Widodo        — BRONZE
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID

import asyncpg

# argon2 hasher lives in the API package — import lazily after we set
# sys.path so the script works whether invoked as `python -m scripts.e2e_seed`
# or via `python scripts/e2e_seed.py`.
from src.auth.password import hash_password

PASSWORD = "password123"

# ── Cast ────────────────────────────────────────────────────────

CLUB_NAME = "Senayan Padel Club"
HYBRID_PERSONAL_NAME = "Coach Hybrid Personal"
SOLO_PERSONAL_NAME = "Coach Solo Personal"


USERS: list[dict[str, str]] = [
    {"email": "admin@coachito.dev",   "name": "Pak Adi (Club Admin)"},
    {"email": "head@coachito.dev",    "name": "Coach Hendra (Head)"},
    {"email": "coach1@coachito.dev",  "name": "Coach Satu"},
    {"email": "coach2@coachito.dev",  "name": "Coach Dua"},
    {"email": "hybrid@coachito.dev",  "name": "Coach Hybrid"},
    {"email": "solo@coachito.dev",    "name": "Coach Solo"},
    # Trainee user accounts (linked to athletes below) so feedback +
    # /home + /my-sessions flows are testable without invite-claim each reseed.
    {"email": "andi@coachito.dev",    "name": "Andi Pratama"},
    {"email": "rina@coachito.dev",    "name": "Rina Sari"},
    {"email": "budi@coachito.dev",    "name": "Budi Santoso"},
    {"email": "sari@coachito.dev",    "name": "Sari Wulandari"},
    {"email": "joko@coachito.dev",    "name": "Joko Widodo"},
]

# (display_name, target_tier_code or None for un-assessed, assigned_coach_email,
#  has_session_today_at, trainee_user_email)
TRAINEES: list[tuple[str, str | None, str, time | None, str]] = [
    ("Andi Pratama",   None,            "head@coachito.dev",   time(8, 0),  "andi@coachito.dev"),
    ("Rina Sari",      "BEGINNER",      "coach1@coachito.dev", time(9, 30), "rina@coachito.dev"),
    ("Budi Santoso",   "LOWER_BRONZE",  "coach2@coachito.dev", time(11, 0), "budi@coachito.dev"),
    ("Sari Wulandari", "BRONZE",        "hybrid@coachito.dev", time(15, 0), "sari@coachito.dev"),
    ("Joko Widodo",    "BRONZE",        "head@coachito.dev",   None,        "joko@coachito.dev"),
]

# Same scoring strategy as dev_seed_demo: hit each requirement at min level.
TIER_LEVELS: dict[str, dict[str, int]] = {
    "BEGINNER": {
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

COURTS = ["Court 1", "Court 2", "Court 3"]
FOCI = ["drilling", "match_play", "technique_focus", "general", "conditioning"]


# ── DB ──────────────────────────────────────────────────────────

_SUPERUSER_DSN = os.environ.get(
    "ALEMBIC_DATABASE_URL",
    "postgresql+asyncpg://coachito:coachito@postgres:5432/coachito",
).replace("postgresql+asyncpg://", "postgresql://")


async def _connect() -> asyncpg.Connection:  # type: ignore[type-arg]
    return await asyncpg.connect(_SUPERUSER_DSN)


# ── Wipe ────────────────────────────────────────────────────────

# Order matters — children before parents.
_WIPE_TABLES = [
    "audit_log",
    "reports",
    "feedbacks",
    "assessment_edits",
    "assessment_scores",
    "assessments",
    "sessions",
    "tier_requirements_overrides" if False else None,  # placeholder, no such table
    "invites",
    "subscriptions",
    "athletes",
    "workspace_memberships",
    "user_guardians",
    "workspaces",
    "users",
]


async def _wipe(conn: asyncpg.Connection) -> None:  # type: ignore[type-arg]
    """Delete all tenant data + all users.  Sports/skills/tiers/curricula
    (the platform catalogue) are preserved."""
    for table in _WIPE_TABLES:
        if table is None:
            continue
        await conn.execute(f"DELETE FROM {table}")


# ── Inserts ─────────────────────────────────────────────────────


async def _insert_users(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
) -> dict[str, UUID]:
    pw = hash_password(PASSWORD)
    out: dict[str, UUID] = {}
    for u in USERS:
        uid = await conn.fetchval(
            """
            INSERT INTO users (email, display_name, preferred_locale,
                               password_hash, last_seen_at)
            VALUES ($1, $2, 'id', $3, NOW())
            RETURNING id
            """,
            u["email"], u["name"], pw,
        )
        out[u["email"]] = uid
    return out


async def _insert_workspace(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    *,
    sport_id: UUID,
    type_: str,
    name: str,
    owner_id: UUID,
    city: str | None = "Jakarta",
) -> UUID:
    return await conn.fetchval(
        """
        INSERT INTO workspaces (
            sport_id, type, name, city, brand_color, primary_locale,
            plan, trial_ends_at, owner_user_id
        ) VALUES (
            $1, $2, $3, $4, '#C66B47', 'id',
            'free_trial', NOW() + INTERVAL '30 days', $5
        )
        RETURNING id
        """,
        sport_id, type_, name, city, owner_id,
    )


async def _add_member(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    *,
    workspace_id: UUID,
    user_id: UUID,
    role: str,
    invited_by: UUID,
    bio: str | None = None,
) -> None:
    """Insert (or update) a workspace_memberships row.  If ``bio`` is provided
    (as a JSON string), it's stored on the membership's bio JSONB column."""
    if bio is None:
        await conn.execute(
            """
            INSERT INTO workspace_memberships (
                workspace_id, user_id, role, status,
                invited_at, joined_at, invited_by_id
            ) VALUES ($1, $2, $3, 'active', NOW(), NOW(), $4)
            """,
            workspace_id, user_id, role, invited_by,
        )
    else:
        await conn.execute(
            """
            INSERT INTO workspace_memberships (
                workspace_id, user_id, role, status,
                invited_at, joined_at, invited_by_id, bio
            ) VALUES ($1, $2, $3, 'active', NOW(), NOW(), $4, $5::jsonb)
            """,
            workspace_id, user_id, role, invited_by, bio,
        )


# Demo bios for the seeded coaches.  Three flavours: full / minimal / empty
# to exercise the FE renderer's empty-section handling.
_COACH_BIOS: dict[str, str] = {
    "head@coachito.dev": """
        {
          "headline": "APPA L2 head coach. 12 years on tour.",
          "about": "Hendra has coached at three clubs across Jakarta and Bali. He focuses on positional play and net dominance, and runs the academy's junior pathway.",
          "years_coaching": 12,
          "certifications": [
            {"issuer": "APPA", "name": "Level 2", "year": 2020},
            {"issuer": "FIP",  "name": "Coaching Certificate", "year": 2018}
          ],
          "languages": ["id", "en", "es"],
          "specialties": ["TACT_NET_POS", "TECH_BANDEJA", "TECH_VIBORA"]
        }
    """,
    "coach1@coachito.dev": """
        {
          "headline": "Junior coach. Strong on fundamentals.",
          "years_coaching": 3,
          "languages": ["id", "en"],
          "specialties": ["TECH_FH", "TECH_BH"]
        }
    """,
    # coach2 gets default empty bio to exercise the empty-section path.
}


async def _compute_tier_id(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    *, athlete_id: UUID, sport_id: UUID,
) -> UUID | None:
    scores = await conn.fetch(
        """
        SELECT DISTINCT ON (sc.skill_id) sc.skill_id, sc.level
        FROM assessment_scores sc
        JOIN assessments a ON a.id = sc.assessment_id
        WHERE a.athlete_id = $1
          AND a.status IN ('published','edited')
        ORDER BY sc.skill_id,
                 COALESCE(a.edited_at, a.published_at) DESC NULLS LAST
        """,
        athlete_id,
    )
    score_map: dict[UUID, int] = {r["skill_id"]: r["level"] for r in scores}
    tiers = await conn.fetch(
        """
        SELECT id FROM tiers
        WHERE sport_id = $1 AND workspace_id IS NULL
        ORDER BY display_order DESC
        """,
        sport_id,
    )
    for t in tiers:
        reqs = await conn.fetch(
            "SELECT skill_id, min_level FROM tier_requirements WHERE tier_id = $1",
            t["id"],
        )
        if all(score_map.get(r["skill_id"], 0) >= r["min_level"] for r in reqs):
            return t["id"]
    return None


async def _insert_trainees(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    *,
    workspace_id: UUID,
    sport_id: UUID,
    user_ids: dict[str, UUID],
) -> None:
    today = datetime.now(UTC).date()

    skill_rows = await conn.fetch(
        "SELECT id, code FROM skills WHERE sport_id = $1 AND workspace_id IS NULL",
        sport_id,
    )
    skill_by_code: dict[str, UUID] = {r["code"]: r["id"] for r in skill_rows}

    for i, (name, tier_code, coach_email, sess_time, trainee_email) in enumerate(
        TRAINEES
    ):
        coach_id = user_ids[coach_email]
        # Each trainee has a real user account so they can sign in directly.
        linked_user_id = user_ids[trainee_email]
        athlete_id = await conn.fetchval(
            """
            INSERT INTO athletes (
                workspace_id, user_id, display_name, joined_at, created_by_id
            ) VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            workspace_id, linked_user_id, name,
            today - timedelta(days=14 + i * 7), coach_id,
        )
        if linked_user_id is not None:
            await conn.execute(
                """
                INSERT INTO workspace_memberships (
                    workspace_id, user_id, role, status,
                    invited_at, joined_at, invited_by_id
                ) VALUES ($1, $2, 'trainee', 'active', NOW(), NOW(), $3)
                """,
                workspace_id, linked_user_id, coach_id,
            )

        if tier_code is not None:
            # Create a completed "historical" session + published assessment
            # so the trainee has a tier-driving record on the new shape.
            hist_dt = datetime.now(UTC) - timedelta(days=5 + i)
            session_id = await conn.fetchval(
                """
                INSERT INTO sessions (
                    workspace_id, sport_id, athlete_id, coach_id, scheduled_at,
                    duration_min, court, focus, status, completed_at,
                    summary
                ) VALUES ($1, (SELECT sport_id FROM workspaces WHERE id = $1),
                          $2, $3, $4, 60, $5, 'general'::session_focus,
                          'completed', $4, 'Seeded historical session.')
                RETURNING id
                """,
                workspace_id, athlete_id, coach_id, hist_dt,
                COURTS[i % len(COURTS)],
            )
            assessment_id = await conn.fetchval(
                """
                INSERT INTO assessments (
                    workspace_id, sport_id, session_id, athlete_id, coach_id,
                    status, summary, saved_at, published_at
                ) VALUES ($1, (SELECT sport_id FROM workspaces WHERE id = $1),
                          $2, $3, $4, 'published',
                          'Seeded for tier calculation.', $5, $5)
                RETURNING id
                """,
                workspace_id, session_id, athlete_id, coach_id, hist_dt,
            )
            for skill_code, level in TIER_LEVELS[tier_code].items():
                await conn.execute(
                    """
                    INSERT INTO assessment_scores (
                        assessment_id, skill_id, level
                    ) VALUES ($1, $2, $3)
                    """,
                    assessment_id, skill_by_code[skill_code], level,
                )
            tier_id = await _compute_tier_id(
                conn, athlete_id=athlete_id, sport_id=sport_id,
            )
            if tier_id is not None:
                await conn.execute(
                    "UPDATE athletes SET current_tier_id = $1 WHERE id = $2",
                    tier_id, athlete_id,
                )

        if sess_time is not None:
            sess_dt = datetime.combine(today, sess_time, tzinfo=UTC)
            await conn.execute(
                """
                INSERT INTO sessions (
                    workspace_id, sport_id, athlete_id, coach_id, scheduled_at,
                    duration_min, court, focus, status
                ) VALUES ($1, (SELECT sport_id FROM workspaces WHERE id = $1),
                          $2, $3, $4, $5, $6, $7::session_focus, 'scheduled')
                """,
                workspace_id, athlete_id, coach_id, sess_dt,
                [45, 60, 90][i % 3],
                COURTS[i % len(COURTS)],
                FOCI[i % len(FOCI)],
            )


# ── Main ────────────────────────────────────────────────────────


async def main() -> None:
    conn = await _connect()
    try:
        async with conn.transaction():
            await _wipe(conn)

            sport_id = await conn.fetchval(
                "SELECT id FROM sports WHERE code = 'padel'"
            )
            if sport_id is None:
                raise RuntimeError("padel sport missing — run scripts/seed.py first.")

            user_ids = await _insert_users(conn)

            club_id = await _insert_workspace(
                conn,
                sport_id=sport_id,
                type_="club",
                name=CLUB_NAME,
                owner_id=user_ids["admin@coachito.dev"],
            )
            hybrid_personal_id = await _insert_workspace(
                conn,
                sport_id=sport_id,
                type_="personal",
                name=HYBRID_PERSONAL_NAME,
                owner_id=user_ids["hybrid@coachito.dev"],
            )
            solo_personal_id = await _insert_workspace(
                conn,
                sport_id=sport_id,
                type_="personal",
                name=SOLO_PERSONAL_NAME,
                owner_id=user_ids["solo@coachito.dev"],
            )

            # Club memberships
            admin_id = user_ids["admin@coachito.dev"]
            await _add_member(conn, workspace_id=club_id,
                              user_id=admin_id, role="club_admin",
                              invited_by=admin_id)
            await _add_member(conn, workspace_id=club_id,
                              user_id=user_ids["head@coachito.dev"],
                              role="head_coach", invited_by=admin_id,
                              bio=_COACH_BIOS.get("head@coachito.dev"))
            await _add_member(conn, workspace_id=club_id,
                              user_id=user_ids["coach1@coachito.dev"],
                              role="coach", invited_by=admin_id,
                              bio=_COACH_BIOS.get("coach1@coachito.dev"))
            await _add_member(conn, workspace_id=club_id,
                              user_id=user_ids["coach2@coachito.dev"],
                              role="coach", invited_by=admin_id)
            await _add_member(conn, workspace_id=club_id,
                              user_id=user_ids["hybrid@coachito.dev"],
                              role="coach", invited_by=admin_id)

            # Personal-workspace owners get a coach membership in their own ws.
            await _add_member(conn, workspace_id=hybrid_personal_id,
                              user_id=user_ids["hybrid@coachito.dev"],
                              role="coach",
                              invited_by=user_ids["hybrid@coachito.dev"])
            await _add_member(conn, workspace_id=solo_personal_id,
                              user_id=user_ids["solo@coachito.dev"],
                              role="coach",
                              invited_by=user_ids["solo@coachito.dev"])

            await _insert_trainees(
                conn,
                workspace_id=club_id,
                sport_id=sport_id,
                user_ids=user_ids,
            )

        print("✓ E2E seed complete\n")
        print(f"  Password (all users): {PASSWORD}\n")
        print("  Sign in as:")
        for u in USERS:
            print(f"    - {u['email']:24s} ({u['name']})")
        print(f"\n  Club workspace:       {CLUB_NAME}")
        print(f"  Hybrid personal:      {HYBRID_PERSONAL_NAME}")
        print(f"  Solo personal:        {SOLO_PERSONAL_NAME}")
        print(f"\n  Trainees (in {CLUB_NAME}):")
        for name, tier, coach, sess, email in TRAINEES:
            tier_lbl = tier or "(un-assessed)"
            sess_lbl = sess.strftime("%H:%M") if sess else "—"
            print(
                f"    - {name:18s} login={email:24s} "
                f"tier={tier_lbl:14s} today@{sess_lbl}"
            )
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())


_: Any = None
