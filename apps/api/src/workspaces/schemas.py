from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceCreateIn(BaseModel):
    type: Literal["club", "personal"]
    name: str = Field(min_length=1, max_length=120)
    city: str | None = Field(default=None, max_length=100)
    brand_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    primary_locale: Literal["en", "id"] = "id"


class WorkspaceSportOut(BaseModel):
    """One active sport offered by a workspace (multi-sport, doc §3.5)."""

    sport_id: str
    sport_code: str
    name_en: str
    name_id: str
    curriculum_id: str | None
    curriculum_code: str | None
    is_active: bool


class WorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    # Legacy single-sport field — kept during the migration window.  Clients
    # should prefer ``sports[]`` for multi-sport awareness.
    sport_id: str
    sports: list[WorkspaceSportOut] = []
    type: str
    name: str
    slug: str | None
    city: str | None
    brand_color: str | None
    logo_url: str | None
    tier_style: str
    primary_locale: str
    plan: str
    trial_ends_at: datetime | None
    active_trainee_quota: int
    owner_user_id: str
    created_at: datetime
    archived_at: datetime | None


class WorkspaceMembershipOut(BaseModel):
    """Workspace plus the current user's role in it."""

    workspace: WorkspaceOut
    role: str
    status: str
    joined_at: datetime | None


class WorkspacesListOut(BaseModel):
    workspaces: list[WorkspaceMembershipOut]


class TokenBundle(BaseModel):
    """Minimal token pair returned by create/switch endpoints — no user blob
    since the client already has it from sign-in."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    workspace_id: str


class WorkspaceCreateOut(BaseModel):
    workspace: WorkspaceOut
    tokens: TokenBundle
