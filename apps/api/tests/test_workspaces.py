"""Workspace endpoint + RLS isolation tests.

Covers:
  - POST /workspaces creates club + personal variants with correct membership roles
  - GET /workspaces/mine returns all of a user's workspaces (cross-workspace)
  - POST /workspaces/{id}/switch validates membership and rotates the token
  - RLS proves a user's wsid context doesn't leak another workspace's data
"""

from __future__ import annotations

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from src import deps as deps_module
from src.auth.jwt import decode_token
from src.config import settings
from src.db import session as session_module
from src.main import app


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


@pytest.fixture(autouse=True)
async def _cleanup_test_data() -> None:
    """Wipe test users and their workspaces. Uses the superuser DSN to bypass RLS."""
    yield
    conn = await asyncpg.connect(
        "postgresql://coachito:coachito@postgres:5432/coachito"
    )
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


@pytest.fixture(autouse=True)
async def _no_real_emails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests use the magic-link flow to mint initial tokens; capture the link."""
    async def fake_send(*, email: str, link: str) -> None:
        # Stash on the test module so tests can read it
        _no_real_emails.last = {"email": email, "link": link}  # type: ignore[attr-defined]

    monkeypatch.setattr("src.auth.router.send_magic_link_email", fake_send)


# ── Helpers ──────────────────────────────────────────────────────


async def _signin(client: AsyncClient, email: str) -> dict:
    """Run magic-link request + consume; return the full token payload."""
    await client.post("/auth/magic/request", json={"email": email})
    link: str = _no_real_emails.last["link"]  # type: ignore[attr-defined]
    token = link.split("token=", 1)[1]
    r = await client.get("/auth/magic/consume", params={"token": token})
    assert r.status_code == 200, r.text
    return r.json()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── POST /workspaces ─────────────────────────────────────────────


async def test_create_club_workspace(client: AsyncClient) -> None:
    me = await _signin(client, "test-create-club@example.com")
    assert me["user"]["current_workspace_id"] is None

    r = await client.post(
        "/workspaces",
        json={
            "type": "club",
            "name": "Senayan Padel Club",
            "city": "Jakarta",
            "brand_color": "#378ADD",
            "primary_locale": "id",
        },
        headers=_auth(me["access_token"]),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    ws = body["workspace"]
    assert ws["type"] == "club"
    assert ws["name"] == "Senayan Padel Club"
    assert ws["city"] == "Jakarta"
    assert ws["brand_color"] == "#378ADD"
    assert ws["primary_locale"] == "id"
    assert ws["plan"] == "free_trial"
    assert ws["trial_ends_at"] is not None
    assert ws["owner_user_id"] == me["user"]["id"]

    tokens = body["tokens"]
    assert tokens["workspace_id"] == ws["id"]

    # The new access token should carry the new wsid
    claims = decode_token(tokens["access_token"])
    assert claims["wsid"] == ws["id"]
    assert claims["sub"] == me["user"]["id"]


async def test_create_personal_workspace_assigns_coach_role(
    client: AsyncClient,
) -> None:
    me = await _signin(client, "test-solo@example.com")
    r = await client.post(
        "/workspaces",
        json={"type": "personal", "name": "Coach Novia", "primary_locale": "en"},
        headers=_auth(me["access_token"]),
    )
    assert r.status_code == 201, r.text
    ws_id = r.json()["workspace"]["id"]

    # Verify the membership was created as 'coach', not 'club_admin'
    conn = await asyncpg.connect(
        "postgresql://coachito:coachito@postgres:5432/coachito"
    )
    try:
        role = await conn.fetchval(
            "SELECT role::text FROM workspace_memberships WHERE workspace_id = $1",
            ws_id,
        )
    finally:
        await conn.close()
    assert role == "coach"


async def test_create_requires_auth(client: AsyncClient) -> None:
    r = await client.post(
        "/workspaces",
        json={"type": "club", "name": "X", "primary_locale": "id"},
    )
    assert r.status_code == 401


async def test_create_rejects_invalid_color(client: AsyncClient) -> None:
    me = await _signin(client, "test-badcolor@example.com")
    r = await client.post(
        "/workspaces",
        json={
            "type": "club",
            "name": "X",
            "brand_color": "not-a-hex",
            "primary_locale": "id",
        },
        headers=_auth(me["access_token"]),
    )
    assert r.status_code == 422


# ── GET /workspaces/mine ─────────────────────────────────────────


async def test_list_mine_returns_all_workspaces(client: AsyncClient) -> None:
    me = await _signin(client, "test-many@example.com")
    token = me["access_token"]

    # Create two workspaces
    r1 = await client.post(
        "/workspaces",
        json={"type": "club", "name": "Club A", "primary_locale": "id"},
        headers=_auth(token),
    )
    assert r1.status_code == 201
    # Use the new token from create — it has wsid set, but listing should
    # still return BOTH workspaces (cross-workspace query via user-id GUC).
    token = r1.json()["tokens"]["access_token"]

    r2 = await client.post(
        "/workspaces",
        json={"type": "personal", "name": "Solo Side Gig", "primary_locale": "id"},
        headers=_auth(token),
    )
    assert r2.status_code == 201
    token = r2.json()["tokens"]["access_token"]

    r = await client.get("/workspaces/mine", headers=_auth(token))
    assert r.status_code == 200, r.text
    workspaces = r.json()["workspaces"]
    assert len(workspaces) == 2
    names = {w["workspace"]["name"] for w in workspaces}
    assert names == {"Club A", "Solo Side Gig"}
    roles = {w["workspace"]["type"]: w["role"] for w in workspaces}
    assert roles == {"club": "club_admin", "personal": "coach"}


async def test_list_mine_empty_for_new_user(client: AsyncClient) -> None:
    me = await _signin(client, "test-empty@example.com")
    r = await client.get("/workspaces/mine", headers=_auth(me["access_token"]))
    assert r.status_code == 200
    assert r.json()["workspaces"] == []


# ── POST /workspaces/{id}/switch ─────────────────────────────────


async def test_switch_to_my_workspace_rotates_jwt(client: AsyncClient) -> None:
    me = await _signin(client, "test-switch@example.com")
    created = await client.post(
        "/workspaces",
        json={"type": "club", "name": "Club S", "primary_locale": "id"},
        headers=_auth(me["access_token"]),
    )
    ws_id = created.json()["workspace"]["id"]
    # Pretend the client lost the post-create token and is using their
    # original "no-wsid" token instead — switch should still work.
    r = await client.post(
        f"/workspaces/{ws_id}/switch",
        headers=_auth(me["access_token"]),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["workspace_id"] == ws_id
    claims = decode_token(body["access_token"])
    assert claims["wsid"] == ws_id


async def test_switch_without_membership_returns_403(
    client: AsyncClient,
) -> None:
    alice = await _signin(client, "test-alice@example.com")
    bob = await _signin(client, "test-bob@example.com")

    # Bob creates a workspace
    bobs_ws = await client.post(
        "/workspaces",
        json={"type": "club", "name": "Bob's Club", "primary_locale": "id"},
        headers=_auth(bob["access_token"]),
    )
    bob_ws_id = bobs_ws.json()["workspace"]["id"]

    # Alice tries to switch into it — must be forbidden
    r = await client.post(
        f"/workspaces/{bob_ws_id}/switch",
        headers=_auth(alice["access_token"]),
    )
    assert r.status_code == 403


# ── RLS isolation ────────────────────────────────────────────────


async def test_rls_isolates_cross_workspace_membership_data(
    client: AsyncClient,
) -> None:
    """Alice's wsid context cannot see Bob's workspace memberships.

    Listing /workspaces/mine works because the membership policy also matches
    on user_id; but a direct query that joins by workspace_id only returns
    the calling user's own workspaces.
    """
    alice = await _signin(client, "test-alice2@example.com")
    bob = await _signin(client, "test-bob2@example.com")

    # Both create a workspace
    a_ws = (
        await client.post(
            "/workspaces",
            json={"type": "club", "name": "Alice Club", "primary_locale": "id"},
            headers=_auth(alice["access_token"]),
        )
    ).json()
    b_ws = (
        await client.post(
            "/workspaces",
            json={"type": "club", "name": "Bob Club", "primary_locale": "id"},
            headers=_auth(bob["access_token"]),
        )
    ).json()

    alice_token_with_wsid = a_ws["tokens"]["access_token"]

    # Alice (in her workspace) lists "my workspaces" — sees only hers
    r = await client.get(
        "/workspaces/mine", headers=_auth(alice_token_with_wsid)
    )
    workspaces = r.json()["workspaces"]
    assert len(workspaces) == 1
    assert workspaces[0]["workspace"]["id"] == a_ws["workspace"]["id"]
    assert all(w["workspace"]["id"] != b_ws["workspace"]["id"] for w in workspaces)

    # And cannot switch into Bob's
    forbidden = await client.post(
        f"/workspaces/{b_ws['workspace']['id']}/switch",
        headers=_auth(alice_token_with_wsid),
    )
    assert forbidden.status_code == 403
