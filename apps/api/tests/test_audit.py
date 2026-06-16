"""@audit_action — verify every mutating route writes an audit row.

The decorator is invoked from FastAPI's handler call chain.  These tests hit
the real endpoints and assert ``audit_log`` grew with the expected
``action`` + linked entity.
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


async def _latest_audit(workspace_id: str, action: str) -> dict | None:
    conn = await asyncpg.connect(SUPERUSER_DSN)
    try:
        row = await conn.fetchrow(
            """
            SELECT action, entity_type, entity_id::text AS entity_id,
                   metadata, user_id::text AS user_id
            FROM audit_log
            WHERE workspace_id = $1 AND action = $2
            ORDER BY created_at DESC LIMIT 1
            """,
            workspace_id,
            action,
        )
    finally:
        await conn.close()
    return dict(row) if row else None


async def test_creating_trainee_writes_audit_row(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-audit-create@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Audit Club")
    workspace_id = ws["workspace"]["id"]
    user_id = user["user"]["id"]
    token = ws["tokens"]["access_token"]

    r = await client.post(
        "/trainees",
        json={"name": "Andi Audit", "phone_e164": "+628123456789"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    athlete_id = r.json()["trainee"]["id"]

    row = await _latest_audit(workspace_id, "trainee.created")
    assert row is not None
    assert row["entity_type"] == "athlete"
    assert row["entity_id"] == athlete_id
    assert row["user_id"] == user_id


async def test_archiving_trainee_writes_audit_row(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-audit-arch@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Arch Club")
    workspace_id = ws["workspace"]["id"]
    token = ws["tokens"]["access_token"]

    created = await client.post(
        "/trainees",
        json={"name": "Budi", "phone_e164": "+628222222200"},
        headers={"Authorization": f"Bearer {token}"},
    )
    athlete_id = created.json()["trainee"]["id"]

    deleted = await client.delete(
        f"/trainees/{athlete_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert deleted.status_code == 204

    row = await _latest_audit(workspace_id, "trainee.archived")
    assert row is not None
    import json
    meta = row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"])
    assert meta["athlete_id"] == athlete_id


async def test_assessment_post_writes_audit_row(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    from datetime import UTC, datetime
    from uuid import uuid4

    user = await sign_in(client, "test-audit-assess@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Assess Audit")
    workspace_id = ws["workspace"]["id"]
    token = ws["tokens"]["access_token"]

    created = await client.post(
        "/trainees",
        json={"name": "Citra", "phone_e164": "+628333333300"},
        headers={"Authorization": f"Bearer {token}"},
    )
    athlete_id = created.json()["trainee"]["id"]

    conn = await asyncpg.connect(SUPERUSER_DSN)
    try:
        fh_id = await conn.fetchval(
            "SELECT id::text FROM skills WHERE code='PADEL_TECH_FH' AND workspace_id IS NULL"
        )
    finally:
        await conn.close()

    payload = {
        "athlete_id": athlete_id,
        "summary": "First draft session",
        "scores": [{"skill_id": fh_id, "level": 3}],
    }
    r = await client.post(
        "/assessments", json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text

    row = await _latest_audit(workspace_id, "assessment.draft_saved")
    assert row is not None
    import json
    meta = row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"])
    assert meta["athlete_id"] == athlete_id
    assert meta["scores"] == 1
    # Suppress unused-import warnings — UTC/datetime/uuid4 were used by the
    # v1 client-id payload; v2 doesn't need them.
    _ = datetime
    _ = UTC
    _ = uuid4


async def test_report_post_writes_audit_row(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-audit-report@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Report Audit")
    workspace_id = ws["workspace"]["id"]
    token = ws["tokens"]["access_token"]

    created = await client.post(
        "/trainees",
        json={"name": "Dewi", "phone_e164": "+628444444400"},
        headers={"Authorization": f"Bearer {token}"},
    )
    athlete_id = created.json()["trainee"]["id"]

    r = await client.post(
        "/reports",
        json={
            "athlete_id": athlete_id,
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 202, r.text

    row = await _latest_audit(workspace_id, "report.requested")
    assert row is not None
    import json
    meta = row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"])
    assert meta["athlete_id"] == athlete_id
    assert meta["job_id"]
