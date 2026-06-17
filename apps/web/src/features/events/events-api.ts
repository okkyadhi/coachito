import { api } from '@/lib/api';

import type {
  EventCreateInput,
  EventDetail,
  EventStatus,
  EventSummary,
  Leaderboard,
  LeaderboardSort,
  Round,
} from './events-types';

interface ApiSummary {
  id: string;
  workspace_id: string;
  title: string;
  venue: string | null;
  format: EventSummary['format'];
  scoring_mode: EventSummary['scoringMode'];
  scoring_target: number | null;
  round_timer_seconds: number | null;
  court_count: number;
  court_names: (string | null)[];
  mexicano_pairing: EventSummary['mexicanoPairing'];
  leaderboard_sort: EventSummary['leaderboardSort'];
  total_rounds: number;
  current_round: number;
  status: EventStatus;
  is_public: boolean;
  public_slug: string | null;
  starts_at: string | null;
  completed_at: string | null;
  created_by_id: string;
  created_at: string;
  participants_count: number;
  teams_count: number;
}

interface ApiParticipant {
  id: string;
  athlete_id: string | null;
  claim_user_id: string | null;
  display_name: string;
  team_id: string | null;
  tag: string | null;
  initial_seed: number | null;
  joined_round: number;
  withdrew_round: number | null;
}

interface ApiTeam {
  id: string;
  display_name: string;
  tag: string | null;
}

interface ApiDetail extends ApiSummary {
  participants: ApiParticipant[];
  teams: ApiTeam[];
}

function fromSummary(r: ApiSummary): EventSummary {
  return {
    id: r.id,
    workspaceId: r.workspace_id,
    title: r.title,
    venue: r.venue,
    format: r.format,
    scoringMode: r.scoring_mode,
    scoringTarget: r.scoring_target,
    roundTimerSeconds: r.round_timer_seconds,
    courtCount: r.court_count,
    courtNames: r.court_names ?? [],
    mexicanoPairing: r.mexicano_pairing,
    leaderboardSort: r.leaderboard_sort,
    totalRounds: r.total_rounds,
    currentRound: r.current_round,
    status: r.status,
    isPublic: r.is_public,
    publicSlug: r.public_slug,
    startsAt: r.starts_at,
    completedAt: r.completed_at,
    createdById: r.created_by_id,
    createdAt: r.created_at,
    participantsCount: r.participants_count,
    teamsCount: r.teams_count,
  };
}

export async function listEvents(
  statusFilter?: EventStatus,
): Promise<EventSummary[]> {
  const qs = statusFilter ? `?status_filter=${statusFilter}` : '';
  const r = await api.get<{ events: ApiSummary[] }>(`/events${qs}`);
  return r.events.map(fromSummary);
}

export async function getEvent(id: string): Promise<EventDetail> {
  const r = await api.get<ApiDetail>(`/events/${id}`);
  return {
    ...fromSummary(r),
    participants: r.participants.map((p) => ({
      id: p.id,
      athleteId: p.athlete_id,
      claimUserId: p.claim_user_id,
      displayName: p.display_name,
      teamId: p.team_id,
      tag: p.tag,
      initialSeed: p.initial_seed,
      joinedRound: p.joined_round,
      withdrewRound: p.withdrew_round,
    })),
    teams: r.teams.map((t) => ({
      id: t.id,
      displayName: t.display_name,
      tag: t.tag,
    })),
  };
}

export async function createEvent(
  input: EventCreateInput,
): Promise<EventSummary> {
  const body: Record<string, unknown> = {
    title: input.title,
    format: input.format,
    scoring_mode: input.scoringMode,
    court_count: input.courtCount,
  };
  if (input.venue !== undefined) body.venue = input.venue;
  if (input.scoringTarget !== undefined) body.scoring_target = input.scoringTarget;
  if (input.roundTimerSeconds !== undefined)
    body.round_timer_seconds = input.roundTimerSeconds;
  if (input.mexicanoPairing !== undefined) body.mexicano_pairing = input.mexicanoPairing;
  if (input.leaderboardSort !== undefined) body.leaderboard_sort = input.leaderboardSort;
  if (input.isPublic !== undefined) body.is_public = input.isPublic;
  if (input.startsAt !== undefined) body.starts_at = input.startsAt;
  return fromSummary(await api.post<ApiSummary>('/events', body));
}

