"""Match Maker service — pure-ish DB operations.

Keeps validation + state-machine guards out of the HTTP layer so they're
unit-testable and reusable from RQ workers later (e.g. when the public
standings backfill or PDF export runs from a background job).
"""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import (
    MEXICANO_FAMILY,
    TEAM_FORMATS,
    EventCreateIn,
    EventDetailOut,
    EventOut,
    EventUpdateIn,
    LeaderboardSort,
    MexicanoPairing,
    ParticipantAddIn,
    ParticipantOut,
    ParticipantPatchIn,
    TeamCreateIn,
    TeamOut,
    TeamPatchIn,
)


class EventNotFoundError(Exception):
    """The event doesn't exist in the caller's workspace (RLS hid it, or
    it's truly missing)."""


class EventStateError(Exception):
    """The event isn't in a state where this mutation is allowed (e.g.
    editing a completed event)."""


# ── Public slug ──────────────────────────────────────────────────


_SLUG_ALPHABET = "abcdefghijkmnopqrstuvwxyz23456789"  # no 0/o/1/l for legibility


def _new_public_slug() -> str:
    """8-char URL-safe slug.  Collision probability is ~1 in 10^12 per
    pair; we still UNIQUE-index it and retry on conflict in the caller."""
    return "".join(secrets.choice(_SLUG_ALPHABET) for _ in range(8))


# ── Domain validation ───────────────────────────────────────────


def _validate_event_create(body: EventCreateIn) -> None:
    """Catch contradictions the DB can't (or shouldn't) express directly."""
    if body.format in MEXICANO_FAMILY and body.mexicano_pairing is None:
        # Mexicano needs a within-court pairing choice; default to the
        # "champion-challenger" variant if the FE didn't pick.  Mutate via
        # a separate path since Pydantic v2 models are frozen by default
        # for `extra='forbid'` — but the caller passes a mutable model.
        body.mexicano_pairing = "1_3_vs_2_4"  # type: ignore[misc]
    if body.scoring_mode == "point" and body.scoring_target is None:
        # 'point' scoring without a target means 'untimed' — needs a timer.
        if body.round_timer_seconds is None:
            body.round_timer_seconds = 12 * 60  # type: ignore[misc]
    if body.scoring_mode != "point" and body.round_timer_seconds is not None:
        # Round timer only makes sense in untimed point scoring.
        body.round_timer_seconds = None  # type: ignore[misc]


# ── Create / list / detail ──────────────────────────────────────


async def create_event(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    created_by_id: UUID,
    body: EventCreateIn,
) -> EventOut:
    _validate_event_create(body)

    # Generate a unique public slug with up to 3 retries on collision.
    slug: str | None = None
    if body.is_public:
        for _ in range(3):
            candidate = _new_public_slug()
            taken = await db.scalar(
                text(
                    "SELECT 1 FROM match_events WHERE public_slug = :s LIMIT 1"
                ),
                {"s": candidate},
            )
            if not taken:
                slug = candidate
                break

    row = (
        await db.execute(
            text(
                """
                INSERT INTO match_events (
                    workspace_id, title, venue, format, scoring_mode,
                    scoring_target, round_timer_seconds, court_count,
                    mexicano_pairing, leaderboard_sort,
                    is_public, public_slug, starts_at, created_by_id
                ) VALUES (
                    :wid, :title, :venue, :format, :scoring_mode,
                    :scoring_target, :round_timer_seconds, :court_count,
                    :mexicano_pairing, :leaderboard_sort,
                    :is_public, :public_slug, :starts_at, :created_by_id
                )
                RETURNING id
                """
            ),
            {
                "wid": workspace_id,
                "title": body.title.strip(),
                "venue": body.venue.strip() if body.venue else None,
                "format": body.format,
                "scoring_mode": body.scoring_mode,
                "scoring_target": body.scoring_target,
                "round_timer_seconds": body.round_timer_seconds,
                "court_count": body.court_count,
                "mexicano_pairing": body.mexicano_pairing,
                "leaderboard_sort": body.leaderboard_sort,
                "is_public": body.is_public,
                "public_slug": slug,
                "starts_at": body.starts_at,
                "created_by_id": created_by_id,
            },
        )
    ).first()
    assert row is not None
    event_id = row[0]
    # IMPORTANT: build the response BEFORE commit.  After commit, the
    # SET LOCAL ``app.current_workspace_id`` GUC dies and RLS would hide
    # the freshly-inserted row from the post-write SELECT.
    out = await fetch_event_summary(db, workspace_id=workspace_id, event_id=event_id)
    await db.commit()
    if out is None:  # pragma: no cover — defensive
        raise EventNotFoundError
    return out


async def list_events(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
    status: str | None = None,
) -> list[EventOut]:
    """Host-scoped visibility: the caller sees events they host or
    participate in, never every event in the workspace.  Coaches in a club
    don't get a feed of every trainee-hosted social event, and trainees
    don't see other trainees' events either.  Public discovery of events
    outside the caller's involvement is the job of /public/e/<slug>
    (Phase 2 follow-up) — that path bypasses workspace context entirely.
    """
    where = [
        "e.workspace_id = :wid",
        "e.archived_at IS NULL",
        # Host OR participant (linked via claim_user_id when claimed, or
        # via athlete_id → athletes.user_id for trainees in this workspace).
        """(
            e.created_by_id = :uid
            OR EXISTS (
                SELECT 1 FROM match_event_participants p
                WHERE p.event_id = e.id
                  AND (
                    p.claim_user_id = :uid
                    OR p.athlete_id IN (
                        SELECT a.id FROM athletes a
                        WHERE a.user_id = :uid AND a.workspace_id = e.workspace_id
                    )
                  )
            )
        )""",
    ]
    params: dict[str, Any] = {"wid": workspace_id, "uid": user_id}
    if status is not None:
        where.append("e.status = :status")
        params["status"] = status
    rows = (
        await db.execute(
            text(
                f"""
                SELECT
                    e.*,
                    (SELECT COUNT(*) FROM match_event_participants p
                       WHERE p.event_id = e.id AND p.withdrew_round IS NULL) AS participants_count,
                    (SELECT COUNT(*) FROM match_event_teams t
                       WHERE t.event_id = e.id) AS teams_count
                FROM match_events e
                WHERE {' AND '.join(where)}
                ORDER BY
                    CASE e.status
                        WHEN 'active' THEN 0
                        WHEN 'draft' THEN 1
                        WHEN 'completed' THEN 2
                        WHEN 'cancelled' THEN 3
                    END,
                    COALESCE(e.starts_at, e.created_at) DESC
                """
            ),
            params,
        )
    ).mappings().all()
    return [_row_to_event_out(r) for r in rows]


