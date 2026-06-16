"""Trainee feedback schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SubmitterRole = Literal["trainee", "parent"]


class FeedbackSubmitIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating_overall: int = Field(ge=1, le=5)
    rating_fairness: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)
    is_anonymous: bool = False


class FeedbackEditIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating_overall: int | None = Field(default=None, ge=1, le=5)
    rating_fairness: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)
    is_anonymous: bool | None = None


class FeedbackOut(BaseModel):
    """View as the submitter (full identity), or as the coach (identity
    stripped when anonymous — see the router's anonymizer)."""

    id: str
    assessment_id: str
    submitter_role: SubmitterRole
    submitter_display_name: str | None
    is_anonymous: bool
    rating_overall: int
    rating_fairness: int | None
    comment: str | None
    submitted_at: datetime
    edited_at: datetime | None
    read_at: datetime | None
    can_edit: bool  # within 24h window
    can_withdraw: bool


class FeedbackInboxItem(BaseModel):
    """A row in the coach's feedback inbox."""

    id: str
    assessment_id: str
    athlete_display_name: str | None  # null when anonymous
    submitter_role: SubmitterRole
    is_anonymous: bool
    rating_overall: int
    rating_fairness: int | None
    comment: str | None
    submitted_at: datetime
    read_at: datetime | None
    session_scheduled_at: datetime | None
    session_focus: str | None
