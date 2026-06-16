"""Invite token generation, create-with-revoke, and DB helpers.

Token format: `{workspace_slug}-{trainee_handle}-{rand}` per docs/07-invite-
and-onboarding.md.  The structured form is intentionally readable (engineers
debugging WhatsApp issues can see which workspace + which trainee a token is
for from log lines alone), with 8 random URL-safe chars at the end for
collision-resistance.
"""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import asyncpg
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.models.invite import Invite
from src.db.models.workspace import Workspace

INVITE_TTL_DAYS = 7
_HANDLE_CHARS = re.compile(r"[^a-z0-9]+")


def _slug_from_workspace(workspace: Workspace) -> str:
    if workspace.slug:
        ascii_slug = _HANDLE_CHARS.sub("", workspace.slug.lower())
        if ascii_slug:
            return ascii_slug[:4]
    base = _HANDLE_CHARS.sub("", workspace.name.lower())
    return base[:3] or "rc"


def _trainee_handle(display_name: str) -> str:
    first = display_name.strip().split()[0] if display_name.strip() else ""
    handle = _HANDLE_CHARS.sub("", first.lower())
    return handle[:8] or "trainee"


def generate_invite_code(workspace: Workspace, trainee_name: str) -> str:
    """Deterministic prefix + random suffix.  Collision odds are negligible at
    MVP scale (8 url-safe chars ≈ 218 trillion combinations per
    (workspace, trainee) bucket) — but the caller still re-tries on the
    UNIQUE constraint just in case."""
    slug = _slug_from_workspace(workspace)
    handle = _trainee_handle(trainee_name)
    suffix = secrets.token_urlsafe(6)[:8]
    return f"{slug}-{handle}-{suffix}"


def expiry_from_now() -> datetime:
    return datetime.now(UTC) + timedelta(days=INVITE_TTL_DAYS)


def is_invite_active(invite: Invite, *, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    if invite.claimed_at is not None:
        return False
    if invite.revoked_at is not None:
        return False
    expires_at = invite.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at > now


async def revoke_pending_invites_for_athlete(
    db: AsyncSession, *, athlete_id: UUID
) -> int:
    """Mark all unclaimed / un-revoked invites for an athlete as revoked.

    Returns the number of rows updated.  Called before re-issuing an invite so
    we don't leave multiple live tokens pointing at the same athlete.
    """
    now = datetime.now(UTC)
    result = await db.execute(
        update(Invite)
        .where(Invite.athlete_id == athlete_id)
        .where(Invite.claimed_at.is_(None))
        .where(Invite.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    return int(result.rowcount or 0)


async def create_invite(
    db: AsyncSession,
    *,
    workspace: Workspace,
    invited_by_id: UUID,
    trainee_name: str,
    athlete_id: UUID,
    phone_e164: str,
    role: str = "trainee",
    invited_user_id: UUID | None = None,
) -> Invite:
    """Generate a token + insert the invite row.  Caller is responsible for the
    surrounding transaction (athletes/create.py wraps this in the same txn as
    athlete creation).

    ``invited_user_id`` is set when we already know which existing user this
    invite is for (e.g. phone match against a prior claim). The trainee then
    sees the invite in their pending-invites banner instead of needing the
    WhatsApp share link round-trip.
    """
    code = generate_invite_code(workspace, trainee_name)
    invite = Invite(
        workspace_id=workspace.id,
        email=None,
        phone_e164=phone_e164,
        role=role,
        athlete_id=athlete_id,
        invite_code=code,
        invited_by_id=invited_by_id,
        invited_user_id=invited_user_id,
        expires_at=expiry_from_now(),
    )
    db.add(invite)
    await db.flush()
    return invite


def _superuser_dsn() -> str:
    raw = settings.alembic_database_url or settings.database_url
    return raw.replace("postgresql+asyncpg://", "postgresql://")


async def find_user_by_invite_phone(
    phone_e164: str,
) -> tuple[UUID, str, str] | None:
    """Look up the most recent claimed invite for this phone number and return
    ``(user_id, email, display_name)``.  Returns None when no prior claim
    matches — caller falls back to the WhatsApp share flow.

    Runs against a privileged connection (RLS-bypass) because the phone
    number itself is the capability: we need to scan invites across all
    workspaces to find prior claims, not just the caller's current one.
    Phone is not on ``users`` directly (privacy + multi-number reality);
    matching off the invites history is the indirect-but-reliable join.
    """
    conn = await asyncpg.connect(_superuser_dsn())
    try:
        row = await conn.fetchrow(
            """
            SELECT u.id, u.email, u.display_name
            FROM invites i
            JOIN users u ON u.id = i.claimed_by_id
            WHERE i.phone_e164 = $1
              AND i.claimed_at IS NOT NULL
            ORDER BY i.claimed_at DESC
            LIMIT 1
            """,
            phone_e164,
        )
    finally:
        await conn.close()
    if row is None:
        return None
    return row["id"], row["email"], row["display_name"]


def public_landing_url(invite_code: str) -> str:
    """The URL the WhatsApp link points to — served by GET /i/{token}."""
    return f"{settings.web_url}/i/{invite_code}"


async def find_invite_by_code(db: AsyncSession, code: str) -> Invite | None:
    result = await db.execute(select(Invite).where(Invite.invite_code == code))
    return result.scalar_one_or_none()
