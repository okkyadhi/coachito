"""Match Maker Phase 3 polish — reshuffle, court rename, detailed
leaderboard columns."""

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
            "  SELECT id FROM users WHERE email LIKE 'test-mmpol-%@example.com')"
        )
        await conn.execute(
            "DELETE FROM users WHERE email LIKE 'test-mmpol-%@example.com'"
        )
    finally:
        await conn.close()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _setup(
    client: AsyncClient,
    captured: list[dict[str, str]],
    *,
    email: str,
    fmt: str = "americano",
    player_count: int = 4,
    court_count: int = 1,
) -> dict[str, str]:
    coach = await sign_in(client, email, captured)
    ws = await create_workspace(client, coach["access_token"], name="MM Pol")
    token = ws["tokens"]["access_token"]
    created = await client.post(
        "/events",
        json={
            "title": "Polish",
            "format": fmt,
            "scoring_mode": "point",
            "scoring_target": 21,
            "court_count": court_count,
        },
        headers=_auth(token),
    )
    assert created.status_code == 201, created.text
    event_id = created.json()["id"]
    for i in range(player_count):
        await client.post(
            f"/events/{event_id}/participants",
            json={"display_name": f"P{i+1}", "initial_seed": i + 1},
            headers=_auth(token),
        )
    return {"token": token, "event_id": event_id}


async def test_event_out_includes_empty_court_names_array(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _setup(client, captured, email="test-mmpol-c1@example.com")
    detail = await client.get(
        f"/events/{s['event_id']}", headers=_auth(s["token"])
    )
    assert detail.status_code == 200
    assert detail.json()["court_names"] == []


async def test_rename_court_then_clear(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _setup(
        client, captured, email="test-mmpol-c2@example.com", court_count=2,
    )
    # Set Court 1 → "Center Court"
    r = await client.patch(
        f"/events/{s['event_id']}/courts/1",
        json={"name": "Center Court"},
        headers=_auth(s["token"]),
    )
    assert r.status_code == 200, r.text
    assert r.json()["court_names"] == ["Center Court", None]

    # Now rename Court 2 too
    r2 = await client.patch(
        f"/events/{s['event_id']}/courts/2",
        json={"name": "Side Court"},
        headers=_auth(s["token"]),
    )
    assert r2.json()["court_names"] == ["Center Court", "Side Court"]

    # Clear Court 1 with null
    r3 = await client.patch(
        f"/events/{s['event_id']}/courts/1",
        json={"name": None},
        headers=_auth(s["token"]),
    )
    assert r3.json()["court_names"] == [None, "Side Court"]


async def test_rename_court_rejects_out_of_range(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _setup(
        client, captured, email="test-mmpol-c3@example.com", court_count=2,
    )
    bad = await client.patch(
        f"/events/{s['event_id']}/courts/9",
        json={"name": "Phantom"},
        headers=_auth(s["token"]),
    )
    assert bad.status_code == 409


async def test_leaderboard_includes_diff_and_compensation(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _setup(
        client, captured, email="test-mmpol-c4@example.com",
        fmt="americano", player_count=4,
    )
    await client.post(
        f"/events/{s['event_id']}/start", headers=_auth(s["token"])
    )
    rounds = (
        await client.get(
            f"/events/{s['event_id']}/rounds", headers=_auth(s["token"])
        )
    ).json()
    m = rounds["rounds"][0]["matches"][0]
    await client.patch(
        f"/events/{s['event_id']}/matches/{m['id']}/score",
        json={"score_a": 21, "score_b": 8},
        headers=_auth(s["token"]),
    )
    lb = (
        await client.get(
            f"/events/{s['event_id']}/leaderboard",
            headers=_auth(s["token"]),
        )
    ).json()
    rows = lb["rows"]
    assert len(rows) == 4
    # Each row carries the new fields.
    sample = rows[0]
    for key in ("ties", "point_diff", "compensation"):
        assert key in sample
    # Side A (winners): +13 point_diff each.  Side B: -13.
    diffs = sorted([r["point_diff"] for r in rows])
    assert diffs == [-13, -13, 13, 13]
    # All four played 1 match → comp is 0 for everyone.
    assert all(r["compensation"] == 0 for r in rows)


async def test_reshuffle_resequences_round_one(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _setup(
        client, captured, email="test-mmpol-c5@example.com",
        fmt="mexicano", player_count=8, court_count=2,
    )
    await client.post(
        f"/events/{s['event_id']}/start", headers=_auth(s["token"])
    )
    before = (
        await client.get(
            f"/events/{s['event_id']}/rounds", headers=_auth(s["token"])
        )
    ).json()["rounds"]
    match_ids_before = {m["id"] for m in before[0]["matches"]}

    r = await client.post(
        f"/events/{s['event_id']}/rounds/current/reshuffle",
        headers=_auth(s["token"]),
    )
    assert r.status_code == 200, r.text

    after = (
        await client.get(
            f"/events/{s['event_id']}/rounds", headers=_auth(s["token"])
        )
    ).json()["rounds"]
    # Still one round (current), but the match rows are fresh inserts.
    assert len(after) == 1
    match_ids_after = {m["id"] for m in after[0]["matches"]}
    assert match_ids_after.isdisjoint(match_ids_before)


async def test_reshuffle_blocked_after_score_recorded(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _setup(
        client, captured, email="test-mmpol-c6@example.com",
        fmt="americano", player_count=4,
    )
    await client.post(
        f"/events/{s['event_id']}/start", headers=_auth(s["token"])
    )
    rounds = (
        await client.get(
            f"/events/{s['event_id']}/rounds", headers=_auth(s["token"])
        )
    ).json()
    m = rounds["rounds"][0]["matches"][0]
    await client.patch(
        f"/events/{s['event_id']}/matches/{m['id']}/score",
        json={"score_a": 21, "score_b": 5},
        headers=_auth(s["token"]),
    )
    bad = await client.post(
        f"/events/{s['event_id']}/rounds/current/reshuffle",
        headers=_auth(s["token"]),
    )
    assert bad.status_code == 409
