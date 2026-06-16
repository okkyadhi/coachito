"""Match Maker Phase 3 — Mexicano + KOTH dynamic pairings.

The interesting properties (rather than exhaustive enumeration):

  - Mexicano: after a round, the **next** round seats players by
    leaderboard rank — top 4 land on Court 1, next 4 on Court 2, etc.
    Within a court, partnerships follow the configured setting.
  - KOTH: after a round, **Court 1 winners stay**, **losers drop**,
    **lower-court winners move up**.

Both behaviours are pure-Python in pairing.py and only need DB-level
verification when wired through the state machine, which is what these
tests do.
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
    KothPlacement,
    build_koth_round,
    build_mexicano_round,
)

from ._test_helpers import SUPERUSER_DSN, create_workspace, sign_in


# ── Pure-Python pairing unit tests ───────────────────────────────


def test_mexicano_top_four_to_court_one_1_3_vs_2_4() -> None:
    rnd = build_mexicano_round(
        round_number=2,
        ranked_player_indices=[0, 1, 2, 3, 4, 5, 6, 7],  # 0 = top
        court_count=2,
        pairing_setting="1_3_vs_2_4",
    )
    assert len(rnd.matches) == 2
    # Court 1: top 4 — pair 1+3 vs 2+4 → indices (0,2) vs (1,3)
    c1 = rnd.matches[0]
    assert c1.court_number == 1
    assert c1.side_a == (0, 2)
    assert c1.side_b == (1, 3)
    # Court 2: next 4 — same shape
    c2 = rnd.matches[1]
    assert c2.court_number == 2
    assert c2.side_a == (4, 6)
    assert c2.side_b == (5, 7)


def test_mexicano_1_4_vs_2_3() -> None:
    rnd = build_mexicano_round(
        round_number=3,
        ranked_player_indices=[0, 1, 2, 3],
        court_count=1,
        pairing_setting="1_4_vs_2_3",
    )
    c1 = rnd.matches[0]
    assert c1.side_a == (0, 3)
    assert c1.side_b == (1, 2)


def test_mexicano_resters_from_bottom_when_surplus() -> None:
    # 6 ranked players, 1 court → top 4 play, bottom 2 rest.
    rnd = build_mexicano_round(
        round_number=2,
        ranked_player_indices=[10, 11, 12, 13, 14, 15],
        court_count=1,
        pairing_setting="1_3_vs_2_4",
    )
    assert len(rnd.matches) == 1
    assert set(rnd.matches[0].side_a + rnd.matches[0].side_b) == {10, 11, 12, 13}
    assert rnd.resters == (14, 15)


def test_koth_winners_stay_on_top_court() -> None:
    # 2 courts, 8 players.  Court 1 winners (0,1) stay; losers (2,3)
    # drop.  Court 2 winners (4,5) move up.  Court 2 losers (6,7) stay.
    placements = [
        KothPlacement(0, 1, True),
        KothPlacement(1, 1, True),
        KothPlacement(2, 1, False),
        KothPlacement(3, 1, False),
        KothPlacement(4, 2, True),
        KothPlacement(5, 2, True),
        KothPlacement(6, 2, False),
        KothPlacement(7, 2, False),
    ]
    rnd = build_koth_round(
        round_number=2, placements=placements, court_count=2,
    )
    court1 = rnd.matches[0]
    court2 = rnd.matches[1]
    assert court1.court_number == 1
    assert court2.court_number == 2
    # Court 1: original winners + court 2 climbers.
    assert set(court1.side_a + court1.side_b) == {0, 1, 4, 5}
    # Court 2: original losers + bottom losers (who stay).
    assert set(court2.side_a + court2.side_b) == {2, 3, 6, 7}


def test_koth_lowest_court_losers_stay() -> None:
    # 1 court — losers and winners both stay on the only court; the
    # partnership rotation is the only thing that changes.
    placements = [
        KothPlacement(0, 1, True),
        KothPlacement(1, 1, True),
        KothPlacement(2, 1, False),
        KothPlacement(3, 1, False),
    ]
    rnd = build_koth_round(
        round_number=2, placements=placements, court_count=1,
    )
    assert len(rnd.matches) == 1
    assert set(rnd.matches[0].side_a + rnd.matches[0].side_b) == {0, 1, 2, 3}


# ── API integration tests ────────────────────────────────────────


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
            "  SELECT id FROM users WHERE email LIKE 'test-mmp3-%@example.com')"
        )
        await conn.execute(
            "DELETE FROM users WHERE email LIKE 'test-mmp3-%@example.com'"
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
    fmt: str,
    player_count: int = 4,
    court_count: int = 1,
) -> dict[str, str]:
    coach = await sign_in(client, email, captured)
    ws = await create_workspace(client, coach["access_token"], name="MMP3 Club")
    token = ws["tokens"]["access_token"]

    payload: dict[str, object] = {
        "title": f"{fmt} test",
        "format": fmt,
        "scoring_mode": "point",
        "scoring_target": 21,
        "court_count": court_count,
    }
    if fmt in {"mexicano", "mixicano"}:
        payload["mexicano_pairing"] = "1_3_vs_2_4"
    created = await client.post(
        "/events", json=payload, headers=_auth(token)
    )
    assert created.status_code == 201, created.text
    event_id = created.json()["id"]

    for i in range(player_count):
        r = await client.post(
            f"/events/{event_id}/participants",
            json={"display_name": f"Player {i + 1}", "initial_seed": i + 1},
            headers=_auth(token),
        )
        assert r.status_code == 201, r.text

    return {"token": token, "event_id": event_id}


async def test_mexicano_start_creates_only_round_one(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    s = await _setup(
        client, captured,
        email="test-mmp3-mex1@example.com", fmt="mexicano", player_count=4,
    )
    r = await client.post(
        f"/events/{s['event_id']}/start", headers=_auth(s["token"])
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "active"
    # Lazy generation: only round 1 should exist in the DB.
    rounds = await client.get(
        f"/events/{s['event_id']}/rounds", headers=_auth(s["token"])
    )
    rs = rounds.json()["rounds"]
    assert len(rs) == 1
    assert rs[0]["round_number"] == 1


async def test_mexicano_advance_round_reranks_by_leaderboard(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    """8 players, 2 courts.  After round 1, force side A to win all
    matches — those 4 players should ALL land on Court 1 in round 2."""
    s = await _setup(
        client, captured,
        email="test-mmp3-mex2@example.com",
        fmt="mexicano", player_count=8, court_count=2,
    )
    await client.post(
        f"/events/{s['event_id']}/start", headers=_auth(s["token"])
    )
    rnd1 = (
        await client.get(
            f"/events/{s['event_id']}/rounds", headers=_auth(s["token"])
        )
    ).json()["rounds"][0]
    # Score every match: side A wins 21-5.  That gives side A players
    # 21 points each (vs 5 for side B), so they should top the
    # leaderboard going into round 2.
    side_a_winners: set[str] = set()
    for m in rnd1["matches"]:
        side_a_winners |= set(m["side_a"])
        score = await client.patch(
            f"/events/{s['event_id']}/matches/{m['id']}/score",
            json={"score_a": 21, "score_b": 5},
            headers=_auth(s["token"]),
        )
        assert score.status_code == 200, score.text

    # Advance — Mexicano re-ranks, top 4 to Court 1.
    nxt = await client.post(
        f"/events/{s['event_id']}/rounds/next", headers=_auth(s["token"])
    )
    assert nxt.status_code == 200, nxt.text
    assert nxt.json()["current_round"] == 2

    rounds_after = (
        await client.get(
            f"/events/{s['event_id']}/rounds", headers=_auth(s["token"])
        )
    ).json()["rounds"]
    assert len(rounds_after) == 2  # round 2 now exists
    r2_court1 = next(
        m for m in rounds_after[1]["matches"] if m["court_number"] == 1
    )
    court1_players = set(r2_court1["side_a"]) | set(r2_court1["side_b"])
    # All 4 round-1 winners should be on Court 1.
    assert court1_players == side_a_winners


async def test_koth_winners_climb_losers_drop(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    """8 players, 2 courts.  Court 2 winners should move up to Court 1
    in round 2; Court 1 losers should drop to Court 2."""
    s = await _setup(
        client, captured,
        email="test-mmp3-koth1@example.com",
        fmt="koth", player_count=8, court_count=2,
    )
    await client.post(
        f"/events/{s['event_id']}/start", headers=_auth(s["token"])
    )
    rnd1 = (
        await client.get(
            f"/events/{s['event_id']}/rounds", headers=_auth(s["token"])
        )
    ).json()["rounds"][0]

    # Court 1: side A wins.  Court 2: side A wins.
    c1 = next(m for m in rnd1["matches"] if m["court_number"] == 1)
    c2 = next(m for m in rnd1["matches"] if m["court_number"] == 2)
    c1_winners = set(c1["side_a"])
    c1_losers = set(c1["side_b"])
    c2_winners = set(c2["side_a"])
    c2_losers = set(c2["side_b"])

    for m in (c1, c2):
        await client.patch(
            f"/events/{s['event_id']}/matches/{m['id']}/score",
            json={"score_a": 21, "score_b": 12},
            headers=_auth(s["token"]),
        )

    await client.post(
        f"/events/{s['event_id']}/rounds/next", headers=_auth(s["token"])
    )
    rounds_after = (
        await client.get(
            f"/events/{s['event_id']}/rounds", headers=_auth(s["token"])
        )
    ).json()["rounds"]
    assert len(rounds_after) == 2

    r2_c1 = next(m for m in rounds_after[1]["matches"] if m["court_number"] == 1)
    r2_c2 = next(m for m in rounds_after[1]["matches"] if m["court_number"] == 2)
    r2_c1_players = set(r2_c1["side_a"]) | set(r2_c1["side_b"])
    r2_c2_players = set(r2_c2["side_a"]) | set(r2_c2["side_b"])

    # Court 1 round 2: original C1 winners + C2 winners (who climbed).
    assert r2_c1_players == c1_winners | c2_winners
    # Court 2 round 2: original C1 losers (dropped) + C2 losers (stayed).
    assert r2_c2_players == c1_losers | c2_losers


async def test_team_format_start_still_blocked(
    client: AsyncClient, captured: list[dict[str, str]]
) -> None:
    """Team variants share the same draft surface but the pairing
    engine isn't wired up yet — start should error precisely."""
    s = await _setup(
        client, captured,
        email="test-mmp3-team@example.com",
        fmt="team_americano", player_count=4,
    )
    r = await client.post(
        f"/events/{s['event_id']}/start", headers=_auth(s["token"])
    )
    assert r.status_code == 409, r.text
    assert "not implemented" in r.json()["detail"].lower()
