"""Multi-sport resolution + workspace-sport management.

Implements the query-layer half of the multi-sport refactor
(tennis-skill-framework-v0.1 §3).  RLS still scopes by ``workspace_id``;
sport is an app-layer filter resolved here.

Backward-compatibility rule (doc §3.5): when a request omits a sport and the
workspace has exactly one active sport, the server defaults to that sport.
Single-sport workspaces therefore keep working with no client changes.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SportError(Exception):
    """Base for sport-resolution / authorization failures."""


class SportRequiredError(SportError):
    """Workspace offers multiple sports and the caller didn't pick one."""


class SportNotEnabledError(SportError):
    """Requested sport isn't active on this workspace."""


class SportNotQualifiedError(SportError):
    """Coach isn't qualified to act in the requested sport."""


# ── Resolution ──────────────────────────────────────────────────────


async def resolve_sport_id(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    sport_id: UUID | None = None,
    sport_code: str | None = None,
) -> UUID:
    """Resolve the effective sport for a request.

    Precedence: explicit ``sport_id`` / ``sport_code`` (validated active) →
    the workspace's single active sport → legacy ``workspaces.sport_id``
    (dual-write fallback during the migration window).
    """
    if sport_id is None and sport_code is not None:
        sport_id = await db.scalar(
            text("SELECT id FROM sports WHERE code = :c"), {"c": sport_code}
        )
        if sport_id is None:
            raise SportNotEnabledError(f"Unknown sport '{sport_code}'.")

    if sport_id is not None:
        ok = await db.scalar(
            text(
                "SELECT 1 FROM workspace_sports "
                "WHERE workspace_id = :wid AND sport_id = :sid "
                "  AND is_active AND archived_at IS NULL"
            ),
            {"wid": workspace_id, "sid": sport_id},
        )
        if ok is None:
            raise SportNotEnabledError("That sport isn't active on this workspace.")
        return sport_id

    active = (
        await db.execute(
            text(
                "SELECT sport_id FROM workspace_sports "
                "WHERE workspace_id = :wid AND is_active AND archived_at IS NULL "
                "ORDER BY enabled_at"
            ),
            {"wid": workspace_id},
        )
    ).scalars().all()

    if active:
        # Default to the first active sport (by enabled_at) when the caller
        # didn't specify one — even with multiple sports.  This keeps every
        # not-yet-sport-aware screen working the moment a 2nd sport is enabled;
        # sport-aware screens pass an explicit sport_id via the switcher.
        return active[0]
    legacy = await db.scalar(
        text("SELECT sport_id FROM workspaces WHERE id = :wid"),
        {"wid": workspace_id},
    )
    if legacy is not None:
        return legacy
    raise SportNotEnabledError("Workspace has no active sport.")


async def coach_qualified_for_sport(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
    sport_id: UUID,
) -> bool:
    """True if the coach (by user_id) may act in the sport.

    A coach with **explicit** qualification rows is allowed only for the listed
    sports.  A coach with **no** qualification rows is treated as legacy /
    unscoped and allowed for all sports — this keeps coaches created through the
    invite flow (which doesn't yet write membership_sports) working, and is
    safe because RLS already confines them to the workspace.
    """
    quals = (
        await db.execute(
            text(
                "SELECT ms.sport_id FROM membership_sports ms "
                "JOIN workspace_memberships m ON m.id = ms.membership_id "
                "WHERE m.workspace_id = :wid AND m.user_id = :uid "
                "  AND m.archived_at IS NULL"
            ),
            {"wid": workspace_id, "uid": user_id},
        )
    ).scalars().all()
    if not quals:
        return True
    return sport_id in set(quals)


# ── Workspace sports listing ────────────────────────────────────────


async def list_workspace_sports(
    db: AsyncSession, *, workspace_id: UUID
) -> list[dict]:  # type: ignore[type-arg]
    """Active sports for a workspace with their curriculum reference, for the
    workspace detail response (doc §3.5)."""
    rows = (
        await db.execute(
            text(
                """
                SELECT s.id::text          AS sport_id,
                       s.code              AS sport_code,
                       s.name_en           AS name_en,
                       s.name_id           AS name_id,
                       ws.curriculum_id::text AS curriculum_id,
                       c.code              AS curriculum_code,
                       ws.is_active        AS is_active
                FROM workspace_sports ws
                JOIN sports s ON s.id = ws.sport_id
                LEFT JOIN curricula c ON c.id = ws.curriculum_id
                WHERE ws.workspace_id = :wid AND ws.archived_at IS NULL
                ORDER BY s.display_order
                """
            ),
            {"wid": workspace_id},
        )
    ).mappings().all()
    return [dict(r) for r in rows]


# ── Management: enable / archive a sport on a workspace ─────────────


