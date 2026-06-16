"""Public + authenticated invite endpoints.

  GET /i/{token}                       (public, HTML, OG-tagged)
  POST /trainees/{athlete_id}/invite   (authenticated, re-invite — revokes old)

The public landing page is the URL WhatsApp / iMessage / Telegram fetch when
the coach shares the link.  Cache-Control: public, max-age=86400 so the CDN
caches the unfurl response and re-fetches don't hit the API.
"""

from __future__ import annotations

from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, Field
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.decorators import audit_action
from src.auth.password import WeakPasswordError, hash_password
from src.auth.schemas import TokenPair, UserOut
from src.auth.service import (
    get_role_in_workspace,
    issue_and_register_token_pair,
    touch_last_seen,
)
from src.config import settings
from src.db.models.athlete import Athlete
from src.db.models.user import User
from src.db.models.workspace import Workspace
from src.db.session import get_session
from src.deps import get_current_user_id, get_redis
from src.middleware.rls import db_with_rls, set_user_context

from .claim import (
    InviteAlreadyClaimedError,
    InviteExpiredError,
    InviteNotFoundError,
    claim_invite,
)
from .og_landing import fetch_invite_public
from .schemas import InviteOut
from .service import (
    create_invite,
    public_landing_url,
    revoke_pending_invites_for_athlete,
)

# Templates dir resolves relative to /app/apps/api/templates inside the container.
_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"
_templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))

public_router = APIRouter(tags=["invites"])
trainees_router = APIRouter(prefix="/trainees", tags=["invites"])
invites_router = APIRouter(prefix="/invites", tags=["invites"])


# ── GET /i/{token} ───────────────────────────────────────────────


def _is_active(row: dict, now: datetime) -> bool:
    if row.get("claimed_at") is not None or row.get("revoked_at") is not None:
        return False
    exp = row["expires_at"]
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=UTC)
    return exp > now


def _locale_copy(locale: str, key: str) -> str:
    return _COPY.get(locale, _COPY["en"]).get(key, _COPY["en"][key])


_COPY = {
    "en": {
        "greeting_generic": "You're invited",
        "greeting_with_name": "You're invited, {name}",
        "lead": "Track your padel progress with {workspace}. The link below opens the Coachito app.",
        "workspace_label": "From",
        "coach_label": "Invited by",
        "continue_cta": "Continue to Coachito →",
        "signin_cta": "I already have an account",
        "expiry_line": "This invite expires {when}.",
        "expired_title": "This invite has expired",
        "expired_lead": "Ask your coach to send a new one.",
        "invalid_title": "Invite not found",
        "invalid_lead": "The link may be mistyped, or the invite was revoked.",
        "og_desc": "Track your padel progress with {workspace}.",
    },
    "id": {
        "greeting_generic": "Kamu diundang",
        "greeting_with_name": "Kamu diundang, {name}",
        "lead": "Track progres padel-mu bersama {workspace}. Link di bawah membuka aplikasi Coachito.",
        "workspace_label": "Dari",
        "coach_label": "Diundang oleh",
        "continue_cta": "Lanjut ke Coachito →",
        "signin_cta": "Saya sudah punya akun",
        "expiry_line": "Undangan ini kedaluwarsa {when}.",
        "expired_title": "Undangan ini sudah kedaluwarsa",
        "expired_lead": "Minta coach untuk mengirim yang baru.",
        "invalid_title": "Undangan tidak ditemukan",
        "invalid_lead": "Mungkin salah ketik, atau undangan dicabut.",
        "og_desc": "Track progres padel-mu bersama {workspace}.",
    },
}


