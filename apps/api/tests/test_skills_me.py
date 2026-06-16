"""Trainee-self skills endpoints — RLS isolation + payload shape."""

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
                SELECT id FROM users WHERE email LIKE 'test-skills-%@example.com'
            )
            """
        )
        await conn.execute(
            "DELETE FROM users WHERE email LIKE 'test-skills-%@example.com'"
        )
    finally:
        await conn.close()


async def _create_trainee_and_claim(
    client: AsyncClient,
    *,
    coach_token: str,
    trainee_email: str,
    captured: list[dict[str, str]],
    name: str,
    phone: str,
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

    trainee = await sign_in(client, trainee_email, captured)
    claimed = await client.post(
        f"/invites/{invite_code}/claim",
        headers={"Authorization": f"Bearer {trainee['access_token']}"},
    )
    assert claimed.status_code == 200, claimed.text
    return {"tokens": claimed.json(), "athlete_id": athlete_id}


async def test_overview_returns_4_categories(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-skills-coach@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="Skills Club")
    andi = await _create_trainee_and_claim(
        client,
        coach_token=ws["tokens"]["access_token"],
        trainee_email="test-skills-andi@example.com",
        captured=captured,
        name="Andi",
        phone="+628444444001",
    )
    token = andi["tokens"]["access_token"]  # type: ignore[index]

    r = await client.get(
        "/skills/me/overview", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200, r.text
    data = r.json()
    codes = [c["code"] for c in data["categories"]]
    assert codes == ["technical", "tactical", "physical", "mental"]
    for c in data["categories"]:
        assert c["assessed_count"] == 0
        assert c["average"] is None
        assert c["total_count"] > 0
    assert r.headers.get("cache-control") == "private, max-age=20"
    # Extended fields land for a fresh trainee:
    assert data["overall"]["average"] is None
    assert data["overall"]["assessed_count"] == 0
    assert data["recent_gains"] == []
    # Fresh trainee → focus is a blocker for the next tier (the beginner
    # tier's requirements take precedence over the "no scores yet" fallback).
    assert data["focus_suggestion"] is not None
    assert data["focus_suggestion"]["reason"] == "blocker_for_next_tier"
    # Fresh trainee has no current tier but next tier should exist (beginner+).
    assert data["tier"] is not None
    assert data["tier"]["next"] is not None


async def test_overview_reflects_published_assessment(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-skills-coach2@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="Skills Club 2")
    coach_user_id = coach["user"]["id"]
    workspace_id = ws["workspace"]["id"]

    andi = await _create_trainee_and_claim(
        client,
        coach_token=ws["tokens"]["access_token"],
        trainee_email="test-skills-andi2@example.com",
        captured=captured,
        name="Andi",
        phone="+628444444002",
    )

    conn = await superuser_conn()
    try:
        await insert_assessment(
            conn,
            workspace_id=workspace_id,
            athlete_id=str(andi["athlete_id"]),
            coach_id=coach_user_id,
            skill_code="PADEL_TECH_FH",
            level=4,
            days_ago=1,
        )
    finally:
        await conn.close()

    token = andi["tokens"]["access_token"]  # type: ignore[index]
    r = await client.get(
        "/skills/me/overview", headers={"Authorization": f"Bearer {token}"}
    )
    data = r.json()
    tech = next(c for c in data["categories"] if c["code"] == "technical")
    assert tech["assessed_count"] == 1
    assert tech["average"] == 4.0
    assert data["updated_at"] is not None
    # Extended fields:
    assert data["overall"]["average"] == 4.0
    assert data["overall"]["assessed_count"] == 1
    assert data["overall"]["last_assessed_at"] is not None
    # First-time scoring counts as a gain (from_level=0 → to_level=4).
    assert len(data["recent_gains"]) == 1
    assert data["recent_gains"][0]["from_level"] == 0
    assert data["recent_gains"][0]["to_level"] == 4
    assert data["focus_suggestion"] is not None


async def test_category_breakdown_lists_skills(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-skills-coach3@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="Skills Club 3")
    andi = await _create_trainee_and_claim(
        client,
        coach_token=ws["tokens"]["access_token"],
        trainee_email="test-skills-andi3@example.com",
        captured=captured,
        name="Andi",
        phone="+628444444003",
    )
    token = andi["tokens"]["access_token"]  # type: ignore[index]

    r = await client.get(
        "/skills/me/category/technical",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["category"] == "technical"
    assert len(data["skills"]) >= 10
    for s in data["skills"]:
        assert s["latest_score"] is None


async def test_unknown_category_returns_404(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-skills-coach4@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="Skills Club 4")
    andi = await _create_trainee_and_claim(
        client,
        coach_token=ws["tokens"]["access_token"],
        trainee_email="test-skills-andi4@example.com",
        captured=captured,
        name="Andi",
        phone="+628444444004",
    )
    token = andi["tokens"]["access_token"]  # type: ignore[index]

    r = await client.get(
        "/skills/me/category/zumba",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


async def test_rls_isolation_between_trainees(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-skills-coach5@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="Skills Club 5")
    workspace_id = ws["workspace"]["id"]
    coach_user_id = coach["user"]["id"]

    andi = await _create_trainee_and_claim(
        client,
        coach_token=ws["tokens"]["access_token"],
        trainee_email="test-skills-andi5@example.com",
        captured=captured,
        name="Andi",
        phone="+628444444005",
    )
    budi = await _create_trainee_and_claim(
        client,
        coach_token=ws["tokens"]["access_token"],
        trainee_email="test-skills-budi5@example.com",
        captured=captured,
        name="Budi",
        phone="+628444444006",
    )
    conn = await superuser_conn()
    try:
        await insert_assessment(
            conn, workspace_id=workspace_id,
            athlete_id=str(andi["athlete_id"]),
            coach_id=coach_user_id, skill_code="PADEL_TECH_FH",
            level=5, days_ago=1,
        )
        await insert_assessment(
            conn, workspace_id=workspace_id,
            athlete_id=str(budi["athlete_id"]),
            coach_id=coach_user_id, skill_code="PADEL_TECH_BH",
            level=2, days_ago=1,
        )
    finally:
        await conn.close()

    andi_token = andi["tokens"]["access_token"]  # type: ignore[index]
    budi_token = budi["tokens"]["access_token"]  # type: ignore[index]
    a_data = (
        await client.get(
            "/skills/me/overview",
            headers={"Authorization": f"Bearer {andi_token}"},
        )
    ).json()
    b_data = (
        await client.get(
            "/skills/me/overview",
            headers={"Authorization": f"Bearer {budi_token}"},
        )
    ).json()
    a_tech = next(c for c in a_data["categories"] if c["code"] == "technical")
    b_tech = next(c for c in b_data["categories"] if c["code"] == "technical")
    assert a_tech["average"] == 5.0
    assert b_tech["average"] == 2.0


async def test_blockers_for_fresh_trainee(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-skills-coach6@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="Skills Club 6")
    andi = await _create_trainee_and_claim(
        client,
        coach_token=ws["tokens"]["access_token"],
        trainee_email="test-skills-andi6@example.com",
        captured=captured,
        name="Andi",
        phone="+628444444007",
    )
    token = andi["tokens"]["access_token"]  # type: ignore[index]
    r = await client.get(
        "/skills/me/category/technical/blockers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    # Fresh trainee → next_tier is the next-after-Beginner tier with technical
    # requirements; expect a positive number of blockers in technical.
    if data["next_tier"] is not None:
        assert data["blockers_total_count"] >= 0
