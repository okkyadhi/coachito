"""GET /sessions/today: shape, sort, RLS isolation."""

from __future__ import annotations

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from src import deps as deps_module
from src.config import settings
from src.db import session as session_module
from src.main import app

from ._test_helpers import (
    SUPERUSER_DSN,
    create_workspace,
    insert_assessment,
    insert_athlete,
    insert_session_today,
    sign_in,
    superuser_conn,
)


# ── Fixtures ─────────────────────────────────────────────────────


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
        await conn.execute(
            "DELETE FROM users WHERE email LIKE 'test-%@example.com'"
        )
    finally:
        await conn.close()


# ── Tests ────────────────────────────────────────────────────────


async def test_today_empty_when_no_sessions(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-sess-empty@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Empty Club")
    token = ws["tokens"]["access_token"]

    r = await client.get(
        "/sessions/today", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert r.json() == []


async def test_today_returns_sessions_with_trainee_and_tier(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-sess-coach@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Sessions Club")
    workspace_id = ws["workspace"]["id"]
    user_id = user["user"]["id"]
    token = ws["tokens"]["access_token"]

    conn = await superuser_conn()
    try:
        a1 = await insert_athlete(
            conn, workspace_id=workspace_id, coach_id=user_id,
            display_name="Test Alpha",
        )
        a2 = await insert_athlete(
            conn, workspace_id=workspace_id, coach_id=user_id,
            display_name="Test Bravo",
        )
        await insert_assessment(
            conn, workspace_id=workspace_id, athlete_id=a1, coach_id=user_id,
            skill_code="PADEL_TECH_FH", level=3, days_ago=2,
        )
        # Two sessions today, out of natural order to verify ASC sort
        await insert_session_today(
            conn, workspace_id=workspace_id, athlete_id=a1, coach_id=user_id,
            hour=14, minute=0, court="Court 1", focus="drilling",
        )
        await insert_session_today(
            conn, workspace_id=workspace_id, athlete_id=a2, coach_id=user_id,
            hour=8, minute=30, court="Court 2", focus="match_play",
        )
    finally:
        await conn.close()

    r = await client.get(
        "/sessions/today", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data) == 2
    # Sorted by scheduled_at ASC: Bravo (08:30) first, then Alpha (14:00)
    assert data[0]["trainee"]["display_name"] == "Test Bravo"
    assert data[0]["court"] == "Court 2"
    assert data[0]["focuses"] == ["match_play"]
    assert data[0]["trainee"]["last_assessed_at"] is None  # Bravo never assessed
    assert data[1]["trainee"]["display_name"] == "Test Alpha"
    assert data[1]["trainee"]["last_assessed_at"] is not None
    # current_tier is None because we never updated the cached field
    assert data[1]["trainee"]["current_tier"] is None


async def test_today_only_returns_calling_coach_sessions(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    """A session belonging to a different coach in the same workspace is
    filtered out at the query level (s.coach_id = :coach_id)."""
    alice = await sign_in(client, "test-sess-alice@example.com", captured)
    bob = await sign_in(client, "test-sess-bob@example.com", captured)

    alice_ws = await create_workspace(client, alice["access_token"], name="Alice's Club")
    workspace_id = alice_ws["workspace"]["id"]
    alice_token = alice_ws["tokens"]["access_token"]
    alice_id = alice["user"]["id"]
    bob_id = bob["user"]["id"]

    conn = await superuser_conn()
    try:
        athlete = await insert_athlete(
            conn, workspace_id=workspace_id, coach_id=alice_id,
            display_name="Shared Trainee",
        )
        # Two sessions for the same athlete — one taught by Alice, one by Bob.
        await insert_session_today(
            conn, workspace_id=workspace_id, athlete_id=athlete, coach_id=alice_id,
            hour=9,
        )
        await insert_session_today(
            conn, workspace_id=workspace_id, athlete_id=athlete, coach_id=bob_id,
            hour=10,
        )
    finally:
        await conn.close()

    r = await client.get(
        "/sessions/today", headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["scheduled_at"][11:13] == "09"  # Alice's only


async def test_today_rls_isolates_workspaces(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    """A coach in workspace A cannot see sessions in workspace B even if the
    same user is in both."""
    alice = await sign_in(client, "test-sess-rls-a@example.com", captured)
    a_ws = await create_workspace(client, alice["access_token"], name="A Club")
    a_id = a_ws["workspace"]["id"]
    a_token = a_ws["tokens"]["access_token"]

    bob = await sign_in(client, "test-sess-rls-b@example.com", captured)
    b_ws = await create_workspace(client, bob["access_token"], name="B Club")
    b_id = b_ws["workspace"]["id"]

    conn = await superuser_conn()
    try:
        b_athlete = await insert_athlete(
            conn, workspace_id=b_id, coach_id=bob["user"]["id"],
            display_name="Bob's Trainee",
        )
        # A session for Bob's coach in Bob's workspace — Alice must not see it.
        await insert_session_today(
            conn, workspace_id=b_id, athlete_id=b_athlete, coach_id=bob["user"]["id"],
            hour=11,
        )
    finally:
        await conn.close()

    # Alice queries with her A-workspace token → 0 results
    r = await client.get(
        "/sessions/today", headers={"Authorization": f"Bearer {a_token}"}
    )
    assert r.status_code == 200
    assert r.json() == []


async def test_today_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/sessions/today")
    assert r.status_code == 401
