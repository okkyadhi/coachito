"""Idempotent seed: sports + per-sport curriculum, skills, descriptors,
tiers, and tier requirements.

Padel: default APPA-aligned curriculum, 27 skills, 135 descriptors.
Tennis: default ITF-aligned curriculum, 29 skills, 145 descriptors. Seeded
        as platform content but the sport stays ``is_active = FALSE`` until
        the multi-sport activation deploy (tennis-skill-framework-v0.1 §10.2).
        Seeding the content early is harmless and idempotent — skills are
        already sport-scoped, so the rows sit dormant until the sport flips on.

Run base seed:    python -m scripts.seed
With Okky admin:  python -m scripts.seed --with-admin

``--with-admin`` additionally flips tennis active platform-wide and creates
the PoC demo workspace "Coachito Demo Club" with Okky Adhi
(okkyadhi7@gmail.com) as the club admin, password "password123",
multi-sport (padel + tennis), club_pro plan, 30-day trial.

Re-run safely: uses conflict targets on partial unique indexes
(uq_*_platform_* from migration 0008) so NULL workspace_id rows
never cause duplicates.
"""

import argparse
import asyncio
import json
import os
from pathlib import Path

import asyncpg
from argon2 import PasswordHasher

# Prefer the superuser DSN (used by alembic) so seeding workspace/users/
# membership tables bypasses RLS. Falls back to DATABASE_URL for ad-hoc
# local runs where only the runtime role is configured.
DATABASE_URL = (
    os.environ.get("ALEMBIC_DATABASE_URL")
    or os.environ.get("DATABASE_URL")
    or "postgresql+asyncpg://coachito:coachito@localhost:5433/coachito"
)

# asyncpg uses its own DSN format (no +asyncpg prefix)
PG_DSN = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

DATA = Path(__file__).parent.parent / "data"


def _load(filename: str) -> list[dict]:  # type: ignore[type-arg]
    with open(DATA / filename) as f:
        return json.load(f)  # type: ignore[no-any-return]


# ── Per-sport curriculum bundles ────────────────────────────────────
# Each entry describes one platform-default curriculum and the JSON data
# files that populate it.  Tiers + tier_requirements may be shared (padel)
# or sport-specific (tennis uses its own labels per §6).

CURRICULA = [
    {
        "sport_code": "padel",
        "curriculum_code": "padel-default-appa",
        "name_en": "Padel Default (APPA-aligned)",
        "name_id": "Padel Default (sesuai APPA)",
        "description_en": (
            "Platform default curriculum for padel, aligned with "
            "Asia-Pacific Padel Association standards."
        ),
        "description_id": (
            "Kurikulum default platform untuk padel, sesuai dengan "
            "standar Asia-Pacific Padel Association."
        ),
        "skills_file": "skills_padel.json",
        "descriptors_file": "descriptors_padel.json",
        "tiers_file": "tiers.json",
        "requirements_file": "tier_requirements.json",
    },
    {
        "sport_code": "tennis",
        "curriculum_code": "tennis-default-itf",
        "name_en": "Tennis (ITF default)",
        "name_id": "Tenis (ITF default)",
        "description_en": (
            "Default tennis curriculum aligned with the ITF coaching "
            "framework."
        ),
        "description_id": (
            "Kurikulum tenis default berdasarkan kerangka pelatih ITF."
        ),
        "skills_file": "skills_tennis.json",
        "descriptors_file": "descriptors_tennis.json",
        "tiers_file": "tiers_tennis.json",
        "requirements_file": "tier_requirements_tennis.json",
    },
]


async def seed(with_admin: bool = False) -> None:
    conn = await asyncpg.connect(PG_DSN)
    try:
        await _seed(conn)
        if with_admin:
            await _seed_admin(conn)
    finally:
        await conn.close()


