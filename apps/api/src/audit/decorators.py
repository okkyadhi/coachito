"""@audit_action decorator for FastAPI routes.

Wraps a handler and, on success, writes one ``audit_log`` row.  Runs *after*
the handler returns so the handler's own commit settles first; the audit
write uses its own RLS-bypassing asyncpg connection so it can't accidentally
roll back the user-visible state on a logging failure.

The decorator pulls ``user_id`` / ``workspace_id`` from the handler's
kwargs (FastAPI passes DI dependencies by name) and the ``entity_id`` from
the response model when present (``id`` field).  Pass ``extract`` to derive
custom metadata from (result, kwargs).
"""

from __future__ import annotations

import functools
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

import asyncpg

from src.invites.og_landing import _superuser_dsn

log = logging.getLogger(__name__)

Handler = Callable[..., Awaitable[Any]]


def audit_action(
    action: str,
    *,
    entity_type: str | None = None,
    extract: Callable[[Any, dict[str, Any]], dict[str, Any]] | None = None,
) -> Callable[[Handler], Handler]:
    """Decorator factory.

    ``action`` — short verb-noun string, e.g. ``"trainee.created"``.
    ``entity_type`` — optional table-ish hint stored alongside.
    ``extract`` — optional ``(result, kwargs) -> dict`` for custom metadata.
    """

    def decorator(handler: Handler) -> Handler:
        @functools.wraps(handler)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = await handler(*args, **kwargs)
            try:
                await _record(action, entity_type, extract, result, kwargs)
            except Exception:  # pragma: no cover - audit must never break a route
                log.exception("audit_log_failed", extra={"action": action})
            return result

        return wrapper

    return decorator


async def _record(
    action: str,
    entity_type: str | None,
    extract: Callable[[Any, dict[str, Any]], dict[str, Any]] | None,
    result: Any,
    kwargs: dict[str, Any],
) -> None:
    user_id = kwargs.get("user_id")
    workspace_id = kwargs.get("workspace_id")
    entity_id = _extract_entity_id(result)
    metadata = extract(result, kwargs) if extract else None

    # Path of least resistance: open our own asyncpg connection so we don't
    # depend on the handler's session being still-open or its transaction
    # being still-clean.  Audit rows are append-only; one extra connection
    # per mutating call is fine.
    conn = await asyncpg.connect(_superuser_dsn())
    try:
        await conn.execute(
            """
            INSERT INTO audit_log (
                workspace_id, user_id, action,
                entity_type, entity_id, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            """,
            _to_uuid(workspace_id),
            _to_uuid(user_id),
            action,
            entity_type,
            _to_uuid(entity_id),
            json.dumps(metadata) if metadata is not None else None,
        )
    finally:
        await conn.close()


def _to_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, AttributeError):
        return None


def _extract_entity_id(result: Any) -> Any:
    """Try common shapes: a bare model with ``id``, or a wrapper exposing the
    persisted row under a known key."""
    if result is None:
        return None
    # Pydantic model or attrs object.
    candidate = getattr(result, "id", None)
    if candidate is not None:
        return candidate
    # Wrapper like {"trainee": {...}, "invite": {...}} — pick the first
    # nested object with an id.
    for attr in ("trainee", "report", "workspace", "athlete"):
        nested = getattr(result, attr, None)
        if nested is not None:
            inner = getattr(nested, "id", None)
            if inner is not None:
                return inner
    return None
