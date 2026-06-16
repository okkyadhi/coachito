"""GET /workspaces/public/{slug} — unauthenticated branding lookup.

Used by the FE public landing page (/welcome/:token).  No PII; just enough
to render the workspace's name, color, logo, and sport.  Reads via a
superuser asyncpg connection because the caller has no JWT and the
workspaces RLS policy would otherwise hide the row.
"""

from __future__ import annotations

from typing import Any

import asyncpg
from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from src.invites.og_landing import _superuser_dsn

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspacePublicOut(BaseModel):
    id: str
    slug: str | None
    name: str
    brand_color: str | None
    logo_url: str | None
    sport_code: str
    primary_locale: str


@router.get("/public/{slug}", response_model=WorkspacePublicOut)
async def get_public_workspace(slug: str, response: Response) -> WorkspacePublicOut:
    conn = await asyncpg.connect(_superuser_dsn())
    try:
        row = await _lookup(conn, slug)
    finally:
        await conn.close()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found."
        )

    response.headers["Cache-Control"] = "public, max-age=300"
    return WorkspacePublicOut(
        id=str(row["id"]),
        slug=row["slug"],
        name=row["name"],
        brand_color=row["brand_color"],
        logo_url=row["logo_url"],
        sport_code=row["sport_code"],
        primary_locale=row["primary_locale"],
    )


async def _lookup(conn: asyncpg.Connection, slug: str) -> dict[str, Any] | None:
    # Accept slug OR id so the FE can fall through to id-based lookup before
    # workspaces have hand-set slugs.  Both paths share the same projection.
    row = await conn.fetchrow(
        """
        SELECT w.id, w.slug, w.name, w.brand_color, w.logo_url,
               w.primary_locale, s.code AS sport_code
        FROM workspaces w
        JOIN sports s ON s.id = w.sport_id
        WHERE (w.slug = $1 OR w.id::text = $1)
          AND w.archived_at IS NULL
        LIMIT 1
        """,
        slug,
    )
    return dict(row) if row else None
