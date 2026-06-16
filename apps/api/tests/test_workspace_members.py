"""Coach management endpoints — GET/POST/PATCH/DELETE /workspaces/me/members."""

from __future__ import annotations

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from src import deps as deps_module
from src.config import settings
from src.db import session as session_module
from src.main import app

from ._test_helpers import SUPERUSER_DSN


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
async def _capture_magic_link(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_send(*, email: str, link: str) -> None:
        _capture_magic_link.last = {"email": email, "link": link}  # type: ignore[attr-defined]

    monkeypatch.setattr("src.auth.router.send_magic_link_email", fake_send)


@pytest.fixture(autouse=True)
async def _cleanup() -> None:
    yield
    conn = await asyncpg.connect(SUPERUSER_DSN)
    try:
        await conn.execute(
            """
            DELETE FROM workspaces WHERE owner_user_id IN (
                SELECT id FROM users WHERE email LIKE 'test-mem-%@example.com'
            )
            """
        )
        await conn.execute(
            "DELETE FROM users WHERE email LIKE 'test-mem-%@example.com'"
        )
    finally:
        await conn.close()


async def _signin(client: AsyncClient, email: str) -> dict:
    await client.post("/auth/magic/request", json={"email": email})
    link: str = _capture_magic_link.last["link"]  # type: ignore[attr-defined]
    token = link.split("token=", 1)[1]
    r = await client.get("/auth/magic/consume", params={"token": token})
    assert r.status_code == 200, r.text
    return r.json()


async def _create_club(client: AsyncClient, token: str) -> dict:
    r = await client.post(
        "/workspaces",
        json={"type": "club", "name": "Test Club Mem", "primary_locale": "id"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── Tests ────────────────────────────────────────────────────────


async def test_list_members_includes_admin_owner(client: AsyncClient) -> None:
    me = await _signin(client, "test-mem-list@example.com")
    ws = await _create_club(client, me["access_token"])
    admin_token = ws["tokens"]["access_token"]

    r = await client.get("/workspaces/me/members", headers=_auth(admin_token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["coach_count"] == 1
    assert body["trainee_count"] == 0
    assert len(body["members"]) == 1
    m = body["members"][0]
    assert m["role"] == "club_admin"
    assert m["is_owner"] is True
    assert m["is_self"] is True


async def test_invite_coach_appears_in_pending(client: AsyncClient) -> None:
    me = await _signin(client, "test-mem-inv@example.com")
    ws = await _create_club(client, me["access_token"])
    admin = ws["tokens"]["access_token"]

    r = await client.post(
        "/workspaces/me/members/invite",
        json={
            "email": "test-mem-newcoach@example.com",
            "display_name": "Coach Baru",
            "role": "coach",
        },
        headers=_auth(admin),
    )
    assert r.status_code == 201, r.text
    invite = r.json()
    assert invite["role"] == "coach"
    assert "-" in invite["invite_code"]
    assert invite["landing_url"].endswith(invite["invite_code"])

    listing = (await client.get("/workspaces/me/members", headers=_auth(admin))).json()
    assert len(listing["pending_invites"]) == 1
    assert listing["pending_invites"][0]["email"] == "test-mem-newcoach@example.com"


async def test_invite_duplicate_email_returns_409(client: AsyncClient) -> None:
    me = await _signin(client, "test-mem-dup@example.com")
    ws = await _create_club(client, me["access_token"])
    admin = ws["tokens"]["access_token"]

    # The admin's own email already belongs to a member.
    r = await client.post(
        "/workspaces/me/members/invite",
        json={
            "email": "test-mem-dup@example.com",
            "display_name": "self",
            "role": "coach",
        },
        headers=_auth(admin),
    )
    assert r.status_code == 409, r.text


async def test_invite_revokes_previous_pending_to_same_email(
    client: AsyncClient,
) -> None:
    me = await _signin(client, "test-mem-revoke@example.com")
    ws = await _create_club(client, me["access_token"])
    admin = ws["tokens"]["access_token"]

    first = (
        await client.post(
            "/workspaces/me/members/invite",
            json={
                "email": "test-mem-target@example.com",
                "display_name": "Coach",
                "role": "coach",
            },
            headers=_auth(admin),
        )
    ).json()
    second = (
        await client.post(
            "/workspaces/me/members/invite",
            json={
                "email": "test-mem-target@example.com",
                "display_name": "Coach",
                "role": "head_coach",
            },
            headers=_auth(admin),
        )
    ).json()
    assert first["id"] != second["id"]

    listing = (await client.get("/workspaces/me/members", headers=_auth(admin))).json()
    pending_ids = [p["id"] for p in listing["pending_invites"]]
    assert second["id"] in pending_ids
    assert first["id"] not in pending_ids


async def test_non_admin_cannot_invite(client: AsyncClient) -> None:
    """A plain coach hitting the invite endpoint gets 403."""
    admin = await _signin(client, "test-mem-rbac-admin@example.com")
    ws = await _create_club(client, admin["access_token"])
    admin_token = ws["tokens"]["access_token"]
    ws_id = ws["workspace"]["id"]

    # Promote a second user into the club via a real invite + claim.
    invite = (
        await client.post(
            "/workspaces/me/members/invite",
            json={
                "email": "test-mem-rbac-coach@example.com",
                "display_name": "Coach",
                "role": "coach",
            },
            headers=_auth(admin_token),
        )
    ).json()
    coach_user = await _signin(client, "test-mem-rbac-coach@example.com")
    claim = await client.post(
        f"/invites/{invite['invite_code']}/claim",
        headers=_auth(coach_user["access_token"]),
    )
    assert claim.status_code == 200, claim.text
    coach_token = claim.json()["access_token"]

    # Coach trying to invite another → 403.
    r = await client.post(
        "/workspaces/me/members/invite",
        json={
            "email": "test-mem-rbac-other@example.com",
            "display_name": "Other",
            "role": "coach",
        },
        headers=_auth(coach_token),
    )
    assert r.status_code == 403, r.text

    # But the coach can still view the member list.
    g = await client.get("/workspaces/me/members", headers=_auth(coach_token))
    assert g.status_code == 200
    assert g.json()["coach_count"] == 2
    _ = ws_id  # keep mypy happy for future scoped assertions


async def test_remove_member_archives_membership(client: AsyncClient) -> None:
    admin = await _signin(client, "test-mem-del-admin@example.com")
    ws = await _create_club(client, admin["access_token"])
    admin_token = ws["tokens"]["access_token"]

    invite = (
        await client.post(
            "/workspaces/me/members/invite",
            json={
                "email": "test-mem-del-coach@example.com",
                "display_name": "Coach",
                "role": "coach",
            },
            headers=_auth(admin_token),
        )
    ).json()
    coach_user = await _signin(client, "test-mem-del-coach@example.com")
    await client.post(
        f"/invites/{invite['invite_code']}/claim",
        headers=_auth(coach_user["access_token"]),
    )

    listing = (await client.get("/workspaces/me/members", headers=_auth(admin_token))).json()
    coach_membership_id = next(
        m["id"] for m in listing["members"]
        if m["email"] == "test-mem-del-coach@example.com"
    )

    r = await client.delete(
        f"/workspaces/me/members/{coach_membership_id}",
        headers=_auth(admin_token),
    )
    assert r.status_code == 204

    after = (await client.get("/workspaces/me/members", headers=_auth(admin_token))).json()
    assert after["coach_count"] == 1
    assert not any(m["email"] == "test-mem-del-coach@example.com" for m in after["members"])


async def test_cannot_remove_owner_or_self(client: AsyncClient) -> None:
    admin = await _signin(client, "test-mem-self@example.com")
    ws = await _create_club(client, admin["access_token"])
    admin_token = ws["tokens"]["access_token"]

    listing = (await client.get("/workspaces/me/members", headers=_auth(admin_token))).json()
    admin_membership_id = listing["members"][0]["id"]

    r = await client.delete(
        f"/workspaces/me/members/{admin_membership_id}",
        headers=_auth(admin_token),
    )
    # is_owner check fires before is_self check.
    assert r.status_code == 403


async def test_patch_role_promotes_coach_to_head(client: AsyncClient) -> None:
    admin = await _signin(client, "test-mem-prom-admin@example.com")
    ws = await _create_club(client, admin["access_token"])
    admin_token = ws["tokens"]["access_token"]
    invite = (
        await client.post(
            "/workspaces/me/members/invite",
            json={
                "email": "test-mem-prom-coach@example.com",
                "display_name": "Coach",
                "role": "coach",
            },
            headers=_auth(admin_token),
        )
    ).json()
    coach_user = await _signin(client, "test-mem-prom-coach@example.com")
    await client.post(
        f"/invites/{invite['invite_code']}/claim",
        headers=_auth(coach_user["access_token"]),
    )
    listing = (await client.get("/workspaces/me/members", headers=_auth(admin_token))).json()
    coach_membership_id = next(
        m["id"] for m in listing["members"]
        if m["email"] == "test-mem-prom-coach@example.com"
    )

    r = await client.patch(
        f"/workspaces/me/members/{coach_membership_id}",
        json={"role": "head_coach"},
        headers=_auth(admin_token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "head_coach"


async def test_patch_owner_role_forbidden(client: AsyncClient) -> None:
    admin = await _signin(client, "test-mem-ownerpatch@example.com")
    ws = await _create_club(client, admin["access_token"])
    admin_token = ws["tokens"]["access_token"]
    listing = (await client.get("/workspaces/me/members", headers=_auth(admin_token))).json()
    owner_mid = listing["members"][0]["id"]

    r = await client.patch(
        f"/workspaces/me/members/{owner_mid}",
        json={"role": "coach"},
        headers=_auth(admin_token),
    )
    assert r.status_code == 403


async def test_hybrid_user_sees_both_workspaces_after_switch(
    client: AsyncClient,
) -> None:
    """Regression for the hybrid-coach switcher bug: when a user is both a
    member of someone else's club AND owner of a personal workspace, the
    `/workspaces/mine` listing must include the club from inside the personal
    workspace too — otherwise the FE switcher hides itself and there's no
    way back."""
    # Pak Adi creates a club and invites the hybrid coach.
    admin = await _signin(client, "test-mem-hybrid-admin@example.com")
    club = await _create_club(client, admin["access_token"])
    admin_token = club["tokens"]["access_token"]
    invite = (
        await client.post(
            "/workspaces/me/members/invite",
            json={
                "email": "test-mem-hybrid-coach@example.com",
                "display_name": "Hybrid",
                "role": "coach",
            },
            headers=_auth(admin_token),
        )
    ).json()

    # The hybrid coach signs in for the first time, claims the invite,
    # creates their OWN personal workspace, then switches into it.
    hybrid = await _signin(client, "test-mem-hybrid-coach@example.com")
    claim = await client.post(
        f"/invites/{invite['invite_code']}/claim",
        headers=_auth(hybrid["access_token"]),
    )
    assert claim.status_code == 200
    hybrid_token_club = claim.json()["access_token"]

    create_personal = await client.post(
        "/workspaces",
        json={"type": "personal", "name": "Hybrid Personal", "primary_locale": "id"},
        headers=_auth(hybrid_token_club),
    )
    assert create_personal.status_code == 201
    hybrid_token_personal = create_personal.json()["tokens"]["access_token"]

    # The critical assertion: from inside the personal workspace, the hybrid
    # coach must still see the club they're a member of.
    listing = await client.get(
        "/workspaces/mine", headers=_auth(hybrid_token_personal)
    )
    assert listing.status_code == 200
    names = {w["workspace"]["name"] for w in listing.json()["workspaces"]}
    assert names == {"Test Club Mem", "Hybrid Personal"}

    # And the switch itself must work too.
    club_id = club["workspace"]["id"]
    switch_back = await client.post(
        f"/workspaces/{club_id}/switch", headers=_auth(hybrid_token_personal)
    )
    assert switch_back.status_code == 200, switch_back.text


async def test_revoke_pending_invite(client: AsyncClient) -> None:
    admin = await _signin(client, "test-mem-revinv@example.com")
    ws = await _create_club(client, admin["access_token"])
    admin_token = ws["tokens"]["access_token"]
    invite = (
        await client.post(
            "/workspaces/me/members/invite",
            json={
                "email": "test-mem-revinv-target@example.com",
                "display_name": "Coach",
                "role": "coach",
            },
            headers=_auth(admin_token),
        )
    ).json()

    r = await client.delete(
        f"/workspaces/me/members/invites/{invite['id']}",
        headers=_auth(admin_token),
    )
    assert r.status_code == 204

    listing = (await client.get("/workspaces/me/members", headers=_auth(admin_token))).json()
    assert listing["pending_invites"] == []
