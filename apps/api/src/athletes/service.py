"""Trainee list query: joins last-assessed-at and cached tier."""

import base64
import binascii
from collections.abc import Mapping
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_LIMIT = 25
MAX_LIMIT = 100


# Opaque cursor that just encodes the offset.  We could pack
# (last_assessed_at, id) for true keyset pagination, but offset is fine at
# MVP scale and the cursor stays opaque so we can switch later without an API
# break.
def encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode()).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        pad = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode((cursor + pad).encode()).decode()
        value = int(raw)
        return max(value, 0)
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return 0


# Single query: athletes + their latest assessment time + their cached tier.
# RLS filters by current_workspace_id() so the caller doesn't need to pass it.
_LIST_SQL = """
    WITH last_assessed AS (
        SELECT athlete_id,
               MAX(COALESCE(edited_at, published_at)) AS last_at
        FROM assessments
        WHERE status IN ('published','edited')
        GROUP BY athlete_id
    )
    SELECT
        a.id,
        a.display_name,
        a.date_of_birth,
        a.is_minor,
        a.joined_at,
        a.archived_at,
        a.created_at,
        la.last_at         AS last_assessed_at,
        t.id               AS tier_id,
        t.code             AS tier_code,
        t.name_game_en     AS tier_name_game_en,
        t.name_game_id     AS tier_name_game_id
    FROM athletes a
    LEFT JOIN last_assessed la ON la.athlete_id = a.id
    LEFT JOIN tiers t          ON t.id = a.current_tier_id
    WHERE a.archived_at IS NULL
      AND a.display_name ILIKE :pattern
    ORDER BY la.last_at DESC NULLS LAST, a.id DESC
    LIMIT :limit OFFSET :offset
"""


async def list_athletes(
    db: AsyncSession,
    *,
    q: str | None,
    limit: int,
    cursor: str | None,
) -> tuple[list[Mapping[str, Any]], str | None]:
    """Returns (rows, next_cursor).  Caller maps rows to schema."""
    limit = max(1, min(limit, MAX_LIMIT))
    offset = decode_cursor(cursor)
    # Empty q → '%' wildcard matches everything; avoids a Postgres `IS NULL`
    # branch that SQLAlchemy's `text()` mis-parses around `::` casts.
    pattern = f"%{q}%" if q else "%"

    result = await db.execute(
        text(_LIST_SQL),
        {"pattern": pattern, "limit": limit + 1, "offset": offset},
    )
    rows = list(result.mappings())
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]
    next_cursor = encode_cursor(offset + limit) if has_more else None
    return rows, next_cursor