async def fetch_event_summary(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_id: UUID,
) -> EventOut | None:
    row = (
        await db.execute(
            text(
                """
                SELECT
                    e.*,
                    (SELECT COUNT(*) FROM match_event_participants p
                       WHERE p.event_id = e.id AND p.withdrew_round IS NULL) AS participants_count,
                    (SELECT COUNT(*) FROM match_event_teams t
                       WHERE t.event_id = e.id) AS teams_count
                FROM match_events e
                WHERE e.id = :eid AND e.workspace_id = :wid
                  AND e.archived_at IS NULL
                """
            ),
            {"eid": event_id, "wid": workspace_id},
        )
    ).mappings().first()
    return _row_to_event_out(row) if row else None


async def fetch_event_detail(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_id: UUID,
) -> EventDetailOut | None:
    summary = await fetch_event_summary(
        db, workspace_id=workspace_id, event_id=event_id
    )
    if summary is None:
        return None

    parts = (
        await db.execute(
            text(
                """
                SELECT id, athlete_id, claim_user_id, display_name,
                       team_id, tag, initial_seed, joined_round,
                       withdrew_round
                FROM match_event_participants
                WHERE event_id = :eid
                ORDER BY COALESCE(initial_seed, 999999), created_at
                """
            ),
            {"eid": event_id},
        )
    ).mappings().all()
    teams = (
        await db.execute(
            text(
                """
                SELECT id, display_name, tag
                FROM match_event_teams
                WHERE event_id = :eid
                ORDER BY created_at
                """
            ),
            {"eid": event_id},
        )
    ).mappings().all()
    return EventDetailOut(
        **summary.model_dump(),
        participants=[
            ParticipantOut(
                id=str(p["id"]),
                athlete_id=str(p["athlete_id"]) if p["athlete_id"] else None,
                claim_user_id=str(p["claim_user_id"]) if p["claim_user_id"] else None,
                display_name=p["display_name"],
                team_id=str(p["team_id"]) if p["team_id"] else None,
                tag=p["tag"],
                initial_seed=p["initial_seed"],
                joined_round=p["joined_round"],
                withdrew_round=p["withdrew_round"],
            )
            for p in parts
        ],
        teams=[
            TeamOut(
                id=str(t["id"]),
                display_name=t["display_name"],
                tag=t["tag"],
            )
            for t in teams
        ],
    )


# ── Patch ───────────────────────────────────────────────────────


_ALWAYS_MUTABLE: frozenset[str] = frozenset(
    {"court_count", "mexicano_pairing", "leaderboard_sort"}
)


async def patch_event(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_id: UUID,
    body: EventUpdateIn,
) -> EventOut:
    current = await db.execute(
        text(
            "SELECT status FROM match_events "
            "WHERE id = :eid AND workspace_id = :wid"
        ),
        {"eid": event_id, "wid": workspace_id},
    )
    row = current.first()
    if row is None:
        raise EventNotFoundError
    status_val = row[0]
    if status_val in ("completed", "cancelled"):
        raise EventStateError(
            f"Cannot edit event in '{status_val}' state."
        )

    patch = body.model_dump(exclude_unset=True)
    if not patch:
        out = await fetch_event_summary(
            db, workspace_id=workspace_id, event_id=event_id
        )
        assert out is not None
        return out

    # Once active, only court_count / mexicano_pairing / leaderboard_sort
    # are mutable (docs/20 §8).
    if status_val == "active":
        bad = set(patch.keys()) - _ALWAYS_MUTABLE
        if bad:
            raise EventStateError(
                f"Active event: cannot change {sorted(bad)}."
            )

    set_clauses = ", ".join(f"{k} = :{k}" for k in patch.keys())
    await db.execute(
        text(
            f"UPDATE match_events SET {set_clauses}, updated_at = NOW() "
            f"WHERE id = :eid AND workspace_id = :wid"
        ),
        {**patch, "eid": event_id, "wid": workspace_id},
    )
    out = await fetch_event_summary(
        db, workspace_id=workspace_id, event_id=event_id
    )
    await db.commit()
    assert out is not None
    return out


# ── Cancel ───────────────────────────────────────────────────────


async def cancel_event(
    db: AsyncSession, *, workspace_id: UUID, event_id: UUID
) -> EventOut:
    res = await db.execute(
        text(
            """
            UPDATE match_events
               SET status = 'cancelled',
                   archived_at = NOW(),
                   updated_at = NOW()
             WHERE id = :eid AND workspace_id = :wid
               AND status IN ('draft','active')
             RETURNING id
            """
        ),
        {"eid": event_id, "wid": workspace_id},
    )
    if res.first() is None:
        raise EventNotFoundError
    # cancel_event sets archived_at, which `fetch_event_summary`'s filter
    # would hide.  Read past the filter explicitly, then commit.
    row = (
        await db.execute(
            text(
                """
                SELECT
                    e.*,
                    0 AS participants_count,
                    0 AS teams_count
                FROM match_events e
                WHERE e.id = :eid AND e.workspace_id = :wid
                """
            ),
            {"eid": event_id, "wid": workspace_id},
        )
    ).mappings().first()
    assert row is not None
    summary = _row_to_event_out(row)
    await db.commit()
    return summary


# ── Participants ─────────────────────────────────────────────────


