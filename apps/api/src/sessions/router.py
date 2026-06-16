"""Session endpoints — schedule / list / edit / cancel / complete / no-show
/ funnel / conflicts.  Multi-focus via the `session_focuses` join table.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.athletes.schemas import TierBrief
from src.audit.decorators import audit_action
from src.auth.service import get_role_in_workspace
from src.deps import get_current_user_id, get_current_workspace_id
from src.middleware.rls import db_with_rls
from src.sports.service import SportError, resolve_sport_id

from .schemas import (
    CoachBrief,
    FunnelCountsOut,
    FunnelStage,
    SessionCreateIn,
    SessionFocus,
    SessionOut,
    SessionTodayOut,
    SessionTraineeBrief,
    SessionUpdateIn,
    SessionWorkspaceBrief,
)
from .service import get_today_all_coaches, get_today_for_coach

router = APIRouter(prefix="/sessions", tags=["sessions"])


async def _is_admin_or_head_coach(
    db: AsyncSession, user_id: UUID, workspace_id: UUID | None
) -> bool:
    role = await get_role_in_workspace(db, user_id=user_id, workspace_id=workspace_id)
    return role in ("club_admin", "head_coach")


async def _is_coach_member(
    db: AsyncSession, user_id: UUID, workspace_id: UUID
) -> bool:
    """True iff `user_id` is an active coach-tier member of `workspace_id`.
    Coach-tier = club_admin / head_coach / coach. Used to validate
    `coach_id` on session create/update so admins can't assign a session
    to a stranger or a trainee."""
    role = await get_role_in_workspace(
        db, user_id=user_id, workspace_id=workspace_id
    )
    return role in ("club_admin", "head_coach", "coach")


def _build_today_out(r: dict, focuses_map: dict) -> SessionTodayOut:
    return SessionTodayOut(
        id=str(r["id"]),
        scheduled_at=r["scheduled_at"],
        duration_min=r["duration_min"],
        court=r["court"],
        focuses=focuses_map.get(r["id"], _legacy_focuses(r["focus"])),
        status=r["status"],
        sport_id=r.get("sport_id"),
        coach=CoachBrief(
            id=str(r["coach_id"]),
            display_name=r["coach_name"],
        ) if r.get("coach_id") else None,
        trainee=SessionTraineeBrief(
            id=str(r["trainee_id"]),
            display_name=r["trainee_name"],
            last_assessed_at=r["last_assessed_at"],
            current_tier=(
                TierBrief(
                    id=str(r["tier_id"]),
                    code=r["tier_code"],
                    name_game_en=r["tier_name_game_en"],
                    name_game_id=r["tier_name_game_id"],
                )
                if r["tier_id"] is not None
                else None
            ),
        ),
    )


# ── GET /sessions/today ──────────────────────────────────────────


@router.get("/today", response_model=list[SessionTodayOut])
async def get_today(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
    all: bool = Query(default=False),
) -> list[SessionTodayOut]:
    if all:
        if not await _is_admin_or_head_coach(db, user_id, workspace_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin or head coach required.",
            )
        rows = await get_today_all_coaches(db)
    else:
        rows = await get_today_for_coach(db, coach_id=user_id)
    session_ids = [r["id"] for r in rows]
    focuses = await _load_focuses_for_sessions(db, session_ids)
    return [_build_today_out(dict(r), focuses) for r in rows]


# ── Helpers ─────────────────────────────────────────────────────


_BASE_SELECT = """
    SELECT s.id, s.scheduled_at, s.duration_min, s.court, s.focus::text AS focus,
           s.status, s.summary AS notes, s.completed_at, s.created_at,
           s.coach_id, cu.display_name AS coach_name,
           ath.id AS trainee_id, ath.display_name AS trainee_name,
           lat.last_at AS last_assessed_at,
           tier.id AS tier_id, tier.code AS tier_code,
           tier.name_game_en, tier.name_game_id,
           a.id AS assessment_id, a.status AS assessment_status
