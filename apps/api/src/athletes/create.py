"""POST /trainees: create the athlete + the first invite in one transaction."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.athlete import Athlete
from src.db.models.invite import Invite
from src.db.models.workspace import Workspace
from src.invites.service import (
    create_invite,
    find_user_by_invite_phone,
    public_landing_url,
    revoke_pending_invites_for_athlete,
)

_AGE_OF_MAJORITY_YEARS = 18

E164_RE = re.compile(r"^\+[1-9]\d{1,14}$")


def _is_minor(dob: date | None, *, today: date | None = None) -> bool:
    if dob is None:
        return False
    today = today or datetime.now(UTC).date()
    eighteenth = dob.replace(year=dob.year + _AGE_OF_MAJORITY_YEARS)
    return today < eighteenth


async def create_athlete_with_invite(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    coach_id: UUID,
    name: str,
    phone_e164: str,
    date_of_birth: date | None,
    parent_phone_e164: str | None,
) -> tuple[Athlete, Invite, dict[str, Any]]:
    """Create the athlete + an initial invite atomically.  Caller commits.

    Returns the persisted ORM objects plus a dict of extra fields (currently
    just `landing_url`) the router needs to assemble the response.
    """
    workspace = (
        await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ).scalar_one()

    athlete = Athlete(
        workspace_id=workspace_id,
        display_name=name.strip(),
        date_of_birth=date_of_birth,
        is_minor=_is_minor(date_of_birth),
        joined_at=datetime.now(UTC).date(),
        created_by_id=coach_id,
    )
    db.add(athlete)
    await db.flush()

    # Phone shortcut: if this phone has previously claimed an invite, we know
    # the user — link the new invite to them directly. The coach FE shows
    # "Linked to existing account" instead of the WhatsApp share button, and
    # the trainee gets a pending-invite banner the next time they open the app.
    matched = await find_user_by_invite_phone(phone_e164)
    invited_user_id = matched[0] if matched else None

    invite = await create_invite(
        db,
        workspace=workspace,
        invited_by_id=coach_id,
        trainee_name=athlete.display_name,
        athlete_id=athlete.id,
        phone_e164=phone_e164,
        role="trainee",
        invited_user_id=invited_user_id,
    )

    # Parent phone is not modeled on its own table at MVP — keep it on the
    # athlete via the optional `notes` column so it isn't silently dropped.
    # Real schema (separate user_guardians link) lands when we ship the parent
    # account flow.
    if parent_phone_e164:
        existing = athlete.notes or ""
        marker = f"parent_phone: {parent_phone_e164}"
        if marker not in existing:
            athlete.notes = (existing + ("\n" if existing else "") + marker).strip()
            await db.flush()

    extras: dict[str, Any] = {
        "landing_url": public_landing_url(invite.invite_code),
    }
    if matched is not None:
        extras["linked_user"] = {
            "id": str(matched[0]),
            "email": matched[1],
            "display_name": matched[2],
        }
    return athlete, invite, extras


# Re-invite is a separate flow (used after "Send WhatsApp invite" fails or
# when the coach wants to retry).  Lives here for now alongside the create
# helper; eventually moves into invites/service.py.
async def reinvite_athlete(
    db: AsyncSession,
    *,
    athlete: Athlete,
    coach_id: UUID,
    phone_e164: str,
) -> Invite:
    workspace = (
        await db.execute(select(Workspace).where(Workspace.id == athlete.workspace_id))
    ).scalar_one()
    await revoke_pending_invites_for_athlete(db, athlete_id=athlete.id)
    return await create_invite(
        db,
        workspace=workspace,
        invited_by_id=coach_id,
        trainee_name=athlete.display_name,
        athlete_id=athlete.id,
        phone_e164=phone_e164,
        role="trainee",
    )


# Silence unused-import warnings on imports kept for the type-system view.
_ = timedelta