async def add_participant(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_id: UUID,
    body: ParticipantAddIn,
) -> ParticipantOut:
    event = await db.execute(
        text(
            "SELECT status, current_round FROM match_events "
            "WHERE id = :eid AND workspace_id = :wid"
        ),
        {"eid": event_id, "wid": workspace_id},
    )
    row = event.first()
    if row is None:
        raise EventNotFoundError
    status_val, current_round = row
    if status_val in ("completed", "cancelled"):
        raise EventStateError(f"Cannot add participants to {status_val} event.")
    joined_round = max(1, int(current_round) + (1 if status_val == "active" else 0))

    if body.athlete_id is not None:
        ath_check = await db.scalar(
            text(
                "SELECT 1 FROM athletes "
                "WHERE id = :aid AND workspace_id = :wid AND archived_at IS NULL"
            ),
            {"aid": body.athlete_id, "wid": workspace_id},
        )
        if not ath_check:
            raise EventStateError("Athlete is not in this workspace.")

    if body.team_id is not None:
        team_check = await db.scalar(
            text(
                "SELECT 1 FROM match_event_teams "
                "WHERE id = :tid AND event_id = :eid AND workspace_id = :wid"
            ),
            {"tid": body.team_id, "eid": event_id, "wid": workspace_id},
        )
        if not team_check:
            raise EventStateError("Team does not exist for this event.")

    inserted = (
        await db.execute(
            text(
                """
                INSERT INTO match_event_participants (
                    workspace_id, event_id, athlete_id, display_name,
                    team_id, tag, initial_seed, joined_round
                ) VALUES (
                    :wid, :eid, :aid, :name, :tid, :tag, :seed, :jr
                )
                RETURNING id, athlete_id, claim_user_id, display_name,
                          team_id, tag, initial_seed, joined_round,
                          withdrew_round
                """
            ),
            {
                "wid": workspace_id,
                "eid": event_id,
                "aid": body.athlete_id,
                "name": body.display_name.strip(),
                "tid": body.team_id,
                "tag": body.tag,
                "seed": body.initial_seed,
                "jr": joined_round,
            },
        )
    ).mappings().first()
    assert inserted is not None
    await db.commit()
    return _row_to_participant_out(inserted)


async def patch_participant(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_id: UUID,
    participant_id: UUID,
    body: ParticipantPatchIn,
) -> ParticipantOut:
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        existing = (
            await db.execute(
                text(
                    "SELECT id, athlete_id, claim_user_id, display_name, "
                    "team_id, tag, initial_seed, joined_round, withdrew_round "
                    "FROM match_event_participants "
                    "WHERE id = :pid AND event_id = :eid AND workspace_id = :wid"
                ),
                {"pid": participant_id, "eid": event_id, "wid": workspace_id},
            )
        ).mappings().first()
        if existing is None:
            raise EventNotFoundError
        return _row_to_participant_out(existing)
    set_clauses = ", ".join(f"{k} = :{k}" for k in patch.keys())
    res = (
        await db.execute(
            text(
                f"""
                UPDATE match_event_participants
                   SET {set_clauses}
                 WHERE id = :pid AND event_id = :eid AND workspace_id = :wid
                RETURNING id, athlete_id, claim_user_id, display_name,
                          team_id, tag, initial_seed, joined_round,
                          withdrew_round
                """
            ),
            {**patch, "pid": participant_id, "eid": event_id, "wid": workspace_id},
        )
    ).mappings().first()
    if res is None:
        raise EventNotFoundError
    await db.commit()
    return _row_to_participant_out(res)


async def withdraw_participant(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_id: UUID,
    participant_id: UUID,
) -> None:
    """Soft withdraw — keeps accumulated points on the leaderboard.  In
    draft state, this is just a hard delete (no points exist yet)."""
    event = (
        await db.execute(
            text(
                "SELECT status, current_round FROM match_events "
                "WHERE id = :eid AND workspace_id = :wid"
            ),
            {"eid": event_id, "wid": workspace_id},
        )
    ).first()
    if event is None:
        raise EventNotFoundError
    status_val, current_round = event
    if status_val == "draft":
        await db.execute(
            text(
                "DELETE FROM match_event_participants "
                "WHERE id = :pid AND event_id = :eid AND workspace_id = :wid"
            ),
            {"pid": participant_id, "eid": event_id, "wid": workspace_id},
        )
    else:
        await db.execute(
            text(
                "UPDATE match_event_participants "
                "   SET withdrew_round = :round "
                " WHERE id = :pid AND event_id = :eid "
                "   AND workspace_id = :wid AND withdrew_round IS NULL"
            ),
            {
                "pid": participant_id,
                "eid": event_id,
                "wid": workspace_id,
                "round": int(current_round) + 1,
            },
        )
    await db.commit()


# ── Teams ────────────────────────────────────────────────────────


async def create_team(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_id: UUID,
    body: TeamCreateIn,
) -> TeamOut:
    event = (
        await db.execute(
            text(
                "SELECT format, status FROM match_events "
                "WHERE id = :eid AND workspace_id = :wid"
            ),
            {"eid": event_id, "wid": workspace_id},
        )
    ).first()
    if event is None:
        raise EventNotFoundError
    fmt, status_val = event
    if fmt not in TEAM_FORMATS:
        raise EventStateError("This event format does not use teams.")
    if status_val in ("completed", "cancelled"):
        raise EventStateError(f"Cannot add teams to {status_val} event.")
    row = (
        await db.execute(
            text(
                """
                INSERT INTO match_event_teams (workspace_id, event_id, display_name, tag)
                VALUES (:wid, :eid, :name, :tag)
                RETURNING id, display_name, tag
                """
            ),
            {
                "wid": workspace_id,
                "eid": event_id,
                "name": body.display_name.strip(),
                "tag": body.tag,
            },
        )
    ).mappings().first()
    assert row is not None
    await db.commit()
    return TeamOut(
        id=str(row["id"]),
        display_name=row["display_name"],
        tag=row["tag"],
    )


async def patch_team(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_id: UUID,
    team_id: UUID,
    body: TeamPatchIn,
) -> TeamOut:
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        existing = (
            await db.execute(
                text(
                    "SELECT id, display_name, tag FROM match_event_teams "
                    "WHERE id = :tid AND event_id = :eid AND workspace_id = :wid"
                ),
                {"tid": team_id, "eid": event_id, "wid": workspace_id},
            )
        ).mappings().first()
        if existing is None:
            raise EventNotFoundError
        return TeamOut(id=str(existing["id"]),
                       display_name=existing["display_name"], tag=existing["tag"])
    set_clauses = ", ".join(f"{k} = :{k}" for k in patch.keys())
    res = (
        await db.execute(
            text(
                f"""
                UPDATE match_event_teams SET {set_clauses}
                 WHERE id = :tid AND event_id = :eid AND workspace_id = :wid
                RETURNING id, display_name, tag
                """
            ),
            {**patch, "tid": team_id, "eid": event_id, "wid": workspace_id},
        )
    ).mappings().first()
    if res is None:
        raise EventNotFoundError
    await db.commit()
    return TeamOut(id=str(res["id"]), display_name=res["display_name"], tag=res["tag"])


