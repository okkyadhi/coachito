"""Auth endpoints: Google id_token verify, magic-link request/consume, refresh."""

import asyncio
from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.models.user import User
from src.db.session import get_session
from src.deps import get_current_user_id, get_redis, get_refresh_claims
from src.middleware.rls import set_user_context

from .email import (
    send_magic_link_email,
    send_password_reset_email,
    send_welcome_email,
)
from .google import verify_google_id_token
from .jwt import TokenPairOut
from .magic import (
    consume_magic_token,
    consume_password_reset_token,
    generate_token,
    revoke_and_check_refresh_jti,
    store_magic_token,
    store_password_reset_token,
)
from .password import (
    RateLimitedError,
    WeakPasswordError,
    check_rate_limit,
    clear_attempts,
    hash_password,
    needs_rehash,
    record_failure,
    verify_password,
)
from pydantic import BaseModel, EmailStr

from .schemas import (
    GoogleSignInIn,
    MagicLinkRequestIn,
    MagicLinkRequestOut,
    PasswordForgotIn,
    PasswordForgotOut,
    PasswordLoginIn,
    PasswordResetIn,
    PasswordSetIn,
    SignupClubIn,
    SignupCoachIn,
    SignupOut,
    TokenPair,
    UserOut,
)
from .service import (
    find_or_create_user_by_email,
    find_or_create_user_by_google,
    get_primary_workspace_id,
    get_role_in_workspace,
    issue_and_register_token_pair,
    touch_last_seen,
)
from src.db.models.sport import Sport
from src.workspaces.service import create_workspace_with_owner

log = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["auth"])


def _build_response(
    user: User,
    workspace_id: UUID | None,
    tokens: TokenPairOut,
    role: str | None = None,
) -> TokenPair:
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
            current_workspace_id=str(workspace_id) if workspace_id else None,
            role=role,
            is_platform_admin=user.is_platform_admin,
        ),
    )


async def _issue(user: User, workspace_id: UUID | None, redis: Redis) -> TokenPairOut:
    return await issue_and_register_token_pair(
        user_id=user.id, workspace_id=workspace_id, redis=redis
    )


# ── POST /auth/magic/request ─────────────────────────────────────


@router.post(
    "/magic/request",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=MagicLinkRequestOut,
)
async def request_magic_link(
    body: MagicLinkRequestIn,
    redis: Annotated[Redis, Depends(get_redis)],
) -> MagicLinkRequestOut:
    token = generate_token()
    await store_magic_token(redis, token, body.email)
    link = f"{settings.web_url}/auth/magic?token={token}"
    try:
        await send_magic_link_email(email=body.email, link=link)
    except Exception:
        log.exception("magic_link_email_send_failed", email=body.email)
        # Don't expose failure detail — still return 202 so we don't leak which
        # addresses are deliverable. Operators inspect logs / DLQ.
    return MagicLinkRequestOut()


# ── GET /auth/magic/consume?token=... ────────────────────────────


