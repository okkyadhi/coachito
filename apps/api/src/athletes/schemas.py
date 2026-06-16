from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class TierBrief(BaseModel):
    id: str
    code: str
    name_game_en: str
    name_game_id: str


class AthleteOut(BaseModel):
    id: str
    display_name: str
    date_of_birth: date | None
    is_minor: bool
    joined_at: date
    last_assessed_at: datetime | None
    current_tier: TierBrief | None
    archived_at: datetime | None
    created_at: datetime


class AthleteListOut(BaseModel):
    athletes: list[AthleteOut]
    next_cursor: str | None = None


# ── Inbound ──────────────────────────────────────────────────────


import re

E164_RE = re.compile(r"^\+[1-9]\d{1,14}$")


class TraineeCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone_e164: str = Field(min_length=2, max_length=20)
    date_of_birth: date | None = None
    parent_phone_e164: str | None = None

    @field_validator("phone_e164")
    @classmethod
    def _validate_phone(cls, v: str) -> str:
        cleaned = v.replace(" ", "")
        if not E164_RE.match(cleaned):
            raise ValueError("phone_e164 must be in E.164 format (e.g. +628123456789)")
        return cleaned

    @field_validator("parent_phone_e164")
    @classmethod
    def _validate_parent_phone(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        cleaned = v.replace(" ", "")
        if not E164_RE.match(cleaned):
            raise ValueError("parent_phone_e164 must be in E.164 format")
        return cleaned


class TraineeUpdateIn(BaseModel):
    """PATCH body — all fields optional."""

    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    date_of_birth: date | None = None
    notes: str | None = None


# ── Outbound ─────────────────────────────────────────────────────


class InviteBrief(BaseModel):
    id: str
    code: str
    phone_e164: str | None
    expires_at: datetime
    landing_url: str


class LinkedUserBrief(BaseModel):
    """Surfaced when ``invites.invited_user_id`` was auto-resolved via a
    phone match — the coach FE shows "linked to existing account" instead of
    the WhatsApp share button."""

    id: str
    email: str | None
    display_name: str


class TraineeCreateOut(BaseModel):
    trainee: AthleteOut
    invite: InviteBrief
    # Present iff phone matched a prior claim. ``None`` keeps the existing
    # WhatsApp-share path as the default.
    linked_user: LinkedUserBrief | None = None
