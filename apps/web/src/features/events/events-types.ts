/**
 * Match Maker FE types — mirror of apps/api/src/match_maker/schemas.py.
 * Keep the two in lockstep when adding fields.
 */

export type EventStatus = 'draft' | 'active' | 'completed' | 'cancelled';

export type EventFormat =
  | 'americano'
  | 'team_americano'
  | 'mix_americano'
  | 'mexicano'
  | 'team_mexicano'
  | 'mixicano'
  | 'koth'
  | 'team_koth';

export type ScoringMode =
  | 'point'
  | 'normal_first_to'
  | 'normal_total'
  | 'normal_first_to_tiebreak';

export type MexicanoPairing = '1_3_vs_2_4' | '1_4_vs_2_3';
export type LeaderboardSort = 'points' | 'wins';

export const TEAM_FORMATS: ReadonlySet<EventFormat> = new Set<EventFormat>([
  'team_americano',
  'team_mexicano',
  'team_koth',
]);

export const MIX_FORMATS: ReadonlySet<EventFormat> = new Set<EventFormat>([
  'mix_americano',
  'mixicano',
]);

export const MEXICANO_FAMILY: ReadonlySet<EventFormat> = new Set<EventFormat>([
  'mexicano',
  'team_mexicano',
  'mixicano',
]);

/** Logical grouping shown in the format picker. */
export type EventFamily = 'americano' | 'mexicano' | 'koth';

export interface FormatDescriptor {
  format: EventFormat;
  family: EventFamily;
  isTeam: boolean;
  isMix: boolean;
}

export const FORMATS: readonly FormatDescriptor[] = [
  { format: 'americano',       family: 'americano', isTeam: false, isMix: false },
  { format: 'team_americano',  family: 'americano', isTeam: true,  isMix: false },
  { format: 'mix_americano',   family: 'americano', isTeam: false, isMix: true  },
  { format: 'mexicano',        family: 'mexicano',  isTeam: false, isMix: false },
  { format: 'team_mexicano',   family: 'mexicano',  isTeam: true,  isMix: false },
  { format: 'mixicano',        family: 'mexicano',  isTeam: false, isMix: true  },
  { format: 'koth',            family: 'koth',      isTeam: false, isMix: false },
  { format: 'team_koth',       family: 'koth',      isTeam: true,  isMix: false },
];

export interface EventSummary {
  id: string;
  workspaceId: string;
  title: string;
  venue: string | null;
  format: EventFormat;
  scoringMode: ScoringMode;
  scoringTarget: number | null;
  roundTimerSeconds: number | null;
  courtCount: number;
  /** Sparse array indexed by court_number-1; nulls / shorter arrays mean
   *  the default "Court {n}" label applies. */
  courtNames: (string | null)[];
  mexicanoPairing: MexicanoPairing | null;
  leaderboardSort: LeaderboardSort;
  totalRounds: number;
  currentRound: number;
  status: EventStatus;
  isPublic: boolean;
  publicSlug: string | null;
  startsAt: string | null;
  completedAt: string | null;
  createdById: string;
  createdAt: string;
  participantsCount: number;
  teamsCount: number;
}

export interface Participant {
  id: string;
  athleteId: string | null;
  claimUserId: string | null;
  displayName: string;
  teamId: string | null;
  tag: string | null;
  initialSeed: number | null;
  joinedRound: number;
  withdrewRound: number | null;
}

export interface Team {
  id: string;
  displayName: string;
  tag: string | null;
}

export interface EventDetail extends EventSummary {
  participants: Participant[];
  teams: Team[];
}

export interface Match {
  id: string;
  courtNumber: number;
  sideA: string[];
  sideB: string[];
  scoreA: number | null;
  scoreB: number | null;
  winnerSide: 'A' | 'B' | 'D' | null;
  recordedAt: string | null;
}

export interface Round {
  roundNumber: number;
  startedAt: string | null;
  completedAt: string | null;
  matches: Match[];
}

export interface LeaderboardRow {
  participantId: string;
  displayName: string;
  /** Total score on the board.  Equals raw points scored + compensation. */
  points: number;
  wins: number;
  losses: number;
  ties: number;
  matchesPlayed: number;
  /** Point differential (points scored − points conceded). */
  pointDiff: number;
  /** Compensation for fewer matches played.  Already included in `points`. */
  compensation: number;
}

export interface Leaderboard {
  sort: LeaderboardSort;
  rows: LeaderboardRow[];
}

export interface EventCreateInput {
  title: string;
  venue?: string | null;
  format: EventFormat;
  scoringMode: ScoringMode;
  scoringTarget?: number | null;
  roundTimerSeconds?: number | null;
  courtCount: number;
  mexicanoPairing?: MexicanoPairing | null;
  leaderboardSort?: LeaderboardSort;
  isPublic?: boolean;
  startsAt?: string | null;
}
