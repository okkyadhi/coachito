"""Sentry init.  No-op when the SDK isn't installed or the DSN is unset, so
dev workflows don't need any extra config.  Workers + the API call
``init_sentry`` once on startup; subsequent calls are idempotent."""

from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

_initialized = False


def init_sentry(service: str) -> bool:
    """Initialize Sentry for ``service`` ("api" / "worker").

    Reads ``SENTRY_DSN`` from env (separate DSNs per service supported via
    ``SENTRY_DSN_API`` / ``SENTRY_DSN_WORKER``).  Returns True iff Sentry was
    actually initialized — handy for healthz / logs.
    """
    global _initialized
    if _initialized:
        return True

    dsn = (
        os.environ.get(f"SENTRY_DSN_{service.upper()}")
        or os.environ.get("SENTRY_DSN")
        or ""
    ).strip()
    if not dsn:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError:
        log.warning("sentry_sdk not installed; Sentry disabled")
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=os.environ.get("ENVIRONMENT", "development"),
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_RATE", "0.0")),
        profiles_sample_rate=float(os.environ.get("SENTRY_PROFILES_RATE", "0.0")),
        integrations=[
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        send_default_pii=False,
    )
    sentry_sdk.set_tag("service", service)
    _initialized = True
    log.info("sentry_initialized", extra={"service": service})
    return True


def tag_request(*, workspace_id: str | None, user_id: str | None) -> None:
    """Attach per-request tags to the current Sentry scope."""
    if not _initialized:
        return
    try:
        import sentry_sdk
    except ImportError:
        return
    with sentry_sdk.configure_scope() as scope:
        if workspace_id:
            scope.set_tag("workspace_id", workspace_id)
        if user_id:
            scope.set_tag("user_id", user_id)