async def delete_team(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_id: UUID,
    team_id: UUID,
) -> None:
    """Hard-delete a team — only allowed if no participants reference it
    AND no scored matches reference it (Phase 2+).  Participants on this
    team get their team_id NULL'd via ON DELETE SET NULL."""
    has_scored = await db.scalar(
        text(
            """
            SELECT 1 FROM match_event_matches m
            JOIN match_event_participants p
              ON p.id IN (m.side_a_p1_id, m.side_a_p2_id,
                          m.side_b_p1_id, m.side_b_p2_id)
            WHERE m.event_id = :eid
              AND p.team_id = :tid
              AND m.score_a IS NOT NULL
            LIMIT 1
            """
        ),
        {"eid": event_id, "tid": team_id},
    )
    if has_scored:
        raise EventStateError(
            "Team has scored matches — withdraw individual members instead."
        )
    res = await db.execute(
        text(
            "DELETE FROM match_event_teams "
            "WHERE id = :tid AND event_id = :eid AND workspace_id = :wid"
        ),
        {"tid": team_id, "eid": event_id, "wid": workspace_id},
    )
    if res.rowcount == 0:
        raise EventNotFoundError
    await db.commit()


# ── Row → Pydantic helpers ──────────────────────────────────────


def _row_to_event_out(row: Any) -> EventOut:
    # ``court_names`` is JSONB.  Normalise NULL → [] so the FE always
    # gets a list; sparse arrays keep the indexing simple (court N's
    # label = court_names[N-1] or fallback).
    raw_names = row.get("court_names") if hasattr(row, "get") else row["court_names"]
    if raw_names is None:
        court_names: list[str | None] = []
    elif isinstance(raw_names, str):
        # Some drivers serialize JSONB as a string; parse defensively.
        import json as _json
        try:
            court_names = list(_json.loads(raw_names) or [])
        except Exception:
            court_names = []
    else:
        court_names = list(raw_names)

    return EventOut(
        id=str(row["id"]),
        workspace_id=str(row["workspace_id"]),
        title=row["title"],
        venue=row["venue"],
        format=row["format"],
        scoring_mode=row["scoring_mode"],
        scoring_target=row["scoring_target"],
        round_timer_seconds=row["round_timer_seconds"],
        court_count=row["court_count"],
        court_names=court_names,
        mexicano_pairing=row["mexicano_pairing"],
        leaderboard_sort=row["leaderboard_sort"],
        total_rounds=row["total_rounds"],
        current_round=row["current_round"],
        status=row["status"],
        is_public=row["is_public"],
        public_slug=row["public_slug"],
        starts_at=row["starts_at"],
        completed_at=row["completed_at"],
        created_by_id=str(row["created_by_id"]),
        created_at=row["created_at"],
        participants_count=int(row.get("participants_count") or 0),
        teams_count=int(row.get("teams_count") or 0),
    )


def _row_to_participant_out(row: Any) -> ParticipantOut:
    return ParticipantOut(
        id=str(row["id"]),
        athlete_id=str(row["athlete_id"]) if row["athlete_id"] else None,
        claim_user_id=str(row["claim_user_id"]) if row["claim_user_id"] else None,
        display_name=row["display_name"],
        team_id=str(row["team_id"]) if row["team_id"] else None,
        tag=row["tag"],
        initial_seed=row["initial_seed"],
        joined_round=row["joined_round"],
        withdrew_round=row["withdrew_round"],
    )


# Silence unused-import warning in environments where the type isn't
# referenced (mypy strict otherwise grumbles).
_ = (datetime, LeaderboardSort, MexicanoPairing)


# ── Phase 2: starting an event, advancing rounds, scoring, completing ──


from .pairing import (  # noqa: E402
    KothPlacement,
    PairedRound,
    build_americano_schedule,
    build_koth_round,
    build_mexicano_round,
    total_rounds_for,
)


# Formats that need dynamic per-round generation (can't pre-compute the
# full schedule at start because each round depends on prior results).
_DYNAMIC_FORMATS: frozenset[str] = frozenset({"mexicano", "koth"})
# Formats fully supported by the Phase 2/3 pairing engine.  Team variants
# + Mix + Mixicano come in later phases — they share the same draft API
# but can't be started yet.
_SUPPORTED_FORMATS: frozenset[str] = frozenset(
    {"americano", "mexicano", "koth"}
)


async def _load_active_participant_ids(
    db: AsyncSession, *, workspace_id: UUID, event_id: UUID
) -> list[UUID]:
    """Active (non-withdrawn) participants ordered by initial_seed then
    creation time — that order is the schedule-1 seeding for all
    individual formats."""
    rows = (
        await db.execute(
            text(
                """
                SELECT id FROM match_event_participants
                WHERE event_id = :eid AND workspace_id = :wid
                  AND withdrew_round IS NULL
                ORDER BY COALESCE(initial_seed, 999999), created_at
                """
            ),
            {"eid": event_id, "wid": workspace_id},
        )
    ).all()
    return [r[0] for r in rows]


async def _persist_paired_round(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_id: UUID,
    paired: PairedRound,
    participant_ids: list[UUID],
    mark_started: bool,
) -> UUID:
    """Insert one PairedRound (with its matches) into the DB and return
    the new round id.  Used by both the Americano pre-computed path and
    the Mexicano/KOTH lazy paths."""
    # Insert the round shell first (started_at NULL by default), then
    # stamp NOW() in a separate UPDATE — asyncpg can't bind ``NOW()`` as
    # a parameter, so we keep it inside the SQL itself.
    row = (
        await db.execute(
            text(
                """
                INSERT INTO match_event_rounds
                    (workspace_id, event_id, round_number,
                     started_at, completed_at)
                VALUES (:wid, :eid, :rn, NULL, NULL)
                RETURNING id
                """
            ),
            {
                "wid": workspace_id,
                "eid": event_id,
                "rn": paired.round_number,
            },
        )
    ).first()
    assert row is not None
    round_id = row[0]
    if mark_started:
        await db.execute(
            text(
                "UPDATE match_event_rounds SET started_at = NOW() "
                "WHERE id = :rid"
            ),
            {"rid": round_id},
        )
    for m in paired.matches:
        a1, a2 = m.side_a
        b1, b2 = m.side_b
        await db.execute(
            text(
                """
                INSERT INTO match_event_matches (
                    workspace_id, event_id, round_id, court_number,
                    side_a_p1_id, side_a_p2_id,
                    side_b_p1_id, side_b_p2_id
                ) VALUES (
                    :wid, :eid, :rid, :court,
                    :a1, :a2, :b1, :b2
                )
                """
            ),
            {
                "wid": workspace_id,
                "eid": event_id,
                "rid": round_id,
                "court": m.court_number,
                "a1": participant_ids[a1],
                "a2": participant_ids[a2],
                "b1": participant_ids[b1],
                "b2": participant_ids[b2],
            },
        )
    return round_id


