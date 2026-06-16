"""Pydantic schemas for /sessions endpoints (v2 — session-first)."""

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

SessionStatus = Literal["scheduled", "completed", "cancelled", "no_show"]


class SessionTraineeBrief(BaseModel):
    id: str
    display_name: str
    last_assessed_at: datetime | None
    current_tier: TierBrief | None


class CoachBrief(BaseModel):
    id: str
    display_name: str


class SessionWorkspaceBrief(BaseModel):
    """Workspace context surfaced on every session row — drives the
    Personal-vs-Club badge on the coach Sessions calendar so multi-workspace
    coaches don't need to switch workspaces to see what's where."""

    id: str
    name: str
    type: str  # 'personal' | 'club'
    brand_color: str | None = None


class SessionTodayOut(BaseModel):
    id: str
    scheduled_at: datetime
    duration_min: int
    court: str | None
    focuses: list[str]
    status: str
    sport_id: str | None = None
    coach: CoachBrief | None = None
    trainee: SessionTraineeBrief


# ── New v2 schemas ──────────────────────────────────────────────


class SessionCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    athlete_id: UUID
    # Optional: which sport this session is for.  Omit on single-sport
    # workspaces — the server defaults to the one active sport.
    sport_id: UUID | None = None
    # Admin / head_coach only — assign session to a different coach.
    coach_id: UUID | None = None
    scheduled_at: datetime
    duration_min: int = Field(default=60, ge=5, le=600)
    court: str | None = Field(default=None, max_length=50)
    focuses: list[SessionFocus] = Field(default_factory=list, max_length=4)
    notes: str | None = Field(default=None, max_length=500)


class SessionUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Admin / head_coach only — reassign session to a different coach.
    coach_id: UUID | None = None
    scheduled_at: datetime | None = None
    duration_min: int | None = Field(default=None, ge=5, le=600)
    court: str | None = Field(default=None, max_length=50)
    focuses: list[SessionFocus] | None = Field(default=None, max_length=4)
    notes: str | None = Field(default=None, max_length=500)


FunnelStage = Literal[
    "upcoming", "to_assess", "draft", "published", "cancelled"
]


class SessionOut(BaseModel):
    id: str
    athlete: SessionTraineeBrief
    coach: CoachBrief
    # Optional so existing single-workspace queries that don't join workspaces
    # stay backwards compatible. The cross-workspace endpoints always set it.
    workspace: SessionWorkspaceBrief | None = None
    scheduled_at: datetime
    duration_min: int
    court: str | None
    focuses: list[str]
    status: SessionStatus
    notes: str | None
    completed_at: datetime | None
    has_assessment: bool
    assessment_id: str | None
    assessment_status: str | None  # 'draft' | 'published' | 'edited' | None
    funnel_stage: FunnelStage
    created_at: datetime


class FunnelCountsOut(BaseModel):
    upcoming: int
    to_assess: int
    draft: int
    published: int
    cancelled: int