export async function cancelEvent(id: string): Promise<EventSummary> {
  return fromSummary(await api.post<ApiSummary>(`/events/${id}/cancel`));
}

// ── Phase 2 — live event ──────────────────────────────────────────

export async function startEvent(id: string): Promise<EventSummary> {
  return fromSummary(await api.post<ApiSummary>(`/events/${id}/start`));
}

export async function advanceRound(id: string): Promise<EventSummary> {
  return fromSummary(await api.post<ApiSummary>(`/events/${id}/rounds/next`));
}

export async function completeEvent(id: string): Promise<EventSummary> {
  return fromSummary(await api.post<ApiSummary>(`/events/${id}/complete`));
}

interface ApiMatch {
  id: string;
  court_number: number;
  side_a: string[];
  side_b: string[];
  score_a: number | null;
  score_b: number | null;
  winner_side: 'A' | 'B' | 'D' | null;
  recorded_at: string | null;
}

interface ApiRound {
  round_number: number;
  started_at: string | null;
  completed_at: string | null;
  matches: ApiMatch[];
}

export async function listRounds(id: string): Promise<Round[]> {
  const r = await api.get<{ rounds: ApiRound[] }>(`/events/${id}/rounds`);
  return r.rounds.map((rd) => ({
    roundNumber: rd.round_number,
    startedAt: rd.started_at,
    completedAt: rd.completed_at,
    matches: rd.matches.map((m) => ({
      id: m.id,
      courtNumber: m.court_number,
      sideA: m.side_a,
      sideB: m.side_b,
      scoreA: m.score_a,
      scoreB: m.score_b,
      winnerSide: m.winner_side,
      recordedAt: m.recorded_at,
    })),
  }));
}

export interface RecordScoreInput {
  scoreA: number;
  scoreB: number;
  clientRecordedAt?: string;
}

export async function recordScore(
  eventId: string,
  matchId: string,
  input: RecordScoreInput,
): Promise<void> {
  const body: Record<string, unknown> = {
    score_a: input.scoreA,
    score_b: input.scoreB,
  };
  if (input.clientRecordedAt) body.client_recorded_at = input.clientRecordedAt;
  await api.patch(`/events/${eventId}/matches/${matchId}/score`, body);
}

interface ApiLeaderboard {
  sort: LeaderboardSort;
  rows: {
    participant_id: string;
    display_name: string;
    points: number;
    wins: number;
    losses: number;
    ties: number;
    matches_played: number;
    point_diff: number;
    compensation: number;
  }[];
}

export async function getLeaderboard(
  eventId: string,
  sort: LeaderboardSort = 'points',
): Promise<Leaderboard> {
  const r = await api.get<ApiLeaderboard>(
    `/events/${eventId}/leaderboard?sort=${sort}`,
  );
  return {
    sort: r.sort,
    rows: r.rows.map((row) => ({
      participantId: row.participant_id,
      displayName: row.display_name,
      points: row.points,
      wins: row.wins,
      losses: row.losses,
      ties: row.ties,
      matchesPlayed: row.matches_played,
      pointDiff: row.point_diff,
      compensation: row.compensation,
    })),
  };
}

export async function reshuffleCurrentRound(
  eventId: string,
): Promise<EventSummary> {
  return fromSummary(
    await api.post<ApiSummary>(`/events/${eventId}/rounds/current/reshuffle`),
  );
}

export async function extendRounds(eventId: string): Promise<EventSummary> {
  return fromSummary(
    await api.post<ApiSummary>(`/events/${eventId}/rounds/extend`),
  );
}

export async function renameCourt(
  eventId: string,
  courtNumber: number,
  name: string | null,
): Promise<EventSummary> {
  return fromSummary(
    await api.patch<ApiSummary>(
      `/events/${eventId}/courts/${courtNumber}`,
      { name },
    ),
  );
}

/**
 * Resolve a court's display label.  Falls back to the default
 * ``Court {n}`` localised string when no override is set.
 */
export function courtDisplayName(
  courtNumber: number,
  courtNames: (string | null)[],
  fallback: (n: number) => string,
): string {
  const override = courtNames[courtNumber - 1];
  return override && override.trim() ? override : fallback(courtNumber);
}