async def start_event(
    db: AsyncSession, *, workspace_id: UUID, event_id: UUID
) -> EventOut:
    """Draft → active.  For Americano, pre-computes the full schedule.
    For Mexicano + KOTH, persists only round 1 (later rounds get
    generated lazily by ``advance_round`` based on the leaderboard or
    last-round results)."""
    row = (
        await db.execute(
            text(
                """
                SELECT format, status, court_count, mexicano_pairing
                FROM match_events
                WHERE id = :eid AND workspace_id = :wid
                """
            ),
            {"eid": event_id, "wid": workspace_id},
        )
    ).first()
    if row is None:
        raise EventNotFoundError
    fmt, status_val, court_count, mex_pairing = row
    if status_val != "draft":
        raise EventStateError(f"Event is already {status_val}.")
    if fmt not in _SUPPORTED_FORMATS:
        raise EventStateError(
            f"Pairing engine for '{fmt}' is not implemented yet."
        )

    participant_ids = await _load_active_participant_ids(
        db, workspace_id=workspace_id, event_id=event_id
    )
    if len(participant_ids) < 4:
        raise EventStateError(
            f"{fmt.title()} needs at least 4 players to start."
        )

    n = len(participant_ids)
    rounds_count = total_rounds_for(n)

    if fmt == "americano":
        schedule = build_americano_schedule(
            player_count=n,
            court_count=int(court_count),
            total_rounds=rounds_count,
        )
        for rnd in schedule:
            await _persist_paired_round(
                db,
                workspace_id=workspace_id,
                event_id=event_id,
                paired=rnd,
                participant_ids=participant_ids,
                mark_started=(rnd.round_number == 1),
            )
    else:
        # Mexicano + KOTH share the same round-1 seeding: input order.
        # Subsequent rounds are generated by advance_round.
        first = (
            build_mexicano_round(
                round_number=1,
                ranked_player_indices=list(range(n)),
                court_count=int(court_count),
                pairing_setting=(mex_pairing or "1_3_vs_2_4"),
            )
            if fmt == "mexicano"
            else build_mexicano_round(
                # KOTH round 1 uses the same top-down seeding shape as
                # Mexicano — top-N to top court etc.  The unique KOTH
                # behaviour (winners-up / losers-down) starts in round 2.
                round_number=1,
                ranked_player_indices=list(range(n)),
                court_count=int(court_count),
                pairing_setting="1_3_vs_2_4",
            )
        )
        await _persist_paired_round(
            db,
            workspace_id=workspace_id,
            event_id=event_id,
            paired=first,
            participant_ids=participant_ids,
            mark_started=True,
        )

    await db.execute(
        text(
            """
            UPDATE match_events
               SET status = 'active',
                   total_rounds = :tr,
                   current_round = 1,
                   starts_at = COALESCE(starts_at, NOW()),
                   updated_at = NOW()
             WHERE id = :eid AND workspace_id = :wid
            """
        ),
        {"tr": rounds_count, "eid": event_id, "wid": workspace_id},
    )

    out = await fetch_event_summary(
        db, workspace_id=workspace_id, event_id=event_id
    )
    await db.commit()
    assert out is not None
    return out


async def advance_round(
    db: AsyncSession, *, workspace_id: UUID, event_id: UUID
) -> EventOut:
    """Finish the current round and prepare the next one.  For
    Americano the next round was pre-computed at start, so we just
    flip timestamps.  For Mexicano + KOTH we compute the next round
    here from the latest leaderboard / last-round results."""
    row = (
        await db.execute(
            text(
                """
                SELECT status, current_round, total_rounds,
                       format, court_count, mexicano_pairing
                FROM match_events WHERE id = :eid AND workspace_id = :wid
                """
            ),
            {"eid": event_id, "wid": workspace_id},
        )
    ).first()
    if row is None:
        raise EventNotFoundError
    status_val, current_round, total_rounds, fmt, court_count, mex_pairing = row
    if status_val != "active":
        raise EventStateError(f"Event is {status_val}, not active.")
    if current_round >= total_rounds:
        raise EventStateError(
            "Final round already started — complete the event instead."
        )

    # Mark the round we're leaving as done.
    await db.execute(
        text(
            """
            UPDATE match_event_rounds
               SET completed_at = NOW()
             WHERE event_id = :eid AND round_number = :cr
            """
        ),
        {"eid": event_id, "cr": current_round},
    )

    new_round = current_round + 1

    if fmt in _DYNAMIC_FORMATS:
        # Generate the next round's pairings now, using the live state.
        participant_ids = await _load_active_participant_ids(
            db, workspace_id=workspace_id, event_id=event_id
        )
        idx_by_pid = {pid: i for i, pid in enumerate(participant_ids)}

        if fmt == "mexicano":
            # Re-rank participants by leaderboard.
            lb = await leaderboard(
                db,
                workspace_id=workspace_id,
                event_id=event_id,
                sort="points",
            )
            ranked: list[int] = []
            for row_lb in lb:
                pid = UUID(row_lb["participant_id"])
                if pid in idx_by_pid:
                    ranked.append(idx_by_pid[pid])
            # Any active participant that didn't appear on the
            # leaderboard yet (joined this round, never scored) is
            # appended at the bottom of the ranking.
            for pid, i in idx_by_pid.items():
                if i not in ranked:
                    ranked.append(i)

            paired = build_mexicano_round(
                round_number=new_round,
                ranked_player_indices=ranked,
                court_count=int(court_count),
                pairing_setting=(mex_pairing or "1_3_vs_2_4"),
            )
        else:
            # KOTH: read last round's matches + winners to compute
            # per-player placements, then move winners up / losers
            # down via build_koth_round.
            last_matches = (
                await db.execute(
                    text(
                        """
                        SELECT m.court_number, m.winner_side,
                               m.side_a_p1_id, m.side_a_p2_id,
                               m.side_b_p1_id, m.side_b_p2_id
                        FROM match_event_matches m
                        JOIN match_event_rounds r ON r.id = m.round_id
                        WHERE m.event_id = :eid
                          AND r.round_number = :cr
                        """
                    ),
                    {"eid": event_id, "cr": current_round},
                )
            ).mappings().all()
            placements: list[KothPlacement] = []
            for m in last_matches:
                a_won = m["winner_side"] == "A"
                b_won = m["winner_side"] == "B"
                # Draws (winner_side='D') count as "lost" for both
                # sides — the lower-court player drops, higher-court
                # one stays.  Rare in KOTH; rule keeps determinism.
                for pid in (m["side_a_p1_id"], m["side_a_p2_id"]):
                    placements.append(
                        KothPlacement(
                            player_index=idx_by_pid[pid],
                            court_number=int(m["court_number"]),
                            won=a_won,
                        )
                    )
                for pid in (m["side_b_p1_id"], m["side_b_p2_id"]):
                    placements.append(
                        KothPlacement(
                            player_index=idx_by_pid[pid],
                            court_number=int(m["court_number"]),
                            won=b_won,
                        )
                    )

            paired = build_koth_round(
                round_number=new_round,
                placements=placements,
                court_count=int(court_count),
            )

        await _persist_paired_round(
            db,
            workspace_id=workspace_id,
            event_id=event_id,
            paired=paired,
            participant_ids=participant_ids,
            mark_started=True,
        )
    else:
        # Americano: next round was pre-computed at start; just stamp.
        await db.execute(
            text(
                "UPDATE match_event_rounds SET started_at = NOW() "
                "WHERE event_id = :eid AND round_number = :nr"
            ),
            {"eid": event_id, "nr": new_round},
        )

    await db.execute(
        text(
            """
            UPDATE match_events
               SET current_round = :nr, updated_at = NOW()
             WHERE id = :eid AND workspace_id = :wid
            """
        ),
        {"nr": new_round, "eid": event_id, "wid": workspace_id},
    )
    out = await fetch_event_summary(
        db, workspace_id=workspace_id, event_id=event_id
    )
    await db.commit()
    assert out is not None
    return out