async def _seed(conn: asyncpg.Connection) -> None:  # type: ignore[type-arg]
    # ── Sports ──────────────────────────────────────────────────────
    # Padel ships active; tennis is seeded but gated off until the
    # multi-sport activation deploy flips is_active (§10.2).
    await conn.execute("""
        INSERT INTO sports (code, name_en, name_id, is_active, display_order)
        VALUES
            ('padel',  'Padel',  'Padel',  TRUE,  1),
            ('tennis', 'Tennis', 'Tenis',  FALSE, 2)
        ON CONFLICT (code) DO NOTHING
    """)
    print("  sports: seeded")

    for bundle in CURRICULA:
        await _seed_curriculum(conn, bundle)

    print("Seed complete.")


# ── Admin bootstrap (PoC) ───────────────────────────────────────────


ADMIN_EMAIL = "okkyadhi7@gmail.com"
ADMIN_DISPLAY_NAME = "Okky Adhi"
ADMIN_PASSWORD = "password123"
ADMIN_WORKSPACE_NAME = "Coachito Demo Club"
ADMIN_TRIAL_DAYS = 30


async def _seed_admin(conn: asyncpg.Connection) -> None:  # type: ignore[type-arg]
    """Bootstrap the PoC demo club admin.

    Idempotent: if the workspace named ``Coachito Demo Club`` already exists,
    the function only touches its trial date (so re-running ``--with-admin``
    bumps the expiry).  Skips password rehash to keep argon2 cost in check
    on repeated runs.
    """
    print("── admin (--with-admin) ──")

    # Tennis is gated off platform-wide by default (see §10.2).  Flip it on
    # so the demo Club workspace can offer both sports.
    await conn.execute(
        "UPDATE sports SET is_active = TRUE WHERE code = 'tennis'"
    )
    print("  tennis: activated")

    padel_id = await conn.fetchval(
        "SELECT id FROM sports WHERE code = 'padel'"
    )
    tennis_id = await conn.fetchval(
        "SELECT id FROM sports WHERE code = 'tennis'"
    )
    padel_curr = await conn.fetchval(
        "SELECT id FROM curricula WHERE sport_id = $1 AND workspace_id IS NULL",
        padel_id,
    )
    tennis_curr = await conn.fetchval(
        "SELECT id FROM curricula WHERE sport_id = $1 AND workspace_id IS NULL",
        tennis_id,
    )

    # ── User: insert if missing, otherwise leave the existing row (and its
    # password hash) untouched so re-running doesn't churn auth state.
    existing_user = await conn.fetchval(
        "SELECT id FROM users WHERE email = $1", ADMIN_EMAIL
    )
    if existing_user is None:
        password_hash = PasswordHasher().hash(ADMIN_PASSWORD)
        user_id = await conn.fetchval(
            """
            INSERT INTO users (email, display_name, password_hash, preferred_locale)
            VALUES ($1, $2, $3, 'id')
            RETURNING id
            """,
            ADMIN_EMAIL, ADMIN_DISPLAY_NAME, password_hash,
        )
        print(f"  user: created {ADMIN_EMAIL}")
    else:
        user_id = existing_user
        print(f"  user: exists (left untouched) {ADMIN_EMAIL}")

    # ── Workspace: insert if missing; if present, just bump trial.
    existing_ws = await conn.fetchval(
        "SELECT id FROM workspaces WHERE name = $1 AND owner_user_id = $2",
        ADMIN_WORKSPACE_NAME, user_id,
    )
    if existing_ws is None:
        workspace_id = await conn.fetchval(
            """
            INSERT INTO workspaces (
                sport_id, type, name, primary_locale, plan,
                trial_ends_at, owner_user_id, curriculum_id
            )
            VALUES ($1, 'club', $2, 'id', 'club_pro',
                    NOW() + ($3 || ' days')::interval, $4, $5)
            RETURNING id
            """,
            padel_id, ADMIN_WORKSPACE_NAME, str(ADMIN_TRIAL_DAYS),
            user_id, padel_curr,
        )
        print(f"  workspace: created '{ADMIN_WORKSPACE_NAME}'")
    else:
        workspace_id = existing_ws
        await conn.execute(
            "UPDATE workspaces "
            "SET trial_ends_at = NOW() + ($1 || ' days')::interval "
            "WHERE id = $2",
            str(ADMIN_TRIAL_DAYS), workspace_id,
        )
        print(f"  workspace: exists, trial bumped to +{ADMIN_TRIAL_DAYS}d")

    # ── Membership (owner / club_admin / active)
    membership_id = await conn.fetchval(
        """
        INSERT INTO workspace_memberships (
            workspace_id, user_id, role, status, invited_at, joined_at, invited_by_id
        )
        VALUES ($1, $2, 'club_admin', 'active', NOW(), NOW(), $2)
        ON CONFLICT (workspace_id, user_id, role) DO UPDATE
            SET status = 'active', joined_at = COALESCE(workspace_memberships.joined_at, NOW())
        RETURNING id
        """,
        workspace_id, user_id,
    )
    print("  membership: club_admin / active")

    # ── Multi-sport: enable padel + tennis for this workspace, qualify
    # Okky in both.
    for sid, curr in ((padel_id, padel_curr), (tennis_id, tennis_curr)):
        await conn.execute(
            """
            INSERT INTO workspace_sports (workspace_id, sport_id, curriculum_id, is_active)
            VALUES ($1, $2, $3, TRUE)
            ON CONFLICT (workspace_id, sport_id) DO UPDATE
                SET is_active = TRUE, archived_at = NULL,
                    curriculum_id = COALESCE(EXCLUDED.curriculum_id, workspace_sports.curriculum_id)
            """,
            workspace_id, sid, curr,
        )
        await conn.execute(
            """
            INSERT INTO membership_sports (workspace_id, membership_id, sport_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (membership_id, sport_id) DO NOTHING
            """,
            workspace_id, membership_id, sid,
        )
    print("  workspace_sports + membership_sports: padel + tennis")

    print(
        f"Admin seed complete.  Login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}"
    )


