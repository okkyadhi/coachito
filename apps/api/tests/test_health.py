"""GET /healthz — 200 when all probes pass, 503 when one fails."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.db import session as session_module
from src.main import app
from src.observability import health as health_mod


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await session_module.engine.dispose()


async def test_healthz_returns_200_when_all_subsystems_ok(
    client: AsyncClient,
) -> None:
    r = await client.get("/healthz")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    for name in ("db", "redis", "s3", "smtp"):
        assert body["checks"][name]["status"] == "ok", body["checks"][name]


async def test_healthz_returns_503_when_redis_probe_fails(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def failing_probe() -> tuple[str, str]:
        return "fail", "Connection refused"

    monkeypatch.setattr(health_mod, "probe_redis", failing_probe)
    r = await client.get("/healthz")
    assert r.status_code == 503, r.text
    body = r.json()
    assert body["status"] == "degraded"
    assert body["checks"]["redis"]["status"] == "fail"
    assert body["checks"]["redis"]["error"] == "Connection refused"
    # Other subsystems still report individually.
    assert body["checks"]["db"]["status"] == "ok"


async def test_healthz_response_carries_request_id_header(
    client: AsyncClient,
) -> None:
    r = await client.get("/healthz", headers={"X-Request-Id": "test-xyz-123"})
    assert r.headers.get("x-request-id") == "test-xyz-123"


async def test_healthz_generates_request_id_when_missing(
    client: AsyncClient,
) -> None:
    r = await client.get("/healthz")
    rid = r.headers.get("x-request-id")
    assert rid is not None and len(rid) >= 16
