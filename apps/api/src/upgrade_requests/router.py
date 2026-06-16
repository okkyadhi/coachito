"""Upgrade-request endpoints.

  POST  /me/upgrade-requests           — coach taps "Choose plan" in
                                          the picker; we record the
                                          intent for the platform admin
                                          to follow up off-platform.

  GET   /admin/upgrade-requests        — admin queue, defaults to
                                          status=pending.
  PATCH /admin/upgrade-requests/{id}   — admin marks resolved/dismissed
                                          (or back to pending) and may
                                          leave a scratch note.

The POST runs under RLS so the workspace_id comes from the JWT, not
from the body — the requester can't move the request to someone else's
tenant.  The admin endpoints run through ``get_admin_session`` (RLS
bypass) the same way the rest of /admin/* does.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.db import get_admin_session
from src.admin.deps import require_platform_admin
from src.audit.decorators import audit_action
from src.deps import get_current_user_id, get_current_workspace_id
from src.middleware.rls import db_with_rls

from .schemas import (
    UpgradeRequestCreateIn,
    UpgradeRequestListOut,
    UpgradeRequestOut,
    UpgradeRequestPatchIn,
)

router = APIRouter(tags=["upgrade-requests"])


# Dedup window — if the same workspace already has a pending request
# (regardless of which plan), don't create a second row.  We just
# update the requested_plan + bump created_at so the admin sees the
# latest intent.  Prevents accidental spam from impatient taps.
def _row_to_out(row: dict) -> UpgradeRequestOut:
    return UpgradeRequestOut(
        id=str(row["id"]),
        workspace_id=str(row["workspace_id"]),
        workspace_name=row["workspace_name"],
        requested_plan=row["requested_plan"],
        requester_user_id=str(row["requester_user_id"])
        if row["requester_user_id"]
        else None,
        requester_email=row.get("requester_email"),
        requester_display_name=row.get("requester_display_name"),
        owner_email=row.get("owner_email"),
        owner_display_name=row.get("owner_display_name"),
        status=row["status"],
        note=row["note"],
        created_at=row["created_at"],
        resolved_at=row["resolved_at"],
        resolved_by_user_id=str(row["resolved_by_user_id"])
        if row["resolved_by_user_id"]
        else None,
    )


_LIST_SELECT = """
    SELECT
        ur.id,
        ur.workspace_id,
        w.name              AS workspace_name,
        ur.requested_plan,
        ur.requester_user_id,
        ru.email            AS requester_email,
        ru.display_name     AS requester_display_name,
        ou.email            AS owner_email,
        ou.display_name     AS owner_display_name,
        ur.status,
        ur.note,
        ur.created_at,
        ur.resolved_at,
        ur.resolved_by_user_id
    FROM upgrade_requests ur
    JOIN workspaces w ON w.id = ur.workspace_id
    LEFT JOIN users ru ON ru.id = ur.requester_user_id
    LEFT JOIN users ou ON ou.id = w.owner_user_id
