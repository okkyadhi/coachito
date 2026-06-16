from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Allow-list mirrors the FE plan codes the picker actually surfaces.
# `free_trial` isn't in here on purpose — coaches don't "request to
# downgrade to trial."
PlanCode = Literal[
    "solo_coach",
    "solo_coach_unlimited",
    "club_starter",
    "club_pro",
]


class UpgradeRequestCreateIn(BaseModel):
    requested_plan: PlanCode


class UpgradeRequestOut(BaseModel):
    id: str
    workspace_id: str
    workspace_name: str
    requested_plan: str
    requester_user_id: str | None
    requester_email: str | None
    requester_display_name: str | None
    owner_email: str | None
    owner_display_name: str | None
    status: str
    note: str | None
    created_at: datetime
    resolved_at: datetime | None
    resolved_by_user_id: str | None


class UpgradeRequestListOut(BaseModel):
    total: int
    requests: list[UpgradeRequestOut]


class UpgradeRequestPatchIn(BaseModel):
    status: Literal["resolved", "dismissed", "pending"]
    note: str | None = Field(default=None, max_length=2000)
