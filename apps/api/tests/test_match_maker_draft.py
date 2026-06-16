"""Match Maker — draft state CRUD (docs/20 Phase 1).

Covers event create/list/detail/edit/cancel + participants/teams.  Pairing
engine, scoring, and public-read endpoints come in later phases and have
their own tests when they land.
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
async def _cleanup() -> None:
    yield
    conn = await asyncpg.connect(SUPERUSER_DSN)
    try:
        await conn.execute(
            "DELETE FROM workspaces WHERE owner_user_id IN ("
            "  SELECT id FROM users WHERE email LIKE 'test-mm-%@example.com')"
        )
        await conn.execute(
            "DELETE FROM users WHERE email LIKE 'test-mm-%@example.com'"
        )
    finally:
        await conn.close()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _coach_workspace(
    client: AsyncClient, captured: list[dict[str, str]], email: str
) -> dict[str, str]:
    coach = await sign_in(client, email, captured)
    ws = await create_workspace(client, coach["access_token"], name="MM Club")
    return {
        "token": ws["tokens"]["access_token"],
        "workspace_id": ws["workspace"]["id"],
        "coach_user_id": coach["user"]["id"],
    }


# ── Tests ────────────────────────────────────────────────────────


async def test_create_americano_draft(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    ws = await _coach_workspace(client, captured, "test-mm-c1@example.com")
    r = await client.post(
        "/events",
        json={
            "title": "Sunday Americano",
            "venue": "GBK Padel",
            "format": "americano",
            "scoring_mode": "point",
            "scoring_target": 21,
            "court_count": 2,
        },
        headers=_auth(ws["token"]),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "draft"
    assert body["title"] == "Sunday Americano"
    assert body["is_public"] is True
    assert body["public_slug"] is not None
    assert len(body["public_slug"]) == 8
    assert body["participants_count"] == 0


async def test_mexicano_defaults_pairing_when_omitted(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    ws = await _coach_workspace(client, captured, "test-mm-c2@example.com")
    r = await client.post(
        "/events",
        json={
            "title": "Mex Night",
            "format": "mexicano",
            "scoring_mode": "point",
            "scoring_target": 24,
            "court_count": 2,
        },
        headers=_auth(ws["token"]),
    )
    assert r.status_code == 201, r.text
    # Service should fill the default within-court pairing.
    assert r.json()["mexicano_pairing"] == "1_3_vs_2_4"


async def test_untimed_point_fills_round_timer(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    ws = await _coach_workspace(client, captured, "test-mm-c3@example.com")
    r = await client.post(
        "/events",
        json={
            "title": "Untimed",
            "format": "americano",
            "scoring_mode": "point",
            "scoring_target": None,
            "court_count": 1,
        },
        headers=_auth(ws["token"]),
    )
    assert r.status_code == 201
    # Default 12-minute timer.
    assert r.json()["round_timer_seconds"] == 12 * 60


async def test_list_filters_by_status(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    ws = await _coach_workspace(client, captured, "test-mm-c4@example.com")
    # Create 2 drafts.
    for i in range(2):
        await client.post(
            "/events",
            json={
                "title": f"Draft {i}",
                "format": "americano",
                "scoring_mode": "point",
                "scoring_target": 21,
                "court_count": 1,
            },
            headers=_auth(ws["token"]),
        )
    r = await client.get(
        "/events?status_filter=draft", headers=_auth(ws["token"])
    )
    assert r.status_code == 200
    assert len(r.json()["events"]) == 2


async def test_rls_isolation_between_workspaces(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    a = await _coach_workspace(client, captured, "test-mm-aA@example.com")
    b = await _coach_workspace(client, captured, "test-mm-aB@example.com")
    await client.post(
        "/events",
        json={
            "title": "A's event",
            "format": "americano",
            "scoring_mode": "point",
            "scoring_target": 21,
            "court_count": 1,
        },
        headers=_auth(a["token"]),
    )
    # B should see zero.
    r = await client.get("/events", headers=_auth(b["token"]))
    assert r.json()["events"] == []


async def test_patch_draft_then_cancel(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    ws = await _coach_workspace(client, captured, "test-mm-c5@example.com")
    created = await client.post(
        "/events",
        json={
            "title": "First name",
            "format": "americano",
            "scoring_mode": "point",
            "scoring_target": 21,
            "court_count": 2,
        },
        headers=_auth(ws["token"]),
    )
    eid = created.json()["id"]
    r = await client.patch(
        f"/events/{eid}",
        json={"title": "Renamed", "court_count": 3},
        headers=_auth(ws["token"]),
    )
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "Renamed"
    assert r.json()["court_count"] == 3

    cancelled = await client.post(
        f"/events/{eid}/cancel", headers=_auth(ws["token"])
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    # archived_at filter hides it from the list.
    listed = await client.get("/events", headers=_auth(ws["token"]))
    assert listed.json()["events"] == []


async def test_add_participant_from_athlete(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    ws = await _coach_workspace(client, captured, "test-mm-c6@example.com")
    conn = await superuser_conn()
    try:
        athlete_id = await insert_athlete(
            conn,
            workspace_id=ws["workspace_id"],
            coach_id=ws["coach_user_id"],
            display_name="Andi P.",
        )
    finally:
        await conn.close()

    created = await client.post(
        "/events",
        json={
            "title": "Sunday",
            "format": "americano",
            "scoring_mode": "point",
            "scoring_target": 21,
            "court_count": 1,
        },
        headers=_auth(ws["token"]),
    )
    eid = created.json()["id"]
    r = await client.post(
        f"/events/{eid}/participants",
        json={
            "display_name": "Andi P.",
            "athlete_id": athlete_id,
            "initial_seed": 1,
        },
        headers=_auth(ws["token"]),
    )
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["athlete_id"] == athlete_id
    assert p["initial_seed"] == 1
    assert p["joined_round"] == 1

    detail = await client.get(f"/events/{eid}", headers=_auth(ws["token"]))
    assert len(detail.json()["participants"]) == 1


async def test_add_guest_participant_without_athlete(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    ws = await _coach_workspace(client, captured, "test-mm-c7@example.com")
    created = await client.post(
        "/events",
        json={
            "title": "Guest event",
            "format": "americano",
            "scoring_mode": "point",
            "scoring_target": 21,
            "court_count": 1,
        },
        headers=_auth(ws["token"]),
    )
    r = await client.post(
        f"/events/{created.json()['id']}/participants",
        json={"display_name": "Walk-in Wira", "tag": "M"},
        headers=_auth(ws["token"]),
    )
    assert r.status_code == 201
    p = r.json()
    assert p["athlete_id"] is None
    assert p["display_name"] == "Walk-in Wira"
    assert p["tag"] == "M"


async def test_team_format_team_and_member_flow(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    ws = await _coach_workspace(client, captured, "test-mm-c8@example.com")
    created = await client.post(
        "/events",
        json={
            "title": "Team Night",
            "format": "team_americano",
            "scoring_mode": "point",
            "scoring_target": 21,
            "court_count": 1,
        },
        headers=_auth(ws["token"]),
    )
    eid = created.json()["id"]

    team_r = await client.post(
        f"/events/{eid}/teams",
        json={"display_name": "Andi & Budi"},
        headers=_auth(ws["token"]),
    )
    assert team_r.status_code == 201, team_r.text
    team_id = team_r.json()["id"]

    p1 = await client.post(
        f"/events/{eid}/participants",
        json={"display_name": "Andi", "team_id": team_id},
        headers=_auth(ws["token"]),
    )
    assert p1.status_code == 201
    assert p1.json()["team_id"] == team_id

    # Patch team name.
    renamed = await client.patch(
        f"/events/{eid}/teams/{team_id}",
        json={"display_name": "The Dynamos"},
        headers=_auth(ws["token"]),
    )
    assert renamed.status_code == 200
    assert renamed.json()["display_name"] == "The Dynamos"

    # Delete team (no scored matches yet).
    deleted = await client.delete(
        f"/events/{eid}/teams/{team_id}", headers=_auth(ws["token"])
    )
    assert deleted.status_code == 204


async def test_team_endpoint_rejects_non_team_format(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    ws = await _coach_workspace(client, captured, "test-mm-c9@example.com")
    created = await client.post(
        "/events",
        json={
            "title": "Solo",
            "format": "americano",
            "scoring_mode": "point",
            "scoring_target": 21,
            "court_count": 1,
        },
        headers=_auth(ws["token"]),
    )
    r = await client.post(
        f"/events/{created.json()['id']}/teams",
        json={"display_name": "Whatever"},
        headers=_auth(ws["token"]),
    )
    assert r.status_code == 409  # EventStateError → 409


async def test_withdraw_participant_in_draft_hard_deletes(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    ws = await _coach_workspace(client, captured, "test-mm-c10@example.com")
    created = await client.post(
        "/events",
        json={
            "title": "X",
            "format": "americano",
            "scoring_mode": "point",
            "scoring_target": 21,
            "court_count": 1,
        },
        headers=_auth(ws["token"]),
    )
    eid = created.json()["id"]
    p = await client.post(
        f"/events/{eid}/participants",
        json={"display_name": "Whoops"},
        headers=_auth(ws["token"]),
    )
    pid = p.json()["id"]

    delete_r = await client.delete(
        f"/events/{eid}/participants/{pid}", headers=_auth(ws["token"])
    )
    assert delete_r.status_code == 204

    detail = await client.get(f"/events/{eid}", headers=_auth(ws["token"]))
    assert detail.json()["participants"] == []


async def test_trainee_can_create_event_in_their_workspace(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    """A claimed trainee in a club workspace can also host events.
    Backend has no role gate — only RLS on workspace_id — so the same
    /events surface works for both roles.  FE wires the Events tab into
    the trainee shell separately."""
    coach = await sign_in(client, "test-mm-c11@example.com", captured)
    ws = await create_workspace(client, coach["access_token"], name="MM Club 11")
    coach_token = ws["tokens"]["access_token"]

    created = await client.post(
        "/trainees",
        json={"name": "Andi", "phone_e164": "+62811900900"},
        headers=_auth(coach_token),
    )
    assert created.status_code == 201
    invite_code = created.json()["invite"]["code"]

    trainee = await sign_in(client, "test-mm-andi@example.com", captured)
    claim = await client.post(
        f"/invites/{invite_code}/claim",
        headers=_auth(trainee["access_token"]),
    )
    assert claim.status_code == 200
    trainee_token = claim.json()["access_token"]
    assert claim.json()["user"]["role"] == "trainee"

    # The trainee creates an event in the same workspace.
    r = await client.post(
        "/events",
        json={
            "title": "Trainee-hosted Americano",
            "format": "americano",
            "scoring_mode": "point",
            "scoring_target": 21,
            "court_count": 1,
        },
        headers=_auth(trainee_token),
    )
    assert r.status_code == 201, r.text
    event = r.json()
    assert event["title"] == "Trainee-hosted Americano"

    # Host-scoped listing: the coach does NOT see the trainee's event by
    # default — they aren't the host and aren't a participant.  The coach
    # can still pull it directly via GET /events/:id if they know the id,
    # or via the public slug (Phase 2 follow-up).
    coach_list = await client.get("/events", headers=_auth(coach_token))
    titles = [e["title"] for e in coach_list.json()["events"]]
    assert "Trainee-hosted Americano" not in titles

    # The trainee themselves sees it (they're the host).
    own_list = await client.get("/events", headers=_auth(trainee_token))
    own_titles = [e["title"] for e in own_list.json()["events"]]
    assert "Trainee-hosted Americano" in own_titles


async def test_play_workspace_type_accepted_by_db() -> None:
    """Sanity check: the 'play' value was added to workspaces.type CHECK
    by the migration.  Asserted at the DB layer rather than via API since
    no /play workspace creation endpoint exists yet (Phase 4)."""
    conn = await superuser_conn()
    try:
        user_id = await conn.fetchval(
            "INSERT INTO users (email, display_name, preferred_locale) "
            "VALUES ('test-mm-play@example.com', 'Player', 'en') RETURNING id"
        )
        sport_id = await conn.fetchval(
            "SELECT id FROM sports WHERE code = 'padel' LIMIT 1"
        )
        ws_id = await conn.fetchval(
            """
            INSERT INTO workspaces (sport_id, type, name, brand_color, primary_locale,
                                    plan, trial_ends_at, owner_user_id)
            VALUES ($1, 'play', 'A Player', '#C66B47', 'en',
                    'free_trial', NOW() + INTERVAL '30 days', $2)
            RETURNING id
            """,
            sport_id, user_id,
        )
        assert ws_id is not None
    finally:
        await conn.execute(
            "DELETE FROM workspaces WHERE owner_user_id IN ("
            "  SELECT id FROM users WHERE email = 'test-mm-play@example.com')"
        )
        await conn.execute(
            "DELETE FROM users WHERE email = 'test-mm-play@example.com'"
        )
        await conn.close()
