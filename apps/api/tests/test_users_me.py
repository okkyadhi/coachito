"""GET/PATCH /users/me — trainee self-service profile."""

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
    cap: list[dict[str, str]] = []

    async def fake_send(*, email: str, link: str) -> None:
        cap.append({"email": email, "link": link})

    monkeypatch.setattr("src.auth.router.send_magic_link_email", fake_send)
    return cap


@pytest.fixture(autouse=True)
async def _cleanup() -> None:
    yield
    conn = await asyncpg.connect(SUPERUSER_DSN)
    try:
        await conn.execute(
            "DELETE FROM user_notification_prefs WHERE user_id IN ("
            "  SELECT id FROM users WHERE email LIKE 'test-me-%@example.com'"
            ")"
        )
        await conn.execute("DELETE FROM users WHERE email LIKE 'test-me-%@example.com'")
    finally:
        await conn.close()


async def test_get_me_returns_defaults(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    me = await sign_in(client, "test-me-andi@example.com", captured)
    r = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {me['access_token']}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["email"] == "test-me-andi@example.com"
    assert data["preferred_locale"] in ("en", "id")
    assert data["notifications"]["session_reminders"] is True
    assert data["notifications"]["monthly_report"] is True


async def test_patch_display_name_and_locale(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    me = await sign_in(client, "test-me-budi@example.com", captured)
    token = me["access_token"]
    r = await client.patch(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"display_name": "Budi P.", "preferred_locale": "en"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["display_name"] == "Budi P."
    assert r.json()["preferred_locale"] == "en"


async def test_patch_notifications_partial_upsert(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    me = await sign_in(client, "test-me-sari@example.com", captured)
    token = me["access_token"]
    r = await client.patch(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"notifications": {"session_reminders": False}},
    )
    assert r.status_code == 200, r.text
    n = r.json()["notifications"]
    assert n["session_reminders"] is False
    # untouched default preserved
    assert n["monthly_report"] is True

    # Toggle the other one with the first preserved.
    r2 = await client.patch(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"notifications": {"monthly_report": False}},
    )
    n2 = r2.json()["notifications"]
    assert n2["session_reminders"] is False
    assert n2["monthly_report"] is False


async def test_patch_summary_style(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    me = await sign_in(client, "test-me-style@example.com", captured)
    token = me["access_token"]
    # Default is encouraging.
    initial = await client.get(
        "/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert initial.json()["summary_style"] == "encouraging"

    r = await client.patch(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"summary_style": "direct"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["summary_style"] == "direct"

    # Invalid value rejected at the Pydantic layer.
    bad = await client.patch(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"summary_style": "shouty"},
    )
    assert bad.status_code == 422


async def test_patch_rejects_dob_field(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    me = await sign_in(client, "test-me-joko@example.com", captured)
    token = me["access_token"]
    r = await client.patch(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"date_of_birth": "2010-01-01"},
    )
    assert r.status_code == 422, r.text


async def test_patch_avatar_rejects_external_url(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    me = await sign_in(client, "test-me-rina@example.com", captured)
    token = me["access_token"]
    r = await client.patch(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"avatar_url": "https://malicious.example/some.png"},
    )
    assert r.status_code == 400


async def test_avatar_presign_returns_policy(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    me = await sign_in(client, "test-me-asep@example.com", captured)
    token = me["access_token"]
    r = await client.post(
        "/uploads/avatar/sign",
        headers={"Authorization": f"Bearer {token}"},
        json={"content_type": "image/png", "content_length": 12345},
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["public_url"].startswith("http")
    assert out["key"].startswith(f"users/{me['user']['id']}/avatar/")
