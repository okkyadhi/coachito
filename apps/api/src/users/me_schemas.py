"""Schemas for /users/me — trainee self-service profile."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SummaryStyle = Literal["encouraging", "direct", "warm"]


class NotificationsOut(BaseModel):
    session_reminders: bool
    monthly_report: bool


class ParentLinkOut(BaseModel):
    id: str
    display_name: str


class MeOut(BaseModel):
    id: str
    email: str | None
    display_name: str
    avatar_url: str | None
    preferred_locale: Literal["en", "id"]
    is_minor: bool
    date_of_birth: date | None
    primary_guardian: ParentLinkOut | None
    notifications: NotificationsOut
    summary_style: SummaryStyle


class NotificationsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_reminders: bool | None = None
    monthly_report: bool | None = None


class MePatch(BaseModel):
    """Partial patch — only writable fields. DOB / parent link are
    admin-owned; passing them returns 422."""

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    avatar_url: str | None = None
    preferred_locale: Literal["en", "id"] | None = None
    notifications: NotificationsPatch | None = None
    summary_style: SummaryStyle | None = None
