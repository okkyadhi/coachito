"""Trainee-scoped RLS: trainee A sees only A's data, never B's.

After claiming an invite the trainee user has role=trainee in the workspace
plus athletes.user_id linked.  Migration 0015's policy restricts athletes/
assessments/sessions to rows where athlete.user_id = current_user_id.

We exercise that via /trainees/me/home + a direct /trainees query (which
returns 0 athletes for a trainee since they can't see other trainees), and
/workspaces/public/{slug} as a quick sanity check on the public branding.
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
                SELECT id FROM users WHERE email LIKE 'test-%@example.com'
            )
            """
        )
        await conn.execute("DELETE FROM users WHERE email LIKE 'test-%@example.com'")
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
    """Create the athlete + invite via coach, then claim as the trainee.

    Returns the trainee's TokenPair (post-claim, scoped to the workspace).
    """
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


# ── Tests ────────────────────────────────────────────────────────


async def test_trainee_home_returns_own_profile(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-scope-coach@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="Scope Club")
    coach_token = ws["tokens"]["access_token"]

    claim = await _create_trainee_and_claim(
        client,
        coach_token=coach_token,
        trainee_email="test-scope-andi@example.com",
        captured=captured,
        name="Andi",
        phone="+628111111111",
    )
    trainee_token = claim["tokens"]["access_token"]  # type: ignore[index]

    r = await client.get(
        "/trainees/me/home", headers={"Authorization": f"Bearer {trainee_token}"}
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["trainee_first_name"] == "Andi"
    assert data["workspace_name"] == "Scope Club"
    assert data["has_assessment"] is False
    assert len(data["rhythm_days14"]) == 14


async def test_trainee_rls_isolates_assessments_between_trainees(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    """Two trainees in the same workspace.  Coach assesses both.  Each
    trainee's /me/home reflects only their own scores."""
    coach = await sign_in(client, "test-iso-coach@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="Iso Club")
    coach_token = ws["tokens"]["access_token"]
    workspace_id = ws["workspace"]["id"]
    coach_user_id = coach["user"]["id"]

    andi = await _create_trainee_and_claim(
        client,
        coach_token=coach_token,
        trainee_email="test-iso-andi@example.com",
        captured=captured,
        name="Andi",
        phone="+628222222001",
    )
    budi = await _create_trainee_and_claim(
        client,
        coach_token=coach_token,
        trainee_email="test-iso-budi@example.com",
        captured=captured,
        name="Budi",
        phone="+628222222002",
    )

    # Inject distinct assessments directly (RLS-bypass) so we don't depend on
    # the /assessments endpoint.
    conn = await superuser_conn()
    try:
        await insert_assessment(
            conn,
            workspace_id=workspace_id,
            athlete_id=str(andi["athlete_id"]),
            coach_id=coach_user_id,
            skill_code="PADEL_TECH_FH",
            level=3,
            days_ago=1,
        )
        await insert_assessment(
            conn,
            workspace_id=workspace_id,
            athlete_id=str(budi["athlete_id"]),
            coach_id=coach_user_id,
            skill_code="PADEL_TECH_BH",
            level=1,
            days_ago=1,
        )
    finally:
        await conn.close()

    andi_token = andi["tokens"]["access_token"]  # type: ignore[index]
    budi_token = budi["tokens"]["access_token"]  # type: ignore[index]

    andi_home = (
        await client.get(
            "/trainees/me/home", headers={"Authorization": f"Bearer {andi_token}"}
        )
    ).json()
    budi_home = (
        await client.get(
            "/trainees/me/home", headers={"Authorization": f"Bearer {budi_token}"}
        )
    ).json()

    assert andi_home["trainee_first_name"] == "Andi"
    assert andi_home["has_assessment"] is True
    technical_andi = next(c for c in andi_home["category_averages"] if c["category"] == "technical")
    # Andi only has a level-3 forehand → average 3, one skill rated.
    assert technical_andi["skills_rated"] == 1
    assert technical_andi["average"] == 3.0

    assert budi_home["trainee_first_name"] == "Budi"
    assert budi_home["has_assessment"] is True
    technical_budi = next(c for c in budi_home["category_averages"] if c["category"] == "technical")
    assert technical_budi["skills_rated"] == 1
    assert technical_budi["average"] == 1.0


async def test_trainee_cannot_list_other_trainees(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    """GET /trainees from a trainee account returns only their own row (RLS)."""
    coach = await sign_in(client, "test-list-coach@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="List Club")
    coach_token = ws["tokens"]["access_token"]

    andi = await _create_trainee_and_claim(
        client,
        coach_token=coach_token,
        trainee_email="test-list-andi@example.com",
        captured=captured,
        name="Andi",
        phone="+628333333001",
    )
    await _create_trainee_and_claim(
        client,
        coach_token=coach_token,
        trainee_email="test-list-budi@example.com",
        captured=captured,
        name="Budi",
        phone="+628333333002",
    )

    andi_token = andi["tokens"]["access_token"]  # type: ignore[index]
    r = await client.get(
        "/trainees", headers={"Authorization": f"Bearer {andi_token}"}
    )
    assert r.status_code == 200, r.text
    rows = r.json()["athletes"]
    assert len(rows) == 1
    assert rows[0]["display_name"] == "Andi"


async def test_public_workspace_endpoint_returns_branding(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-pub-coach@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="Pub Club")
    workspace_id = ws["workspace"]["id"]

    # Looked up by id (no slug populated yet in tests).
    r = await client.get(f"/workspaces/public/{workspace_id}")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["name"] == "Pub Club"
    assert data["sport_code"] == "padel"
    assert r.headers["cache-control"] == "public, max-age=300"


async def test_public_workspace_unknown_returns_404(client: AsyncClient) -> None:
    r = await client.get("/workspaces/public/no-such-slug")
    assert r.status_code == 404
