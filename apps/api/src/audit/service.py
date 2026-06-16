"""Audit-log writes.

Append-only.  Every mutating endpoint that crosses a tenant boundary should
call `write_audit_log` so we can answer "who changed X and when?".

RLS on `audit_log` allows the current workspace's rows + platform rows; the
inserter only needs `app.current_workspace_id` to be set, which it already is
via `db_with_rls`.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def write_audit_log(
    db: AsyncSession,
    *,
    workspace_id: UUID | None,
    user_id: UUID | None,
    action: str,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Insert one audit_log row.  Caller is responsible for the surrounding
    transaction — we just stage the write."""
    import json

    await db.execute(
        text(
            """
            INSERT INTO audit_log (
                workspace_id, user_id, action,
                entity_type, entity_id,
                metadata, ip_address, user_agent
            )
            VALUES (
                :wid, :uid, :action,
                :etype, :eid,
                CAST(:meta AS JSONB), CAST(:ip AS INET), :ua
            )
            """
        ),
        {
            "wid": workspace_id,
            "uid": user_id,
            "action": action,
            "etype": entity_type,
            "eid": entity_id,
            "meta": json.dumps(metadata) if metadata is not None else None,
            "ip": ip_address,
            "ua": user_agent,
        },
    )
