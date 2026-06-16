from typing import Literal

from pydantic import BaseModel, EmailStr, Field


# ── Inbound ──────────────────────────────────────────────────────


class GoogleSignInIn(BaseModel):
    id_token: str = Field(min_length=1)


class MagicLinkRequestIn(BaseModel):
    email: EmailStr


class PasswordLoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)


class PasswordSetIn(BaseModel):
    """Authenticated set-or-change.  ``current_password`` is required when
    the user already has one (prevents drive-by takeover via a stolen
    session); first-time set lets it be None."""

    current_password: str | None = Field(default=None, max_length=1024)
    new_password: str = Field(min_length=8, max_length=1024)


# ── Outbound ─────────────────────────────────────────────────────


class UserOut(BaseModel):
    id: str
    email: str | None
    display_name: str
    preferred_locale: str
    is_minor: bool
    current_workspace_id: str | None = None
    # Role in the current workspace ("coach" / "head_coach" / "club_admin" /
    # "trainee" / "parent").  None when the user has no membership yet
    # (e.g. just signed in, hasn't created a workspace).
    role: str | None = None
    # Cross-tenant platform-admin flag.  Surfaced to the FE so the admin
    # shell can gate.  Default false; flipped by DBA, never via signup.
    is_platform_admin: bool = False


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class MagicLinkRequestOut(BaseModel):
    status: str = "sent"


# ── Self-signup ──────────────────────────────────────────────────


SportCode = Literal["padel", "tennis"]


class SignupCoachIn(BaseModel):
    """Solo coach self-signup. Auto-creates a Personal workspace named
    "<First name>'s coaching" with the chosen sport enabled."""

    display_name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=1024)
    sport_code: SportCode = "padel"


class SignupClubIn(BaseModel):
    """Club admin self-signup. Auto-creates a Club workspace under the
    admin's ownership with one or more sports enabled."""

    display_name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=1024)
    club_name: str = Field(min_length=2, max_length=120)
    city: str | None = Field(default=None, max_length=100)
    sport_codes: list[SportCode] = Field(min_length=1, max_length=2)


class SignupOut(BaseModel):
    """Same shape as ``TokenPair`` plus a ``redirect_to`` hint so the FE can
    drop the user on the right empty-state screen after signup."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
    redirect_to: str


# ── Forgot / reset password ──────────────────────────────────────


class PasswordForgotIn(BaseModel):
    email: EmailStr


class PasswordForgotOut(BaseModel):
    """Always returned, regardless of whether the email exists, to avoid
    leaking account existence."""

    status: str = "sent"


class PasswordResetIn(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=1024)