def _format_expires(dt: datetime, locale: str) -> str:
    # Compact, locale-aware "in N days" rendered server-side so the unfurl
    # is self-contained.  date-fns lives on the FE.
    now = datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    delta_days = max(int((dt - now).total_seconds() // 86400), 0)
    if locale == "id":
        return f"dalam {delta_days} hari" if delta_days != 1 else "dalam 1 hari"
    return f"in {delta_days} days" if delta_days != 1 else "in 1 day"


@public_router.get("/i/{token}", response_class=HTMLResponse)
async def invite_landing(request: Request, token: str) -> HTMLResponse:
    data = await fetch_invite_public(token)
    now = datetime.now(UTC)

    # Common context for both invalid + valid templates
    if data is None:
        ctx = _build_invalid_context(
            request, locale="en", title_key="invalid_title", lead_key="invalid_lead"
        )
        return _templates.TemplateResponse(
            request, "invite_landing.html", ctx, status_code=status.HTTP_404_NOT_FOUND
        )

    locale = data.get("primary_locale") or "en"
    if locale not in _COPY:
        locale = "en"

    if not _is_active(data, now):
        ctx = _build_invalid_context(
            request,
            locale=locale,
            title_key="expired_title",
            lead_key="expired_lead",
            workspace_name=data["workspace_name"],
            logo_url=data.get("logo_url"),
            brand_color=data.get("brand_color"),
        )
        return _templates.TemplateResponse(
            request, "invite_landing.html", ctx, status_code=status.HTTP_410_GONE
        )

    workspace_name = data["workspace_name"]
    coach_name = (data["coach_display_name"] or "").replace("Coach ", "").strip() or "your coach"
    trainee_first_name = (
        (data["trainee_display_name"] or "").split()[0]
        if data["trainee_display_name"]
        else ""
    )

    greeting_with_name = _locale_copy(locale, "greeting_with_name").format(
        name=trainee_first_name
    )
    lead_copy = _locale_copy(locale, "lead").format(workspace=workspace_name)
    expiry_line = _locale_copy(locale, "expiry_line").format(
        when=_format_expires(data["expires_at"], locale)
    )

    ctx = {
        "request": request,
        "locale": locale,
        "workspace_name": workspace_name,
        "workspace_initial": (workspace_name[:1] or "R").upper(),
        "logo_url": data.get("logo_url"),
        "brand_color": data.get("brand_color"),
        "trainee_first_name": trainee_first_name,
        "greeting_generic": _locale_copy(locale, "greeting_generic"),
        "greeting_with_name": greeting_with_name,
        "lead_copy": lead_copy,
        "workspace_label": _locale_copy(locale, "workspace_label"),
        "coach_label": _locale_copy(locale, "coach_label"),
        "coach_display_name": data["coach_display_name"],
        "continue_cta": _locale_copy(locale, "continue_cta"),
        "signin_cta": _locale_copy(locale, "signin_cta"),
        "continue_url": f"{settings.web_url}/invite/{token}",
        "web_signin_url": f"{settings.web_url}/signin",
        "landing_url": public_landing_url(token),
        "og_description": _locale_copy(locale, "og_desc").format(workspace=workspace_name),
        "expiry_line": expiry_line,
    }
    response = _templates.TemplateResponse(request, "invite_landing.html", ctx)
    # Aggressive CDN caching — once we know a token's metadata, it doesn't
    # change until the underlying workspace logo/name changes.
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response


def _build_invalid_context(
    request: Request,
    *,
    locale: str,
    title_key: str,
    lead_key: str,
    workspace_name: str = "Coachito",
    logo_url: str | None = None,
    brand_color: str | None = None,
) -> dict:
    return {
        "request": request,
        "locale": locale,
        "workspace_name": workspace_name,
        "workspace_initial": (workspace_name[:1] or "C").upper(),
        "logo_url": logo_url,
        "brand_color": brand_color,
        "trainee_first_name": "",
        "greeting_generic": _locale_copy(locale, title_key),
        "greeting_with_name": _locale_copy(locale, title_key),
        "lead_copy": _locale_copy(locale, lead_key),
        "workspace_label": _locale_copy(locale, "workspace_label"),
        "coach_label": _locale_copy(locale, "coach_label"),
        "coach_display_name": "—",
        "continue_cta": _locale_copy(locale, "signin_cta"),
        "signin_cta": _locale_copy(locale, "signin_cta"),
        "continue_url": f"{settings.web_url}/signin",
        "web_signin_url": f"{settings.web_url}/signin",
        "landing_url": f"{settings.web_url}/i/expired",
        "og_description": _locale_copy(locale, lead_key),
        "expiry_line": "",
    }


# ── POST /trainees/{athlete_id}/invite (re-invite) ───────────────


@trainees_router.post(
    "/{athlete_id}/invite",
    response_model=InviteOut,
    status_code=status.HTTP_201_CREATED,
)
async def reinvite_trainee(
    athlete_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> InviteOut:
    # Look up athlete (RLS scopes to current workspace)
    athlete = (
        await db.execute(select(Athlete).where(Athlete.id == athlete_id))
    ).scalar_one_or_none()
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trainee not found."
        )

    # Need the most recent invite for this athlete to recover the phone number
    # (athletes don't store phone directly — it lives on the invite).
    last_invite_row = await db.execute(
        select(
            __import__("src.db.models.invite", fromlist=["Invite"]).Invite
        )
        .where(__import__("src.db.models.invite", fromlist=["Invite"]).Invite.athlete_id == athlete.id)
        .order_by(
            __import__("src.db.models.invite", fromlist=["Invite"]).Invite.created_at.desc()
        )
        .limit(1)
    )
    last_invite = last_invite_row.scalar_one_or_none()
    if last_invite is None or last_invite.phone_e164 is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No phone number on record for this trainee.",
        )

    workspace = (
        await db.execute(select(Workspace).where(Workspace.id == athlete.workspace_id))
    ).scalar_one()

    await revoke_pending_invites_for_athlete(db, athlete_id=athlete.id)
    invite = await create_invite(
        db,
        workspace=workspace,
        invited_by_id=user_id,
        trainee_name=athlete.display_name,
        athlete_id=athlete.id,
        phone_e164=last_invite.phone_e164,
        role="trainee",
    )
    await db.commit()

    return InviteOut(
        id=str(invite.id),
        code=invite.invite_code,
        phone_e164=invite.phone_e164,
        expires_at=invite.expires_at,
        landing_url=public_landing_url(invite.invite_code),
    )


# ── GET /invites/public/{token} ──────────────────────────────────


class InvitePublicOut(BaseModel):
    token: str
    workspace_name: str
    workspace_logo_url: str | None
    brand_color: str | None
    coach_display_name: str | None
    trainee_first_name: str | None
    primary_locale: str
    expires_in_days: int
    state: str  # 'active' | 'expired' | 'consumed' | 'invalid'


@invites_router.get("/public/{token}", response_model=InvitePublicOut)
async def get_public_invite(token: str) -> InvitePublicOut:
    data = await fetch_invite_public(token)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found."
        )

    now = datetime.now(UTC)
    expires_at = data["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)

    if data.get("revoked_at") is not None:
        state = "invalid"
    elif data.get("claimed_at") is not None:
        state = "consumed"
    elif expires_at <= now:
        state = "expired"
    else:
        state = "active"

    expires_in_days = max(int((expires_at - now).total_seconds() // 86400), 0)
    trainee_first = (
        (data["trainee_display_name"] or "").split()[0]
        if data["trainee_display_name"]
        else None
    )
    coach_clean = (
        (data["coach_display_name"] or "").replace("Coach ", "").strip() or None
    )

    return InvitePublicOut(
        token=token,
        workspace_name=data["workspace_name"],
        workspace_logo_url=data.get("logo_url"),
        brand_color=data.get("brand_color"),
        coach_display_name=coach_clean,
        trainee_first_name=trainee_first,
        primary_locale=data.get("primary_locale") or "en",
        expires_in_days=expires_in_days,
        state=state,
    )


# ── POST /invites/{token}/claim ──────────────────────────────────


@invites_router.post("/{token}/claim", response_model=TokenPair)
@audit_action(
    "invite.claimed",
    entity_type="invite",
    extract=lambda r, kw: {"token": kw.get("token"), "role": r.user.role},
)
async def claim_invite_endpoint(
    token: str,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    redis: Annotated[Redis, Depends(get_redis)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TokenPair:
    try:
        result = await claim_invite(token=token, user_id=user_id)
    except InviteNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found."
        )
    except InviteAlreadyClaimedError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This invite has already been claimed.",
        )
    except InviteExpiredError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This invite has expired.",
        )

    workspace_id: UUID = result["workspace_id"]  # type: ignore[assignment]
    role: str = result["role"]  # type: ignore[assignment]

    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists."
        )

    # Mint a token pair scoped to the newly-claimed workspace.  Reuses the
    # same redis registry so refresh rotation keeps working.
    await set_user_context(db, user_id)
    actual_role = await get_role_in_workspace(db, user_id, workspace_id) or role
    tokens = await issue_and_register_token_pair(
        user_id=user_id, workspace_id=workspace_id, redis=redis
    )
    await db.commit()

    return TokenPair(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        user=UserOut(
            id=str(user.id),
            email=user.email,
            display_name=user.display_name,
            preferred_locale=user.preferred_locale,
            is_minor=user.is_minor,
            current_workspace_id=str(workspace_id),
            role=actual_role,
            is_platform_admin=user.is_platform_admin,
        ),
    )


# ── POST /invites/{token}/signup ─────────────────────────────────


class InviteSignupIn(BaseModel):
    """New-trainee signup that consumes an invite atomically. No Google /
    magic-link round-trip: trainee picks email + password from the invite
    landing and lands straight in their workspace."""

    display_name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=1024)


