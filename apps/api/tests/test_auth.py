"""Auth flow tests: JWT roundtrip, magic-link, refresh rotation."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import asyncpg
import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from src.auth.jwt import decode_token, encode_token, issue_token_pair
from src.auth.magic import (
    consume_magic_token,
    generate_token,
    store_magic_token,
)
from src.config import settings
from src.main import app
from src import deps as deps_module

TEST_EMAIL = "test-magic@example.com"


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
async def redis() -> Redis:
    """Per-test redis client.  Closing it after the test avoids loop-binding
    issues that surface when a connection outlives its asyncio loop."""
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
async def client(redis: Redis) -> AsyncClient:
    # Override the redis dependency so the app reuses the per-test client
    # bound to this loop instead of the module-level singleton.
    app.dependency_overrides[deps_module.get_redis] = lambda: redis
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(deps_module.get_redis, None)
    # Dispose the engine — its connection pool is bound to this test's loop.
    from src.db import session as session_module
    await session_module.engine.dispose()


@pytest.fixture(autouse=True)
async def _captured_emails(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, str]]:
    """Capture outbound magic-link emails instead of hitting Mailpit."""
    captured: list[dict[str, str]] = []

    async def fake_send(*, email: str, link: str) -> None:
        captured.append({"email": email, "link": link})

    # Patch where the symbol is imported (router.py), not where defined.
    monkeypatch.setattr("src.auth.router.send_magic_link_email", fake_send)
    return captured


@pytest.fixture(autouse=True)
async def _cleanup_test_users() -> None:
    """Delete any test users we created.  Uses the superuser DSN to bypass RLS."""
    yield
    conn = await asyncpg.connect(
        "postgresql://coachito:coachito@postgres:5432/coachito"
    )
    try:
        await conn.execute(
            "DELETE FROM users WHERE email LIKE 'test-%@example.com'"
        )
    finally:
        await conn.close()


# ── JWT primitives ───────────────────────────────────────────────


async def test_jwt_roundtrip_access() -> None:
    user_id = uuid4()
    workspace_id = uuid4()
    token, jti, _ = encode_token(
        user_id=user_id, workspace_id=workspace_id, token_type="access"
    )
    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["wsid"] == str(workspace_id)
    assert payload["type"] == "access"
    assert payload["jti"] == jti


async def test_jwt_roundtrip_no_workspace() -> None:
    user_id = uuid4()
    token, _, _ = encode_token(
        user_id=user_id, workspace_id=None, token_type="refresh"
    )
    payload = decode_token(token)
    assert payload["wsid"] is None
    assert payload["type"] == "refresh"


async def test_jwt_invalid_signature_rejected() -> None:
    user_id = uuid4()
    token, _, _ = encode_token(
        user_id=user_id, workspace_id=None, token_type="access"
    )
    # Tamper with last segment (the HMAC)
    tampered = token[:-4] + "AAAA"
    with pytest.raises(jwt.PyJWTError):
        decode_token(tampered)


async def test_issue_token_pair_shape() -> None:
    pair = issue_token_pair(uuid4())
    assert pair.access_token
    assert pair.refresh_token
    assert pair.access_token != pair.refresh_token
    assert pair.expires_in == settings.jwt_access_ttl_minutes * 60


# ── Magic-link storage ───────────────────────────────────────────


async def test_magic_token_is_one_shot(redis: Redis) -> None:
    token = generate_token()
    await store_magic_token(redis, token, TEST_EMAIL)
    assert await consume_magic_token(redis, token) == TEST_EMAIL
    # Second consume must miss
    assert await consume_magic_token(redis, token) is None


async def test_magic_token_unknown_returns_none(redis: Redis) -> None:
    assert await consume_magic_token(redis, "does-not-exist") is None


# ── HTTP endpoints ───────────────────────────────────────────────


async def test_request_magic_link_returns_202(
    client: AsyncClient, _captured_emails: list[dict[str, str]]
) -> None:
    r = await client.post("/auth/magic/request", json={"email": TEST_EMAIL})
    assert r.status_code == 202
    assert r.json() == {"status": "sent"}
    assert len(_captured_emails) == 1
    assert _captured_emails[0]["email"] == TEST_EMAIL
    assert _captured_emails[0]["link"].startswith(f"{settings.web_url}/auth/magic?token=")


async def test_request_invalid_email_returns_422(client: AsyncClient) -> None:
    r = await client.post("/auth/magic/request", json={"email": "not-an-email"})
    assert r.status_code == 422


async def test_consume_invalid_token_returns_410(client: AsyncClient) -> None:
    r = await client.get("/auth/magic/consume", params={"token": "deadbeef"})
    assert r.status_code == 410


async def test_magic_link_full_flow(
    client: AsyncClient, _captured_emails: list[dict[str, str]]
) -> None:
    # 1. Request the link
    r = await client.post("/auth/magic/request", json={"email": TEST_EMAIL})
    assert r.status_code == 202
    link = _captured_emails[-1]["link"]
    token = link.split("token=", 1)[1]

    # 2. Consume — first time succeeds, returns JWT + user payload
    r = await client.get("/auth/magic/consume", params={"token": token})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.jwt_access_ttl_minutes * 60

    user = body["user"]
    assert user["email"] == TEST_EMAIL
    assert UUID(user["id"])
    assert user["current_workspace_id"] is None  # fresh user → no membership

    # JWT actually decodes to the right user
    access_claims = decode_token(body["access_token"])
    assert access_claims["sub"] == user["id"]
    assert access_claims["wsid"] is None
    assert access_claims["type"] == "access"

    # 3. Re-consume same token — 410 (one-shot)
    r = await client.get("/auth/magic/consume", params={"token": token})
    assert r.status_code == 410


async def test_refresh_rotates_and_revokes_old(
    client: AsyncClient, _captured_emails: list[dict[str, str]]
) -> None:
    # Get initial pair via magic-link
    await client.post("/auth/magic/request", json={"email": TEST_EMAIL})
    token = _captured_emails[-1]["link"].split("token=", 1)[1]
    r = await client.get("/auth/magic/consume", params={"token": token})
    initial = r.json()
    refresh_1 = initial["refresh_token"]

    # Rotate
    r = await client.post(
        "/auth/refresh", headers={"Authorization": f"Bearer {refresh_1}"}
    )
    assert r.status_code == 200, r.text
    rotated = r.json()
    refresh_2 = rotated["refresh_token"]
    assert refresh_2 != refresh_1
    assert rotated["user"]["id"] == initial["user"]["id"]

    # Old refresh is now revoked → 401
    r = await client.post(
        "/auth/refresh", headers={"Authorization": f"Bearer {refresh_1}"}
    )
    assert r.status_code == 401


async def test_refresh_rejects_access_token(client: AsyncClient) -> None:
    # An access token shouldn't pass the refresh-type gate
    access_token, _, _ = encode_token(
        user_id=uuid4(), workspace_id=None, token_type="access"
    )
    r = await client.post(
        "/auth/refresh", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert r.status_code == 401


async def test_refresh_without_header_returns_401(client: AsyncClient) -> None:
    r = await client.post("/auth/refresh")
    assert r.status_code == 401


async def test_google_signin_with_empty_config_returns_401(client: AsyncClient) -> None:
    # GOOGLE_CLIENT_ID isn't set in dev → any id_token verification fails.
    r = await client.post(
        "/auth/google", json={"id_token": "not-a-real-google-token"}
    )
    assert r.status_code == 401


# Silence unused-fixture warnings — pytest fixtures referenced by name.
_ = (Any,)
