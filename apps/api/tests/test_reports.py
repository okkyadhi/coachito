"""Reports HTTP surface + PDF generation worker.

The worker isn't running in-process during pytest — we invoke the RQ job's
underlying function directly to avoid flake from the queue.  That still
exercises the asyncpg + Jinja + WeasyPrint + S3 path end-to-end."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import asyncpg
import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from src import deps as deps_module
from src.config import settings
from src.db import session as session_module
from src.main import app
from src.reports.cron import prior_month_range, run_monthly_async
from src.reports.jobs import generate_report_pdf_async
from src.uploads import s3 as s3_module

from ._test_helpers import (
    SUPERUSER_DSN,
    create_workspace,
    insert_assessment,
    insert_athlete,
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
    captured: list[dict[str, str]] = []

    async def fake_send(*, email: str, link: str) -> None:
        captured.append({"email": email, "link": link})

    monkeypatch.setattr("src.auth.router.send_magic_link_email", fake_send)
    return captured


@pytest.fixture(autouse=True)
async def _s3_public_aligned(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inside-container HTTP runs over docker network; align the public
    endpoint so signed/public URLs are reachable from this process."""
    monkeypatch.setattr(settings, "s3_public_endpoint", settings.s3_endpoint)
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


# ── Helpers ──────────────────────────────────────────────────────


async def _scaffold(client: AsyncClient, captured: list[dict[str, str]], email: str):
    user = await sign_in(client, email, captured)
    ws = await create_workspace(client, user["access_token"], name="Reports Club")
    workspace_id = ws["workspace"]["id"]
    user_id = user["user"]["id"]
    token = ws["tokens"]["access_token"]

    conn = await superuser_conn()
    try:
        athlete_id = await insert_athlete(
            conn, workspace_id=workspace_id, coach_id=user_id, display_name="Andi"
        )
        # Two assessments in the prior month so the cron can pick this up.
        ps, pe = prior_month_range()
        await insert_assessment(
            conn,
            workspace_id=workspace_id,
            athlete_id=athlete_id,
            coach_id=user_id,
            skill_code="PADEL_TECH_FH",
            level=3,
            days_ago=max(int((datetime.now(UTC).date() - ps).days) - 2, 1),
        )
        await insert_assessment(
            conn,
            workspace_id=workspace_id,
            athlete_id=athlete_id,
            coach_id=user_id,
            skill_code="PADEL_TECH_BH",
            level=2,
            days_ago=max(int((datetime.now(UTC).date() - ps).days) - 5, 1),
        )
    finally:
        await conn.close()
    return {
        "token": token,
        "workspace_id": workspace_id,
        "athlete_id": athlete_id,
        "user_id": user_id,
    }


# ── Tests ────────────────────────────────────────────────────────


