"""Wire shapes for /skills/me/* endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

CategoryCode = Literal["technical", "tactical", "physical", "mental"]


class CategoryScoreOut(BaseModel):
    code: CategoryCode
    label_en: str
    label_id: str
    average: float | None  # null when no skills assessed in this category
    assessed_count: int
    total_count: int


class OverallProgressOut(BaseModel):
    average: float | None
    assessed_count: int
    total_count: int
    last_assessed_at: datetime | None


class TierBriefOut(BaseModel):
    code: str
    label_en: str
    label_id: str


class TierProgressOut(BaseModel):
    current: TierBriefOut | None
    next: TierBriefOut | None
    blockers_remaining_count: int
    progress_to_next: float  # 0..1


class RecentGainOut(BaseModel):
    skill_code: str
    label_en: str
    label_id: str
    # JSON keeps the ``from_level`` / ``to_level`` naming (snake_case is the
    # API convention).  The spec's ``from``/``to`` is shorthand; the FE maps
    # the snake fields into camelCase.
    from_level: int
    to_level: int
    at: datetime


FocusReason = Literal[
    "blocker_for_next_tier",
    "oldest_unassessed",
    "lowest_score",
]


class FocusSuggestionOut(BaseModel):
    skill_code: str
    label_en: str
    label_id: str
    current_level: int | None
    required_level: int | None
    category: CategoryCode
    latest_note_en: str | None
    latest_note_id: str | None
    reason: FocusReason


class SkillsOverviewOut(BaseModel):
    categories: list[CategoryScoreOut]
    overall: OverallProgressOut
    tier: TierProgressOut | None
    recent_gains: list[RecentGainOut]
    focus_suggestion: FocusSuggestionOut | None
    updated_at: datetime | None


class SkillScoreOut(BaseModel):
    code: str
    label_en: str
    label_id: str
    label_short_en: str | None
    label_short_id: str | None
    latest_score: int | None
    latest_descriptor_en: str | None
    latest_descriptor_id: str | None
    last_assessed_at: datetime | None


class CategoryBreakdownOut(BaseModel):
    category: CategoryCode
    skills: list[SkillScoreOut]
    updated_at: datetime | None


class TierBriefLiteOut(BaseModel):
    code: str
    label_en: str
    label_id: str


class TierBlockerEntryOut(BaseModel):
    skill_code: str
    required_level: int
    current_level: int


class CategoryBlockersOut(BaseModel):
    next_tier: TierBriefLiteOut | None
    blockers_in_category: list[TierBlockerEntryOut]
    blockers_total_count: int
