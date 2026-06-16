"""ASGI middleware: stamp ``X-Request-Id`` on every response and surface the
same value to logging via ``contextvars`` so structlog can include it.

Honors an inbound ``X-Request-Id`` (so multi-service traces stitch together)
and falls back to a fresh UUID otherwise.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Awaitable, Callable
from uuid import uuid4

from starlette.types import ASGIApp, Receive, Scope, Send

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def current_request_id() -> str | None:
    """Read inside any async handler / logging filter."""
    return _request_id_var.get()


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp, header: str = "x-request-id") -> None:
        self.app = app
        self.header = header.encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        inbound = _find_header(scope.get("headers") or [], self.header)
        request_id = inbound or uuid4().hex
        token = _request_id_var.set(request_id)

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                headers.append((self.header, request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            _request_id_var.reset(token)


def _find_header(headers: list[tuple[bytes, bytes]], name: bytes) -> str | None:
    for k, v in headers:
        if k.lower() == name:
            try:
                return v.decode()
            except UnicodeDecodeError:
                return None
    return None


# Silence "imported but unused" for the Awaitable/Callable hints — kept for
# downstream extensions that wrap send/receive differently.
_ = Awaitable
_ = Callable