async def test_post_returns_202_and_job_runs_to_completion(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _scaffold(client, captured, "test-rp-happy@example.com")
    today = datetime.now(UTC).date()
    period_start = today.replace(day=1) - timedelta(days=28)
    period_end = today

    r = await client.post(
        "/reports",
        json={
            "athlete_id": s["athlete_id"],
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        },
        headers={"Authorization": f"Bearer {s['token']}"},
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["report"]["status"] == "pending"
    report_id = body["report"]["id"]

    # Invoke the worker function directly (avoid queue flake in tests).
    result = await generate_report_pdf_async(report_id)
    assert result["status"] == "completed", result
    assert result["bytes"] > 1000  # real PDF, not an empty file

    # GET /reports/:id now shows status=completed + pdf_url.
    poll = await client.get(
        f"/reports/{report_id}",
        headers={"Authorization": f"Bearer {s['token']}"},
    )
    assert poll.status_code == 200, poll.text
    payload = poll.json()
    assert payload["status"] == "completed"
    assert payload["pdf_url"]

    # The public URL is fetchable + bytes match what the job uploaded.
    async with httpx.AsyncClient(timeout=10.0) as anon:
        fetched = await anon.get(payload["pdf_url"])
    assert fetched.status_code == 200
    assert fetched.content[:5] == b"%PDF-"
    assert len(fetched.content) == result["bytes"]


async def test_list_returns_reports_newest_first(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _scaffold(client, captured, "test-rp-list@example.com")
    period_start = datetime.now(UTC).date().replace(day=1) - timedelta(days=28)
    period_end = datetime.now(UTC).date()

    first = await client.post(
        "/reports",
        json={
            "athlete_id": s["athlete_id"],
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        },
        headers={"Authorization": f"Bearer {s['token']}"},
    )
    assert first.status_code == 202
    await generate_report_pdf_async(first.json()["report"]["id"])

    r = await client.get(
        "/reports", headers={"Authorization": f"Bearer {s['token']}"}
    )
    assert r.status_code == 200, r.text
    reports = r.json()["reports"]
    assert len(reports) == 1
    assert reports[0]["status"] == "completed"


async def test_post_rejects_unknown_trainee(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _scaffold(client, captured, "test-rp-404@example.com")
    r = await client.post(
        "/reports",
        json={
            "athlete_id": "00000000-0000-0000-0000-000000000000",
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
        },
        headers={"Authorization": f"Bearer {s['token']}"},
    )
    assert r.status_code == 404


async def test_post_rejects_inverted_period(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _scaffold(client, captured, "test-rp-period@example.com")
    r = await client.post(
        "/reports",
        json={
            "athlete_id": s["athlete_id"],
            "period_start": "2026-04-30",
            "period_end": "2026-04-01",
        },
        headers={"Authorization": f"Bearer {s['token']}"},
    )
    assert r.status_code == 400


async def test_view_count_increments(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _scaffold(client, captured, "test-rp-view@example.com")
    today = datetime.now(UTC).date()
    period_start = today.replace(day=1) - timedelta(days=28)
    period_end = today
    created = await client.post(
        "/reports",
        json={
            "athlete_id": s["athlete_id"],
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        },
        headers={"Authorization": f"Bearer {s['token']}"},
    )
    report_id = created.json()["report"]["id"]
    await generate_report_pdf_async(report_id)

    for _ in range(3):
        v = await client.post(
            f"/reports/{report_id}/view",
            headers={"Authorization": f"Bearer {s['token']}"},
        )
        assert v.status_code == 204

    final = await client.get(
        f"/reports/{report_id}",
        headers={"Authorization": f"Bearer {s['token']}"},
    )
    assert final.json()["view_count"] == 3


async def test_monthly_cron_dry_lists_candidates(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    """Seed an assessment in the prior month, then run the cron --dry."""
    await _scaffold(client, captured, "test-rp-cron@example.com")
    out = await run_monthly_async(dry_run=True)
    names = {row["trainee"] for row in out}
    assert "Andi" in names
    for row in out:
        assert row["dry_run"] is True


async def test_per_session_report_scopes_to_one_session(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _scaffold(client, captured, "test-rp-session@example.com")
    conn = await superuser_conn()
    try:
        session_id = await insert_session_today(
            conn,
            workspace_id=s["workspace_id"],
            athlete_id=s["athlete_id"],
            coach_id=s["user_id"],
            hour=10,
            court="Court 1",
            focus="drilling",
        )
    finally:
        await conn.close()

    # Trainee sessions list visible to the picker.
    sessions = await client.get(
        f"/trainees/{s['athlete_id']}/sessions",
        headers={"Authorization": f"Bearer {s['token']}"},
    )
    assert sessions.status_code == 200, sessions.text
    assert any(row["id"] == session_id for row in sessions.json()["sessions"])

    # POST without period_* — BE derives it from the session.
    r = await client.post(
        "/reports",
        json={"athlete_id": s["athlete_id"], "session_id": session_id},
        headers={"Authorization": f"Bearer {s['token']}"},
    )
    assert r.status_code == 202, r.text
    body = r.json()["report"]
    assert body["period_start"] == body["period_end"]

    # Worker renders + uploads.
    result = await generate_report_pdf_async(body["id"])
    assert result["status"] == "completed", result
    assert result["bytes"] > 1000

    # The persisted row links back to the source session.
    conn = await superuser_conn()
    try:
        linked_session = await conn.fetchval(
            "SELECT session_id::text FROM reports WHERE id = $1", body["id"]
        )
    finally:
        await conn.close()
    assert linked_session == session_id


async def test_per_session_report_404_for_unknown_session(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _scaffold(client, captured, "test-rp-session-404@example.com")
    r = await client.post(
        "/reports",
        json={
            "athlete_id": s["athlete_id"],
            "session_id": "00000000-0000-0000-0000-000000000000",
        },
        headers={"Authorization": f"Bearer {s['token']}"},
    )
    assert r.status_code == 404


async def _add_second_user_membership(
    *,
    workspace_id: str,
    email: str,
    role: str,
    captured: list[dict[str, str]],
    client: AsyncClient,
) -> dict[str, Any]:
    """Sign in a second user and force-add them as `role` in the given
    workspace via direct DB insert.  Returns {token, user_id} for that user
    re-signed-in so the JWT carries the right wsid."""
    user = await sign_in(client, email, captured)
    user_id = user["user"]["id"]
    conn = await superuser_conn()
    try:
        await conn.execute(
            """
            INSERT INTO workspace_memberships
                (workspace_id, user_id, role, status, invited_at, joined_at)
            VALUES ($1, $2, $3, 'active', NOW(), NOW())
            ON CONFLICT (workspace_id, user_id, role) DO NOTHING
            """,
            workspace_id, user_id, role,
        )
    finally:
        await conn.close()
    # Re-sign-in so the new JWT carries wsid for this workspace.
    switch = await client.post(
        f"/workspaces/{workspace_id}/switch",
        headers={"Authorization": f"Bearer {user['access_token']}"},
    )
    assert switch.status_code == 200, switch.text
    return {"token": switch.json()["access_token"], "user_id": user_id}


async def test_post_rejects_trainee_role(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _scaffold(client, captured, "test-rp-block-trainee@example.com")
    other = await _add_second_user_membership(
        workspace_id=s["workspace_id"],
        email="test-rp-trainee-user@example.com",
        role="trainee",
        captured=captured,
        client=client,
    )
    today = datetime.now(UTC).date()
    r = await client.post(
        "/reports",
        json={
            "athlete_id": s["athlete_id"],
            "period_start": (today - timedelta(days=14)).isoformat(),
            "period_end": today.isoformat(),
        },
        headers={"Authorization": f"Bearer {other['token']}"},
    )
    assert r.status_code == 403, r.text


async def test_post_rejects_coach_without_session_with_trainee(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _scaffold(client, captured, "test-rp-block-coach@example.com")
    coach2 = await _add_second_user_membership(
        workspace_id=s["workspace_id"],
        email="test-rp-coach2-user@example.com",
        role="coach",
        captured=captured,
        client=client,
    )
    today = datetime.now(UTC).date()
    r = await client.post(
        "/reports",
        json={
            "athlete_id": s["athlete_id"],
            "period_start": (today - timedelta(days=14)).isoformat(),
            "period_end": today.isoformat(),
        },
        headers={"Authorization": f"Bearer {coach2['token']}"},
    )
    assert r.status_code == 403, r.text


async def test_post_allows_coach_with_session_with_trainee(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _scaffold(client, captured, "test-rp-allow-coach@example.com")
    coach2 = await _add_second_user_membership(
        workspace_id=s["workspace_id"],
        email="test-rp-coach2-allow@example.com",
        role="coach",
        captured=captured,
        client=client,
    )
    # Drop a session linking coach2 to this trainee — the auth fence now opens.
    conn = await superuser_conn()
    try:
        await insert_session_today(
            conn,
            workspace_id=s["workspace_id"],
            athlete_id=s["athlete_id"],
            coach_id=coach2["user_id"],
        )
    finally:
        await conn.close()

    today = datetime.now(UTC).date()
    r = await client.post(
        "/reports",
        json={
            "athlete_id": s["athlete_id"],
            "period_start": (today - timedelta(days=14)).isoformat(),
            "period_end": today.isoformat(),
        },
        headers={"Authorization": f"Bearer {coach2['token']}"},
    )
    assert r.status_code == 202, r.text
