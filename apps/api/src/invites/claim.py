"""POST /invites/{token}/claim — authenticated invite redemption.

Flow:
  1. Look up the invite (bypass RLS — token IS the capability, like the public
     landing).  Reject if expired / revoked / already claimed.
  2. Mark `claimed_at = NOW()` and `claimed_by_id = current_user`.
  3. Insert a `workspace_memberships` row with role = invite.role (typically
     trainee) and status active.  No-op if it already exists.
  4. If the invite points at an athlete row, set `athletes.user_id` to the
     authenticated user — this is the link the trainee-scoped RLS relies on.
  5. Mint a new JWT pair with `wsid` set to the invite's workspace so
     subsequent FE requests land in the right tenant context.

Returns the standard TokenPair so the FE just calls signIn() again.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import asyncpg

from src.invites.og_landing import _superuser_dsn


class InviteNotFoundError(Exception):
    pass


class InviteAlreadyClaimedError(Exception):
    pass


class InviteExpiredError(Exception):
    pass


async def claim_invite(*, token: str, user_id: UUID) -> dict[str, object]:
    """Returns a dict {workspace_id, role, athlete_id}.

    Runs against a privileged asyncpg connection (RLS-bypass) because the
    invite token is itself the authorization for the operation.  The caller
    is still required to be authenticated — that's enforced at the router
    layer via Depends(get_current_user_id).
    """
    now = datetime.now(UTC)
    conn = await asyncpg.connect(_superuser_dsn())
    try:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                SELECT
                    id, workspace_id, athlete_id, role,
                    expires_at, claimed_at, revoked_at
                FROM invites
                WHERE invite_code = $1
                FOR UPDATE
                """,
                token,
            )
            if row is None:
                raise InviteNotFoundError(token)
            if row["revoked_at"] is not None:
                raise InviteNotFoundError(token)
            if row["claimed_at"] is not None:
                raise InviteAlreadyClaimedError(token)

            expires_at = row["expires_at"]
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at <= now:
                raise InviteExpiredError(token)

            workspace_id: UUID = row["workspace_id"]
            athlete_id: UUID | None = row["athlete_id"]
            role: str = row["role"]

            # Mark consumed.
            await conn.execute(
                """
                UPDATE invites
                   SET claimed_at = $1,
                       claimed_by_id = $2,
                       invited_user_id = COALESCE(invited_user_id, $2)
                 WHERE id = $3
                """,
                now,
                user_id,
                row["id"],
            )

            # Membership upsert.  ON CONFLICT covers re-claim after a coach
            # manually re-issued the same role; we just flip status to active.
            await conn.execute(
                """
                INSERT INTO workspace_memberships (
                    workspace_id, user_id, role, status,
                    invited_at, joined_at, invited_by_id
                )
                VALUES ($1, $2, $3::workspace_role, 'active', $4, $4, NULL)
                ON CONFLICT (workspace_id, user_id, role)
                DO UPDATE SET status = 'active', joined_at = EXCLUDED.joined_at
                """,
                workspace_id,
                user_id,
                role,
                now,
            )

            # Link athlete row.  Only set when null OR matches us, to avoid
            # silently re-pointing an already-claimed athlete.  RLS for the
            # trainee role keys off this column, so without the link the
            # trainee would see an empty home.
            #
            # Also point-in-time sync ``athletes.display_name`` to the user's
            # current ``users.display_name`` so the coach view picks up the
            # name the trainee chose at signup (instead of the placeholder
            # the coach typed when issuing the invite). Subsequent changes to
            # users.display_name do NOT propagate — this is a one-shot copy
            # at claim time. Coaches who want to rename later own that alias.
            if athlete_id is not None:
                await conn.execute(
                    """
                    UPDATE athletes a
                       SET user_id = $1,
                           display_name = COALESCE(
                               (SELECT u.display_name FROM users u WHERE u.id = $1),
                               a.display_name
                           ),
                           updated_at = NOW()
                     WHERE a.id = $2
                       AND (a.user_id IS NULL OR a.user_id = $1)
                    """,
                    user_id,
                    athlete_id,
                )

            return {
                "workspace_id": workspace_id,
                "role": role,
                "athlete_id": athlete_id,
            }
    finally:
        await conn.close()
