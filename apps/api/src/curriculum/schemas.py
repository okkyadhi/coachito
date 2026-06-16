"""Pydantic v2 schemas for /curriculum/*."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Skills ──────────────────────────────────────────────────────────


class SkillRowOut(BaseModel):
    """One skill in the admin's curriculum list.

    ``is_override`` tells the FE whether the workspace has a custom toggle
    state for this skill (i.e. an override row exists shadowing the platform
    row).  When ``is_enabled`` matches the platform default and there's no
    override, ``is_override`` is False — useful for a "reset to platform" CTA.

    ``last_changed_at`` is the most recent admin action on this skill within
    the workspace (toggle, descriptor edit) — derived from audit_log.  The
    FE uses it to badge recently-updated skills so coaches notice curriculum
    drift since their last visit.  None means "no admin action recorded
    within the lookback window (7 days)".
    """

    id: str
    code: str
    category: str
    name_en: str
    name_id: str
    description_en: str | None
    description_id: str | None
    display_order: int
    is_enabled: bool
    is_override: bool
    last_changed_at: Optional[datetime] = None


class CurriculumSkillsOut(BaseModel):
    skills: list[SkillRowOut]


class SkillEnabledIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_enabled: bool


class SkillImpactOut(BaseModel):
    """Preflight count shown in the disable-confirmation sheet."""

    trainee_count: int
    assessment_count: int
    in_tier_requirements: bool  # True if any tier currently requires this skill


# ── Tier context (which tiers require this skill, at what level) ────


class TierRequirementOut(BaseModel):
    """One tier requirement entry for the skill detail screen.

    ``tier_name`` is the *effective* name for the workspace's current
    ``tier_style`` (game/skill/custom) — resolved server-side so the FE
    doesn't need to know the workspace setting.
    """

    tier_code: str
    tier_display_order: int
    tier_name: str
    min_level: int


class TierContextOut(BaseModel):
    skill_code: str
    requirements: list[TierRequirementOut]


# ── Tiers ───────────────────────────────────────────────────────────


class TierOut(BaseModel):
    id: str
    code: str
    display_order: int
    name_game_en: str
    name_game_id: str
    name_skill_en: str
    name_skill_id: str
    name_custom_en: str | None
    name_custom_id: str | None
    color_hex: str | None
    icon_name: str | None
    is_override: bool


class CurriculumTiersOut(BaseModel):
    tiers: list[TierOut]


class TierNamesPatch(BaseModel):
    """All optional — only the keys actually sent get applied.

    Game and Skill names are platform-locked at the row level, so the patch
    only allows the *custom* names to vary per workspace.  If a club admin
    wants ``Bronze`` to read ``Beginner`` they should switch ``tier_style``
    on the workspace, not rename the game tier.
    """

    model_config = ConfigDict(extra="forbid")
    name_custom_en: str | None = Field(default=None, min_length=1, max_length=50)
    name_custom_id: str | None = Field(default=None, min_length=1, max_length=50)


# ── Feedback notes ──────────────────────────────────────────────────


class FeedbackNoteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skill_id: str | None = None  # nullable — None = general curriculum feedback
    body: str = Field(min_length=1, max_length=2000)


class FeedbackNoteOut(BaseModel):
    id: str
    author_display_name: str
    skill_code: str | None
    skill_name_en: str | None
    body: str
    created_at: datetime
    read_at: datetime | None


class FeedbackInboxOut(BaseModel):
    notes: list[FeedbackNoteOut]
    unread_count: int
