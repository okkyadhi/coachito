"""POST /invites/{token}/claim — happy path, expiry, double-claim."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from src import deps as deps_module
from src.config import settings
from src.db import session as session_module
from src.main import app

from ._test_helpers import SUPERUSER_DSN, create_workspace, sign_in, superuser_conn


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


async def _create_trainee_invite(
    client: AsyncClient,
    *,
    coach_token: str,
    name: str = "Andi",
    phone: str = "+628123456789",
) -> dict[str, object]:
    r = await client.post(
        "/trainees",
        json={"name": name, "phone_e164": phone},
        headers={"Authorization": f"Bearer {coach_token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ── Tests ────────────────────────────────────────────────────────


async def test_claim_creates_membership_and_links_athlete(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-claim-coach@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="Claim Club")
    coach_token = ws["tokens"]["access_token"]

    created = await _create_trainee_invite(client, coach_token=coach_token)
    invite_code = created["invite"]["code"]
    athlete_id = created["trainee"]["id"]

    # Trainee signs in (separate user) and claims the invite.
    trainee = await sign_in(client, "test-claim-trainee@example.com", captured)
    r = await client.post(
        f"/invites/{invite_code}/claim",
        headers={"Authorization": f"Bearer {trainee['access_token']}"},
    )
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["user"]["role"] == "trainee"
    assert payload["user"]["current_workspace_id"] == ws["workspace"]["id"]

    # Verify DB side-effects.
    conn = await superuser_conn()
    try:
        membership_role = await conn.fetchval(
            "SELECT role FROM workspace_memberships WHERE user_id = $1 AND workspace_id = $2",
            trainee["user"]["id"],
            ws["workspace"]["id"],
        )
        athlete_user = await conn.fetchval(
            "SELECT user_id::text FROM athletes WHERE id = $1",
            athlete_id,
        )
        claimed_at = await conn.fetchval(
            "SELECT claimed_at FROM invites WHERE invite_code = $1",
            invite_code,
        )
    finally:
        await conn.close()

    assert membership_role == "trainee"
    assert athlete_user == trainee["user"]["id"]
    assert claimed_at is not None


async def test_claim_second_attempt_returns_410(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-claim-dbl-coach@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="Dbl Club")
    coach_token = ws["tokens"]["access_token"]
    created = await _create_trainee_invite(client, coach_token=coach_token)
    invite_code = created["invite"]["code"]

    trainee = await sign_in(client, "test-claim-dbl-trainee@example.com", captured)

    r1 = await client.post(
        f"/invites/{invite_code}/claim",
        headers={"Authorization": f"Bearer {trainee['access_token']}"},
    )
    assert r1.status_code == 200, r1.text

    r2 = await client.post(
        f"/invites/{invite_code}/claim",
        headers={"Authorization": f"Bearer {trainee['access_token']}"},
    )
    assert r2.status_code == 410, r2.text


async def test_claim_expired_token_returns_410(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-claim-exp-coach@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="Exp Club")
    coach_token = ws["tokens"]["access_token"]
    created = await _create_trainee_invite(client, coach_token=coach_token)
    invite_code = created["invite"]["code"]

    # Force the token to be expired.
    conn = await superuser_conn()
    try:
        await conn.execute(
            "UPDATE invites SET expires_at = $1 WHERE invite_code = $2",
            datetime.now(UTC) - timedelta(days=1),
            invite_code,
        )
    finally:
        await conn.close()

    trainee = await sign_in(client, "test-claim-exp-trainee@example.com", captured)
    r = await client.post(
        f"/invites/{invite_code}/claim",
        headers={"Authorization": f"Bearer {trainee['access_token']}"},
    )
    assert r.status_code == 410, r.text


async def test_claim_unknown_token_returns_404(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    trainee = await sign_in(client, "test-claim-404@example.com", captured)
    r = await client.post(
        "/invites/nonsense-token/claim",
        headers={"Authorization": f"Bearer {trainee['access_token']}"},
    )
    assert r.status_code == 404


async def test_claim_requires_auth(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-claim-noauth-coach@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="NoAuth Club")
    coach_token = ws["tokens"]["access_token"]
    created = await _create_trainee_invite(client, coach_token=coach_token)
    invite_code = created["invite"]["code"]

    r = await client.post(f"/invites/{invite_code}/claim")
    assert r.status_code in (401, 403)
