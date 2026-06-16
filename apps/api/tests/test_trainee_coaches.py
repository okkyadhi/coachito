"""GET /trainees/me/coaches and GET /coaches/:id — smoke tests."""

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
    insert_session_today,
    sign_in,
    superuser_conn,
)


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
            """
            DELETE FROM workspaces WHERE owner_user_id IN (
                SELECT id FROM users WHERE email LIKE 'test-tcoach-%@example.com'
            )
            """
        )
        await conn.execute(
            "DELETE FROM users WHERE email LIKE 'test-tcoach-%@example.com'"
        )
    finally:
        await conn.close()


async def _claim(
    client: AsyncClient, coach_token: str, email: str, name: str,
    phone: str, captured: list[dict[str, str]],
) -> dict[str, object]:
    created = await client.post(
        "/trainees",
        json={"name": name, "phone_e164": phone},
        headers={"Authorization": f"Bearer {coach_token}"},
    )
    assert created.status_code == 201, created.text
    payload = created.json()
    invite_code = payload["invite"]["code"]
    athlete_id = payload["trainee"]["id"]
    trainee = await sign_in(client, email, captured)
    claimed = await client.post(
        f"/invites/{invite_code}/claim",
        headers={"Authorization": f"Bearer {trainee['access_token']}"},
    )
    return {"tokens": claimed.json(), "athlete_id": athlete_id}


async def test_empty_coach_list_for_fresh_trainee(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-tcoach-c1@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="TC Club")
    andi = await _claim(
        client, ws["tokens"]["access_token"],
        "test-tcoach-andi@example.com", "Andi", "+628555555001", captured,
    )
    r = await client.get(
        "/trainees/me/coaches",
        headers={"Authorization": f"Bearer {andi['tokens']['access_token']}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["coaches"] == []


async def test_coach_list_includes_session_coach(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-tcoach-c2@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="TC Club 2")
    coach_user_id = coach["user"]["id"]
    workspace_id = ws["workspace"]["id"]

    andi = await _claim(
        client, ws["tokens"]["access_token"],
        "test-tcoach-andi2@example.com", "Andi", "+628555555002", captured,
    )

    conn = await superuser_conn()
    try:
        await insert_session_today(
            conn,
            workspace_id=workspace_id,
            athlete_id=str(andi["athlete_id"]),
            coach_id=coach_user_id,
        )
    finally:
        await conn.close()

    r = await client.get(
        "/trainees/me/coaches",
        headers={"Authorization": f"Bearer {andi['tokens']['access_token']}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["coaches"]) == 1
    assert data["coaches"][0]["coach_id"] == coach_user_id


async def test_coach_bio_returns_404_for_other_workspace(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach_a = await sign_in(client, "test-tcoach-ca@example.com", captured)
    ws_a = await create_workspace(client, coach_a["access_token"], name="WS A")
    # Coach B in their own workspace — but trainee is in WS A; bio request
    # for coach B from WS A's context should 404.
    coach_b = await sign_in(client, "test-tcoach-cb@example.com", captured)
    await create_workspace(client, coach_b["access_token"], name="WS B")

    andi = await _claim(
        client, ws_a["tokens"]["access_token"],
        "test-tcoach-andiA@example.com", "Andi", "+628555555003", captured,
    )
    r = await client.get(
        f"/coaches/{coach_b['user']['id']}",
        headers={"Authorization": f"Bearer {andi['tokens']['access_token']}"},
    )
    assert r.status_code == 404


async def test_coach_bio_returns_data_for_shared_workspace(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-tcoach-cd@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="TC Club D")
    andi = await _claim(
        client, ws["tokens"]["access_token"],
        "test-tcoach-andiD@example.com", "Andi", "+628555555004", captured,
    )
    r = await client.get(
        f"/coaches/{coach['user']['id']}",
        headers={"Authorization": f"Bearer {andi['tokens']['access_token']}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["coach_id"] == coach["user"]["id"]
    # Coach has no bio yet → defaults to empty object.
    assert data["bio"]["headline"] is None
    assert data["coached_trainees_count"] == 0