"""

_BASE_FROM = """
    FROM sessions s
    JOIN athletes ath ON ath.id = s.athlete_id
    JOIN users cu     ON cu.id = s.coach_id
    LEFT JOIN tiers tier ON tier.id = ath.current_tier_id
    LEFT JOIN LATERAL (
        SELECT MAX(COALESCE(edited_at, published_at)) AS last_at
        FROM assessments
        WHERE athlete_id = ath.id AND status IN ('published','edited')
    ) lat ON TRUE
    LEFT JOIN assessments a ON a.session_id = s.id
"""


def _legacy_focuses(value: str | None) -> list[str]:
    return [value] if value else []


def _funnel_stage_for(
    *, status_: str, scheduled_at: datetime, assessment_status: str | None
) -> FunnelStage:
    if status_ in ("cancelled", "no_show"):
        return "cancelled"
    if assessment_status in ("published", "edited"):
        return "published"
    if assessment_status == "draft":
        return "draft"
    now = datetime.now(UTC)
    sa = scheduled_at if scheduled_at.tzinfo else scheduled_at.replace(tzinfo=UTC)
    if sa < now and status_ != "cancelled":
        return "to_assess"
    return "upcoming"


async def _load_focuses_for_sessions(
    db: AsyncSession, session_ids: list[UUID]
) -> dict[UUID, list[str]]:
    if not session_ids:
        return {}
    placeholders = ", ".join(f":s{i}" for i in range(len(session_ids)))
    params: dict = {f"s{i}": sid for i, sid in enumerate(session_ids)}
    rows = (
        await db.execute(
            text(
                f"SELECT session_id, focus FROM session_focuses "
                f"WHERE session_id IN ({placeholders}) "
                f"ORDER BY session_id, ordinal"
            ),
            params,
        )
    ).all()
    out: dict[UUID, list[str]] = {}
    for sid, focus in rows:
        out.setdefault(sid, []).append(focus)
    return out


async def _replace_focuses(
    db: AsyncSession,
    *,
    session_id: UUID,
    workspace_id: UUID,
    focuses: list[str],
) -> None:
    await db.execute(
        text("DELETE FROM session_focuses WHERE session_id = :sid"),
        {"sid": session_id},
    )
    for i, f in enumerate(focuses):
        await db.execute(
            text(
                """
                INSERT INTO session_focuses (
                    session_id, focus, ordinal, workspace_id
                ) VALUES (:sid, :focus, :ordinal, :wid)
                """
            ),
            {"sid": session_id, "focus": f, "ordinal": i, "wid": workspace_id},
        )
    # Mirror primary focus (first one) into the deprecated column so old
    # readers don't break during the deprecation window.
    primary = focuses[0] if focuses else None
    await db.execute(
        text(
            "UPDATE sessions SET focus = CAST(:f AS session_focus) "
            "WHERE id = :sid"
        ),
        {"sid": session_id, "f": primary},
    )


def _row_to_session_out(r: dict, focuses: list[str]) -> SessionOut:
    return SessionOut(
        id=str(r["id"]),
        athlete=SessionTraineeBrief(
            id=str(r["trainee_id"]),
            display_name=r["trainee_name"],
            last_assessed_at=r["last_assessed_at"],
            current_tier=(
                TierBrief(
                    id=str(r["tier_id"]),
                    code=r["tier_code"],
                    name_game_en=r["name_game_en"],
                    name_game_id=r["name_game_id"],
                )
                if r["tier_id"] is not None
                else None
            ),
        ),
        coach=CoachBrief(
            id=str(r["coach_id"]),
            display_name=r["coach_name"],
        ),
        scheduled_at=r["scheduled_at"],
        duration_min=int(r["duration_min"] or 60),
        court=r["court"],
        focuses=focuses,
        status=r["status"],
        notes=r["notes"],
        completed_at=r["completed_at"],
        has_assessment=r["assessment_id"] is not None,
        assessment_id=str(r["assessment_id"]) if r["assessment_id"] else None,
        assessment_status=r["assessment_status"],
        funnel_stage=_funnel_stage_for(
            status_=r["status"],
            scheduled_at=r["scheduled_at"],
            assessment_status=r["assessment_status"],
        ),
        created_at=r["created_at"],
    )


# ── POST /sessions ──────────────────────────────────────────────


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
@audit_action(
    "session.scheduled",
    entity_type="session",
    extract=lambda r, _kw: {
        "session_id": r.id,
        "athlete_id": r.athlete.id,
    },
)
async def schedule_session(
    body: SessionCreateIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> SessionOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No active workspace."
        )

    athlete = await db.scalar(
        text(
            "SELECT id FROM athletes "
            "WHERE id = :aid AND workspace_id = :wid AND archived_at IS NULL"
        ),
        {"aid": body.athlete_id, "wid": workspace_id},
    )
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trainee not found."
        )

    # Resolve the coach for this session.
    assigned_coach_id = user_id
    if body.coach_id is not None and body.coach_id != user_id:
        if not await _is_admin_or_head_coach(db, user_id, workspace_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin or head coach can assign sessions to other coaches.",
            )
        if not await _is_coach_member(db, body.coach_id, workspace_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user is not an active coach in this workspace.",
            )
        assigned_coach_id = body.coach_id

    try:
        sport_id = await resolve_sport_id(
            db, workspace_id=workspace_id, sport_id=body.sport_id
        )
    except SportError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e

    new_id = uuid4()
    primary_focus = body.focuses[0] if body.focuses else None
    await db.execute(
        text(
            """
            INSERT INTO sessions (
                id, workspace_id, sport_id, athlete_id, coach_id,
                scheduled_at, duration_min, court, focus,
                summary, status
            ) VALUES (
                :id, :wid, :sid, :aid, :cid, :sat, :dur, :court,
                CAST(:focus AS session_focus),
                :notes, 'scheduled'
            )
            """
        ),
        {
            "id": new_id,
            "wid": workspace_id,
            "sid": sport_id,
            "aid": body.athlete_id,
            "cid": assigned_coach_id,
            "sat": body.scheduled_at,
            "dur": body.duration_min,
            "court": body.court,
            "focus": primary_focus,
            "notes": body.notes,
        },
    )
    if body.focuses:
        await _replace_focuses(
            db,
            session_id=new_id,
            workspace_id=workspace_id,
            focuses=list(body.focuses),
        )
    out = await _load(db, session_id=new_id)
    await db.commit()
    return out


# ── GET /sessions ───────────────────────────────────────────────


@router.get("", response_model=list[SessionOut])
async def list_sessions(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
    scope: Literal["all", "mine", "upcoming", "past"] = Query("all"),
    stage: FunnelStage | None = Query(default=None),
    athlete_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[SessionOut]:
    if workspace_id is None:
        return []

    clauses: list[str] = ["s.workspace_id = :wid"]
    params: dict = {"wid": workspace_id, "limit": limit, "uid": user_id}

    if scope == "mine":
        clauses.append("s.coach_id = :uid")
    elif scope == "upcoming":
        clauses.append("s.scheduled_at >= NOW() AND s.status = 'scheduled'")
    elif scope == "past":
        clauses.append(
            "(s.status IN ('completed','no_show','cancelled') "
            "OR s.scheduled_at < NOW())"
        )

    if stage == "upcoming":
        clauses.append("s.scheduled_at >= NOW() AND s.status = 'scheduled'")
    elif stage == "to_assess":
        clauses.append(
            "s.scheduled_at < NOW() "
            "AND s.status NOT IN ('cancelled','no_show') "
            "AND (a.status IS NULL OR a.status = 'withdrawn')"
        )
    elif stage == "draft":
        clauses.append("a.status = 'draft'")
    elif stage == "published":
        clauses.append("a.status IN ('published','edited')")
    elif stage == "cancelled":
        clauses.append("s.status IN ('cancelled','no_show')")

    if athlete_id is not None:
        clauses.append("s.athlete_id = :aid")
        params["aid"] = athlete_id

    where = " AND ".join(clauses)
    order = (
        "s.scheduled_at ASC"
        if scope == "upcoming" or stage == "upcoming"
        else "s.scheduled_at DESC"
    )
    sql = f"{_BASE_SELECT} {_BASE_FROM} WHERE {where} ORDER BY {order} LIMIT :limit"
    rows = (await db.execute(text(sql), params)).mappings().all()
    session_ids = [r["id"] for r in rows]
    focuses_map = await _load_focuses_for_sessions(db, session_ids)
    return [
        _row_to_session_out(
            dict(r), focuses_map.get(r["id"], _legacy_focuses(r["focus"]))
        )
        for r in rows
    ]


# ── GET /sessions/funnel/counts ─────────────────────────────────


@router.get("/funnel/counts", response_model=FunnelCountsOut)
async def funnel_counts(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
    mine: bool = Query(default=True),
) -> FunnelCountsOut:
    if workspace_id is None:
        return FunnelCountsOut(
            upcoming=0, to_assess=0, draft=0, published=0, cancelled=0
        )
    extra = "AND s.coach_id = :uid" if mine else ""
    sql = f"""
        SELECT
          SUM(CASE WHEN s.scheduled_at >= NOW() AND s.status = 'scheduled'
                   THEN 1 ELSE 0 END) AS upcoming,
          SUM(CASE WHEN s.scheduled_at < NOW()
                    AND s.status NOT IN ('cancelled','no_show')
                    AND (a.status IS NULL OR a.status = 'withdrawn')
                   THEN 1 ELSE 0 END) AS to_assess,
          SUM(CASE WHEN a.status = 'draft' THEN 1 ELSE 0 END) AS draft,
          SUM(CASE WHEN a.status IN ('published','edited') THEN 1 ELSE 0 END) AS published,
          SUM(CASE WHEN s.status IN ('cancelled','no_show') THEN 1 ELSE 0 END) AS cancelled
        FROM sessions s
        LEFT JOIN assessments a ON a.session_id = s.id
        WHERE s.workspace_id = :wid {extra}
    """
    row = (
        await db.execute(text(sql), {"wid": workspace_id, "uid": user_id})
    ).mappings().first()
    return FunnelCountsOut(
        upcoming=int(row["upcoming"] or 0) if row else 0,
        to_assess=int(row["to_assess"] or 0) if row else 0,
        draft=int(row["draft"] or 0) if row else 0,
        published=int(row["published"] or 0) if row else 0,
        cancelled=int(row["cancelled"] or 0) if row else 0,
    )


# ── GET /sessions/conflicts ─────────────────────────────────────


@router.get("/conflicts")
async def session_conflicts(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
    scheduled_at: datetime = Query(...),
    duration_min: int = Query(60, ge=5, le=600),
    athlete_id: UUID | None = Query(default=None),
    exclude_session_id: UUID | None = Query(default=None),
) -> dict:
    if workspace_id is None:
        return {"coach_conflicts": [], "trainee_conflicts": []}
    start = scheduled_at
    end = scheduled_at + timedelta(minutes=duration_min)

    base = f"""
        {_BASE_SELECT} {_BASE_FROM}
         WHERE s.workspace_id = :wid
           AND s.status = 'scheduled'
           AND s.scheduled_at < :end
           AND (s.scheduled_at + (s.duration_min || ' minutes')::interval) > :start
           {"AND s.id <> :exid" if exclude_session_id else ""}
    """
    base_params: dict = {
        "wid": workspace_id,
        "start": start,
        "end": end,
    }
    if exclude_session_id is not None:
        base_params["exid"] = exclude_session_id

    coach_rows = (
        await db.execute(
            text(base + " AND s.coach_id = :cid"),
            {**base_params, "cid": user_id},
        )
    ).mappings().all()
    trainee_rows: list = []
    if athlete_id is not None:
        trainee_rows = list(
            (
                await db.execute(
                    text(base + " AND s.athlete_id = :aid"),
                    {**base_params, "aid": athlete_id},
                )
            ).mappings().all()
        )
    all_rows = list(coach_rows) + trainee_rows
    focuses_map = await _load_focuses_for_sessions(
        db, [r["id"] for r in all_rows]
    )
    return {
        "coach_conflicts": [
            _row_to_session_out(
                dict(r), focuses_map.get(r["id"], _legacy_focuses(r["focus"]))
            ).model_dump(mode="json")
            for r in coach_rows
        ],
        "trainee_conflicts": [
            _row_to_session_out(
                dict(r), focuses_map.get(r["id"], _legacy_focuses(r["focus"]))
            ).model_dump(mode="json")
            for r in trainee_rows
        ],
    }


# ── GET /sessions/mine (trainee-side) ───────────────────────────


@router.get("/mine", response_model=list[SessionOut])
async def list_mine(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
    scope: Literal["all", "upcoming", "past"] = Query("all"),
) -> list[SessionOut]:
    if workspace_id is None:
        return []
    extra = ""
    if scope == "upcoming":
        extra = " AND s.scheduled_at >= NOW() AND s.status = 'scheduled'"
    elif scope == "past":
        extra = (
            " AND (s.status IN ('completed','no_show','cancelled') "
            "OR s.scheduled_at < NOW())"
        )
    sql = (
        f"{_BASE_SELECT} {_BASE_FROM} "
        f"WHERE s.workspace_id = :wid AND ath.user_id = :uid {extra} "
        f"ORDER BY s.scheduled_at DESC LIMIT 60"
    )
    rows = (
        await db.execute(text(sql), {"wid": workspace_id, "uid": user_id})
    ).mappings().all()
    focuses_map = await _load_focuses_for_sessions(db, [r["id"] for r in rows])
    return [
        _row_to_session_out(
            dict(r), focuses_map.get(r["id"], _legacy_focuses(r["focus"]))
        )
        for r in rows
    ]


# ── Cross-workspace coach view ──────────────────────────────────
# Aggregates the sessions a coach has across ALL workspaces they coach in
# (e.g. solo Personal workspace + one or more Clubs) so they don't need to
# switch workspace just to see what's on the schedule. Auth gate is
# ``s.coach_id = current_user`` — RLS bypassed because the query crosses
# workspaces. Declared BEFORE ``/{session_id}`` so the static paths win.


_CROSS_SELECT = """
    SELECT s.id, s.scheduled_at, s.duration_min, s.court, s.focus::text AS focus,
           s.status, s.summary AS notes, s.completed_at, s.created_at,
           s.coach_id, cu.display_name AS coach_name,
           ath.id AS trainee_id, ath.display_name AS trainee_name,
           NULL::timestamptz AS last_assessed_at,
           tier.id AS tier_id, tier.code AS tier_code,
           tier.name_game_en, tier.name_game_id,
           a.id AS assessment_id, a.status AS assessment_status,
           w.id AS workspace_id, w.name AS workspace_name,
           w.type AS workspace_type, w.brand_color AS workspace_brand_color
    FROM sessions s
    JOIN athletes ath  ON ath.id = s.athlete_id
    JOIN users cu      ON cu.id = s.coach_id
    JOIN workspaces w  ON w.id = s.workspace_id
    LEFT JOIN tiers tier ON tier.id = ath.current_tier_id
    LEFT JOIN assessments a ON a.session_id = s.id
