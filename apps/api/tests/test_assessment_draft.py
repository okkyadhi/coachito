"""POST /assessments/{id}/draft-summary — auth + payload + audit + error mapping.

Network calls to Gemini are stubbed via dependency-override of the shared
httpx client so we exercise the FastAPI surface without hitting Google.
"""

from __future__ import annotations

import asyncpg
import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from src import deps as deps_module
from src.assessments import draft_router as draft_module
from src.config import settings
from src.db import session as session_module
from src.main import app

from ._test_helpers import (
    SUPERUSER_DSN,
    create_workspace,
    insert_athlete,
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
def _gemini_key() -> object:
    """Force a non-empty key for every test in this module.  Restores the
    original value (typically empty in dev) on teardown.

    Used a yield-based fixture instead of monkeypatch.setattr because the
    interleaving with the autouse async ``_cleanup`` fixture was flaking the
    restore ordering — direct mutation is bullet-proof."""
    original = settings.gemini_api_key
    settings.gemini_api_key = "test-key"
    yield
    settings.gemini_api_key = original


@pytest.fixture(autouse=True)
async def _cleanup() -> None:
    yield
    conn = await asyncpg.connect(SUPERUSER_DSN)
    try:
        await conn.execute(
            "DELETE FROM audit_log WHERE user_id IN ("
            "  SELECT id FROM users WHERE email LIKE 'test-aidraft-%@example.com')"
        )
        await conn.execute(
            """
            DELETE FROM workspaces WHERE owner_user_id IN (
                SELECT id FROM users WHERE email LIKE 'test-aidraft-%@example.com'
            )
            """
        )
        await conn.execute(
            "DELETE FROM users WHERE email LIKE 'test-aidraft-%@example.com'"
        )
    finally:
        await conn.close()


def _stub_http(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _ok_response(text: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={"candidates": [{"content": {"parts": [{"text": text}]}}]},
    )


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _scaffold_assessment(
    client: AsyncClient,
    captured: list[dict[str, str]],
    email: str,
    *,
    with_scores: bool = True,
) -> dict[str, str]:
    """Create coach + workspace + athlete + a draft assessment with one score
    (unless ``with_scores=False``).  Returns ids the tests need."""
    coach = await sign_in(client, email, captured)
    ws = await create_workspace(client, coach["access_token"], name="AI Club")
    workspace_id = ws["workspace"]["id"]
    user_id = coach["user"]["id"]
    token = ws["tokens"]["access_token"]

    conn = await superuser_conn()
    try:
        athlete_id = await insert_athlete(
            conn, workspace_id=workspace_id, coach_id=user_id, display_name="Andi Pratama",
        )
        skill_id = await conn.fetchval(
            "SELECT id::text FROM skills WHERE code='PADEL_TECH_FH' AND workspace_id IS NULL"
        )
    finally:
        await conn.close()

    body = {"athlete_id": athlete_id}
    if with_scores:
        body["scores"] = [{"skill_id": skill_id, "level": 3}]
    r = await client.post("/assessments", json=body, headers=_auth(token))
    assert r.status_code == 200, r.text
    return {
        "token": token,
        "workspace_id": workspace_id,
        "user_id": user_id,
        "athlete_id": athlete_id,
        "assessment_id": r.json()["id"],
    }


async def _add_membership(
    workspace_id: str, email: str, role: str,
    client: AsyncClient, captured: list[dict[str, str]],
) -> dict[str, str]:
    """Sign in a second user, force-add to workspace, switch tokens to it."""
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
    sw = await client.post(
        f"/workspaces/{workspace_id}/switch",
        headers=_auth(user["access_token"]),
    )
    assert sw.status_code == 200, sw.text
    return {"token": sw.json()["access_token"], "user_id": user_id}


# ── Tests ────────────────────────────────────────────────────────


async def test_owning_coach_gets_draft_and_audit_row(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return _ok_response("Andi, your forehand was solid today.")

    app.dependency_overrides[draft_module.get_http_client] = lambda: _stub_http(handler)
    try:
        s = await _scaffold_assessment(client, captured, "test-aidraft-owner@example.com")
        r = await client.post(
            f"/assessments/{s['assessment_id']}/draft-summary",
            headers=_auth(s["token"]),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["draft"] == "Andi, your forehand was solid today."
        assert body["model"] == settings.gemini_model
        assert "generativelanguage.googleapis.com" in str(seen["url"])
    finally:
        app.dependency_overrides.pop(draft_module.get_http_client, None)

    # Audit row written exactly once with the expected metadata.
    conn = await superuser_conn()
    try:
        row = await conn.fetchrow(
            "SELECT action, entity_type, metadata::text "
            "FROM audit_log WHERE user_id = $1 AND action = 'ai.draft_generated'",
            s["user_id"],
        )
    finally:
        await conn.close()
    assert row is not None
    assert row["action"] == "ai.draft_generated"
    assert row["entity_type"] == "assessment"
    meta = row["metadata"]
    assert "encouraging" in meta or "direct" in meta or "warm" in meta
    assert "skill_count" in meta
    assert "latency_ms" in meta


async def test_head_coach_can_draft_for_another_coachs_assessment(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return _ok_response("head coach draft")

    app.dependency_overrides[draft_module.get_http_client] = lambda: _stub_http(handler)
    try:
        s = await _scaffold_assessment(client, captured, "test-aidraft-h1@example.com")
        head = await _add_membership(
            s["workspace_id"], "test-aidraft-head@example.com",
            "head_coach", client, captured,
        )
        r = await client.post(
            f"/assessments/{s['assessment_id']}/draft-summary",
            headers=_auth(head["token"]),
        )
        assert r.status_code == 200, r.text
    finally:
        app.dependency_overrides.pop(draft_module.get_http_client, None)


async def test_other_coach_in_same_workspace_blocked_403(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    app.dependency_overrides[draft_module.get_http_client] = lambda: _stub_http(
        lambda r: _ok_response("never called"),
    )
    try:
        s = await _scaffold_assessment(client, captured, "test-aidraft-o1@example.com")
        other = await _add_membership(
            s["workspace_id"], "test-aidraft-other@example.com",
            "coach", client, captured,
        )
        r = await client.post(
            f"/assessments/{s['assessment_id']}/draft-summary",
            headers=_auth(other["token"]),
        )
        assert r.status_code == 403
    finally:
        app.dependency_overrides.pop(draft_module.get_http_client, None)


async def test_trainee_role_blocked_403(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    app.dependency_overrides[draft_module.get_http_client] = lambda: _stub_http(
        lambda r: _ok_response("never called"),
    )
    try:
        s = await _scaffold_assessment(client, captured, "test-aidraft-t1@example.com")
        trainee = await _add_membership(
            s["workspace_id"], "test-aidraft-traineeuser@example.com",
            "trainee", client, captured,
        )
        r = await client.post(
            f"/assessments/{s['assessment_id']}/draft-summary",
            headers=_auth(trainee["token"]),
        )
        assert r.status_code == 403
    finally:
        app.dependency_overrides.pop(draft_module.get_http_client, None)


async def test_empty_assessment_returns_409(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    app.dependency_overrides[draft_module.get_http_client] = lambda: _stub_http(
        lambda r: _ok_response("never called"),
    )
    try:
        s = await _scaffold_assessment(
            client, captured, "test-aidraft-empty@example.com", with_scores=False,
        )
        r = await client.post(
            f"/assessments/{s['assessment_id']}/draft-summary",
            headers=_auth(s["token"]),
        )
        assert r.status_code == 409, r.text
    finally:
        app.dependency_overrides.pop(draft_module.get_http_client, None)


async def test_missing_api_key_returns_503(
    client: AsyncClient,
    captured: list[dict[str, str]],
) -> None:
    settings.gemini_api_key = ""  # restored by the autouse fixture
    app.dependency_overrides[draft_module.get_http_client] = lambda: _stub_http(
        lambda r: _ok_response("never called"),
    )
    try:
        s = await _scaffold_assessment(client, captured, "test-aidraft-503@example.com")
        r = await client.post(
            f"/assessments/{s['assessment_id']}/draft-summary",
            headers=_auth(s["token"]),
        )
        assert r.status_code == 503
    finally:
        app.dependency_overrides.pop(draft_module.get_http_client, None)


async def test_upstream_5xx_returns_502(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="upstream overloaded")

    app.dependency_overrides[draft_module.get_http_client] = lambda: _stub_http(handler)
    try:
        s = await _scaffold_assessment(client, captured, "test-aidraft-502@example.com")
        r = await client.post(
            f"/assessments/{s['assessment_id']}/draft-summary",
            headers=_auth(s["token"]),
        )
        assert r.status_code == 502, r.text
    finally:
        app.dependency_overrides.pop(draft_module.get_http_client, None)
