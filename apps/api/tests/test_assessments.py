"""Assessment v2 — draft / publish / edit / discard lifecycle + tier recalc."""

from __future__ import annotations

from uuid import uuid4

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


# ── Helpers ──────────────────────────────────────────────────────


async def _skills_by_code(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    codes: list[str],
) -> dict[str, str]:
    rows = await conn.fetch(
        "SELECT code, id::text FROM skills WHERE code = ANY($1::text[]) "
        "AND workspace_id IS NULL",
        codes,
    )
    return {r["code"]: r["id"] for r in rows}


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── Tests ────────────────────────────────────────────────────────


async def test_save_draft_creates_assessment_in_draft_status(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-assess-draft@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Draft Club")
    workspace_id = ws["workspace"]["id"]
    user_id = user["user"]["id"]
    token = ws["tokens"]["access_token"]

    conn = await superuser_conn()
    try:
        athlete_id = await insert_athlete(
            conn, workspace_id=workspace_id, coach_id=user_id,
            display_name="Test Draft",
        )
        skills = await _skills_by_code(conn, ["PADEL_TECH_FH", "PADEL_TECH_BH"])
    finally:
        await conn.close()

    payload = {
        "athlete_id": athlete_id,
        "summary": "Solid first read",
        "scores": [
            {"skill_id": skills["PADEL_TECH_FH"], "level": 3},
            {"skill_id": skills["PADEL_TECH_BH"], "level": 2},
        ],
    }
    r = await client.post("/assessments", json=payload, headers=_auth(token))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "draft"
    assert data["athlete_id"] == athlete_id
    assert len(data["scores"]) == 2
    assert data["published_at"] is None


async def test_save_draft_idempotent_via_session_id(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    """v2 idempotency comes from UNIQUE(session_id) on assessments — a
    second POST referencing the same session updates the same row."""
    user = await sign_in(client, "test-assess-idem@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Idem Club")
    workspace_id = ws["workspace"]["id"]
    user_id = user["user"]["id"]
    token = ws["tokens"]["access_token"]

    conn = await superuser_conn()
    try:
        athlete_id = await insert_athlete(
            conn, workspace_id=workspace_id, coach_id=user_id,
            display_name="Test Idem",
        )
        skills = await _skills_by_code(conn, ["PADEL_TECH_FH"])
    finally:
        await conn.close()

    payload = {
        "athlete_id": athlete_id,
        "scores": [{"skill_id": skills["PADEL_TECH_FH"], "level": 2}],
    }
    r1 = await client.post("/assessments", json=payload, headers=_auth(token))
    session_id = r1.json()["session_id"]

    # Re-save with a new score against the same session.
    payload["session_id"] = session_id
    payload["scores"][0]["level"] = 4
    r2 = await client.post("/assessments", json=payload, headers=_auth(token))
    assert r2.status_code == 200
    assert r2.json()["id"] == r1.json()["id"]  # same assessment
    assert r2.json()["scores"][0]["level"] == 4

    conn = await superuser_conn()
    try:
        count = await conn.fetchval(
            "SELECT count(*) FROM assessments WHERE session_id = $1",
            session_id,
        )
    finally:
        await conn.close()
    assert count == 1


async def test_publish_flips_status_and_recalcs_tier(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-assess-pub@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Pub Club")
    workspace_id = ws["workspace"]["id"]
    user_id = user["user"]["id"]
    token = ws["tokens"]["access_token"]

    conn = await superuser_conn()
    try:
        athlete_id = await insert_athlete(
            conn, workspace_id=workspace_id, coach_id=user_id,
            display_name="Test Pub",
        )
        # All LOWER_BRONZE requirements.
        skills = await _skills_by_code(
            conn,
            ["PADEL_TECH_FH", "PADEL_TECH_BH", "PADEL_TECH_SERVE", "PADEL_TECH_RETURN"],
        )
    finally:
        await conn.close()

    # Save draft with all LOWER_BRONZE requirements met.
    draft = await client.post(
        "/assessments",
        json={
            "athlete_id": athlete_id,
            "scores": [
                {"skill_id": skills["PADEL_TECH_FH"], "level": 2},
                {"skill_id": skills["PADEL_TECH_BH"], "level": 2},
                {"skill_id": skills["PADEL_TECH_SERVE"], "level": 1},
                {"skill_id": skills["PADEL_TECH_RETURN"], "level": 1},
            ],
        },
        headers=_auth(token),
    )
    assessment_id = draft.json()["id"]

    # Publish.
    r = await client.post(
        f"/assessments/{assessment_id}/publish",
        json={"force_empty": False},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "published"
    assert data["published_at"] is not None
    assert data["tier"]["current_tier"]["code"] == "LOWER_BRONZE"
    assert data["tier"]["next_tier"]["code"] == "BRONZE"


async def test_publish_blocks_empty_assessment_unless_forced(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-assess-empty@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Empty Club")
    workspace_id = ws["workspace"]["id"]
    user_id = user["user"]["id"]
    token = ws["tokens"]["access_token"]

    conn = await superuser_conn()
    try:
        athlete_id = await insert_athlete(
            conn, workspace_id=workspace_id, coach_id=user_id,
            display_name="Test Empty",
        )
    finally:
        await conn.close()

    draft = await client.post(
        "/assessments",
        json={"athlete_id": athlete_id, "scores": []},
        headers=_auth(token),
    )
    assert draft.status_code == 200, draft.text
    assessment_id = draft.json()["id"]

    # Without force_empty → 422.
    r = await client.post(
        f"/assessments/{assessment_id}/publish",
        json={"force_empty": False}, headers=_auth(token),
    )
    assert r.status_code == 422

    # With force_empty → 200.
    r2 = await client.post(
        f"/assessments/{assessment_id}/publish",
        json={"force_empty": True}, headers=_auth(token),
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "published"


async def test_edit_published_writes_audit_row(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-assess-edit@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Edit Club")
    workspace_id = ws["workspace"]["id"]
    user_id = user["user"]["id"]
    token = ws["tokens"]["access_token"]

    conn = await superuser_conn()
    try:
        athlete_id = await insert_athlete(
            conn, workspace_id=workspace_id, coach_id=user_id,
            display_name="Test Edit",
        )
        skills = await _skills_by_code(conn, ["PADEL_TECH_FH"])
    finally:
        await conn.close()

    draft = await client.post(
        "/assessments",
        json={
            "athlete_id": athlete_id,
            "summary": "Original summary",
            "scores": [{"skill_id": skills["PADEL_TECH_FH"], "level": 3}],
        },
        headers=_auth(token),
    )
    assessment_id = draft.json()["id"]
    await client.post(
        f"/assessments/{assessment_id}/publish",
        json={"force_empty": False}, headers=_auth(token),
    )

    # Edit.
    r = await client.patch(
        f"/assessments/{assessment_id}",
        json={"summary": "Revised summary after second look."},
        headers=_auth(token),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "edited"
    assert r.json()["edited_at"] is not None

    # Audit row recorded.
    edits = await client.get(
        f"/assessments/{assessment_id}/edits", headers=_auth(token)
    )
    assert edits.status_code == 200
    history = edits.json()
    assert len(history) == 1
    assert history[0]["changes"]["summary"]["to"] == "Revised summary after second look."


async def test_cannot_publish_or_patch_someone_elses_assessment(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    alice = await sign_in(client, "test-assess-alice2@example.com", captured)
    alice_ws = await create_workspace(
        client, alice["access_token"], name="Alice's"
    )
    workspace_id = alice_ws["workspace"]["id"]
    user_id = alice["user"]["id"]
    alice_token = alice_ws["tokens"]["access_token"]

    conn = await superuser_conn()
    try:
        athlete_id = await insert_athlete(
            conn, workspace_id=workspace_id, coach_id=user_id,
            display_name="Alice's Athlete",
        )
        skills = await _skills_by_code(conn, ["PADEL_TECH_FH"])
    finally:
        await conn.close()

    alice_draft = await client.post(
        "/assessments",
        json={
            "athlete_id": athlete_id,
            "scores": [{"skill_id": skills["PADEL_TECH_FH"], "level": 2}],
        },
        headers=_auth(alice_token),
    )
    assessment_id = alice_draft.json()["id"]

    # Bob joins Alice's workspace (manually for the test) as coach but the
    # assessment is owned by Alice — publish/PATCH must 409 for him.  We
    # mimic this by inviting Bob.
    invite = (
        await client.post(
            "/workspaces/me/members/invite",
            json={
                "email": "test-assess-bob2@example.com",
                "display_name": "Bob",
                "role": "coach",
            },
            headers=_auth(alice_token),
        )
    ).json()
    bob = await sign_in(client, "test-assess-bob2@example.com", captured)
    claim = await client.post(
        f"/invites/{invite['invite_code']}/claim", headers=_auth(bob["access_token"])
    )
    bob_token = claim.json()["access_token"]

    r = await client.post(
        f"/assessments/{assessment_id}/publish",
        json={"force_empty": False},
        headers=_auth(bob_token),
    )
    assert r.status_code == 409


async def test_discard_draft_removes_assessment(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-assess-discard@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Discard Club")
    workspace_id = ws["workspace"]["id"]
    user_id = user["user"]["id"]
    token = ws["tokens"]["access_token"]

    conn = await superuser_conn()
    try:
        athlete_id = await insert_athlete(
            conn, workspace_id=workspace_id, coach_id=user_id,
            display_name="Test Discard",
        )
        skills = await _skills_by_code(conn, ["PADEL_TECH_FH"])
    finally:
        await conn.close()

    draft = await client.post(
        "/assessments",
        json={
            "athlete_id": athlete_id,
            "scores": [{"skill_id": skills["PADEL_TECH_FH"], "level": 2}],
        },
        headers=_auth(token),
    )
    assessment_id = draft.json()["id"]

    r = await client.delete(
        f"/assessments/{assessment_id}", headers=_auth(token)
    )
    assert r.status_code == 204

    # GET now 404.
    r2 = await client.get(
        f"/assessments/{assessment_id}", headers=_auth(token)
    )
    assert r2.status_code == 404


async def test_by_session_returns_draft_or_none(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-assess-by-sess@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="By Sess")
    workspace_id = ws["workspace"]["id"]
    user_id = user["user"]["id"]
    token = ws["tokens"]["access_token"]

    conn = await superuser_conn()
    try:
        athlete_id = await insert_athlete(
            conn, workspace_id=workspace_id, coach_id=user_id,
            display_name="Test BySess",
        )
        skills = await _skills_by_code(conn, ["PADEL_TECH_FH"])
    finally:
        await conn.close()

    # First, /by-session for a non-existent id → 200 with null body.
    r = await client.get(
        f"/assessments/by-session/{uuid4()}", headers=_auth(token)
    )
    assert r.status_code == 200
    assert r.json() is None

    draft = await client.post(
        "/assessments",
        json={
            "athlete_id": athlete_id,
            "scores": [{"skill_id": skills["PADEL_TECH_FH"], "level": 2}],
        },
        headers=_auth(token),
    )
    session_id = draft.json()["session_id"]

    r2 = await client.get(
        f"/assessments/by-session/{session_id}", headers=_auth(token)
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body is not None
    assert body["status"] == "draft"


async def test_skills_endpoint_returns_27_padel_skills(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-skills-list@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Skills List")
    token = ws["tokens"]["access_token"]

    r = await client.get("/skills", headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert len(data["skills"]) == 27
    codes = {s["code"] for s in data["skills"]}
    assert "PADEL_TECH_BANDEJA" in codes


async def test_descriptors_endpoint_returns_five_levels(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-skills-desc@example.com", captured)
    ws = await create_workspace(client, user["access_token"], name="Desc Club")
    token = ws["tokens"]["access_token"]

    r = await client.get(
        "/skills/PADEL_TECH_FH/descriptors", headers=_auth(token)
    )
    assert r.status_code == 200
    data = r.json()
    assert data["skill_code"] == "PADEL_TECH_FH"
    assert len(data["descriptors"]) == 5
    assert [d["level"] for d in data["descriptors"]] == [1, 2, 3, 4, 5]