"""


def _cross_row_to_session_out(r: dict) -> SessionOut:
    return SessionOut(
        id=str(r["id"]),
        athlete=SessionTraineeBrief(
            id=str(r["trainee_id"]),
            display_name=r["trainee_name"],
            last_assessed_at=r["last_assessed_at"],
            current_tier=(
                TierBrief(
                    id=str(r["tier_id"]),
                    code=r["tier_code"],
                    name_game_en=r["name_game_en"],
                    name_game_id=r["name_game_id"],
                )
                if r["tier_id"] is not None
                else None
            ),
        ),
        coach=CoachBrief(
            id=str(r["coach_id"]),
            display_name=r["coach_name"],
        ),
        workspace=SessionWorkspaceBrief(
            id=str(r["workspace_id"]),
            name=r["workspace_name"],
            type=r["workspace_type"],
            brand_color=r["workspace_brand_color"],
        ),
        scheduled_at=r["scheduled_at"],
        duration_min=int(r["duration_min"] or 60),
        court=r["court"],
        focuses=[r["focus"]] if r["focus"] else [],
        status=r["status"],
        notes=r["notes"],
        completed_at=r["completed_at"],
        has_assessment=r["assessment_id"] is not None,
        assessment_id=str(r["assessment_id"]) if r["assessment_id"] else None,
        assessment_status=r["assessment_status"],
        funnel_stage=_funnel_stage_for(
            status_=r["status"],
            scheduled_at=r["scheduled_at"],
            assessment_status=r["assessment_status"],
        ),
        created_at=r["created_at"],
    )


@router.get("/all-mine", response_model=list[SessionOut])
async def list_all_mine(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
) -> list[SessionOut]:
    """All sessions where the current user is the coach, across every
    workspace they're a coach in. Optional ``from`` / ``to`` clip to a date
    range (used by the calendar to fetch the visible month)."""
    import asyncpg

    from src.invites.service import _superuser_dsn

    clauses: list[str] = ["s.coach_id = $1"]
    params: list[object] = [user_id]
    if from_ is not None:
        params.append(from_)
        clauses.append(f"s.scheduled_at >= ${len(params)}")
    if to is not None:
        params.append(to)
        clauses.append(f"s.scheduled_at < ${len(params)}")
    params.append(limit)
    where = " AND ".join(clauses)
    sql = (
        f"{_CROSS_SELECT} WHERE {where} "
        f"ORDER BY s.scheduled_at ASC LIMIT ${len(params)}"
    )
    conn = await asyncpg.connect(_superuser_dsn())
    try:
        rows = await conn.fetch(sql, *params)
    finally:
        await conn.close()
    return [_cross_row_to_session_out(dict(r)) for r in rows]


@router.get("/today/all-mine", response_model=list[SessionOut])
async def list_today_all_mine(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> list[SessionOut]:
    """Today's sessions across all workspaces the user coaches in. Used by
    Coach Today so multi-workspace coaches see the full day at a glance."""
    import asyncpg

    from src.invites.service import _superuser_dsn

    now = datetime.now(UTC)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    sql = (
        f"{_CROSS_SELECT} "
        f"WHERE s.coach_id = $1 AND s.scheduled_at >= $2 AND s.scheduled_at < $3 "
        f"ORDER BY s.scheduled_at ASC"
    )
    conn = await asyncpg.connect(_superuser_dsn())
    try:
        rows = await conn.fetch(sql, user_id, day_start, day_end)
    finally:
        await conn.close()
    return [_cross_row_to_session_out(dict(r)) for r in rows]


# ── GET /sessions/{id} ──────────────────────────────────────────


@router.get("/{session_id}", response_model=SessionOut)
async def get_one(
    session_id: UUID,
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> SessionOut:
    return await _load(db, session_id=session_id)


# ── PATCH /sessions/{id} ────────────────────────────────────────


@router.patch("/{session_id}", response_model=SessionOut)
@audit_action(
    "session.updated",
    entity_type="session",
    extract=lambda r, _kw: {"session_id": r.id},
)
async def update_session(
    session_id: UUID,
    body: SessionUpdateIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> SessionOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No active workspace."
        )
    row = (
        await db.execute(
            text("SELECT coach_id, status FROM sessions WHERE id = :id"),
            {"id": session_id},
        )
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found."
        )
    is_privileged = await _is_admin_or_head_coach(db, user_id, workspace_id)
    if row[0] != user_id and not is_privileged:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned coach can edit this session.",
        )
    if row[1] in ("cancelled", "no_show"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot edit a {row[1]} session.",
        )

    sets: list[str] = []
    params: dict = {"id": session_id}
    if body.coach_id is not None:
        if not is_privileged:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin or head coach can reassign sessions.",
            )
        if workspace_id is None or not await _is_coach_member(
            db, body.coach_id, workspace_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user is not an active coach in this workspace.",
            )
        sets.append("coach_id = :coach_id")
        params["coach_id"] = body.coach_id
    if body.scheduled_at is not None:
        sets.append("scheduled_at = :sat")
        params["sat"] = body.scheduled_at
    if body.duration_min is not None:
        sets.append("duration_min = :dur")
        params["dur"] = body.duration_min
    if body.court is not None:
        sets.append("court = :court")
        params["court"] = body.court
    if body.notes is not None:
        sets.append("summary = :notes")
        params["notes"] = body.notes
    if sets:
        sets.append("updated_at = NOW()")
        await db.execute(
            text(f"UPDATE sessions SET {', '.join(sets)} WHERE id = :id"),
            params,
        )
    if body.focuses is not None:
        await _replace_focuses(
            db,
            session_id=session_id,
            workspace_id=workspace_id,
            focuses=list(body.focuses),
        )
    out = await _load(db, session_id=session_id)
    await db.commit()
    return out


# ── POST /sessions/{id}/cancel ──────────────────────────────────


@router.post("/{session_id}/cancel", response_model=SessionOut)
@audit_action(
    "session.cancelled",
    entity_type="session",
    extract=lambda r, _kw: {"session_id": r.id},
)
async def cancel_session(
    session_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> SessionOut:
    row = (
        await db.execute(
            text("SELECT coach_id, status FROM sessions WHERE id = :id"),
            {"id": session_id},
        )
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found."
        )
    if row[0] != user_id and not await _is_admin_or_head_coach(db, user_id, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned coach can cancel this session.",
        )
    if row[1] == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed sessions can't be cancelled.",
        )
    await db.execute(
        text(
            "DELETE FROM assessments WHERE session_id = :id AND status = 'draft'"
        ),
        {"id": session_id},
    )
    await db.execute(
        text(
            "UPDATE sessions SET status = 'cancelled', updated_at = NOW() "
            "WHERE id = :id"
        ),
        {"id": session_id},
    )
    out = await _load(db, session_id=session_id)
    await db.commit()
    return out


# ── POST /sessions/{id}/complete ────────────────────────────────


@router.post("/{session_id}/complete", response_model=SessionOut)
@audit_action(
    "session.completed",
    entity_type="session",
    extract=lambda r, _kw: {"session_id": r.id},
)
async def complete_session(
    session_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> SessionOut:
    row = (
        await db.execute(
            text("SELECT coach_id, status FROM sessions WHERE id = :id"),
            {"id": session_id},
        )
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found."
        )
    if row[0] != user_id and not await _is_admin_or_head_coach(db, user_id, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned coach can mark this session.",
        )
    if row[1] in ("cancelled", "no_show"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot complete a {row[1]} session.",
        )
    await db.execute(
        text(
            """
            UPDATE sessions
               SET status       = 'completed',
                   completed_at = COALESCE(completed_at, NOW()),
                   updated_at   = NOW()
             WHERE id = :id
            """
        ),
        {"id": session_id},
    )
    out = await _load(db, session_id=session_id)
    await db.commit()
    return out


# ── POST /sessions/{id}/no_show ─────────────────────────────────


@router.post("/{session_id}/no_show", response_model=SessionOut)
@audit_action(
    "session.no_show",
    entity_type="session",
    extract=lambda r, _kw: {"session_id": r.id},
)
async def no_show_session(
    session_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> SessionOut:
    row = (
        await db.execute(
            text("SELECT coach_id, status FROM sessions WHERE id = :id"),
            {"id": session_id},
        )
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found."
        )
    if row[0] != user_id and not await _is_admin_or_head_coach(db, user_id, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned coach can mark this session.",
        )
    if row[1] in ("cancelled", "completed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot mark a {row[1]} session as no-show.",
        )
    # No-show shouldn't keep a draft around either.
    await db.execute(
        text(
            "DELETE FROM assessments WHERE session_id = :id AND status = 'draft'"
        ),
        {"id": session_id},
    )
    await db.execute(
        text(
            "UPDATE sessions SET status = 'no_show', updated_at = NOW() "
            "WHERE id = :id"
        ),
        {"id": session_id},
    )
    out = await _load(db, session_id=session_id)
    await db.commit()
    return out


# ── Load helper ─────────────────────────────────────────────────


async def _load(db: AsyncSession, *, session_id: UUID) -> SessionOut:
    sql = f"{_BASE_SELECT} {_BASE_FROM} WHERE s.id = :id LIMIT 1"
    row = (await db.execute(text(sql), {"id": session_id})).mappings().first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found."
        )
    focuses_map = await _load_focuses_for_sessions(db, [row["id"]])
    return _row_to_session_out(
        dict(row), focuses_map.get(row["id"], _legacy_focuses(row["focus"]))
    )


# Silence unused-import noise (Literal/SessionFocus referenced in lambda params).
_ = SessionFocus
_ = UTC
