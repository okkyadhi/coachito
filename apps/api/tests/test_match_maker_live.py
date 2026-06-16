"""Match Maker — Phase 2 live event tests.

Covers the Americano pairing engine, start → score → next-round →
complete state machine, and the leaderboard endpoint.  Pure-Python
pairing tests sit alongside the API integration suite — they don't
touch the DB.
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
from src.match_maker.pairing import (
    build_americano_schedule,
    courts_for,
    total_rounds_for,
)

from ._test_helpers import SUPERUSER_DSN, create_workspace, sign_in


# ── Pairing engine unit tests ────────────────────────────────────


def test_pairing_eight_players_two_courts_seven_rounds() -> None:
    schedule = build_americano_schedule(
        player_count=8, court_count=2, total_rounds=total_rounds_for(8),
    )
    assert len(schedule) == 7
    for rnd in schedule:
        # Two courts, 4 players per court — all 8 play every round.
        assert len(rnd.matches) == 2
        seen: set[int] = set()
        for m in rnd.matches:
            for p in (*m.side_a, *m.side_b):
                assert p not in seen, "player double-booked in a round"
                seen.add(p)
        assert seen == set(range(8))
        assert rnd.resters == ()


def test_pairing_rotates_partners() -> None:
    """Across 7 rounds of 8 players, each player should partner several
    different players.  Exact ⌈7/(N-1)⌉ = 1 perfect match isn't
    guaranteed by the greedy builder, but it should keep repeats low."""
    schedule = build_americano_schedule(
        player_count=8, court_count=2, total_rounds=7,
    )
    partner_counts: dict[tuple[int, int], int] = {}
    for rnd in schedule:
        for m in rnd.matches:
            for side in (m.side_a, m.side_b):
                key = tuple(sorted(side))
                partner_counts[key] = partner_counts.get(key, 0) + 1
    # 8 players → 28 distinct pairs.  Across 7 rounds × 4 pairs = 28
    # partnership slots — perfect schedule = each pair exactly once.
    # The greedy builder won't always hit that, but no pair should
    # partner more than 3 times across 7 rounds (≤ ⌈7×4/28⌉×2 = 2 in
    # theory; allowing 3 gives the greedy algorithm slack).
    max_repeat = max(partner_counts.values())
    assert max_repeat <= 3, (
        f"greedy pairing repeated some partnership {max_repeat} times"
    )


def test_pairing_six_players_one_court_rotates_resters() -> None:
    """6 players + 1 court means 2 rest each round.  Across enough
    rounds each player rests roughly evenly."""
    schedule = build_americano_schedule(
        player_count=6, court_count=1, total_rounds=5,
    )
    rest_count: dict[int, int] = {i: 0 for i in range(6)}
    for rnd in schedule:
        assert len(rnd.matches) == 1
        assert len(rnd.resters) == 2
        for r_idx in rnd.resters:
            rest_count[r_idx] += 1
    # Total rest slots = 5 rounds × 2 resters = 10, distributed across
    # 6 players → mean ~1.67.  Max gap shouldn't exceed 2.
    assert max(rest_count.values()) - min(rest_count.values()) <= 2


def test_pairing_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        build_americano_schedule(
            player_count=3, court_count=1, total_rounds=2,
        )
    with pytest.raises(ValueError):
        build_americano_schedule(
            player_count=8, court_count=0, total_rounds=1,
        )
    with pytest.raises(ValueError):
        build_americano_schedule(
            player_count=8, court_count=2, total_rounds=0,
        )


def test_courts_for_caps_to_player_count() -> None:
    # 7 players, host wanted 3 courts → only 1 full court fits.
    assert courts_for(7, 3) == 1
    # 8 players, host wanted 3 courts → 2 courts fit.
    assert courts_for(8, 3) == 2


# ── API state-machine tests ──────────────────────────────────────


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
            "  SELECT id FROM users WHERE email LIKE 'test-mml-%@example.com')"
        )
        await conn.execute(
            "DELETE FROM users WHERE email LIKE 'test-mml-%@example.com'"
        )
    finally:
        await conn.close()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _setup_event_with_players(
    client: AsyncClient,
    captured: list[dict[str, str]],
    email: str,
    *,
    player_count: int = 4,
    court_count: int = 1,
) -> dict[str, str]:
    coach = await sign_in(client, email, captured)
    ws = await create_workspace(client, coach["access_token"], name="MML Club")
    token = ws["tokens"]["access_token"]

    event_resp = await client.post(
        "/events",
        json={
            "title": "Live Test",
            "format": "americano",
            "scoring_mode": "point",
            "scoring_target": 21,
            "court_count": court_count,
        },
        headers=_auth(token),
    )
    assert event_resp.status_code == 201
    event_id = event_resp.json()["id"]

    for i in range(player_count):
        r = await client.post(
            f"/events/{event_id}/participants",
            json={"display_name": f"Player {i + 1}"},
            headers=_auth(token),
        )
        assert r.status_code == 201, r.text

    return {"token": token, "event_id": event_id}


async def test_start_event_rejects_under_four_players(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _setup_event_with_players(
        client, captured, "test-mml-c1@example.com", player_count=3,
    )
    r = await client.post(
        f"/events/{s['event_id']}/start", headers=_auth(s["token"])
    )
    assert r.status_code == 409


async def test_start_event_creates_round_one_with_one_match(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _setup_event_with_players(
        client, captured, "test-mml-c2@example.com", player_count=4,
    )
    r = await client.post(
        f"/events/{s['event_id']}/start", headers=_auth(s["token"])
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "active"
    assert r.json()["current_round"] == 1
    assert r.json()["total_rounds"] == 3  # N-1 for 4 players

    rounds = await client.get(
        f"/events/{s['event_id']}/rounds", headers=_auth(s["token"])
    )
    assert rounds.status_code == 200
    body = rounds.json()
    assert len(body["rounds"]) == 3
    # Round 1: one match on Court 1 with all 4 players.
    r1 = body["rounds"][0]
    assert len(r1["matches"]) == 1
    assert r1["matches"][0]["court_number"] == 1
    all_players = set(r1["matches"][0]["side_a"]) | set(r1["matches"][0]["side_b"])
    assert len(all_players) == 4


async def test_score_entry_updates_leaderboard(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _setup_event_with_players(
        client, captured, "test-mml-c3@example.com", player_count=4,
    )
    await client.post(
        f"/events/{s['event_id']}/start", headers=_auth(s["token"])
    )
    rounds = (
        await client.get(
            f"/events/{s['event_id']}/rounds", headers=_auth(s["token"])
        )
    ).json()
    match = rounds["rounds"][0]["matches"][0]

    score_resp = await client.patch(
        f"/events/{s['event_id']}/matches/{match['id']}/score",
        json={"score_a": 21, "score_b": 15},
        headers=_auth(s["token"]),
    )
    assert score_resp.status_code == 200, score_resp.text
    assert score_resp.json()["winner_side"] == "A"

    lb = await client.get(
        f"/events/{s['event_id']}/leaderboard", headers=_auth(s["token"])
    )
    assert lb.status_code == 200
    rows = lb.json()["rows"]
    assert len(rows) == 4
    # Side A players have 21 points + 1 win; Side B has 15 points + 0 wins.
    a_ids = set(match["side_a"])
    for r in rows:
        if r["participant_id"] in a_ids:
            assert r["points"] == 21
            assert r["wins"] == 1
        else:
            assert r["points"] == 15
            assert r["wins"] == 0


async def test_advance_round_then_complete(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _setup_event_with_players(
        client, captured, "test-mml-c4@example.com", player_count=4,
    )
    started = await client.post(
        f"/events/{s['event_id']}/start", headers=_auth(s["token"])
    )
    assert started.json()["current_round"] == 1

    nxt = await client.post(
        f"/events/{s['event_id']}/rounds/next", headers=_auth(s["token"])
    )
    assert nxt.status_code == 200, nxt.text
    assert nxt.json()["current_round"] == 2

    # Two more rounds → can't advance past round 3 (total = 3).
    await client.post(
        f"/events/{s['event_id']}/rounds/next", headers=_auth(s["token"])
    )
    last_advance = await client.post(
        f"/events/{s['event_id']}/rounds/next", headers=_auth(s["token"])
    )
    assert last_advance.status_code == 409  # at total_rounds already

    done = await client.post(
        f"/events/{s['event_id']}/complete", headers=_auth(s["token"])
    )
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "completed"
    assert done.json()["completed_at"] is not None