@invites_router.post(
    "/{token}/signup",
    response_model=TokenPair,
    status_code=status.HTTP_201_CREATED,
)
@audit_action(
    "invite.signed_up",
    entity_type="invite",
    extract=lambda r, kw: {"token": kw.get("token")},
)
async def signup_via_invite(
    token: str,
    body: InviteSignupIn,
    redis: Annotated[Redis, Depends(get_redis)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TokenPair:
    # Validate the invite up-front so we don't create an orphan user when the
    # token is bad. The claim itself re-checks under FOR UPDATE, so a racing
    # claim still fails cleanly.
    data = await fetch_invite_public(token)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found."
        )
    now = datetime.now(UTC)
    if not _is_active(data, now):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This invite has expired or has already been used.",
        )

    email = body.email.lower().strip()
    existing = (
        await db.execute(select(User.id).where(User.email == email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Sign in instead.",
        )

    try:
        password_hash = hash_password(body.password)
    except WeakPasswordError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e

    locale = (data.get("primary_locale") or "id") if isinstance(data, dict) else "id"
    user = User(
        email=email,
        display_name=body.display_name.strip(),
        password_hash=password_hash,
        preferred_locale=locale,
    )
    db.add(user)
    await db.flush()
    await db.commit()  # Persist user before the asyncpg-based claim runs.

    try:
        result = await claim_invite(token=token, user_id=user.id)
    except InviteNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found."
        ) from e
    except InviteAlreadyClaimedError as e:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This invite has already been claimed.",
        ) from e
    except InviteExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This invite has expired.",
        ) from e

    workspace_id: UUID = result["workspace_id"]  # type: ignore[assignment]
    role: str = result["role"]  # type: ignore[assignment]

    await set_user_context(db, user.id)
    actual_role = await get_role_in_workspace(db, user.id, workspace_id) or role
    await touch_last_seen(db, user)
    tokens = await issue_and_register_token_pair(
        user_id=user.id, workspace_id=workspace_id, redis=redis
    )
    await db.commit()

    return TokenPair(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        user=UserOut(
            id=str(user.id),
            email=user.email,
            display_name=user.display_name,
            preferred_locale=user.preferred_locale,
            is_minor=user.is_minor,
            current_workspace_id=str(workspace_id),
            role=actual_role,
            is_platform_admin=user.is_platform_admin,
        ),
    )