async def complete_event(
    db: AsyncSession, *, workspace_id: UUID, event_id: UUID
) -> EventOut:
    row = (
        await db.execute(
            text(
                "SELECT status, current_round FROM match_events "
                "WHERE id = :eid AND workspace_id = :wid"
            ),
            {"eid": event_id, "wid": workspace_id},
        )
    ).first()
    if row is None:
        raise EventNotFoundError
    status_val, current_round = row
    if status_val != "active":
        raise EventStateError(f"Cannot complete a {status_val} event.")
    await db.execute(
        text(
            "UPDATE match_event_rounds SET completed_at = COALESCE(completed_at, NOW()) "
            "WHERE event_id = :eid AND round_number = :cr"
        ),
        {"eid": event_id, "cr": current_round},
    )
    await db.execute(
        text(
            """
            UPDATE match_events
               SET status = 'completed', completed_at = NOW(),
                   updated_at = NOW()
             WHERE id = :eid AND workspace_id = :wid
            """
        ),
        {"eid": event_id, "wid": workspace_id},
    )
    out = await fetch_event_summary(
        db, workspace_id=workspace_id, event_id=event_id
    )
    await db.commit()
    assert out is not None
    return out


async def reshuffle_current_round(
    db: AsyncSession, *, workspace_id: UUID, event_id: UUID
) -> EventOut:
    """Re-pair the current round.  Only allowed when no matches in the
    round have a score recorded yet — once any score lands the round is
    immutable history.  Deletes the current round's matches + the round
    row, regenerates from the format's pairing function, persists.

    For Americano this is just a re-pair of an already-known round.
    For Mexicano/KOTH it's also a re-pair (uses the same logic
    advance_round would for the *current* round number)."""
    row = (
        await db.execute(
            text(
                """
                SELECT status, current_round, format,
                       court_count, mexicano_pairing
                FROM match_events WHERE id = :eid AND workspace_id = :wid
                """
            ),
            {"eid": event_id, "wid": workspace_id},
        )
    ).first()
    if row is None:
        raise EventNotFoundError
    status_val, current_round, fmt, court_count, mex_pairing = row
    if status_val != "active":
        raise EventStateError(f"Event is {status_val}, not active.")
    if fmt not in _SUPPORTED_FORMATS:
        raise EventStateError(
            f"Pairing engine for '{fmt}' is not implemented yet."
        )

    # Bail if any match in the current round is already scored.
    scored_check = await db.scalar(
        text(
            """
            SELECT 1 FROM match_event_matches m
            JOIN match_event_rounds r ON r.id = m.round_id
            WHERE m.event_id = :eid AND r.round_number = :cr
              AND m.score_a IS NOT NULL
            LIMIT 1
            """
        ),
        {"eid": event_id, "cr": current_round},
    )
    if scored_check:
        raise EventStateError(
            "Round already has scores recorded — reshuffle is locked."
        )

    # Drop the current round's matches + the round row itself, then
    # rebuild fresh.  CASCADE on ``round_id`` cleans up matches.
    await db.execute(
        text(
            """
            DELETE FROM match_event_rounds
             WHERE event_id = :eid AND round_number = :cr
            """
        ),
        {"eid": event_id, "cr": current_round},
    )

    participant_ids = await _load_active_participant_ids(
        db, workspace_id=workspace_id, event_id=event_id
    )
    n = len(participant_ids)
    if n < 4:
        raise EventStateError(
            f"Need 4 players to reshuffle, only {n} active."
        )

    if fmt == "americano":
        # Re-pair just this one round.  We can't reuse build_americano_
        # schedule because it returns the full N-1 schedule; instead we
        # build a fresh single-round schedule with target=current_round
        # and pick the last entry.  Round 1 is the most common reshuffle
        # case, so this is cheap.
        sched = build_americano_schedule(
            player_count=n,
            court_count=int(court_count),
            total_rounds=current_round,
        )
        paired = sched[-1]
        # Keep the same round_number we just deleted.
        from dataclasses import replace as _replace
        paired = _replace(paired, round_number=current_round)
    elif fmt == "mexicano":
        if current_round == 1:
            ranked = list(range(n))
        else:
            lb = await leaderboard(
                db, workspace_id=workspace_id, event_id=event_id,
                sort="points",
            )
            idx_by_pid = {pid: i for i, pid in enumerate(participant_ids)}
            ranked = []
            for r in lb:
                pid = UUID(r["participant_id"])
                if pid in idx_by_pid:
                    ranked.append(idx_by_pid[pid])
            for pid, i in idx_by_pid.items():
                if i not in ranked:
                    ranked.append(i)
        paired = build_mexicano_round(
            round_number=current_round,
            ranked_player_indices=ranked,
            court_count=int(court_count),
            pairing_setting=(mex_pairing or "1_3_vs_2_4"),
        )
    else:
        # KOTH round 1 reshuffles via the same seeded layout as start;
        # later rounds reshuffle via the placement-based movement (we
        # need to re-read the prior round's results).
        if current_round == 1:
            paired = build_mexicano_round(
                round_number=1,
                ranked_player_indices=list(range(n)),
                court_count=int(court_count),
                pairing_setting="1_3_vs_2_4",
            )
        else:
            idx_by_pid = {pid: i for i, pid in enumerate(participant_ids)}
            prev_matches = (
                await db.execute(
                    text(
                        """
                        SELECT m.court_number, m.winner_side,
                               m.side_a_p1_id, m.side_a_p2_id,
                               m.side_b_p1_id, m.side_b_p2_id
                        FROM match_event_matches m
                        JOIN match_event_rounds r ON r.id = m.round_id
                        WHERE m.event_id = :eid AND r.round_number = :pr
                        """
                    ),
                    {"eid": event_id, "pr": current_round - 1},
                )
            ).mappings().all()
            placements: list[KothPlacement] = []
            for m in prev_matches:
                a_won = m["winner_side"] == "A"
                b_won = m["winner_side"] == "B"
                for pid in (m["side_a_p1_id"], m["side_a_p2_id"]):
                    placements.append(
                        KothPlacement(idx_by_pid[pid], int(m["court_number"]), a_won)
                    )
                for pid in (m["side_b_p1_id"], m["side_b_p2_id"]):
                    placements.append(
                        KothPlacement(idx_by_pid[pid], int(m["court_number"]), b_won)
                    )
            paired = build_koth_round(
                round_number=current_round,
                placements=placements,
                court_count=int(court_count),
            )

    await _persist_paired_round(
        db,
        workspace_id=workspace_id,
        event_id=event_id,
        paired=paired,
        participant_ids=participant_ids,
        mark_started=True,
    )
    await db.execute(
        text(
            "UPDATE match_events SET updated_at = NOW() "
            "WHERE id = :eid AND workspace_id = :wid"
        ),
        {"eid": event_id, "wid": workspace_id},
    )
    out = await fetch_event_summary(
        db, workspace_id=workspace_id, event_id=event_id
    )
    await db.commit()
    assert out is not None
    return out


