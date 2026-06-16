"""POST /uploads/logo/sign — presign shape, validation, full round-trip to MinIO."""

from __future__ import annotations

from typing import Any

import asyncpg
import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from src import deps as deps_module
from src.config import settings
from src.db import session as session_module
from src.main import app
from src.uploads import s3 as s3_module

from ._test_helpers import SUPERUSER_DSN, create_workspace, sign_in


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
async def _internal_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """In tests the API container reaches MinIO over the docker network at
    minio:9000.  The PRESIGN URL therefore points there too — the test client
    (also running inside the api container) can PUT to it directly.  Override
    the public endpoint to match so the signed URL is reachable."""
    monkeypatch.setattr(settings, "s3_public_endpoint", settings.s3_endpoint)
    # Invalidate the cached boto3 clients so they pick up the new endpoint.
    s3_module._client.cache_clear()


@pytest.fixture(autouse=True)
async def _cleanup() -> None:
    yield
    conn = await asyncpg.connect(SUPERUSER_DSN)
    try:
        await conn.execute(
            """
            DELETE FROM workspaces WHERE owner_user_id IN (
                SELECT id FROM users WHERE email LIKE 'test-%@example.com'
            )
            """
        )
        await conn.execute("DELETE FROM users WHERE email LIKE 'test-%@example.com'")
    finally:
        await conn.close()


# ── Tests ────────────────────────────────────────────────────────


async def test_sign_returns_policy_with_required_fields(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-up-shape@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Shape Club")
    token = ws["tokens"]["access_token"]

    r = await client.post(
        "/uploads/logo/sign",
        json={"content_type": "image/png", "content_length": 4096},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["url"].endswith("/coachito-dev")
    assert "key" in data["fields"]
    assert data["fields"]["Content-Type"] == "image/png"
    assert data["public_url"].endswith(data["key"])
    assert data["public_url"].endswith(".png")


async def test_sign_rejects_unsupported_content_type(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-up-bad-ct@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="BadCT")
    token = ws["tokens"]["access_token"]

    r = await client.post(
        "/uploads/logo/sign",
        json={"content_type": "application/pdf", "content_length": 1024},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422  # Literal[...] validator rejects


async def test_sign_rejects_oversized(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-up-big@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Big")
    token = ws["tokens"]["access_token"]

    r = await client.post(
        "/uploads/logo/sign",
        json={"content_type": "image/png", "content_length": 10 * 1024 * 1024},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


async def test_full_round_trip_upload_and_patch(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    """Sign → PUT to MinIO → PATCH workspace with the resulting public_url.

    Confirms (a) the signed policy is honored by MinIO, (b) the API HEADs the
    object before persisting `logo_url`, (c) the public_url is fetchable via
    HTTP without auth (anonymous download policy applied to the bucket)."""
    user = await sign_in(client, "test-up-roundtrip@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Round Club")
    token = ws["tokens"]["access_token"]

    # 1x1 transparent PNG (smallest valid PNG so we don't fight headers).
    png_bytes = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000d49444154789c63000100000005000100b50e5cf60000000049454e"
        "44ae426082"
    )

    sign = (
        await client.post(
            "/uploads/logo/sign",
            json={"content_type": "image/png", "content_length": len(png_bytes)},
            headers={"Authorization": f"Bearer {token}"},
        )
    ).json()

    # Upload using the policy.  MinIO's S3-compat layer accepts the same form
    # multipart shape boto3 produces — `data=` fields plus the file.
    fields: dict[str, Any] = dict(sign["fields"])
    async with httpx.AsyncClient(timeout=10.0) as s3_client:
        upload = await s3_client.post(
            sign["url"],
            data=fields,
            files={"file": ("logo.png", png_bytes, "image/png")},
        )
    assert upload.status_code in (200, 204), upload.text

    # PATCH workspace with the persisted URL.
    patch = await client.patch(
        "/workspaces/me",
        json={"logo_url": sign["public_url"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["logo_url"] == sign["public_url"]

    # Public URL is anonymously fetchable.
    async with httpx.AsyncClient(timeout=10.0) as anon:
        head = await anon.get(sign["public_url"])
    assert head.status_code == 200
    assert head.content == png_bytes


async def test_patch_rejects_url_for_missing_object(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    """A presigned URL alone doesn't grant the right to persist a logo_url —
    the object has to actually exist."""
    user = await sign_in(client, "test-up-missing@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Missing Obj")
    token = ws["tokens"]["access_token"]

    sign = (
        await client.post(
            "/uploads/logo/sign",
            json={"content_type": "image/png", "content_length": 4096},
            headers={"Authorization": f"Bearer {token}"},
        )
    ).json()

    # Skip the upload and try to persist the URL anyway.
    r = await client.patch(
        "/workspaces/me",
        json={"logo_url": sign["public_url"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400, r.text
