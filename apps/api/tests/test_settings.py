"""PATCH /workspaces/me — happy path, audit, RBAC, validation."""

from __future__ import annotations

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from src import deps as deps_module
from src.config import settings
from src.db import session as session_module
from src.main import app

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


async def test_patch_updates_branding_and_writes_audit(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-set-admin@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Brand Club")
    token = ws["tokens"]["access_token"]
    workspace_id = ws["workspace"]["id"]

    r = await client.patch(
        "/workspaces/me",
        json={
            "name": "Brand Club Pro",
            "brand_color": "#E27D60",
            "tier_style": "skill",
            "allow_coach_overrides": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["name"] == "Brand Club Pro"
    assert data["brand_color"] == "#E27D60"
    assert data["tier_style"] == "skill"
    assert data["allow_coach_overrides"] is True

    # Audit row exists with the changed_fields list.
    conn = await asyncpg.connect(SUPERUSER_DSN)
    try:
        row = await conn.fetchrow(
            """
            SELECT action, metadata FROM audit_log
            WHERE workspace_id = $1 AND action = 'workspace.updated'
            ORDER BY created_at DESC LIMIT 1
            """,
            workspace_id,
        )
    finally:
        await conn.close()
    assert row is not None
    import json
    raw_meta = row["metadata"]
    meta = raw_meta if isinstance(raw_meta, dict) else json.loads(raw_meta)
    assert set(meta["changed_fields"]) == {
        "name", "brand_color", "tier_style", "allow_coach_overrides",
    }
    assert meta["changes"]["name"]["from"] == "Brand Club"
    assert meta["changes"]["name"]["to"] == "Brand Club Pro"


async def test_patch_persists_across_reload(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-set-persist@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Persist Club")
    token = ws["tokens"]["access_token"]

    await client.patch(
        "/workspaces/me",
        json={"name": "Persisted Club"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # GET /workspaces/mine should reflect the update.
    r = await client.get(
        "/workspaces/mine", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200, r.text
    name = r.json()["workspaces"][0]["workspace"]["name"]
    assert name == "Persisted Club"


async def test_patch_unchanged_does_not_write_audit(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    """Send the same values back; no audit row should be added."""
    user = await sign_in(client, "test-set-noop@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Noop Club")
    token = ws["tokens"]["access_token"]
    workspace_id = ws["workspace"]["id"]

    r = await client.patch(
        "/workspaces/me",
        json={"name": "Noop Club"},  # same as current
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text

    conn = await asyncpg.connect(SUPERUSER_DSN)
    try:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM audit_log WHERE workspace_id = $1 AND action='workspace.updated'",
            workspace_id,
        )
    finally:
        await conn.close()
    assert count == 0


async def test_patch_rejects_coach_role(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    """A coach (non-admin) joining a club workspace via SQL should get 403."""
    admin = await sign_in(client, "test-set-403admin@example.com", captured)
    ws = await create_workspace(client, admin["access_token"], name="Locked Club")
    workspace_id = ws["workspace"]["id"]

    coach = await sign_in(client, "test-set-403coach@example.com", captured)

    conn = await asyncpg.connect(SUPERUSER_DSN)
    try:
        await conn.execute(
            """
            INSERT INTO workspace_memberships (workspace_id, user_id, role, status, invited_at, joined_at)
            VALUES ($1, $2, 'coach', 'active', NOW(), NOW())
            """,
            workspace_id,
            coach["user"]["id"],
        )
    finally:
        await conn.close()

    # Coach switches into that workspace.
    switch = await client.post(
        f"/workspaces/{workspace_id}/switch",
        headers={"Authorization": f"Bearer {coach['access_token']}"},
    )
    assert switch.status_code == 200, switch.text
    coach_token = switch.json()["access_token"]

    r = await client.patch(
        "/workspaces/me",
        json={"name": "Hacked Club"},
        headers={"Authorization": f"Bearer {coach_token}"},
    )
    assert r.status_code == 403, r.text


async def test_patch_rejects_invalid_color(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-set-color@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Color Club")
    token = ws["tokens"]["access_token"]

    r = await client.patch(
        "/workspaces/me",
        json={"brand_color": "not-a-hex"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


async def test_patch_rejects_unrecognized_logo_url(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-set-logo@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Logo Club")
    token = ws["tokens"]["access_token"]

    r = await client.patch(
        "/workspaces/me",
        json={"logo_url": "https://evil.example.com/pwn.png"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