@router.get("/magic/consume", response_model=TokenPair)
async def consume_magic_link(
    token: str,
    redis: Annotated[Redis, Depends(get_redis)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TokenPair:
    email = await consume_magic_token(redis, token)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This sign-in link has expired or has already been used.",
        )
    user = await find_or_create_user_by_email(db, email)
    # Set RLS context so the membership lookup sees the user's own rows.
    await set_user_context(db, user.id)
    workspace_id = await get_primary_workspace_id(db, user.id)
    role = await get_role_in_workspace(db, user.id, workspace_id)
    await touch_last_seen(db, user)
    tokens = await _issue(user, workspace_id, redis)
    await db.commit()
    return _build_response(user, workspace_id, tokens, role)


# ── POST /auth/google ────────────────────────────────────────────


@router.post("/google", response_model=TokenPair)
async def signin_with_google(
    body: GoogleSignInIn,
    redis: Annotated[Redis, Depends(get_redis)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TokenPair:
    if not settings.enable_google_oauth:
        # Return 404 (not 403) so probing doesn't reveal the endpoint exists.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found.",
        )
    try:
        claims = verify_google_id_token(body.id_token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from e

    email = claims.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Google token missing email claim."
        )
    user = await find_or_create_user_by_google(
        db,
        google_sub=claims["sub"],
        email=email,
        display_name=claims.get("name") or email,
    )
    await set_user_context(db, user.id)
    workspace_id = await get_primary_workspace_id(db, user.id)
    role = await get_role_in_workspace(db, user.id, workspace_id)
    await touch_last_seen(db, user)
    tokens = await _issue(user, workspace_id, redis)
    await db.commit()
    return _build_response(user, workspace_id, tokens, role)


# ── POST /auth/refresh ───────────────────────────────────────────


@router.post("/refresh", response_model=TokenPair)
async def refresh_tokens(
    claims: Annotated[dict[str, Any], Depends(get_refresh_claims)],
    redis: Annotated[Redis, Depends(get_redis)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TokenPair:
    user_id_str = claims["sub"]
    old_jti = claims["jti"]

    # Atomic revoke. If the jti wasn't registered (or was already used), bail.
    valid = await revoke_and_check_refresh_jti(redis, user_id_str, old_jti)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked or already used.",
        )

    user_id = UUID(user_id_str)
    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists."
        )

    await set_user_context(db, user_id)
    workspace_id = await get_primary_workspace_id(db, user_id)
    role = await get_role_in_workspace(db, user_id, workspace_id)
    tokens = await _issue(user, workspace_id, redis)
    await db.commit()
    return _build_response(user, workspace_id, tokens, role)


# ── POST /auth/password/login ────────────────────────────────────


@router.post("/password/login", response_model=TokenPair)
async def password_login(
    body: PasswordLoginIn,
    redis: Annotated[Redis, Depends(get_redis)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TokenPair:
    email = body.email.lower().strip()

    try:
        await check_rate_limit(redis, email=email)
    except RateLimitedError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Try again later.",
        ) from e

    user = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()

    # Always run the hasher (even on missing user) so timing doesn't leak
    # account existence.
    if not verify_password(body.password, user.password_hash if user else None):
        await record_failure(redis, email=email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    assert user is not None  # narrowed by verify_password having matched

    await clear_attempts(redis, email=email)
    if user.password_hash and needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)

    await set_user_context(db, user.id)
    workspace_id = await get_primary_workspace_id(db, user.id)
    role = await get_role_in_workspace(db, user.id, workspace_id)
    await touch_last_seen(db, user)
    tokens = await _issue(user, workspace_id, redis)
    await db.commit()
    return _build_response(user, workspace_id, tokens, role)


# ── POST /auth/password/set ──────────────────────────────────────


@router.post("/password/set", status_code=status.HTTP_204_NO_CONTENT)
async def set_password(
    body: PasswordSetIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists."
        )

    # Changing an existing password requires the current one — guards
    # against a stolen access token being used to lock the real owner out.
    if user.password_hash is not None:
        if not body.current_password or not verify_password(
            body.current_password, user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Current password is incorrect.",
            )

    try:
        user.password_hash = hash_password(body.new_password)
    except WeakPasswordError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e

    await db.commit()


# ── POST /auth/dev-login (non-production only) ────────────────────


class DevLoginIn(BaseModel):
    """Email of an existing seeded user + (optional) workspace slug.

    If ``workspace_slug`` is omitted we use the user's primary workspace
    (most recently joined).  This endpoint exists solely to keep curl/cypress
    loops ergonomic in dev — no magic-link round trip through Mailpit.
    """

    email: EmailStr
    workspace_slug: str | None = None


@router.post("/dev-login", response_model=TokenPair)
async def dev_login(
    body: DevLoginIn,
    redis: Annotated[Redis, Depends(get_redis)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TokenPair:
    """Mint a JWT directly for a seeded user.  Disabled in production.

    Looks up the user by email (must exist) and chooses a workspace.  Returns
    the same TokenPair shape as the other auth endpoints so curl flows can
    grab ``.access_token`` and use it directly as ``Authorization: Bearer``.
    """
    if settings.environment == "production":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found.",
        )

    email = body.email.lower().strip()
    user = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No seeded user with email {email}.  Run scripts/seed.py first.",
        )

    await set_user_context(db, user.id)

    workspace_id: UUID | None
    if body.workspace_slug is not None:
        # Look up by slug — bypasses the "most-recent membership" heuristic
        # so tests can pin to a specific workspace.
        from src.db.models.workspace import Workspace

        wid = (
            await db.execute(
                select(Workspace.id).where(Workspace.slug == body.workspace_slug)
            )
        ).scalar_one_or_none()
        if wid is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No workspace with slug '{body.workspace_slug}'.",
            )
        workspace_id = wid
    else:
        workspace_id = await get_primary_workspace_id(db, user.id)

    role = await get_role_in_workspace(db, user.id, workspace_id)
    await touch_last_seen(db, user)
    tokens = await _issue(user, workspace_id, redis)
    await db.commit()
    return _build_response(user, workspace_id, tokens, role)


# ── Self-signup: coach individu + admin club ─────────────────────


async def _resolve_sport_ids(db: AsyncSession, codes: list[str]) -> list[UUID]:
    """Map sport codes ("padel" / "tennis") to ids, preserving order. The
    first id in the returned list seeds the legacy workspaces.sport_id."""
    ids: list[UUID] = []
    for code in codes:
        sid = (
            await db.execute(select(Sport.id).where(Sport.code == code))
        ).scalar_one_or_none()
        if sid is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown sport '{code}'.",
            )
        ids.append(sid)
    return ids


def _signup_response(
    user: User,
    workspace_id: UUID,
    tokens: TokenPairOut,
    role: str,
    redirect_to: str,
) -> SignupOut:
    return SignupOut(
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
            role=role,
            is_platform_admin=user.is_platform_admin,
        ),
        redirect_to=redirect_to,
    )


