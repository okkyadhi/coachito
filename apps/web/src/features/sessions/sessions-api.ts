// Session CRUD client (v2).

import type { QueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api';

/** Invalidate every query that depends on session state.  Call this after
 *  any mutation that touches sessions or assessments (create / update /
 *  cancel / publish / etc.).  The broad `['sessions']` key catches all
 *  variants (mine, upcoming, past, athleteId filters).
 */
export function invalidateSessionCaches(qc: QueryClient): void {
  void qc.invalidateQueries({ queryKey: ['sessions'] });
  void qc.invalidateQueries({ queryKey: ['today-sessions'] });
  void qc.invalidateQueries({ queryKey: ['trainee-profile'] });
  void qc.invalidateQueries({ queryKey: ['feedback-inbox'] });
  // Funnel counts surface in BottomTabBar + Today badge — bump them too
  // (key reserved for Phase 6).
  void qc.invalidateQueries({ queryKey: ['sessions', 'funnel', 'counts'] });
  // Trainee-side mirrors.
  void qc.invalidateQueries({ queryKey: ['trainee-mine-sessions'] });
  void qc.invalidateQueries({ queryKey: ['trainee-home'] });
}

export type SessionFocus =
  | 'drilling'
  | 'match_play'
  | 'conditioning'
  | 'mental_training'
  | 'technique_focus'
  | 'general';

export type SessionStatus =
  | 'scheduled'
  | 'completed'
  | 'cancelled'
  | 'no_show';

export interface SessionTrainee {
  id: string;
  displayName: string;
  lastAssessedAt: string | null;
  currentTier: {
    id: string;
    code: string;
    nameGameEn: string;
    nameGameId: string;
  } | null;
}

export interface SessionCoach {
  id: string;
  displayName: string;
}

export interface SessionWorkspace {
  id: string;
  name: string;
  type: string;  // 'personal' | 'club'
  brandColor: string | null;
}

export type FunnelStage =
  | 'upcoming'
  | 'to_assess'
  | 'draft'
  | 'published'
  | 'cancelled';

export interface Session {
  id: string;
  athlete: SessionTrainee;
  coach: SessionCoach;
  workspace: SessionWorkspace | null;
  scheduledAt: string;
  durationMin: number;
  court: string | null;
  focuses: SessionFocus[];
  status: SessionStatus;
  notes: string | null;
  completedAt: string | null;
  hasAssessment: boolean;
  assessmentId: string | null;
  assessmentStatus: 'draft' | 'published' | 'edited' | null;
  funnelStage: FunnelStage;
  createdAt: string;
  sportId: string | null;
}

export interface FunnelCounts {
  upcoming: number;
  toAssess: number;
  draft: number;
  published: number;
  cancelled: number;
}

// ── Wire ────────────────────────────────────────────────────────

interface ApiTier {
  id: string;
  code: string;
  name_game_en: string;
  name_game_id: string;
}

interface ApiTrainee {
  id: string;
  display_name: string;
  last_assessed_at: string | null;
  current_tier: ApiTier | null;
}

interface ApiCoach {
  id: string;
  display_name: string;
}

interface ApiWorkspace {
  id: string;
  name: string;
  type: string;
  brand_color: string | null;
}

interface ApiSession {
  id: string;
  athlete: ApiTrainee;
  coach: ApiCoach;
  workspace: ApiWorkspace | null;
  scheduled_at: string;
  duration_min: number;
  court: string | null;
  focuses: SessionFocus[];
  status: SessionStatus;
  notes: string | null;
  completed_at: string | null;
  has_assessment: boolean;
  assessment_id: string | null;
  assessment_status: 'draft' | 'published' | 'edited' | null;
  funnel_stage: FunnelStage;
  created_at: string;
  sport_id: string | null;
}

function toSession(s: ApiSession): Session {
  return {
    id: s.id,
    athlete: {
      id: s.athlete.id,
      displayName: s.athlete.display_name,
      lastAssessedAt: s.athlete.last_assessed_at,
      currentTier: s.athlete.current_tier
        ? {
            id: s.athlete.current_tier.id,
            code: s.athlete.current_tier.code,
            nameGameEn: s.athlete.current_tier.name_game_en,
            nameGameId: s.athlete.current_tier.name_game_id,
          }
        : null,
    },
    coach: {
      id: s.coach.id,
      displayName: s.coach.display_name,
    },
    workspace: s.workspace
      ? {
          id: s.workspace.id,
          name: s.workspace.name,
          type: s.workspace.type,
          brandColor: s.workspace.brand_color,
        }
      : null,
    scheduledAt: s.scheduled_at,
    durationMin: s.duration_min,
    court: s.court,
    focuses: s.focuses ?? [],
    status: s.status,
    notes: s.notes,
    completedAt: s.completed_at,
    hasAssessment: s.has_assessment,
    assessmentId: s.assessment_id,
    assessmentStatus: s.assessment_status,
    funnelStage: s.funnel_stage,
    createdAt: s.created_at,
    sportId: s.sport_id ?? null,
  };
}

// ── Public API ──────────────────────────────────────────────────

export interface CreateSessionInput {
  athleteId: string;
  scheduledAt: string;
  durationMin?: number;
  court?: string | null;
  focuses?: SessionFocus[];
  notes?: string | null;
  sportId?: string | null;
  /** Admin / head_coach only — assign to a specific coach. */
  coachId?: string | null;
}

export async function createSession(input: CreateSessionInput): Promise<Session> {
  const body: Record<string, unknown> = {
    athlete_id: input.athleteId,
    scheduled_at: input.scheduledAt,
  };
  if (input.durationMin !== undefined) body.duration_min = input.durationMin;
  if (input.court !== undefined) body.court = input.court;
  if (input.focuses !== undefined) body.focuses = input.focuses;
  if (input.notes !== undefined) body.notes = input.notes;
  if (input.sportId != null) body.sport_id = input.sportId;
  if (input.coachId != null) body.coach_id = input.coachId;
  const r = await api.post<ApiSession>('/sessions', body);
  return toSession(r);
}

export interface ListSessionsInput {
  scope?: 'all' | 'mine' | 'upcoming' | 'past';
  athleteId?: string;
}

export async function listSessions(input: ListSessionsInput & { stage?: FunnelStage } = {}): Promise<Session[]> {
  const q = new URLSearchParams();
  if (input.scope) q.set('scope', input.scope);
  if (input.stage) q.set('stage', input.stage);
  if (input.athleteId) q.set('athlete_id', input.athleteId);
  const qs = q.toString();
  const r = await api.get<ApiSession[]>(`/sessions${qs ? `?${qs}` : ''}`);
  return r.map(toSession);
}

// ── Cross-workspace coach view ──────────────────────────────────

export interface ListAllMineInput {
  /** ISO datetime, inclusive lower bound. Server clips to >=. */
  from?: string;
  /** ISO datetime, exclusive upper bound. Server clips to <. */
  to?: string;
}

/** All sessions the current coach has across every workspace they coach in.
 *  Drives the calendar — query per visible month range. */
export async function listAllMineSessions(input: ListAllMineInput = {}): Promise<Session[]> {
  const q = new URLSearchParams();
  if (input.from) q.set('from', input.from);
  if (input.to) q.set('to', input.to);
  const qs = q.toString();
  const r = await api.get<ApiSession[]>(`/sessions/all-mine${qs ? `?${qs}` : ''}`);
  return r.map(toSession);
}

/** Today's sessions across all workspaces — Coach Today screen. */
export async function listTodayAllMine(): Promise<Session[]> {
  const r = await api.get<ApiSession[]>('/sessions/today/all-mine');
  return r.map(toSession);
}

export async function getFunnelCounts(mine = true): Promise<FunnelCounts> {
  const r = await api.get<{
    upcoming: number;
    to_assess: number;
    draft: number;
    published: number;
    cancelled: number;
  }>(`/sessions/funnel/counts?mine=${mine ? 'true' : 'false'}`);
  return {
    upcoming: r.upcoming,
    toAssess: r.to_assess,
    draft: r.draft,
    published: r.published,
    cancelled: r.cancelled,
  };
}

export interface SessionConflict {
  coachConflicts: Session[];
  traineeConflicts: Session[];
}

export async function getSessionConflicts(args: {
  scheduledAt: string;
  durationMin: number;
  athleteId?: string;
  excludeSessionId?: string;
}): Promise<SessionConflict> {
  const q = new URLSearchParams({
    scheduled_at: args.scheduledAt,
    duration_min: String(args.durationMin),
  });
  if (args.athleteId) q.set('athlete_id', args.athleteId);
  if (args.excludeSessionId) q.set('exclude_session_id', args.excludeSessionId);
  const r = await api.get<{
    coach_conflicts: ApiSession[];
    trainee_conflicts: ApiSession[];
  }>(`/sessions/conflicts?${q.toString()}`);
  return {
    coachConflicts: r.coach_conflicts.map(toSession),
    traineeConflicts: r.trainee_conflicts.map(toSession),
  };
}

export async function completeSession(id: string): Promise<Session> {
  const r = await api.post<ApiSession>(`/sessions/${id}/complete`);
  return toSession(r);
}

export async function markSessionNoShow(id: string): Promise<Session> {
  const r = await api.post<ApiSession>(`/sessions/${id}/no_show`);
  return toSession(r);
}

export async function listMySessions(
  scope: 'all' | 'upcoming' | 'past' = 'all',
): Promise<Session[]> {
  const r = await api.get<ApiSession[]>(`/sessions/mine?scope=${scope}`);
  return r.map(toSession);
}

export async function getSession(id: string): Promise<Session> {
  const r = await api.get<ApiSession>(`/sessions/${id}`);
  return toSession(r);
}

export interface UpdateSessionInput {
  scheduledAt?: string;
  durationMin?: number;
  court?: string | null;
  focuses?: SessionFocus[];
  notes?: string | null;
  /** Admin / head_coach only — reassign to a different coach. */
  coachId?: string | null;
}

export async function updateSession(
  id: string,
  input: UpdateSessionInput,
): Promise<Session> {
  const body: Record<string, unknown> = {};
  if (input.scheduledAt !== undefined) body.scheduled_at = input.scheduledAt;
  if (input.durationMin !== undefined) body.duration_min = input.durationMin;
  if (input.court !== undefined) body.court = input.court;
  if (input.focuses !== undefined) body.focuses = input.focuses;
  if (input.notes !== undefined) body.notes = input.notes;
  if (input.coachId !== undefined) body.coach_id = input.coachId;
  const r = await api.patch<ApiSession>(`/sessions/${id}`, body);
  return toSession(r);
}

export async function cancelSession(id: string): Promise<Session> {
  const r = await api.post<ApiSession>(`/sessions/${id}/cancel`);
  return toSession(r);
}