# ── GET /invites/pending ─────────────────────────────────────────


class PendingInviteOut(BaseModel):
    """Authenticated trainee's view of an incoming invite that was matched to
    them via phone — they decide whether to accept (claim) or decline."""

    token: str
    workspace_name: str
    workspace_logo_url: str | None
    brand_color: str | None
    coach_display_name: str | None
    role: str  # 'trainee', usually
    expires_at: datetime


class PendingInvitesListOut(BaseModel):
    invites: list[PendingInviteOut]


@invites_router.get("/pending", response_model=PendingInvitesListOut)
async def list_pending_invites(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> PendingInvitesListOut:
    """Pending invites where ``invited_user_id`` was pre-bound to the current
    user (typically via a phone match at coach-side trainee creation). Drives
    the in-app accept/decline banner on the trainee home.

    Runs against the superuser DSN (RLS-bypass) because the authorization is
    ``invited_user_id = :uid`` — the invites can live in workspaces the user
    hasn't joined yet, which is exactly the point of the banner.
    """
    import asyncpg as _asyncpg

    from src.invites.service import _superuser_dsn

    conn = await _asyncpg.connect(_superuser_dsn())
    try:
        rows = await conn.fetch(
            """
            SELECT i.invite_code, i.role, i.expires_at,
                   w.name AS workspace_name,
                   w.logo_url, w.brand_color,
                   u.display_name AS coach_display_name
            FROM invites i
            JOIN workspaces w ON w.id = i.workspace_id
            LEFT JOIN users u ON u.id = i.invited_by_id
            WHERE i.invited_user_id = $1
              AND i.claimed_at IS NULL
              AND i.revoked_at IS NULL
              AND i.expires_at > NOW()
            ORDER BY i.created_at DESC
            """,
            user_id,
        )
    finally:
        await conn.close()

    return PendingInvitesListOut(
        invites=[
            PendingInviteOut(
                token=r["invite_code"],
                workspace_name=r["workspace_name"],
                workspace_logo_url=r["logo_url"],
                brand_color=r["brand_color"],
                coach_display_name=(
                    (r["coach_display_name"] or "").replace("Coach ", "").strip()
                    or None
                ),
                role=r["role"],
                expires_at=r["expires_at"],
            )
            for r in rows
        ]
    )


# ── POST /invites/{token}/decline ─────────────────────────────────


@invites_router.post(
    "/{token}/decline",
    status_code=status.HTTP_204_NO_CONTENT,
)
@audit_action(
    "invite.declined",
    entity_type="invite",
    extract=lambda r, kw: {"token": kw.get("token")},
)
async def decline_invite(
    token: str,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> None:
    """Mark a pending invite revoked from the trainee side.

    Authorization: only the user the invite is bound to (``invited_user_id``)
    can decline it.  Already-claimed / already-revoked invites yield 410 so
    the FE can refresh the banner.

    Uses the superuser DSN (RLS-bypass) for the same reason as
    /invites/pending — the invite may belong to a workspace the user hasn't
    joined; ``invited_user_id`` is the authorization gate.
    """
    import asyncpg as _asyncpg

    from src.invites.service import _superuser_dsn

    conn = await _asyncpg.connect(_superuser_dsn())
    try:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                SELECT id, invited_user_id, claimed_at, revoked_at
                FROM invites
                WHERE invite_code = $1
                FOR UPDATE
                """,
                token,
            )
            if row is None or row["invited_user_id"] != user_id:
                # Don't reveal whether the invite exists for someone else.
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Invite not found.",
                )
            if row["claimed_at"] is not None or row["revoked_at"] is not None:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="This invite is no longer active.",
                )
            await conn.execute(
                "UPDATE invites SET revoked_at = NOW() WHERE id = $1",
                row["id"],
            )
    finally:
        await conn.close()


# Silence "imported but unused" warnings for symbols only referenced inside the
# template's f-strings (timezone) — kept here so future-me can find them.
_ = timezone
