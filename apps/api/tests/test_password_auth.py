"""Password auth — set, login, rate limit."""

from __future__ import annotations

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from src import deps as deps_module
from src.config import settings
from src.db import session as session_module
from src.main import app

from ._test_helpers import SUPERUSER_DSN, sign_in


@pytest.fixture
async def redis() -> Redis:
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
async def client(redis: Redis) -> AsyncClient:
    app.dependency_overrides[deps_module.get_redis] = lambda: redis
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(deps_module.get_redis, None)
    await session_module.engine.dispose()


@pytest.fixture
async def captured(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, str]]:
    captured: list[dict[str, str]] = []

    async def fake_send(*, email: str, link: str) -> None:
        captured.append({"email": email, "link": link})

    monkeypatch.setattr("src.auth.router.send_magic_link_email", fake_send)
    return captured


@pytest.fixture(autouse=True)
async def _cleanup(redis: Redis) -> None:
    yield
    conn = await asyncpg.connect(SUPERUSER_DSN)
    try:
        await conn.execute(
            "DELETE FROM users WHERE email LIKE 'test-%@example.com'"
        )
    finally:
        await conn.close()
    # Clear rate-limit buckets that bled into Redis.
    async for k in redis.scan_iter("auth:pwlogin:fails:test-*"):
        await redis.delete(k)


# ── Tests ────────────────────────────────────────────────────────


async def test_set_password_then_login(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-pw-set@example.com", captured)
    token = user["access_token"]

    r = await client.post(
        "/auth/password/set",
        json={"new_password": "correct horse battery"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 204, r.text

    login = await client.post(
        "/auth/password/login",
        json={
            "email": "test-pw-set@example.com",
            "password": "correct horse battery",
        },
    )
    assert login.status_code == 200, login.text
    assert login.json()["user"]["email"] == "test-pw-set@example.com"


async def test_login_wrong_password_returns_401(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-pw-wrong@example.com", captured)
    token = user["access_token"]
    await client.post(
        "/auth/password/set",
        json={"new_password": "the right one"},
        headers={"Authorization": f"Bearer {token}"},
    )

    bad = await client.post(
        "/auth/password/login",
        json={"email": "test-pw-wrong@example.com", "password": "wrong wrong"},
    )
    assert bad.status_code == 401, bad.text


async def test_login_unknown_email_returns_401(client: AsyncClient) -> None:
    r = await client.post(
        "/auth/password/login",
        json={"email": "test-pw-nobody@example.com", "password": "whatever"},
    )
    assert r.status_code == 401, r.text


async def test_change_password_requires_current(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-pw-chg@example.com", captured)
    token = user["access_token"]

    await client.post(
        "/auth/password/set",
        json={"new_password": "first one is here"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Without current_password → 403
    forbidden = await client.post(
        "/auth/password/set",
        json={"new_password": "second one new"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert forbidden.status_code == 403, forbidden.text

    # With wrong current_password → 403
    wrong = await client.post(
        "/auth/password/set",
        json={"current_password": "nope nope", "new_password": "second one new"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert wrong.status_code == 403, wrong.text

    # With correct current → 204 + new password works
    ok = await client.post(
        "/auth/password/set",
        json={
            "current_password": "first one is here",
            "new_password": "second one new",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ok.status_code == 204, ok.text

    login = await client.post(
        "/auth/password/login",
        json={"email": "test-pw-chg@example.com", "password": "second one new"},
    )
    assert login.status_code == 200


async def test_weak_password_rejected(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-pw-weak@example.com", captured)
    token = user["access_token"]
    r = await client.post(
        "/auth/password/set",
        json={"new_password": "short"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Pydantic Field(min_length=8) handles this — 422 vs 400 is fine.
    assert r.status_code in (400, 422)


async def test_rate_limit_after_too_many_failures(
    client: AsyncClient, captured: list[dict[str, str]], redis: Redis
) -> None:
    user = await sign_in(client, "test-pw-rate@example.com", captured)
    token = user["access_token"]
    await client.post(
        "/auth/password/set",
        json={"new_password": "the actual password"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # 6 wrong attempts → bucket fills → 7th hits the limit.
    for _ in range(6):
        r = await client.post(
            "/auth/password/login",
            json={"email": "test-pw-rate@example.com", "password": "wrong xxx"},
        )
        assert r.status_code == 401

    limited = await client.post(
        "/auth/password/login",
        json={"email": "test-pw-rate@example.com", "password": "the actual password"},
    )
    assert limited.status_code == 429, limited.text
