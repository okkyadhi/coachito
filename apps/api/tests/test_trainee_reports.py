"""GET /trainees/me/reports — RLS isolation + shape."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

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
            "DELETE FROM reports WHERE athlete_id IN ("
            "  SELECT id FROM athletes WHERE workspace_id IN ("
            "    SELECT id FROM workspaces WHERE owner_user_id IN ("
            "      SELECT id FROM users WHERE email LIKE 'test-trreports-%@example.com')))"
        )
        await conn.execute(
            "DELETE FROM workspaces WHERE owner_user_id IN ("
            "  SELECT id FROM users WHERE email LIKE 'test-trreports-%@example.com')"
        )
        await conn.execute(
            "DELETE FROM users WHERE email LIKE 'test-trreports-%@example.com'"
        )
    finally:
        await conn.close()


async def _claim(
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
    invite_code = created.json()["invite"]["code"]
    athlete_id = created.json()["trainee"]["id"]
    trainee = await sign_in(client, trainee_email, captured)
    claimed = await client.post(
        f"/invites/{invite_code}/claim",
        headers={"Authorization": f"Bearer {trainee['access_token']}"},
    )
    return {"tokens": claimed.json(), "athlete_id": athlete_id}


async def _insert_completed_report(
    *,
    workspace_id: str,
    athlete_id: str,
    coach_id: str,
    pdf_url: str,
    generated_minutes_ago: int = 1,
) -> str:
    """Direct insert — bypasses the RQ worker so the test stays
    fast + deterministic."""
    today = date.today()
    period_start = (today.replace(day=1) - timedelta(days=28))
    period_end = today
    conn = await superuser_conn()
    try:
        return await conn.fetchval(
            """
            INSERT INTO reports (
                workspace_id, athlete_id, coach_id,
                period_start, period_end,
                status, pdf_url, generated_at, generation_type
            ) VALUES ($1, $2, $3, $4, $5, 'completed', $6, $7, 'manual')
            RETURNING id::text
            """,
            workspace_id,
            athlete_id,
            coach_id,
            period_start,
            period_end,
            pdf_url,
            datetime.now(UTC) - timedelta(minutes=generated_minutes_ago),
        )
    finally:
        await conn.close()


async def test_empty_list_for_trainee_without_reports(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-trreports-c1@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="TR Club")
    andi = await _claim(
        client,
        coach_token=ws["tokens"]["access_token"],
        trainee_email="test-trreports-andi@example.com",
        captured=captured,
        name="Andi",
        phone="+628666666001",
    )
    r = await client.get(
        "/trainees/me/reports",
        headers={"Authorization": f"Bearer {andi['tokens']['access_token']}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["reports"] == []
    assert r.headers.get("cache-control") == "private, max-age=30"


async def test_trainee_sees_own_completed_reports(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    coach = await sign_in(client, "test-trreports-c2@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="TR Club 2")
    workspace_id = ws["workspace"]["id"]
    coach_id = coach["user"]["id"]

    andi = await _claim(
        client,
        coach_token=ws["tokens"]["access_token"],
        trainee_email="test-trreports-andi2@example.com",
        captured=captured,
        name="Andi",
        phone="+628666666002",
    )
    await _insert_completed_report(
        workspace_id=workspace_id,
        athlete_id=str(andi["athlete_id"]),
        coach_id=coach_id,
        pdf_url="http://minio:9000/coachito-dev/test.pdf",
    )

    r = await client.get(
        "/trainees/me/reports",
        headers={"Authorization": f"Bearer {andi['tokens']['access_token']}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["reports"]) == 1
    row = body["reports"][0]
    assert row["pdf_url"].endswith("test.pdf")
    assert row["coach_display_name"]


async def test_trainee_rls_isolation_between_athletes(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    """Trainee B never sees A's reports even if both are in the same
    workspace.  The endpoint joins through athletes.user_id; the RLS
    policy on `reports` also restricts cross-trainee reads."""
    coach = await sign_in(client, "test-trreports-c3@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="TR Club 3")
    workspace_id = ws["workspace"]["id"]
    coach_id = coach["user"]["id"]

    andi = await _claim(
        client,
        coach_token=ws["tokens"]["access_token"],
        trainee_email="test-trreports-andi3@example.com",
        captured=captured,
        name="Andi",
        phone="+628666666003",
    )
    budi = await _claim(
        client,
        coach_token=ws["tokens"]["access_token"],
        trainee_email="test-trreports-budi3@example.com",
        captured=captured,
        name="Budi",
        phone="+628666666004",
    )
    await _insert_completed_report(
        workspace_id=workspace_id,
        athlete_id=str(andi["athlete_id"]),
        coach_id=coach_id,
        pdf_url="http://minio:9000/coachito-dev/andi.pdf",
    )

    budi_resp = await client.get(
        "/trainees/me/reports",
        headers={"Authorization": f"Bearer {budi['tokens']['access_token']}"},
    )
    assert budi_resp.status_code == 200
    assert budi_resp.json()["reports"] == []
