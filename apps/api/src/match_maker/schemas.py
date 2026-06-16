"""Wire shapes for the Match Maker API.

Phase 1 covers the draft state only: event create/list/detail/edit/cancel
plus participant + team CRUD.  Round generation, scoring, and the public
standings surface come in later phases (see docs/20 §16).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ── Enums mirrored from the DB ───────────────────────────────────

EventStatus = Literal["draft", "active", "completed", "cancelled"]
EventFormat = Literal[
    "americano", "team_americano", "mix_americano",
    "mexicano", "team_mexicano", "mixicano",
    "koth", "team_koth",
]
ScoringMode = Literal[
    "point", "normal_first_to", "normal_total", "normal_first_to_tiebreak"
]
MexicanoPairing = Literal["1_3_vs_2_4", "1_4_vs_2_3"]
LeaderboardSort = Literal["points", "wins"]


# Family-of-format helpers — used both server- and client-side to gate UI.
TEAM_FORMATS: frozenset[EventFormat] = frozenset(
    {"team_americano", "team_mexicano", "team_koth"}
)
MIX_FORMATS: frozenset[EventFormat] = frozenset({"mix_americano", "mixicano"})
MEXICANO_FAMILY: frozenset[EventFormat] = frozenset(
    {"mexicano", "team_mexicano", "mixicano"}
)


# ── Create ───────────────────────────────────────────────────────


class EventCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    venue: str | None = Field(default=None, max_length=200)
    format: EventFormat
    scoring_mode: ScoringMode
    scoring_target: int | None = Field(default=None, ge=1, le=200)
    round_timer_seconds: int | None = Field(default=None, ge=60, le=7200)
    court_count: int = Field(ge=1, le=20)
    mexicano_pairing: MexicanoPairing | None = None
    leaderboard_sort: LeaderboardSort = "points"
    is_public: bool = True
    starts_at: datetime | None = None


# ── Update (draft only) ──────────────────────────────────────────


class EventUpdateIn(BaseModel):
    """Partial update, allowed while ``status='draft'`` (per docs/20 §8).
    Once active, only ``court_count`` + ``mexicano_pairing`` +
    ``leaderboard_sort`` are mutable; that's enforced in the service."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=120)
    venue: str | None = Field(default=None, max_length=200)
    format: EventFormat | None = None
    scoring_mode: ScoringMode | None = None
    scoring_target: int | None = Field(default=None, ge=1, le=200)
    round_timer_seconds: int | None = Field(default=None, ge=60, le=7200)
    court_count: int | None = Field(default=None, ge=1, le=20)
    mexicano_pairing: MexicanoPairing | None = None
    leaderboard_sort: LeaderboardSort | None = None
    is_public: bool | None = None
    starts_at: datetime | None = None


# ── Output ───────────────────────────────────────────────────────


class TeamOut(BaseModel):
    id: str
    display_name: str
    tag: str | None


class ParticipantOut(BaseModel):
    id: str
    athlete_id: str | None
    claim_user_id: str | None
    display_name: str
    team_id: str | None
    tag: str | None
    initial_seed: int | None
    joined_round: int
    withdrew_round: int | None


class EventOut(BaseModel):
    id: str
    workspace_id: str
    title: str
    venue: str | None
    format: EventFormat
    scoring_mode: ScoringMode
    scoring_target: int | None
    round_timer_seconds: int | None
    court_count: int
    # Host-editable court labels; sparse array indexed by court_number-1.
    # Missing entries or empty strings fall back to the default "Court {n}".
    court_names: list[str | None]
    mexicano_pairing: MexicanoPairing | None
    leaderboard_sort: LeaderboardSort
    total_rounds: int
    current_round: int
    status: EventStatus
    is_public: bool
    public_slug: str | None
    starts_at: datetime | None
    completed_at: datetime | None
    created_by_id: str
    created_at: datetime
    participants_count: int
    teams_count: int


class EventDetailOut(EventOut):
    """Same as EventOut + nested participants and teams.  Used by GET
    /events/:id.  Rounds + matches are loaded separately once the event
    moves to ``active`` (Phase 2)."""

    participants: list[ParticipantOut]
    teams: list[TeamOut]


# ── Participants ─────────────────────────────────────────────────


class ParticipantAddIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=120)
    athlete_id: UUID | None = None       # link to a known workspace athlete
    team_id: UUID | None = None          # for team formats
    tag: str | None = Field(default=None, max_length=20)
    initial_seed: int | None = Field(default=None, ge=1, le=200)


class ParticipantPatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    team_id: UUID | None = None
    tag: str | None = Field(default=None, max_length=20)
    initial_seed: int | None = Field(default=None, ge=1, le=200)


# ── Teams ────────────────────────────────────────────────────────


class TeamCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=120)
    tag: str | None = Field(default=None, max_length=20)


class TeamPatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    tag: str | None = Field(default=None, max_length=20)


# ── List wrappers ────────────────────────────────────────────────


class EventsListOut(BaseModel):
    events: list[EventOut]


# ── Rounds / matches / scoring (Phase 2) ─────────────────────────


class MatchOut(BaseModel):
    id: str
    court_number: int
    side_a: list[str]                # participant ids
    side_b: list[str]
    score_a: int | None
    score_b: int | None
    winner_side: str | None
    recorded_at: datetime | None


class RoundOut(BaseModel):
    round_number: int
    started_at: datetime | None
    completed_at: datetime | None
    matches: list[MatchOut]


class RoundsListOut(BaseModel):
    rounds: list[RoundOut]


class ScoreIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score_a: int = Field(ge=0, le=999)
    score_b: int = Field(ge=0, le=999)
    client_recorded_at: datetime | None = None


class ScoreOut(BaseModel):
    id: str
    score_a: int
    score_b: int
    winner_side: str
    recorded_at: datetime


class LeaderboardRow(BaseModel):
    participant_id: str
    display_name: str
    points: int
    wins: int
    losses: int
    ties: int
    matches_played: int
    # Point differential = (sum of points scored) - (sum of points conceded).
    # Strong tiebreaker that captures dominance.
    point_diff: int
    # +M = compensation for fewer matches played.  Equal to (max_matches -
    # my_matches) × average_points_per_match for this event, rounded.
    # Surfaces in the table as "+3", "+0" etc.; the leaderboard's ``points``
    # column already includes this comp so totals reconcile.
    compensation: int


class LeaderboardOut(BaseModel):
    rows: list[LeaderboardRow]
    sort: LeaderboardSort


# ── Court rename + reshuffle (Phase 3 polish) ────────────────────


class CourtRenameIn(BaseModel):
    """Rename a single court.  ``name=None`` reverts to the default
    ``Court {n}`` label."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=40)
