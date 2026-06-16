"""Public invite landing page lookup.

`/i/{token}` is the one and only non-API HTTP route on the BE — it returns
HTML so the URL unfurls on WhatsApp / iMessage / Telegram with the workspace's
branding.  Because the request is unauthenticated, RLS doesn't have a JWT-
derived workspace context, and the invites table policy would hide the row.
We bypass it by opening a separate asyncpg connection with the superuser DSN
just for this read.  Cleaner long-term fix: a SECURITY DEFINER function
`public_invite_lookup(token)` granted to coachito_api.
"""

from __future__ import annotations

from typing import Any

import asyncpg

from src.config import settings


def _superuser_dsn() -> str:
    # Always use database_url (internal host). alembic_database_url may be
    # set to the external/public proxy endpoint for running migrations from a
    # dev machine — that host isn't reliably reachable from inside the
    # container and may have different SSL requirements.
    raw = settings.database_url
    return raw.replace("postgresql+asyncpg://", "postgresql://")


async def fetch_invite_public(token: str) -> dict[str, Any] | None:
    """Returns a flat dict the template can render, or None if no such token.

    Joins workspaces (for branding) + users (the inviting coach) + athletes
    (the prospective trainee's first name).  No auth — the token itself is
    the capability.
    """
    conn = await asyncpg.connect(_superuser_dsn())
    try:
        row = await conn.fetchrow(
            """
            SELECT
                i.id::text                  AS invite_id,
                i.invite_code,
                i.phone_e164,
                i.expires_at,
                i.claimed_at,
                i.revoked_at,
                i.created_at,
                w.id::text                  AS workspace_id,
                w.name                      AS workspace_name,
                w.brand_color,
                w.logo_url,
                w.primary_locale,
                u.display_name              AS coach_display_name,
                a.display_name              AS trainee_display_name
            FROM invites i
            JOIN workspaces w ON w.id = i.workspace_id
            JOIN users u      ON u.id = i.invited_by_id
            LEFT JOIN athletes a ON a.id = i.athlete_id
            WHERE i.invite_code = $1
            """,
            token,
        )
        return dict(row) if row else None
    finally:
        await conn.close()
