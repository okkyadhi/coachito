"""Pydantic models for the /admin/* endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

WorkspacePlan = Literal["free_trial", "solo_coach", "club_starter", "club_pro"]
WorkspaceType = Literal["club", "personal"]


class AdminWorkspaceRow(BaseModel):
    """One row in the admin workspaces table.  Joins owner email + counts
    for at-a-glance triage; the detail page fills in the rest."""

    id: str
    name: str
    type: WorkspaceType
    plan: WorkspacePlan
    primary_locale: str
    city: str | None
    owner_user_id: str
    owner_email: str | None
    owner_display_name: str
    trial_ends_at: datetime | None
    paid_until: datetime | None
    archived_at: datetime | None
    created_at: datetime
    coach_count: int
    trainee_count: int
    last_session_at: datetime | None


class AdminWorkspacesListOut(BaseModel):
    total: int
    workspaces: list[AdminWorkspaceRow]


class AdminWorkspaceDetailOut(AdminWorkspaceRow):
    brand_color: str | None
    logo_url: str | None
    tier_style: str
    active_trainee_quota: int
    sport_id: str | None
    updated_at: datetime
    # Derived: which bucket this workspace is in right now.
    billing_status: Literal["trial", "paid", "lapsed", "archived", "unknown"]


class AdminWorkspacePatchIn(BaseModel):
    """All fields optional — PATCH semantics."""

    model_config = ConfigDict(extra="forbid")

    plan: WorkspacePlan | None = None
    trial_ends_at: datetime | None = None
    paid_until: datetime | None = None
    active_trainee_quota: int | None = Field(default=None, ge=0, le=100000)
    # Soft toggle: setting True archives (sets archived_at = NOW()),
    # setting False clears archived_at.  Omit to leave unchanged.
    archived: bool | None = None


class AdminUserRow(BaseModel):
    id: str
    email: str | None
    display_name: str
    preferred_locale: str
    created_at: datetime
    last_seen_at: datetime | None
    is_platform_admin: bool
    workspace_count: int
    # Compact summary: "Senayan Padel (club_admin), My coaching (coach)"
    workspace_summary: str


class AdminUsersListOut(BaseModel):
    total: int
    users: list[AdminUserRow]


class AdminResetPasswordIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_password: str = Field(min_length=8, max_length=1024)


class AdminResetPasswordOut(BaseModel):
    user_id: str
    email: EmailStr | None


class AdminCoachMember(BaseModel):
    id: str
    display_name: str
    email: str | None
    role: str
    distinct_trainee_count: int
    session_count: int


class AdminTraineeMember(BaseModel):
    id: str
    display_name: str
    email: str | None
    tier_name: str | None
    last_session_at: datetime | None


class AdminWorkspaceMembersOut(BaseModel):
    coaches: list[AdminCoachMember]
    trainees: list[AdminTraineeMember]


class AdminStatsOut(BaseModel):
    workspaces_total: int
    workspaces_by_plan: dict[str, int]
    trials_expiring_soon: int
    workspaces_new_this_month: int
    users_total: int
    users_new_this_month: int
    trainees_total: int
    upgrade_requests_pending: int


class AdminToggleAdminOut(BaseModel):
    user_id: str
    is_platform_admin: bool
