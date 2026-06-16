"""Platform admin endpoints (P0).

  GET   /admin/workspaces                — cross-tenant list with stats
  GET   /admin/workspaces/{id}           — single-workspace detail
  PATCH /admin/workspaces/{id}           — plan / trial / paid / quota / archive
  GET   /admin/users                     — search users by email/name
  POST  /admin/users/{id}/reset-password — DBA-style password reset

Every endpoint is gated by ``require_platform_admin`` and every write is
audited.  Reads + writes use a superuser SQLAlchemy session (``get_admin_session``)
so RLS doesn't filter out other tenants.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.decorators import audit_action
from src.auth.password import WeakPasswordError, hash_password
from src.db.models.user import User

from .db import get_admin_session
from .deps import require_platform_admin
from .schemas import (
    AdminResetPasswordIn,
    AdminResetPasswordOut,
    AdminUserRow,
    AdminUsersListOut,
    AdminWorkspaceDetailOut,
    AdminWorkspacePatchIn,
    AdminWorkspaceRow,
    AdminWorkspacesListOut,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ── helpers ──────────────────────────────────────────────────────


def _billing_status(
    *,
    archived_at: datetime | None,
    paid_until: datetime | None,
    trial_ends_at: datetime | None,
) -> str:
    if archived_at is not None:
        return "archived"
    now = datetime.now(UTC)
    if paid_until is not None:
        return "paid" if paid_until > now else "lapsed"
    if trial_ends_at is not None:
        return "trial" if trial_ends_at > now else "lapsed"
    return "unknown"


def _row_to_workspace(row: dict) -> AdminWorkspaceRow:
    return AdminWorkspaceRow(
        id=str(row["id"]),
        name=row["name"],
        type=row["type"],
        plan=row["plan"],
        primary_locale=row["primary_locale"],
        city=row["city"],
        owner_user_id=str(row["owner_user_id"]),
        owner_email=row["owner_email"],
        owner_display_name=row["owner_display_name"],
        trial_ends_at=row["trial_ends_at"],
        paid_until=row["paid_until"],
        archived_at=row["archived_at"],
        created_at=row["created_at"],
        coach_count=row["coach_count"],
        trainee_count=row["trainee_count"],
        last_session_at=row["last_session_at"],
    )


_WORKSPACES_BASE = """
    SELECT
        w.id, w.name, w.type, w.plan, w.primary_locale, w.city,
        w.owner_user_id,
        ou.email           AS owner_email,
        ou.display_name    AS owner_display_name,
        w.trial_ends_at, w.paid_until, w.archived_at,
        w.created_at, w.updated_at,
        w.brand_color, w.logo_url, w.tier_style,
        w.active_trainee_quota, w.sport_id,
        COALESCE(cc.n, 0)  AS coach_count,
        COALESCE(tc.n, 0)  AS trainee_count,
        ls.last_at         AS last_session_at
    FROM workspaces w
    JOIN users ou ON ou.id = w.owner_user_id
    LEFT JOIN LATERAL (
        SELECT COUNT(*)::int AS n FROM workspace_memberships
        WHERE workspace_id = w.id AND status = 'active'
          AND role IN ('club_admin','head_coach','coach')
    ) cc ON TRUE
    LEFT JOIN LATERAL (
        SELECT COUNT(*)::int AS n FROM athletes
        WHERE workspace_id = w.id AND archived_at IS NULL
    ) tc ON TRUE
    LEFT JOIN LATERAL (
        SELECT MAX(scheduled_at) AS last_at FROM sessions
        WHERE workspace_id = w.id
    ) ls ON TRUE
