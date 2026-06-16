"""Multi-sport workspace flow (tennis-skill-framework-v0.1 §3).

Exercises the M2/M3 surface end to end against the real API:
- a fresh workspace lists exactly one sport (padel) by default
- single-sport plans can't add a second sport (402); Club Pro can
- enabling tennis surfaces it in workspace.sports[] and /workspaces/me/sports
- a coach can assess in the sport they're qualified for; a coach scoped to
  only padel is blocked (403) from assessing tennis
- assessment + session rows carry the resolved sport_id
"""

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
            "DELETE FROM workspaces WHERE owner_user_id IN ("
            "  SELECT id FROM users WHERE email LIKE 'test-ms-%@example.com')"
        )
        await conn.execute(
            "DELETE FROM users WHERE email LIKE 'test-ms-%@example.com'"
        )
    finally:
        await conn.close()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _bump_plan(workspace_id: str, plan: str) -> None:
    conn = await asyncpg.connect(SUPERUSER_DSN)
    try:
        await conn.execute(
            "UPDATE workspaces SET plan = $1 WHERE id = $2", plan, workspace_id
        )
    finally:
        await conn.close()


async def test_new_workspace_has_one_sport(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-ms-a@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="One Sport")
    token = ws["tokens"]["access_token"]

    # workspace.sports[] populated with padel
    assert len(ws["workspace"]["sports"]) == 1
    assert ws["workspace"]["sports"][0]["sport_code"] == "padel"

    r = await client.get("/workspaces/me/sports", headers=_auth(token))
    assert r.status_code == 200
    sports = r.json()["sports"]
    assert [s["sport_code"] for s in sports] == ["padel"]
    assert sports[0]["curriculum_code"] == "padel-default-appa"


async def test_single_sport_plan_blocks_second_sport(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-ms-b@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="Trial Club")
    token = ws["tokens"]["access_token"]
    tennis_id = await _tennis_sport_id()

    r = await client.post(
        "/workspaces/me/sports",
        json={"sport_id": tennis_id},
        headers=_auth(token),
    )
    assert r.status_code == 402, r.text


async def test_club_pro_enables_tennis_and_scopes_coach(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-ms-c@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="Dual Club")
    token = ws["tokens"]["access_token"]
    wid = ws["workspace"]["id"]
    tennis_id = await _tennis_sport_id()

    await _bump_plan(wid, "club_pro")

    # Enable tennis.
    r = await client.post(
        "/workspaces/me/sports",
        json={"sport_id": tennis_id},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    codes = {s["sport_code"] for s in r.json()["sports"]}
    assert codes == {"padel", "tennis"}

    # Add a trainee, then enroll them in tennis.
    athlete_resp = await client.post(
        "/trainees",
        json={"name": "Multi Sport Kid", "phone_e164": "+628123456701"},
        headers=_auth(token),
    )
    assert athlete_resp.status_code in (200, 201), athlete_resp.text
    athlete_id = athlete_resp.json()["trainee"]["id"]

    r = await client.patch(
        f"/athletes/{athlete_id}/sports",
        json={"sport_ids": [tennis_id]},
        headers=_auth(token),
    )
    assert r.status_code == 204, r.text

    # The owner enabled tennis, so they're qualified — assess in tennis.
    draft = await client.post(
        "/assessments",
        json={
            "athlete_id": athlete_id,
            "sport_id": tennis_id,
            "summary": "Tennis baseline",
            "scores": [],
        },
        headers=_auth(token),
    )
    assert draft.status_code in (200, 201), draft.text

    # Assessment row carries the tennis sport_id.
    conn = await asyncpg.connect(SUPERUSER_DSN)
    try:
        sport_code = await conn.fetchval(
            """
            SELECT sp.code FROM assessments a
            JOIN sports sp ON sp.id = a.sport_id
            WHERE a.athlete_id = $1
            ORDER BY a.created_at DESC LIMIT 1
            """,
            athlete_id,
        )
    finally:
        await conn.close()
    assert sport_code == "tennis"


async def test_coach_scoped_to_padel_cannot_assess_tennis(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-ms-d@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="Scoped Club")
    token = ws["tokens"]["access_token"]
    wid = ws["workspace"]["id"]
    tennis_id = await _tennis_sport_id()
    await _bump_plan(wid, "club_pro")
    await client.post(
        "/workspaces/me/sports",
        json={"sport_id": tennis_id},
        headers=_auth(token),
    )

    athlete_resp = await client.post(
        "/trainees",
        json={"name": "Tennis Only Kid", "phone_e164": "+628123456702"},
        headers=_auth(token),
    )
    athlete_id = athlete_resp.json()["trainee"]["id"]

    # Re-scope the owner's membership to padel only (revokes the auto-grant).
    conn = await asyncpg.connect(SUPERUSER_DSN)
    try:
        await conn.execute(
            """
            DELETE FROM membership_sports ms
            USING workspace_memberships m, sports sp
            WHERE ms.membership_id = m.id AND m.workspace_id = $1
              AND ms.sport_id = sp.id AND sp.code = 'tennis'
            """,
            wid,
        )
    finally:
        await conn.close()

    draft = await client.post(
        "/assessments",
        json={
            "athlete_id": athlete_id,
            "sport_id": tennis_id,
            "summary": "Should be blocked",
            "scores": [],
        },
        headers=_auth(token),
    )
    assert draft.status_code == 403, draft.text


async def _tennis_sport_id() -> str:
    conn = await asyncpg.connect(SUPERUSER_DSN)
    try:
        return str(await conn.fetchval("SELECT id FROM sports WHERE code = 'tennis'"))
    finally:
        await conn.close()