async def rename_court(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_id: UUID,
    court_number: int,
    name: str | None,
) -> EventOut:
    """Update one slot of ``match_events.court_names``.  ``name=None``
    clears the override (back to default "Court {n}")."""
    row = (
        await db.execute(
            text(
                "SELECT court_count, court_names FROM match_events "
                "WHERE id = :eid AND workspace_id = :wid"
            ),
            {"eid": event_id, "wid": workspace_id},
        )
    ).first()
    if row is None:
        raise EventNotFoundError
    court_count, current_names_raw = row
    if court_number < 1 or court_number > int(court_count):
        raise EventStateError(
            f"Court {court_number} doesn't exist (event has {court_count})."
        )

    # Normalise current_names into a list of length court_count.
    import json as _json
    current = (
        list(current_names_raw)
        if isinstance(current_names_raw, list)
        else (list(_json.loads(current_names_raw)) if current_names_raw else [])
    )
    while len(current) < int(court_count):
        current.append(None)
    cleaned = (name.strip() if name else None) or None
    current[court_number - 1] = cleaned

    await db.execute(
        text(
            # SQLAlchemy parses ``:name`` as a parameter token, so the
            # PG-style ``::jsonb`` cast confuses the binder.  Use the
            # SQL-standard ``CAST(... AS jsonb)`` form instead.
            "UPDATE match_events "
            "   SET court_names = CAST(:names AS jsonb), updated_at = NOW() "
            " WHERE id = :eid AND workspace_id = :wid"
        ),
        {
            "names": _json.dumps(current),
            "eid": event_id,
            "wid": workspace_id,
        },
    )
    out = await fetch_event_summary(
        db, workspace_id=workspace_id, event_id=event_id
    )
    await db.commit()
    assert out is not None
    return out


async def record_score(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_id: UUID,
    match_id: UUID,
    score_a: int,
    score_b: int,
    recorded_by: UUID,
    client_recorded_at: datetime | None = None,
) -> dict[str, Any]:
    """Persist a match score.  Winner is computed from the integers —
    higher score wins, equal scores → 'D' (draw, only sensible in some
    scoring modes; the leaderboard tolerates it)."""
    if score_a < 0 or score_b < 0:
        raise EventStateError("Scores must be non-negative.")
    winner = "A" if score_a > score_b else ("B" if score_b > score_a else "D")

    res = await db.execute(
        text(
            """
            UPDATE match_event_matches
               SET score_a = :sa, score_b = :sb,
                   winner_side = :w,
                   recorded_at = NOW(),
                   recorded_by_id = :uid,
                   client_recorded_at = COALESCE(:cra, NOW())
             WHERE id = :mid AND event_id = :eid AND workspace_id = :wid
             RETURNING id, round_id, court_number, score_a, score_b,
                       winner_side, recorded_at
            """
        ),
        {
            "sa": score_a,
            "sb": score_b,
            "w": winner,
            "uid": recorded_by,
            "cra": client_recorded_at,
            "mid": match_id,
            "eid": event_id,
            "wid": workspace_id,
        },
    )
    row = res.mappings().first()
    if row is None:
        raise EventNotFoundError
    await db.commit()
    return {
        "id": str(row["id"]),
        "score_a": row["score_a"],
        "score_b": row["score_b"],
        "winner_side": row["winner_side"],
        "recorded_at": row["recorded_at"],
    }


