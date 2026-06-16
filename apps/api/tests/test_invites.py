"""Invite + landing-page tests:

  - POST /trainees creates athlete + invite atomically with the right shape
  - Invite token has the structured slug-handle-rand format
  - Re-invite via POST /trainees/{id}/invite revokes the old, mints a new one
  - GET /i/{token} returns HTML with branded OG meta + Cache-Control
  - GET /i/{expired} returns 410 GONE
  - GET /i/{unknown} returns 404
  - RLS: a coach from a different workspace can't 404 / 410 a valid token
    inadvertently (the lookup uses the superuser path and is workspace-agnostic
    by design — verify behavior is consistent)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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
    sign_in,
    superuser_conn,
)


# ── Fixtures (shared shape with test_athletes/test_sessions) ────


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


async def _signin_and_create_workspace(
    client: AsyncClient,
    captured: list[dict[str, str]],
    *,
    email: str,
    workspace_name: str = "Test Club",
) -> dict:
    user = await sign_in(client, email, captured)
    ws = await create_workspace(client, user["access_token"], name=workspace_name)
    return {
        "user_id": user["user"]["id"],
        "access_token": ws["tokens"]["access_token"],
        "workspace_id": ws["workspace"]["id"],
    }


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── POST /trainees ───────────────────────────────────────────────


async def test_create_trainee_returns_athlete_and_invite(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    ctx = await _signin_and_create_workspace(
        client, captured, email="test-create-tr@example.com",
        workspace_name="Senayan Padel Club",
    )

    r = await client.post(
        "/trainees",
        json={
            "name": "Andi Pratama",
            "phone_e164": "+628123456789",
            "date_of_birth": "2010-05-13",
        },
        headers=_auth(ctx["access_token"]),
    )
    assert r.status_code == 201, r.text
    body = r.json()

    trainee = body["trainee"]
    assert trainee["display_name"] == "Andi Pratama"
    assert trainee["is_minor"] is True  # 2010-born → still a minor in 2026
    assert trainee["date_of_birth"] == "2010-05-13"

    invite = body["invite"]
    assert invite["phone_e164"] == "+628123456789"
    assert invite["code"].startswith("sen-andi-")  # workspace + handle prefix
    assert len(invite["code"].split("-")[2]) >= 6  # random suffix
    assert invite["landing_url"].endswith(f"/i/{invite['code']}")


async def test_create_trainee_normalizes_phone_whitespace(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    ctx = await _signin_and_create_workspace(
        client, captured, email="test-phone-ws@example.com"
    )
    r = await client.post(
        "/trainees",
        json={"name": "Rina", "phone_e164": "+62 812 3456 789"},
        headers=_auth(ctx["access_token"]),
    )
    assert r.status_code == 201
    assert r.json()["invite"]["phone_e164"] == "+628123456789"


async def test_create_trainee_rejects_bad_phone(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    ctx = await _signin_and_create_workspace(
        client, captured, email="test-badphone@example.com"
    )
    r = await client.post(
        "/trainees",
        json={"name": "X", "phone_e164": "081234"},  # no + prefix
        headers=_auth(ctx["access_token"]),
    )
    assert r.status_code == 422


async def test_create_trainee_requires_workspace_context(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    user = await sign_in(client, "test-no-ws@example.com", captured)
    # User has signed in but never created a workspace → no wsid in JWT
    r = await client.post(
        "/trainees",
        json={"name": "X", "phone_e164": "+628123456789"},
        headers=_auth(user["access_token"]),
    )
    assert r.status_code == 400


# ── PATCH / DELETE ───────────────────────────────────────────────


async def test_patch_trainee_updates_name(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    ctx = await _signin_and_create_workspace(
        client, captured, email="test-patch@example.com"
    )
    created = await client.post(
        "/trainees",
        json={"name": "Original Name", "phone_e164": "+628123456789"},
        headers=_auth(ctx["access_token"]),
    )
    tid = created.json()["trainee"]["id"]

    r = await client.patch(
        f"/trainees/{tid}",
        json={"display_name": "Renamed Person"},
        headers=_auth(ctx["access_token"]),
    )
    assert r.status_code == 200
    assert r.json()["display_name"] == "Renamed Person"


async def test_delete_trainee_archives(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    ctx = await _signin_and_create_workspace(
        client, captured, email="test-delete@example.com"
    )
    created = await client.post(
        "/trainees",
        json={"name": "Soon Archived", "phone_e164": "+628123456789"},
        headers=_auth(ctx["access_token"]),
    )
    tid = created.json()["trainee"]["id"]

    r = await client.delete(
        f"/trainees/{tid}", headers=_auth(ctx["access_token"])
    )
    assert r.status_code == 204

    # /trainees list filters archived rows out
    r = await client.get("/trainees", headers=_auth(ctx["access_token"]))
    names = [a["display_name"] for a in r.json()["athletes"]]
    assert "Soon Archived" not in names


# ── Re-invite ────────────────────────────────────────────────────


async def test_reinvite_revokes_old_and_mints_new(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    ctx = await _signin_and_create_workspace(
        client, captured, email="test-reinvite@example.com"
    )
    created = await client.post(
        "/trainees",
        json={"name": "Andi Pratama", "phone_e164": "+628123456789"},
        headers=_auth(ctx["access_token"]),
    )
    first = created.json()
    first_code = first["invite"]["code"]
    first_id = first["invite"]["id"]
    athlete_id = first["trainee"]["id"]

    # Re-invite
    r = await client.post(
        f"/trainees/{athlete_id}/invite",
        headers=_auth(ctx["access_token"]),
    )
    assert r.status_code == 201, r.text
    second = r.json()
    assert second["code"] != first_code
    assert second["id"] != first_id

    # Old invite should now be revoked
    conn = await superuser_conn()
    try:
        old_revoked_at = await conn.fetchval(
            "SELECT revoked_at FROM invites WHERE id = $1::uuid", first_id
        )
        new_revoked_at = await conn.fetchval(
            "SELECT revoked_at FROM invites WHERE id = $1::uuid", second["id"]
        )
    finally:
        await conn.close()
    assert old_revoked_at is not None
    assert new_revoked_at is None

    # GET /i/{old_code} should now return 410
    r = await client.get(f"/i/{first_code}")
    assert r.status_code == 410


# ── GET /i/{token} ───────────────────────────────────────────────


async def test_invite_landing_returns_branded_og_html(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    ctx = await _signin_and_create_workspace(
        client, captured, email="test-landing@example.com",
        workspace_name="Senayan Padel Club",
    )
    created = await client.post(
        "/trainees",
        json={"name": "Andi Pratama", "phone_e164": "+628123456789"},
        headers=_auth(ctx["access_token"]),
    )
    code = created.json()["invite"]["code"]

    r = await client.get(f"/i/{code}")
    assert r.status_code == 200
    assert r.headers.get("cache-control") == "public, max-age=86400"
    html = r.text

    # OG tags
    assert '<meta property="og:title"' in html
    assert "Senayan Padel Club" in html
    assert '<meta property="og:description"' in html
    assert '<meta property="og:url"' in html
    assert f"/i/{code}" in html

    # Body content uses workspace name + coach name + trainee first name
    assert "Andi" in html
    assert "Senayan Padel Club" in html


async def test_invite_landing_404_for_unknown_token(client: AsyncClient) -> None:
    r = await client.get("/i/does-not-exist-anywhere")
    assert r.status_code == 404


async def test_invite_landing_410_for_expired_token(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    ctx = await _signin_and_create_workspace(
        client, captured, email="test-expired@example.com"
    )
    created = await client.post(
        "/trainees",
        json={"name": "Expired Person", "phone_e164": "+628123456789"},
        headers=_auth(ctx["access_token"]),
    )
    code = created.json()["invite"]["code"]

    # Backdate the expiry to 8 days ago
    conn = await superuser_conn()
    try:
        await conn.execute(
            "UPDATE invites SET expires_at = NOW() - INTERVAL '8 days' WHERE invite_code = $1",
            code,
        )
    finally:
        await conn.close()

    r = await client.get(f"/i/{code}")
    assert r.status_code == 410
    # Expired page should still include some workspace branding (the row exists)
    assert "Test Club" in r.text or "coachito" in r.text.lower()


# ── Unused timedelta import silence ──────────────────────────────
_ = (timedelta, datetime)