"""


# ── GET /admin/workspaces ────────────────────────────────────────


@router.get("/workspaces", response_model=AdminWorkspacesListOut)
async def list_workspaces(
    _admin: Annotated[UUID, Depends(require_platform_admin)],
    db: Annotated[AsyncSession, Depends(get_admin_session)],
    q: str | None = Query(default=None, max_length=120),
    plan: str | None = Query(default=None),
    type: str | None = Query(default=None),
    archived: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminWorkspacesListOut:
    clauses: list[str] = []
    params: dict = {"lim": limit, "off": offset}
    if q:
        clauses.append(
            "(w.name ILIKE :q OR ou.email ILIKE :q OR ou.display_name ILIKE :q)"
        )
        params["q"] = f"%{q}%"
    if plan:
        clauses.append("w.plan = :plan")
        params["plan"] = plan
    if type:
        clauses.append("w.type = :type")
        params["type"] = type
    if archived is True:
        clauses.append("w.archived_at IS NOT NULL")
    elif archived is False:
        clauses.append("w.archived_at IS NULL")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    total = (
        await db.execute(
            text(
                "SELECT COUNT(*)::int FROM workspaces w "
                "JOIN users ou ON ou.id = w.owner_user_id "
                + where
            ),
            params,
        )
    ).scalar_one()
    rows = (
        await db.execute(
            text(
                f"{_WORKSPACES_BASE} {where} "
                "ORDER BY w.created_at DESC LIMIT :lim OFFSET :off"
            ),
            params,
        )
    ).mappings().all()
    return AdminWorkspacesListOut(
        total=int(total or 0),
        workspaces=[_row_to_workspace(dict(r)) for r in rows],
    )


# ── GET /admin/workspaces/{id} ───────────────────────────────────


@router.get("/workspaces/{workspace_id}", response_model=AdminWorkspaceDetailOut)
async def get_workspace_detail(
    workspace_id: UUID,
    _admin: Annotated[UUID, Depends(require_platform_admin)],
    db: Annotated[AsyncSession, Depends(get_admin_session)],
) -> AdminWorkspaceDetailOut:
    row = (
        await db.execute(
            text(f"{_WORKSPACES_BASE} WHERE w.id = :wid"),
            {"wid": workspace_id},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found."
        )
    d = dict(row)
    base = _row_to_workspace(d)
    return AdminWorkspaceDetailOut(
        **base.model_dump(),
        brand_color=d["brand_color"],
        logo_url=d["logo_url"],
        tier_style=d["tier_style"],
        active_trainee_quota=d["active_trainee_quota"],
        sport_id=str(d["sport_id"]) if d["sport_id"] else None,
        updated_at=d["updated_at"],
        billing_status=_billing_status(
            archived_at=d["archived_at"],
            paid_until=d["paid_until"],
            trial_ends_at=d["trial_ends_at"],
        ),
    )


# ── PATCH /admin/workspaces/{id} ─────────────────────────────────


@router.patch("/workspaces/{workspace_id}", response_model=AdminWorkspaceDetailOut)
@audit_action(
    "platform.workspace.updated",
    entity_type="workspace",
    extract=lambda r, kw: {
        "workspace_id": str(kw.get("workspace_id")),
        "patch": r.model_dump(exclude_none=True) if r else {},
    },
)
async def patch_workspace(
    workspace_id: UUID,
    body: AdminWorkspacePatchIn,
    _admin: Annotated[UUID, Depends(require_platform_admin)],
    db: Annotated[AsyncSession, Depends(get_admin_session)],
) -> AdminWorkspaceDetailOut:
    sets: list[str] = []
    params: dict = {"wid": workspace_id}
    if body.plan is not None:
        sets.append("plan = :plan")
        params["plan"] = body.plan
    if body.trial_ends_at is not None:
        sets.append("trial_ends_at = :trial")
        params["trial"] = body.trial_ends_at
    if body.paid_until is not None:
        sets.append("paid_until = :paid")
        params["paid"] = body.paid_until
    if body.active_trainee_quota is not None:
        sets.append("active_trainee_quota = :quota")
        params["quota"] = body.active_trainee_quota
    if body.archived is True:
        sets.append("archived_at = :arch")
        params["arch"] = datetime.now(UTC)
    elif body.archived is False:
        sets.append("archived_at = NULL")

    if not sets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update."
        )

    sets.append("updated_at = NOW()")
    result = await db.execute(
        text(f"UPDATE workspaces SET {', '.join(sets)} WHERE id = :wid"),
        params,
    )
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found."
        )
    await db.commit()
    return await get_workspace_detail(
        workspace_id=workspace_id, _admin=_admin, db=db
    )


# ── GET /admin/users ─────────────────────────────────────────────


@router.get("/users", response_model=AdminUsersListOut)
async def list_users(
    _admin: Annotated[UUID, Depends(require_platform_admin)],
    db: Annotated[AsyncSession, Depends(get_admin_session)],
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminUsersListOut:
    clauses: list[str] = []
    params: dict = {"lim": limit, "off": offset}
    if q:
        clauses.append("(u.email ILIKE :q OR u.display_name ILIKE :q)")
        params["q"] = f"%{q}%"
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    total = (
        await db.execute(
            text(f"SELECT COUNT(*)::int FROM users u {where}"), params
        )
    ).scalar_one()
    rows = (
        await db.execute(
            text(
                f"""
                SELECT u.id, u.email, u.display_name, u.preferred_locale,
                       u.created_at, u.last_seen_at, u.is_platform_admin,
                       COALESCE(ws.n, 0) AS workspace_count,
                       COALESCE(ws.summary, '') AS workspace_summary
                FROM users u
                LEFT JOIN LATERAL (
                    SELECT COUNT(*)::int AS n,
                           string_agg(
                               w.name || ' (' || m.role || ')',
                               ', ' ORDER BY m.joined_at
                           ) AS summary
                    FROM workspace_memberships m
                    JOIN workspaces w ON w.id = m.workspace_id
                    WHERE m.user_id = u.id AND m.status = 'active'
                ) ws ON TRUE
                {where}
                ORDER BY u.created_at DESC
                LIMIT :lim OFFSET :off
                """
            ),
            params,
        )
    ).mappings().all()
    return AdminUsersListOut(
        total=int(total or 0),
        users=[
            AdminUserRow(
                id=str(r["id"]),
                email=r["email"],
                display_name=r["display_name"],
                preferred_locale=r["preferred_locale"],
                created_at=r["created_at"],
                last_seen_at=r["last_seen_at"],
                is_platform_admin=r["is_platform_admin"],
                workspace_count=r["workspace_count"],
                workspace_summary=r["workspace_summary"] or "",
            )
            for r in rows
        ],
    )


# ── POST /admin/users/{id}/reset-password ────────────────────────


@router.post(
    "/users/{user_id}/reset-password", response_model=AdminResetPasswordOut
)
@audit_action(
    "platform.user.password_reset",
    entity_type="user",
    extract=lambda r, kw: {"user_id": str(kw.get("user_id"))},
)
async def reset_user_password(
    user_id: UUID,
    body: AdminResetPasswordIn,
    _admin: Annotated[UUID, Depends(require_platform_admin)],
    db: Annotated[AsyncSession, Depends(get_admin_session)],
) -> AdminResetPasswordOut:
    try:
        new_hash = hash_password(body.new_password)
    except WeakPasswordError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e

    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    user.password_hash = new_hash
    await db.commit()
    return AdminResetPasswordOut(user_id=str(user.id), email=user.email)