async def list_rounds(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_id: UUID,
) -> list[dict[str, Any]]:
    """All rounds + their matches, ordered by round_number / court_number."""
    rows = (
        await db.execute(
            text(
                """
                SELECT r.id AS round_id, r.round_number,
                       r.started_at, r.completed_at,
                       m.id AS match_id, m.court_number,
                       m.side_a_p1_id, m.side_a_p2_id,
                       m.side_b_p1_id, m.side_b_p2_id,
                       m.score_a, m.score_b, m.winner_side,
                       m.recorded_at
                FROM match_event_rounds r
                LEFT JOIN match_event_matches m ON m.round_id = r.id
                WHERE r.event_id = :eid AND r.workspace_id = :wid
                ORDER BY r.round_number, m.court_number NULLS LAST
                """
            ),
            {"eid": event_id, "wid": workspace_id},
        )
    ).mappings().all()

    grouped: dict[int, dict[str, Any]] = {}
    for r in rows:
        rn = int(r["round_number"])
        if rn not in grouped:
            grouped[rn] = {
                "round_number": rn,
                "started_at": r["started_at"],
                "completed_at": r["completed_at"],
                "matches": [],
            }
        if r["match_id"] is not None:
            grouped[rn]["matches"].append(
                {
                    "id": str(r["match_id"]),
                    "court_number": r["court_number"],
                    "side_a": [
                        str(r["side_a_p1_id"]),
                        str(r["side_a_p2_id"]),
                    ],
                    "side_b": [
                        str(r["side_b_p1_id"]),
                        str(r["side_b_p2_id"]),
                    ],
                    "score_a": r["score_a"],
                    "score_b": r["score_b"],
                    "winner_side": r["winner_side"],
                    "recorded_at": r["recorded_at"],
                }
            )
    return [grouped[k] for k in sorted(grouped)]


async def leaderboard(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_id: UUID,
    sort: str = "points",
) -> list[dict[str, Any]]:
    """Aggregate scores into a per-participant board.  Point scoring →
    sum of points scored; normal-first-to → 1 per win.  Tiebreak by the
    other metric, then by display name (stable, easy to read)."""
    # All matches with a score recorded.
    rows = (
        await db.execute(
            text(
                """
                SELECT m.score_a, m.score_b, m.winner_side,
                       m.side_a_p1_id, m.side_a_p2_id,
                       m.side_b_p1_id, m.side_b_p2_id
                FROM match_event_matches m
                WHERE m.event_id = :eid AND m.workspace_id = :wid
                  AND m.score_a IS NOT NULL AND m.score_b IS NOT NULL
                """
            ),
            {"eid": event_id, "wid": workspace_id},
        )
    ).mappings().all()

    parts = (
        await db.execute(
            text(
                """
                SELECT id, display_name, team_id
                FROM match_event_participants
                WHERE event_id = :eid AND workspace_id = :wid
                """
            ),
            {"eid": event_id, "wid": workspace_id},
        )
    ).mappings().all()

    name_by_id: dict[UUID, str] = {p["id"]: p["display_name"] for p in parts}
    raw_points: dict[UUID, int] = {p["id"]: 0 for p in parts}
    points_against: dict[UUID, int] = {p["id"]: 0 for p in parts}
    wins: dict[UUID, int] = {p["id"]: 0 for p in parts}
    losses: dict[UUID, int] = {p["id"]: 0 for p in parts}
    ties: dict[UUID, int] = {p["id"]: 0 for p in parts}
    matches_played: dict[UUID, int] = {p["id"]: 0 for p in parts}

    for r in rows:
        a1, a2 = r["side_a_p1_id"], r["side_a_p2_id"]
        b1, b2 = r["side_b_p1_id"], r["side_b_p2_id"]
        sa, sb = int(r["score_a"]), int(r["score_b"])
        for pid in (a1, a2):
            raw_points[pid] = raw_points.get(pid, 0) + sa
            points_against[pid] = points_against.get(pid, 0) + sb
            matches_played[pid] = matches_played.get(pid, 0) + 1
        for pid in (b1, b2):
            raw_points[pid] = raw_points.get(pid, 0) + sb
            points_against[pid] = points_against.get(pid, 0) + sa
            matches_played[pid] = matches_played.get(pid, 0) + 1
        if r["winner_side"] == "A":
            for pid in (a1, a2):
                wins[pid] = wins.get(pid, 0) + 1
            for pid in (b1, b2):
                losses[pid] = losses.get(pid, 0) + 1
        elif r["winner_side"] == "B":
            for pid in (b1, b2):
                wins[pid] = wins.get(pid, 0) + 1
            for pid in (a1, a2):
                losses[pid] = losses.get(pid, 0) + 1
        elif r["winner_side"] == "D":
            for pid in (a1, a2, b1, b2):
                ties[pid] = ties.get(pid, 0) + 1

    # Compensation (+M) — equal to (max_matches - my_matches) ×
    # average_points_per_match for this event, integer-rounded.  Surfaces
    # late-joiners / withdrawn players' otherwise empty rows without
    # giving them a free competitive advantage.
    max_m = max(matches_played.values()) if matches_played else 0
    total_points = sum(raw_points.values())
    total_matches = sum(matches_played.values())  # double-counts each match
    avg_per_match = (total_points / total_matches) if total_matches > 0 else 0.0
    compensation: dict[UUID, int] = {
        pid: int(round((max_m - matches_played.get(pid, 0)) * avg_per_match))
        for pid in name_by_id
    }

    out = []
    for pid in name_by_id:
        pts_raw = raw_points.get(pid, 0)
        comp = compensation.get(pid, 0)
        out.append({
            "participant_id": str(pid),
            "display_name": name_by_id.get(pid, "—"),
            "points": pts_raw + comp,
            "wins": wins.get(pid, 0),
            "losses": losses.get(pid, 0),
            "ties": ties.get(pid, 0),
            "matches_played": matches_played.get(pid, 0),
            "point_diff": pts_raw - points_against.get(pid, 0),
            "compensation": comp,
        })
    if sort == "wins":
        out.sort(
            key=lambda r: (
                -r["wins"],
                -r["point_diff"],
                -r["points"],
                r["display_name"],
            )
        )
    else:
        out.sort(
            key=lambda r: (
                -r["points"],
                -r["point_diff"],
                -r["wins"],
                r["display_name"],
            )
        )
    return out

