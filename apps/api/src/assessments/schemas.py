"""Pydantic schemas for assessment endpoints (v2)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.athletes.schemas import TierBrief

SessionFocus = Literal[
    "drilling",
    "match_play",
    "conditioning",
    "mental_training",
    "technique_focus",
    "general",
]

AssessmentStatus = Literal["draft", "published", "edited", "withdrawn"]


# ── In schemas ──────────────────────────────────────────────────


class AssessmentScoreIn(BaseModel):
    skill_id: UUID
    level: int = Field(ge=1, le=5)
    note: str | None = Field(default=None, max_length=2000)


class AssessmentDraftIn(BaseModel):
    """Save-or-update a draft assessment.

    Idempotent by ``session_id`` — re-sending the same body to upsert is fine.
    ``session_id`` may be omitted; the server will then auto-create a session
    with the optional ``session_*`` fields (mirrors the v1 "quick session"
    flow so a coach can score without leaving the trainee screen).
    """

    athlete_id: UUID
    # Optional sport context — defaults to the workspace's single active sport.
    sport_id: UUID | None = None
    session_id: UUID | None = None
    session_scheduled_at: datetime | None = None
    session_duration_min: int | None = Field(default=None, ge=5, le=600)
    session_court: str | None = Field(default=None, max_length=50)
    session_focus: SessionFocus | None = None
    summary: str | None = Field(default=None, max_length=4000)
    internal_notes: str | None = Field(default=None, max_length=4000)
    scores: list[AssessmentScoreIn] = Field(default_factory=list, max_length=50)


class AssessmentEditIn(BaseModel):
    """PATCH a published/edited assessment.  Only the fields the FE sends are
    diffed against the current state for audit + tier recalc."""

    model_config = ConfigDict(extra="forbid")

    summary: str | None = Field(default=None, max_length=4000)
    internal_notes: str | None = Field(default=None, max_length=4000)
    scores: list[AssessmentScoreIn] | None = Field(default=None, max_length=50)
    reason: str | None = Field(default=None, max_length=500)


class PublishIn(BaseModel):
    """Body for POST /assessments/{id}/publish.

    ``force_empty`` lets the coach publish an observation-only session
    (no scores, no summary) — rare but supported per §4 of the spec.
    """

    model_config = ConfigDict(extra="forbid")

    force_empty: bool = False


# ── Out schemas ─────────────────────────────────────────────────


class ScoreOut(BaseModel):
    skill_id: str
    level: int
    note: str | None
    updated_at: datetime


class CategoryAverageOut(BaseModel):
    category: str
    average: float
    skills_rated: int


class SkillBriefOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    code: str
    category: str
    name_en: str
    name_id: str
    display_order: int


class GainOut(BaseModel):
    skill: SkillBriefOut
    from_level: int | None
    to_level: int
    recorded_at: datetime


class TierSliceOut(BaseModel):
    """Tier info returned after publish/edit (so the FE can splice into the
    trainee-profile cache).  None when the assessment is still a draft."""

    current_tier: TierBrief | None
    next_tier: TierBrief | None
    met_count: int
    total_requirements: int
    category_averages: list[CategoryAverageOut]
    recent_gains: list[GainOut]


class AssessmentOut(BaseModel):
    id: str
    workspace_id: str
    session_id: str
    athlete_id: str
    coach_id: str
    coach_display_name: str | None = None
    status: AssessmentStatus
    summary: str | None
    internal_notes: str | None
    saved_at: datetime
    published_at: datetime | None
    edited_at: datetime | None
    scores: list[ScoreOut]
    # Session metadata so the trainee detail screen doesn't need a second
    # round-trip to render "Wed · 14:00 · Court 2 · Drilling".
    session_scheduled_at: datetime | None = None
    session_duration_min: int | None = None
    session_court: str | None = None
    session_focus: str | None = None
    # Slice present when tier recalc fired (publish / edit only).
    tier: TierSliceOut | None = None
    # Previous tier before this publish — only set on the publish response so
    # the FE can detect "tier-up" and trigger a celebration.
    previous_tier: TierBrief | None = None
    # Trainee read-receipt: first time the linked trainee opened this on FE.
    trainee_viewed_at: datetime | None = None
    # FE shows "12 new feedback" — included on GET, omitted on save replies.
    feedback_count: int | None = None
    unread_feedback_count: int | None = None


class AssessmentEditOut(BaseModel):
    id: str
    edited_by_id: str
    edited_by_display_name: str
    edited_at: datetime
    changes: dict
    reason: str | None