"""


# ── POST /me/upgrade-requests ────────────────────────────────────


@router.post(
    "/me/upgrade-requests",
    response_model=UpgradeRequestOut,
    status_code=status.HTTP_201_CREATED,
)
@audit_action(
    "upgrade_request.created",
    entity_type="upgrade_request",
    extract=lambda r, kw: {
        "requested_plan": r.requested_plan if r else None,
    },
)
async def create_upgrade_request(
    body: UpgradeRequestCreateIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> UpgradeRequestOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active workspace.",
        )

    # Dedup: if the workspace already has a pending request, refresh
    # its plan + created_at instead of inserting a new row.
    existing = (
        await db.execute(
            text(
                """
                SELECT id FROM upgrade_requests
                WHERE workspace_id = :wid AND status = 'pending'
                ORDER BY created_at DESC LIMIT 1
                """
            ),
            {"wid": workspace_id},
        )
    ).scalar_one_or_none()

    if existing is not None:
        await db.execute(
            text(
                """
                UPDATE upgrade_requests
                SET requested_plan = :plan,
                    requester_user_id = :uid,
                    created_at = NOW()
                WHERE id = :id
                """
            ),
            {
                "plan": body.requested_plan,
                "uid": user_id,
                "id": existing,
            },
        )
        new_id = existing
    else:
        new_id = uuid4()
        await db.execute(
            text(
                """
                INSERT INTO upgrade_requests
                    (id, workspace_id, requested_plan, requester_user_id)
                VALUES (:id, :wid, :plan, :uid)
                """
            ),
            {
                "id": new_id,
                "wid": workspace_id,
                "plan": body.requested_plan,
                "uid": user_id,
            },
        )

    await db.commit()

    row = (
        await db.execute(
            text(_LIST_SELECT + " WHERE ur.id = :id"),
            {"id": new_id},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Request was created but could not be read back.",
        )
    return _row_to_out(dict(row))


# ── GET /admin/upgrade-requests ──────────────────────────────────


@router.get(
    "/admin/upgrade-requests",
    response_model=UpgradeRequestListOut,
)
async def list_upgrade_requests(
    _admin: Annotated[UUID, Depends(require_platform_admin)],
    db: Annotated[AsyncSession, Depends(get_admin_session)],
    status_filter: Annotated[
        Literal["pending", "resolved", "dismissed", "all"], Query(alias="status")
    ] = "pending",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> UpgradeRequestListOut:
    where = "" if status_filter == "all" else "WHERE ur.status = :status"
    params: dict = {"limit": limit, "offset": offset}
    if status_filter != "all":
        params["status"] = status_filter

    total = (
        await db.execute(
            text(
                f"SELECT COUNT(*)::int FROM upgrade_requests ur {where}"
            ),
            params,
        )
    ).scalar_one()

    rows = (
        await db.execute(
            text(
                f"""
                {_LIST_SELECT}
                {where}
                ORDER BY ur.created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
    ).mappings().all()

    return UpgradeRequestListOut(
        total=int(total or 0),
        requests=[_row_to_out(dict(r)) for r in rows],
    )


# ── PATCH /admin/upgrade-requests/{id} ───────────────────────────


@router.patch(
    "/admin/upgrade-requests/{request_id}",
    response_model=UpgradeRequestOut,
)
@audit_action(
    "platform.upgrade_request.updated",
    entity_type="upgrade_request",
    extract=lambda r, kw: {
        "request_id": str(kw.get("request_id")),
        "status": r.status if r else None,
    },
)
async def patch_upgrade_request(
    request_id: UUID,
    body: UpgradeRequestPatchIn,
    admin_id: Annotated[UUID, Depends(require_platform_admin)],
    db: Annotated[AsyncSession, Depends(get_admin_session)],
) -> UpgradeRequestOut:
    if body.status == "pending":
        # Re-open: clear resolved_* fields.
        sets = "status = 'pending', resolved_at = NULL, resolved_by_user_id = NULL"
        params: dict = {"id": request_id}
    else:
        sets = (
            "status = :status, resolved_at = :now, "
            "resolved_by_user_id = :admin"
        )
        params = {
            "id": request_id,
            "status": body.status,
            "now": datetime.now(UTC),
            "admin": admin_id,
        }
    if body.note is not None:
        sets += ", note = :note"
        params["note"] = body.note

    result = await db.execute(
        text(f"UPDATE upgrade_requests SET {sets} WHERE id = :id"),
        params,
    )
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upgrade request not found.",
        )
    await db.commit()

    row = (
        await db.execute(
            text(_LIST_SELECT + " WHERE ur.id = :id"),
            {"id": request_id},
        )
    ).mappings().first()
    if row is None:  # pragma: no cover — just-updated row
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upgrade request not found.",
        )
    return _row_to_out(dict(row))