async def _seed_curriculum(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    bundle: dict,  # type: ignore[type-arg]
) -> None:
    sport_code = bundle["sport_code"]
    sport_id: str | None = await conn.fetchval(
        "SELECT id::text FROM sports WHERE code = $1", sport_code
    )
    if sport_id is None:
        print(f"  WARN: sport not found, skipping: {sport_code}")
        return

    print(f"── {sport_code} ──")

    # ── Default curriculum ───────────────────────────────────────────
    # Conflict target: partial unique index uq_curricula_platform_code
    await conn.execute("""
        INSERT INTO curricula (sport_id, workspace_id, code, name_en, name_id,
                               description_en, description_id)
        VALUES ($1, NULL, $2, $3, $4, $5, $6)
        ON CONFLICT (sport_id, code) WHERE workspace_id IS NULL DO NOTHING
    """, sport_id, bundle["curriculum_code"], bundle["name_en"],
        bundle["name_id"], bundle["description_en"], bundle["description_id"])

    curriculum_id: str = await conn.fetchval(
        "SELECT id::text FROM curricula "
        "WHERE code = $1 AND workspace_id IS NULL",
        bundle["curriculum_code"],
    )
    print("  curricula: seeded")

    # ── Skills ───────────────────────────────────────────────────────
    # Conflict target: partial unique index uq_skills_platform_code.
    # On conflict, refresh only short labels so curated values propagate to
    # dev DBs seeded before short labels existed.  Row count is unchanged.
    skills_data = _load(bundle["skills_file"])
    for s in skills_data:
        await conn.execute("""
            INSERT INTO skills (sport_id, curriculum_id, workspace_id, code,
                                category, name_en, name_id, display_order, is_enabled,
                                short_label_en, short_label_id)
            VALUES ($1, $2, NULL, $3, $4, $5, $6, $7, TRUE, $8, $9)
            ON CONFLICT (sport_id, code) WHERE workspace_id IS NULL DO UPDATE
              SET short_label_en = EXCLUDED.short_label_en,
                  short_label_id = EXCLUDED.short_label_id
        """, sport_id, curriculum_id, s["code"], s["category"],
            s["name_en"], s["name_id"], s["display_order"],
            s.get("short_label_en"), s.get("short_label_id"))

    count = await conn.fetchval(
        "SELECT count(*) FROM skills WHERE sport_id = $1 AND workspace_id IS NULL",
        sport_id,
    )
    print(f"  skills: {count} rows")

    # ── Skill level descriptors ──────────────────────────────────────
    # Conflict target: partial unique index uq_descriptors_platform_level.
    # Scope the skill lookup to this sport so codes never collide across sports.
    desc_data = _load(bundle["descriptors_file"])
    for d in desc_data:
        skill_id: str | None = await conn.fetchval(
            "SELECT id::text FROM skills "
            "WHERE code = $1 AND workspace_id IS NULL AND sport_id = $2",
            d["skill_code"], sport_id,
        )
        if skill_id is None:
            print(f"  WARN: skill not found for descriptor: {d['skill_code']}")
            continue
        await conn.execute("""
            INSERT INTO skill_level_descriptors
                (skill_id, workspace_id, level, description_en, description_id)
            VALUES ($1, NULL, $2, $3, $4)
            ON CONFLICT (skill_id, level) WHERE workspace_id IS NULL DO NOTHING
        """, skill_id, d["level"], d["description_en"], d["description_id"])

    desc_count = await conn.fetchval(
        "SELECT count(*) FROM skill_level_descriptors sld "
        "JOIN skills s ON s.id = sld.skill_id "
        "WHERE s.sport_id = $1 AND sld.workspace_id IS NULL",
        sport_id,
    )
    print(f"  skill_level_descriptors: {desc_count} rows")

    # ── Tiers ────────────────────────────────────────────────────────
    # Conflict target: partial unique index uq_tiers_platform_code
    tiers_data = _load(bundle["tiers_file"])
    for t in tiers_data:
        await conn.execute("""
            INSERT INTO tiers (sport_id, curriculum_id, workspace_id, code,
                               display_order, name_game_en, name_game_id,
                               name_skill_en, name_skill_id, color_hex, icon_name)
            VALUES ($1, $2, NULL, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (sport_id, curriculum_id, code)
                WHERE workspace_id IS NULL DO NOTHING
        """, sport_id, curriculum_id,
            t["code"], t["display_order"],
            t["name_game_en"], t["name_game_id"],
            t["name_skill_en"], t["name_skill_id"],
            t.get("color_hex"), t.get("icon_name"))

    tier_count = await conn.fetchval(
        "SELECT count(*) FROM tiers WHERE sport_id = $1 AND workspace_id IS NULL",
        sport_id,
    )
    print(f"  tiers: {tier_count} rows")

    # ── Tier requirements ─────────────────────────────────────────────
    # tier_requirements has a real UNIQUE (tier_id, skill_id) with non-nullable
    # columns, so standard ON CONFLICT works here.
    reqs_data = _load(bundle["requirements_file"])
    req_total = 0
    for tier_block in reqs_data:
        tier_id: str | None = await conn.fetchval(
            """SELECT id::text FROM tiers
               WHERE code = $1 AND workspace_id IS NULL AND sport_id = $2""",
            tier_block["tier_code"], sport_id,
        )
        if tier_id is None:
            print(f"  WARN: tier not found: {tier_block['tier_code']}")
            continue
        for req in tier_block["requirements"]:
            skill_id = await conn.fetchval(
                "SELECT id::text FROM skills "
                "WHERE code = $1 AND workspace_id IS NULL AND sport_id = $2",
                req["skill_code"], sport_id,
            )
            if skill_id is None:
                print(f"  WARN: skill not found for requirement: {req['skill_code']}")
                continue
            await conn.execute("""
                INSERT INTO tier_requirements (tier_id, skill_id, min_level)
                VALUES ($1, $2, $3)
                ON CONFLICT (tier_id, skill_id) DO NOTHING
            """, tier_id, skill_id, req["min_level"])
            req_total += 1

    print(f"  tier_requirements: attempted {req_total}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--with-admin",
        action="store_true",
        help="Also bootstrap the Okky Adhi PoC admin + Coachito Demo Club.",
    )
    args = parser.parse_args()
    asyncio.run(seed(with_admin=args.with_admin))