async def enable_sport(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    sport_id: UUID,
    curriculum_id: UUID | None,
) -> None:
    """Enable (or re-activate) a sport on a workspace.  Idempotent: a prior
    archived row is flipped back to active."""
    await db.execute(
        text(
            """
            INSERT INTO workspace_sports
                (workspace_id, sport_id, curriculum_id, is_active)
            VALUES (:wid, :sid, :cid, TRUE)
            ON CONFLICT (workspace_id, sport_id) DO UPDATE
              SET is_active = TRUE,
                  archived_at = NULL,
                  curriculum_id = COALESCE(
                      EXCLUDED.curriculum_id, workspace_sports.curriculum_id
                  )
            """
        ),
        {"wid": workspace_id, "sid": sport_id, "cid": curriculum_id},
    )


async def archive_sport(
    db: AsyncSession, *, workspace_id: UUID, sport_id: UUID
) -> None:
    await db.execute(
        text(
            "UPDATE workspace_sports "
            "SET is_active = FALSE, archived_at = NOW() "
            "WHERE workspace_id = :wid AND sport_id = :sid"
        ),
        {"wid": workspace_id, "sid": sport_id},
    )


async def default_curriculum_for_sport(
    db: AsyncSession, *, sport_id: UUID
) -> UUID | None:
    """The platform-default (workspace_id IS NULL) curriculum for a sport."""
    return await db.scalar(
        text(
            "SELECT id FROM curricula "
            "WHERE sport_id = :sid AND workspace_id IS NULL "
            "ORDER BY created_at LIMIT 1"
        ),
        {"sid": sport_id},
    )


# ── Per-sport tier cache ────────────────────────────────────────────


async def upsert_athlete_sport_tier(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    athlete_id: UUID,
    sport_id: UUID,
    tier_id: UUID | None,
) -> None:
    """Write the denormalized current tier for (athlete, sport).  ``None``
    clears the row (athlete dropped below the first tier)."""
    if tier_id is None:
        await db.execute(
            text(
                "DELETE FROM athlete_sport_tiers "
                "WHERE athlete_id = :aid AND sport_id = :sid"
            ),
            {"aid": athlete_id, "sid": sport_id},
        )
        return
    await db.execute(
        text(
            """
            INSERT INTO athlete_sport_tiers
                (workspace_id, athlete_id, sport_id, tier_id)
            VALUES (:wid, :aid, :sid, :tid)
            ON CONFLICT (athlete_id, sport_id) DO UPDATE
              SET tier_id = EXCLUDED.tier_id, promoted_at = NOW()
            """
        ),
        {"wid": workspace_id, "aid": athlete_id, "sid": sport_id, "tid": tier_id},
    )


# ── Athlete / membership sport enrollment ───────────────────────────


async def set_athlete_sports(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    athlete_id: UUID,
    sport_ids: list[UUID],
) -> None:
    """Replace an athlete's sport enrollment set.  Sports removed are
    archived (soft); sports added are inserted / re-activated."""
    for sid in sport_ids:
        await db.execute(
            text(
                """
                INSERT INTO athlete_sports (workspace_id, athlete_id, sport_id)
                VALUES (:wid, :aid, :sid)
                ON CONFLICT (athlete_id, sport_id) DO UPDATE
                  SET archived_at = NULL
                """
            ),
            {"wid": workspace_id, "aid": athlete_id, "sid": sid},
        )
    if sport_ids:
        placeholders = ", ".join(f":s{i}" for i in range(len(sport_ids)))
        params: dict[str, object] = {f"s{i}": s for i, s in enumerate(sport_ids)}
        params["aid"] = athlete_id
        await db.execute(
            text(
                f"UPDATE athlete_sports SET archived_at = NOW() "
                f"WHERE athlete_id = :aid AND archived_at IS NULL "
                f"  AND sport_id NOT IN ({placeholders})"
            ),
            params,
        )


async def set_membership_sports(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    membership_id: UUID,
    sport_ids: list[UUID],
) -> None:
    """Replace a coach membership's sport qualifications."""
    for sid in sport_ids:
        await db.execute(
            text(
                """
                INSERT INTO membership_sports (workspace_id, membership_id, sport_id)
                VALUES (:wid, :mid, :sid)
                ON CONFLICT (membership_id, sport_id) DO NOTHING
                """
            ),
            {"wid": workspace_id, "mid": membership_id, "sid": sid},
        )
    if sport_ids:
        placeholders = ", ".join(f":s{i}" for i in range(len(sport_ids)))
        params: dict[str, object] = {f"s{i}": s for i, s in enumerate(sport_ids)}
        params["mid"] = membership_id
        await db.execute(
            text(
                f"DELETE FROM membership_sports "
                f"WHERE membership_id = :mid AND sport_id NOT IN ({placeholders})"
            ),
            params,
        )