@router.post(
    "/signup/coach",
    response_model=SignupOut,
    status_code=status.HTTP_201_CREATED,
)
async def signup_coach(
    body: SignupCoachIn,
    redis: Annotated[Redis, Depends(get_redis)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SignupOut:
    """Solo coach self-signup → user + Personal workspace + owner/coach
    membership. Returns the same TokenPair shape as /auth/password/login plus
    a redirect_to hint."""
    email = body.email.lower().strip()

    # Email-already-registered → 409 with a generic message; doesn't leak
    # whether a Google-only or magic-link user exists separately.
    existing = (
        await db.execute(select(User.id).where(User.email == email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    try:
        password_hash = hash_password(body.password)
    except WeakPasswordError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e

    user = User(
        email=email,
        display_name=body.display_name.strip(),
        password_hash=password_hash,
    )
    db.add(user)
    await db.flush()

    await set_user_context(db, user.id)

    sport_ids = await _resolve_sport_ids(db, [body.sport_code])
    first_name = user.display_name.split()[0] if user.display_name else "My"
    workspace = await create_workspace_with_owner(
        db,
        owner_user_id=user.id,
        type_="personal",
        name=f"{first_name}'s coaching",
        primary_locale=user.preferred_locale,
        sport_ids=sport_ids,
        plan="solo_coach",
        trial_days=settings.signup_trial_days,
    )

    await touch_last_seen(db, user)
    tokens = await _issue(user, workspace.id, redis)
    await db.commit()

    # Fire-and-forget — don't block the signup response on SMTP.
    asyncio.create_task(
        send_welcome_email(
            email=user.email or email,
            display_name=user.display_name,
            role="coach",
            workspace_name=workspace.name,
        )
    )

    return _signup_response(user, workspace.id, tokens, "coach", "/today")


@router.post(
    "/signup/club",
    response_model=SignupOut,
    status_code=status.HTTP_201_CREATED,
)
async def signup_club(
    body: SignupClubIn,
    redis: Annotated[Redis, Depends(get_redis)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SignupOut:
    """Club admin self-signup → user + Club workspace (club_pro trial) +
    owner/club_admin membership across all chosen sports."""
    email = body.email.lower().strip()

    existing = (
        await db.execute(select(User.id).where(User.email == email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    try:
        password_hash = hash_password(body.password)
    except WeakPasswordError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e

    user = User(
        email=email,
        display_name=body.display_name.strip(),
        password_hash=password_hash,
    )
    db.add(user)
    await db.flush()

    await set_user_context(db, user.id)

    # De-dupe while preserving order; pydantic already validated min/max
    # length, so we know there's at least one code.
    unique_codes: list[str] = []
    for code in body.sport_codes:
        if code not in unique_codes:
            unique_codes.append(code)
    sport_ids = await _resolve_sport_ids(db, unique_codes)

    workspace = await create_workspace_with_owner(
        db,
        owner_user_id=user.id,
        type_="club",
        name=body.club_name.strip(),
        primary_locale=user.preferred_locale,
        city=body.city.strip() if body.city else None,
        sport_ids=sport_ids,
        plan="club_pro",
        trial_days=settings.signup_trial_days,
    )

    await touch_last_seen(db, user)
    tokens = await _issue(user, workspace.id, redis)
    await db.commit()

    asyncio.create_task(
        send_welcome_email(
            email=user.email or email,
            display_name=user.display_name,
            role="club_admin",
            workspace_name=workspace.name,
        )
    )

    return _signup_response(
        user, workspace.id, tokens, "club_admin", "/settings/coaches"
    )


# ── Forgot / reset password ──────────────────────────────────────


@router.post(
    "/password/forgot",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PasswordForgotOut,
)
async def request_password_reset(
    body: PasswordForgotIn,
    redis: Annotated[Redis, Depends(get_redis)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> PasswordForgotOut:
    """Issue a one-shot reset token if the email maps to a real user.

    Always 202 — never reveal whether the email exists (mirrors magic-link)."""
    email = body.email.lower().strip()

    user_exists = (
        await db.execute(select(User.id).where(User.email == email))
    ).scalar_one_or_none()

    if user_exists is not None:
        token = generate_token()
        await store_password_reset_token(redis, token, email)
        link = f"{settings.web_url}/auth/reset?token={token}"
        try:
            await send_password_reset_email(email=email, link=link)
        except Exception:
            log.exception("password_reset_email_send_failed", email=email)
            # Still return 202 — don't expose delivery failure to caller.
    else:
        log.info("password_reset_unknown_email", email=email)

    return PasswordForgotOut()


@router.post("/password/reset", response_model=TokenPair)
async def reset_password(
    body: PasswordResetIn,
    redis: Annotated[Redis, Depends(get_redis)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TokenPair:
    """Consume reset token + set new password + auto-login.

    Same TokenPair shape as ``/auth/password/login`` so the FE can drop the
    user straight into the dashboard after a successful reset."""
    email = await consume_password_reset_token(redis, body.token)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This reset link has expired or has already been used.",
        )

    user = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if user is None:
        # Token resolved to an email but the account is gone — treat as 410
        # rather than 404 so we don't expose enumeration through this path.
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This reset link is no longer valid.",
        )

    try:
        user.password_hash = hash_password(body.new_password)
    except WeakPasswordError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e

    await set_user_context(db, user.id)
    workspace_id = await get_primary_workspace_id(db, user.id)
    role = await get_role_in_workspace(db, user.id, workspace_id)
    await touch_last_seen(db, user)
    tokens = await _issue(user, workspace_id, redis)
    await db.commit()
    return _build_response(user, workspace_id, tokens, role)
