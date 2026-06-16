"""PATCH /workspaces/me — branding, tier-style, curriculum, allow_overrides.

Authorization: only ``club_admin`` (in club workspaces) or the workspace
*owner* (which for personal workspaces means the solo coach) may modify
settings.  Plain ``coach`` / ``head_coach`` get 403.

Every change writes an audit row with the list of changed fields so we can
answer "who renamed the workspace last Tuesday?" without trawling logs.

When ``logo_url`` is included we re-verify it points at an object that
actually exists in our bucket — guards against a malicious client persisting
a URL to a foreign asset.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from src.audit.service import write_audit_log
from src.auth.service import get_role_in_workspace
from src.config import settings as app_settings
from src.db.models.workspace import Workspace
from src.deps import get_current_user_id, get_current_workspace_id
from src.middleware.rls import db_with_rls
from src.uploads.s3 import head_object

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


_ADMIN_ROLES = {"club_admin"}


class WorkspaceSettingsPatch(BaseModel):
    """Every field optional — `model_dump(exclude_unset=True)` gives us only
    the keys the FE actually sent."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    city: str | None = Field(default=None, max_length=100)
    brand_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    logo_url: str | None = None
    tier_style: str | None = Field(default=None, pattern=r"^(game|skill|custom)$")
    allow_coach_overrides: bool | None = None
    curriculum_id: UUID | None = None


class WorkspaceSettingsOut(BaseModel):
    id: str
    type: str
    name: str
    city: str | None
    brand_color: str | None
    logo_url: str | None
    tier_style: str
    allow_coach_overrides: bool
    curriculum_id: str | None
    plan: str
    primary_locale: str


def _to_out(ws: Workspace) -> WorkspaceSettingsOut:
    return WorkspaceSettingsOut(
        id=str(ws.id),
        type=ws.type,
        name=ws.name,
        city=ws.city,
        brand_color=ws.brand_color,
        logo_url=ws.logo_url,
        tier_style=ws.tier_style,
        allow_coach_overrides=ws.allow_coach_overrides,
        curriculum_id=str(ws.curriculum_id) if ws.curriculum_id else None,
        plan=ws.plan,
        primary_locale=ws.primary_locale,
    )


def _logo_key_from_url(url: str) -> str | None:
    """Extract the S3 key from the public URL we returned at presign-time.
    Used to HEAD the object before persisting.  Returns None if the URL
    doesn't look like ours — caller then rejects."""
    prefix = f"{app_settings.s3_public_endpoint.rstrip('/')}/{app_settings.s3_bucket}/"
    if not url.startswith(prefix):
        return None
    return url[len(prefix):]


@router.patch("/me", response_model=WorkspaceSettingsOut)
async def patch_my_workspace(
    body: WorkspaceSettingsPatch,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> WorkspaceSettingsOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No active workspace."
        )

    ws = (
        await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ).scalar_one_or_none()
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found."
        )

    role = await get_role_in_workspace(db, user_id, workspace_id)
    is_owner = ws.owner_user_id == user_id
    if role not in _ADMIN_ROLES and not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the workspace admin can change settings.",
        )

    patch = body.model_dump(exclude_unset=True)
    if not patch:
        return _to_out(ws)

    # Logo-URL guard — only accept URLs pointing at an object that exists in
    # our bucket.  Skip the check when the URL is null (clearing the logo).
    if "logo_url" in patch and patch["logo_url"] is not None:
        key = _logo_key_from_url(patch["logo_url"])
        if key is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="logo_url is not a recognized storage URL.",
            )
        head = await run_in_threadpool(head_object, key)
        if head is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded logo could not be found in storage.",
            )

    # Field-level diff so the audit row records what actually changed.
    changes: dict[str, dict[str, Any]] = {}
    for field, new in patch.items():
        old = getattr(ws, field)
        if old != new:
            changes[field] = {"from": _safe(old), "to": _safe(new)}
            setattr(ws, field, new)

    if not changes:
        return _to_out(ws)

    await db.flush()
    await write_audit_log(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
        action="workspace.updated",
        entity_type="workspace",
        entity_id=workspace_id,
        metadata={"changed_fields": sorted(changes.keys()), "changes": changes},
    )
    await db.commit()
    await db.refresh(ws)
    return _to_out(ws)


def _safe(v: Any) -> Any:
    """JSON-safe representation for audit metadata."""
    if isinstance(v, UUID):
        return str(v)
    return v
