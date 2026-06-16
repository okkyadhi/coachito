"""GET /trainees: shape, sort order, fuzzy search, pagination, RLS isolation."""

from __future__ import annotations

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from src import deps as deps_module
from src.athletes.service import decode_cursor, encode_cursor
from src.config import settings
from src.db import session as session_module
from src.main import app

from ._test_helpers import (
    SUPERUSER_DSN,
    create_workspace,
    insert_assessment,
    insert_athlete,
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


# ── Cursor primitives ────────────────────────────────────────────


def test_cursor_roundtrip() -> None:
    assert decode_cursor(encode_cursor(0)) == 0
    assert decode_cursor(encode_cursor(42)) == 42
    assert decode_cursor(encode_cursor(1000)) == 1000


def test_cursor_garbage_safely_falls_back_to_zero() -> None:
    assert decode_cursor(None) == 0
    assert decode_cursor("") == 0
    assert decode_cursor("not-base64!!!") == 0
    assert decode_cursor("aGVsbG8=") == 0  # decodes to "hello" → not an int


# ── Endpoint tests ───────────────────────────────────────────────


async def test_trainees_empty_when_no_athletes(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-tr-empty@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Empty Club")
    token = ws["tokens"]["access_token"]

    r = await client.get("/trainees", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body == {"athletes": [], "next_cursor": None}


async def test_trainees_sorted_by_last_assessed_desc(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-tr-sort@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Sort Club")
    workspace_id = ws["workspace"]["id"]
    user_id = user["user"]["id"]
    token = ws["tokens"]["access_token"]

    conn = await superuser_conn()
    try:
        a_old = await insert_athlete(
            conn, workspace_id=workspace_id, coach_id=user_id,
            display_name="Test Old Assessment",
        )
        a_recent = await insert_athlete(
            conn, workspace_id=workspace_id, coach_id=user_id,
            display_name="Test Recent Assessment",
        )
        a_never = await insert_athlete(
            conn, workspace_id=workspace_id, coach_id=user_id,
            display_name="Test Never Assessed",
        )
        await insert_assessment(
            conn, workspace_id=workspace_id, athlete_id=a_old, coach_id=user_id,
            days_ago=30,
        )
        await insert_assessment(
            conn, workspace_id=workspace_id, athlete_id=a_recent, coach_id=user_id,
            days_ago=1,
        )
        _ = a_never  # never assessed
    finally:
        await conn.close()

    r = await client.get("/trainees", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    names = [a["display_name"] for a in r.json()["athletes"]]
    # Recent first, then old, then never-assessed (NULLs last)
    assert names == [
        "Test Recent Assessment",
        "Test Old Assessment",
        "Test Never Assessed",
    ]


async def test_trainees_fuzzy_search(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-tr-search@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Search Club")
    workspace_id = ws["workspace"]["id"]
    user_id = user["user"]["id"]
    token = ws["tokens"]["access_token"]

    conn = await superuser_conn()
    try:
        for name in ["Andi Pratama", "Rina Sari", "Andrea Wibowo", "Budi Santoso"]:
            await insert_athlete(
                conn, workspace_id=workspace_id, coach_id=user_id, display_name=name,
            )
    finally:
        await conn.close()

    # "and" should match Andi + Andrea + (also "Santoso" doesn't have it…
    # actually it's case-insensitive substring so only the And* ones).
    r = await client.get(
        "/trainees", params={"q": "and"},
        headers={"Authorization": f"Bearer {token}"},
    )
    names = {a["display_name"] for a in r.json()["athletes"]}
    assert names == {"Andi Pratama", "Andrea Wibowo"}

    # Empty result for clearly-absent query
    r = await client.get(
        "/trainees", params={"q": "zzzz"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.json()["athletes"] == []


async def test_trainees_pagination(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-tr-page@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Page Club")
    workspace_id = ws["workspace"]["id"]
    user_id = user["user"]["id"]
    token = ws["tokens"]["access_token"]

    conn = await superuser_conn()
    try:
        for i in range(5):
            athlete = await insert_athlete(
                conn, workspace_id=workspace_id, coach_id=user_id,
                display_name=f"Test Athlete {i:02d}",
            )
            # Stagger assessment timestamps so the sort is deterministic
            await insert_assessment(
                conn, workspace_id=workspace_id, athlete_id=athlete,
                coach_id=user_id, days_ago=10 - i,  # 10..6
            )
    finally:
        await conn.close()

    # Page 1: limit=2
    r = await client.get(
        "/trainees", params={"limit": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    page1 = r.json()
    assert len(page1["athletes"]) == 2
    assert page1["next_cursor"] is not None
    # Most-recently-assessed (days_ago=6 → athlete 04) is first
    assert page1["athletes"][0]["display_name"] == "Test Athlete 04"

    # Page 2: same limit, with cursor
    r = await client.get(
        "/trainees",
        params={"limit": 2, "cursor": page1["next_cursor"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    page2 = r.json()
    assert len(page2["athletes"]) == 2
    # No overlap
    page1_ids = {a["id"] for a in page1["athletes"]}
    page2_ids = {a["id"] for a in page2["athletes"]}
    assert page1_ids.isdisjoint(page2_ids)

    # Page 3: last athlete, no further cursor
    r = await client.get(
        "/trainees",
        params={"limit": 2, "cursor": page2["next_cursor"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    page3 = r.json()
    assert len(page3["athletes"]) == 1
    assert page3["next_cursor"] is None


async def test_trainees_rls_isolates_workspaces(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    alice = await sign_in(client, "test-tr-rls-a@example.com", captured)
    a_ws = await create_workspace(client, alice["access_token"], name="A Club")
    a_id = a_ws["workspace"]["id"]
    a_token = a_ws["tokens"]["access_token"]

    bob = await sign_in(client, "test-tr-rls-b@example.com", captured)
    b_ws = await create_workspace(client, bob["access_token"], name="B Club")
    b_id = b_ws["workspace"]["id"]

    conn = await superuser_conn()
    try:
        await insert_athlete(
            conn, workspace_id=a_id, coach_id=alice["user"]["id"],
            display_name="Test Alice's Trainee",
        )
        await insert_athlete(
            conn, workspace_id=b_id, coach_id=bob["user"]["id"],
            display_name="Test Bob's Trainee",
        )
    finally:
        await conn.close()

    r = await client.get("/trainees", headers={"Authorization": f"Bearer {a_token}"})
    names = [a["display_name"] for a in r.json()["athletes"]]
    assert names == ["Test Alice's Trainee"]


async def test_trainees_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/trainees")
    assert r.status_code == 401
