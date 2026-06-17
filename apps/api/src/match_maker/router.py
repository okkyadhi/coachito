"""Match Maker HTTP surface — Phase 1 (draft state only).

Pairing engine, scoring, and public standings ship in Phases 2+.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.deps import get_current_user_id, get_current_workspace_id
from src.middleware.rls import db_with_rls

from . import service
from .schemas import (
    CourtRenameIn,
    EventCreateIn,
    EventDetailOut,
    EventOut,
    EventStatus,
    EventUpdateIn,
    EventsListOut,
    LeaderboardOut,
    LeaderboardRow,
    LeaderboardSort,
    MatchOut,
    ParticipantAddIn,
    ParticipantOut,
    ParticipantPatchIn,
    RoundOut,
    RoundsListOut,
    ScoreIn,
    ScoreOut,
    TeamCreateIn,
    TeamOut,
    TeamPatchIn,
)

router = APIRouter(prefix="/events", tags=["match-maker"])


def _need_workspace(workspace_id: UUID | None) -> UUID:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active workspace.",
        )
    return workspace_id


def _map_state_error(e: service.EventStateError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT, detail=str(e)
    )


# ── Events ───────────────────────────────────────────────────────


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
async def create_event(
    body: EventCreateIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> EventOut:
    wid = _need_workspace(workspace_id)
    return await service.create_event(
        db, workspace_id=wid, created_by_id=user_id, body=body,
    )


@router.get("", response_model=EventsListOut)
async def list_events(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
    status_filter: EventStatus | None = None,
) -> EventsListOut:
    wid = _need_workspace(workspace_id)
    events = await service.list_events(
        db, workspace_id=wid, user_id=user_id, status=status_filter,
    )
    return EventsListOut(events=events)


@router.get("/{event_id}", response_model=EventDetailOut)
async def get_event(
    event_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],  # noqa: ARG001
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> EventDetailOut:
    wid = _need_workspace(workspace_id)
    out = await service.fetch_event_detail(
        db, workspace_id=wid, event_id=event_id,
    )
    if out is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        )
    return out


@router.patch("/{event_id}", response_model=EventOut)
async def patch_event(
    event_id: UUID,
    body: EventUpdateIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],  # noqa: ARG001
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> EventOut:
    wid = _need_workspace(workspace_id)
    try:
        return await service.patch_event(
            db, workspace_id=wid, event_id=event_id, body=body,
        )
    except service.EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        ) from None
    except service.EventStateError as e:
        raise _map_state_error(e) from None


@router.post("/{event_id}/cancel", response_model=EventOut)
async def cancel_event(
    event_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],  # noqa: ARG001
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> EventOut:
    wid = _need_workspace(workspace_id)
    try:
        return await service.cancel_event(
            db, workspace_id=wid, event_id=event_id,
        )
    except service.EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        ) from None


# ── Participants ─────────────────────────────────────────────────


@router.post(
    "/{event_id}/participants",
    response_model=ParticipantOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_participant(
    event_id: UUID,
    body: ParticipantAddIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],  # noqa: ARG001
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> ParticipantOut:
    wid = _need_workspace(workspace_id)
    try:
        return await service.add_participant(
            db, workspace_id=wid, event_id=event_id, body=body,
        )
    except service.EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        ) from None
    except service.EventStateError as e:
        raise _map_state_error(e) from None


@router.patch(
    "/{event_id}/participants/{participant_id}",
    response_model=ParticipantOut,
)
async def patch_participant(
    event_id: UUID,
    participant_id: UUID,
    body: ParticipantPatchIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],  # noqa: ARG001
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> ParticipantOut:
    wid = _need_workspace(workspace_id)
    try:
        return await service.patch_participant(
            db, workspace_id=wid, event_id=event_id,
            participant_id=participant_id, body=body,
        )
    except service.EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found."
        ) from None


@router.delete(
    "/{event_id}/participants/{participant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def withdraw_participant(
    event_id: UUID,
    participant_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],  # noqa: ARG001
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> None:
    wid = _need_workspace(workspace_id)
    try:
        await service.withdraw_participant(
            db, workspace_id=wid, event_id=event_id,
            participant_id=participant_id,
        )
    except service.EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        ) from None


# ── Teams ────────────────────────────────────────────────────────


@router.post(
    "/{event_id}/teams",
    response_model=TeamOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_team(
    event_id: UUID,
    body: TeamCreateIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],  # noqa: ARG001
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> TeamOut:
    wid = _need_workspace(workspace_id)
    try:
        return await service.create_team(
            db, workspace_id=wid, event_id=event_id, body=body,
        )
    except service.EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        ) from None
    except service.EventStateError as e:
        raise _map_state_error(e) from None


@router.patch("/{event_id}/teams/{team_id}", response_model=TeamOut)
async def patch_team(
    event_id: UUID,
    team_id: UUID,
    body: TeamPatchIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],  # noqa: ARG001
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> TeamOut:
    wid = _need_workspace(workspace_id)
    try:
        return await service.patch_team(
            db, workspace_id=wid, event_id=event_id,
            team_id=team_id, body=body,
        )
    except service.EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found."
        ) from None


@router.delete(
    "/{event_id}/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_team(
    event_id: UUID,
    team_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],  # noqa: ARG001
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> None:
    wid = _need_workspace(workspace_id)
    try:
        await service.delete_team(
            db, workspace_id=wid, event_id=event_id, team_id=team_id,
        )
    except service.EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found."
        ) from None
    except service.EventStateError as e:
        raise _map_state_error(e) from None


# ── Phase 2: live event endpoints ────────────────────────────────


@router.post("/{event_id}/start", response_model=EventOut)
async def start_event(
    event_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],  # noqa: ARG001
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> EventOut:
    wid = _need_workspace(workspace_id)
    try:
        return await service.start_event(
            db, workspace_id=wid, event_id=event_id,
        )
    except service.EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        ) from None
    except service.EventStateError as e:
        raise _map_state_error(e) from None


@router.post("/{event_id}/rounds/next", response_model=EventOut)
async def advance_round(
    event_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],  # noqa: ARG001
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> EventOut:
    wid = _need_workspace(workspace_id)
    try:
        return await service.advance_round(
            db, workspace_id=wid, event_id=event_id,
        )
    except service.EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        ) from None
    except service.EventStateError as e:
        raise _map_state_error(e) from None


@router.post("/{event_id}/complete", response_model=EventOut)
async def complete_event(
    event_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],  # noqa: ARG001
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> EventOut:
    wid = _need_workspace(workspace_id)
    try:
        return await service.complete_event(
            db, workspace_id=wid, event_id=event_id,
        )
    except service.EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        ) from None
    except service.EventStateError as e:
        raise _map_state_error(e) from None


@router.get("/{event_id}/rounds", response_model=RoundsListOut)
async def list_rounds(
    event_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],  # noqa: ARG001
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> RoundsListOut:
    wid = _need_workspace(workspace_id)
    rounds = await service.list_rounds(
        db, workspace_id=wid, event_id=event_id,
    )
    return RoundsListOut(
        rounds=[
            RoundOut(
                round_number=r["round_number"],
                started_at=r["started_at"],
                completed_at=r["completed_at"],
                matches=[
                    MatchOut(
                        id=m["id"],
                        court_number=m["court_number"],
                        side_a=m["side_a"],
                        side_b=m["side_b"],
                        score_a=m["score_a"],
                        score_b=m["score_b"],
                        winner_side=m["winner_side"],
                        recorded_at=m["recorded_at"],
                    )
                    for m in r["matches"]
                ],
            )
            for r in rounds
        ]
    )


@router.patch(
    "/{event_id}/matches/{match_id}/score", response_model=ScoreOut
)
async def record_score(
    event_id: UUID,
    match_id: UUID,
    body: ScoreIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> ScoreOut:
    wid = _need_workspace(workspace_id)
    try:
        result = await service.record_score(
            db,
            workspace_id=wid,
            event_id=event_id,
            match_id=match_id,
            score_a=body.score_a,
            score_b=body.score_b,
            recorded_by=user_id,
            client_recorded_at=body.client_recorded_at,
        )
    except service.EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Match not found."
        ) from None
    except service.EventStateError as e:
        raise _map_state_error(e) from None
    return ScoreOut(
        id=result["id"],
        score_a=result["score_a"],
        score_b=result["score_b"],
        winner_side=result["winner_side"],
        recorded_at=result["recorded_at"],
    )


@router.post(
    "/{event_id}/rounds/current/reshuffle", response_model=EventOut
)
async def reshuffle_current_round(
    event_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],  # noqa: ARG001
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> EventOut:
    wid = _need_workspace(workspace_id)
    try:
        return await service.reshuffle_current_round(
            db, workspace_id=wid, event_id=event_id,
        )
    except service.EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        ) from None
    except service.EventStateError as e:
        raise _map_state_error(e) from None


@router.post("/{event_id}/rounds/extend", response_model=EventOut)
async def extend_rounds(
    event_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],  # noqa: ARG001
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> EventOut:
    wid = _need_workspace(workspace_id)
    try:
        return await service.extend_americano_rounds(
            db, workspace_id=wid, event_id=event_id,
        )
    except service.EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        ) from None
    except service.EventStateError as e:
        raise _map_state_error(e) from None


@router.patch(
    "/{event_id}/courts/{court_number}", response_model=EventOut
)
async def rename_court(
    event_id: UUID,
    court_number: int,
    body: CourtRenameIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],  # noqa: ARG001
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> EventOut:
    wid = _need_workspace(workspace_id)
    try:
        return await service.rename_court(
            db,
            workspace_id=wid,
            event_id=event_id,
            court_number=court_number,
            name=body.name,
        )
    except service.EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        ) from None
    except service.EventStateError as e:
        raise _map_state_error(e) from None


@router.get("/{event_id}/leaderboard", response_model=LeaderboardOut)
async def get_leaderboard(
    event_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],  # noqa: ARG001
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
    sort: LeaderboardSort = "points",
) -> LeaderboardOut:
    wid = _need_workspace(workspace_id)
    rows = await service.leaderboard(
        db, workspace_id=wid, event_id=event_id, sort=sort,
    )
    return LeaderboardOut(
        sort=sort,
        rows=[LeaderboardRow(**r) for r in rows],
    )
