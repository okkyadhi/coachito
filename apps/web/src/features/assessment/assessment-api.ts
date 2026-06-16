// Assessment v2 API client — draft / publish / edit / discard.

import { api } from '@/lib/api';

export type AssessmentStatus = 'draft' | 'published' | 'edited' | 'withdrawn';

export type SessionFocus =
  | 'drilling'
  | 'match_play'
  | 'conditioning'
  | 'mental_training'
  | 'technique_focus'
  | 'general';

export interface AssessmentScore {
  skillId: string;
  level: number;
  note: string | null;
  updatedAt: string;
}

export interface CategoryAverage {
  category: 'technical' | 'tactical' | 'physical' | 'mental';
  average: number;
  skillsRated: number;
}

export interface TierBrief {
  id: string;
  code: string;
  nameGameEn: string;
  nameGameId: string;
}

export interface TierSlice {
  currentTier: TierBrief | null;
  nextTier: TierBrief | null;
  metCount: number;
  totalRequirements: number;
  categoryAverages: CategoryAverage[];
}

export interface Assessment {
  id: string;
  workspaceId: string;
  sessionId: string;
  athleteId: string;
  coachId: string;
  coach_display_name: string | null;
  status: AssessmentStatus;
  summary: string | null;
  internalNotes: string | null;
  savedAt: string;
  publishedAt: string | null;
  editedAt: string | null;
  traineeViewedAt: string | null;
  session_scheduled_at: string | null;
  session_duration_min: number | null;
  session_court: string | null;
  session_focus: string | null;
  scores: AssessmentScore[];
  tier: TierSlice | null;
  /** Set on the publish response only — used by the FE to detect tier-up. */
  previousTier: TierBrief | null;
  feedbackCount: number;
  unreadFeedbackCount: number;
}

export interface AssessmentEdit {
  id: string;
  editedById: string;
  editedByDisplayName: string;
  editedAt: string;
  changes: Record<string, unknown>;
  reason: string | null;
}

// ── Wire types ───────────────────────────────────────────────────

interface ApiScore {
  skill_id: string;
  level: number;
  note: string | null;
  updated_at: string;
}

interface ApiTier {
  id: string;
  code: string;
  name_game_en: string;
  name_game_id: string;
}

interface ApiTierSlice {
  current_tier: ApiTier | null;
  next_tier: ApiTier | null;
  met_count: number;
  total_requirements: number;
  category_averages: Array<{
    category: 'technical' | 'tactical' | 'physical' | 'mental';
    average: number;
    skills_rated: number;
  }>;
}

interface ApiAssessment {
  id: string;
  workspace_id: string;
  session_id: string;
  athlete_id: string;
  coach_id: string;
  coach_display_name: string | null;
  status: AssessmentStatus;
  summary: string | null;
  internal_notes: string | null;
  saved_at: string;
  published_at: string | null;
  edited_at: string | null;
  trainee_viewed_at: string | null;
  session_scheduled_at: string | null;
  session_duration_min: number | null;
  session_court: string | null;
  session_focus: string | null;
  scores: ApiScore[];
  tier: ApiTierSlice | null;
  previous_tier: ApiTier | null;
  feedback_count: number | null;
  unread_feedback_count: number | null;
}

function toTier(t: ApiTier | null): TierBrief | null {
  if (!t) return null;
  return {
    id: t.id,
    code: t.code,
    nameGameEn: t.name_game_en,
    nameGameId: t.name_game_id,
  };
}

function toTierSlice(t: ApiTierSlice | null): TierSlice | null {
  if (!t) return null;
  return {
    currentTier: toTier(t.current_tier),
    nextTier: toTier(t.next_tier),
    metCount: t.met_count,
    totalRequirements: t.total_requirements,
    categoryAverages: t.category_averages.map((c) => ({
      category: c.category,
      average: c.average,
      skillsRated: c.skills_rated,
    })),
  };
}

function toAssessment(a: ApiAssessment): Assessment {
  return {
    id: a.id,
    workspaceId: a.workspace_id,
    sessionId: a.session_id,
    athleteId: a.athlete_id,
    coachId: a.coach_id,
    coach_display_name: a.coach_display_name,
    status: a.status,
    summary: a.summary,
    internalNotes: a.internal_notes,
    savedAt: a.saved_at,
    publishedAt: a.published_at,
    editedAt: a.edited_at,
    traineeViewedAt: a.trainee_viewed_at,
    session_scheduled_at: a.session_scheduled_at,
    session_duration_min: a.session_duration_min,
    session_court: a.session_court,
    session_focus: a.session_focus,
    scores: a.scores.map((s) => ({
      skillId: s.skill_id,
      level: s.level,
      note: s.note,
      updatedAt: s.updated_at,
    })),
    tier: toTierSlice(a.tier),
    previousTier: toTier(a.previous_tier),
    feedbackCount: a.feedback_count ?? 0,
    unreadFeedbackCount: a.unread_feedback_count ?? 0,
  };
}

export async function markAssessmentViewed(id: string): Promise<void> {
  await api.post(`/assessments/${id}/view`);
}

export interface DraftSummaryResult {
  draft: string;
  model: string;
}

/** POST /assessments/{id}/draft-summary — Gemini-drafted summary, uses the
 *  caller's voice preset + preferred locale.  Returns text only; nothing is
 *  written to the DB. */
export async function draftAssessmentSummary(
  assessmentId: string,
): Promise<DraftSummaryResult> {
  const r = await api.post<{ draft: string; model: string }>(
    `/assessments/${assessmentId}/draft-summary`,
  );
  return { draft: r.draft, model: r.model };
}

// Tier display_order (mirror of the BE seed).  Used FE-side to detect
// "tier up" — strictly increasing.
const TIER_ORDER: Record<string, number> = {
  BEGINNER: 1,
  LOWER_BRONZE: 2,
  BRONZE: 3,
  SILVER: 4,
  GOLD: 5,
  PLATINUM: 6,
  DIAMOND: 7,
};

/** Returns the new tier code if this publish lifted the trainee to a higher
 *  tier than before, or null if not a promotion. */
export function detectTierUp(a: Assessment): TierBrief | null {
  const next = a.tier?.currentTier ?? null;
  const prev = a.previousTier;
  if (!next) return null;
  if (!prev) return next; // first-ever tier counts as promotion
  const prevRank = TIER_ORDER[prev.code] ?? 0;
  const nextRank = TIER_ORDER[next.code] ?? 0;
  return nextRank > prevRank ? next : null;
}

// ── Public API ───────────────────────────────────────────────────

export interface DraftScoreIn {
  skillId: string;
  level: number;
  note?: string | null;
}

export interface SaveDraftInput {
  athleteId: string;
  sportId?: string | null;
  sessionId?: string | null;
  sessionScheduledAt?: string | null;
  sessionDurationMin?: number | null;
  sessionCourt?: string | null;
  sessionFocus?: SessionFocus | null;
  summary?: string | null;
  internalNotes?: string | null;
  scores: DraftScoreIn[];
}

export async function saveDraft(input: SaveDraftInput): Promise<Assessment> {
  const body: Record<string, unknown> = {
    athlete_id: input.athleteId,
    scores: input.scores.map((s) => ({
      skill_id: s.skillId,
      level: s.level,
      note: s.note ?? null,
    })),
  };
  if (input.sportId != null) body.sport_id = input.sportId;
  if (input.sessionId !== undefined) body.session_id = input.sessionId;
  if (input.sessionScheduledAt !== undefined)
    body.session_scheduled_at = input.sessionScheduledAt;
  if (input.sessionDurationMin !== undefined)
    body.session_duration_min = input.sessionDurationMin;
  if (input.sessionCourt !== undefined) body.session_court = input.sessionCourt;
  if (input.sessionFocus !== undefined) body.session_focus = input.sessionFocus;
  if (input.summary !== undefined) body.summary = input.summary;
  if (input.internalNotes !== undefined) body.internal_notes = input.internalNotes;
  const r = await api.post<ApiAssessment>('/assessments', body);
  return toAssessment(r);
}

export async function getBySession(sessionId: string): Promise<Assessment | null> {
  const r = await api.get<ApiAssessment | null>(
    `/assessments/by-session/${encodeURIComponent(sessionId)}`,
  );
  return r ? toAssessment(r) : null;
}

export async function getAssessment(id: string): Promise<Assessment> {
  const r = await api.get<ApiAssessment>(`/assessments/${id}`);
  return toAssessment(r);
}

export async function publishAssessment(
  id: string,
  forceEmpty = false,
): Promise<Assessment> {
  const r = await api.post<ApiAssessment>(`/assessments/${id}/publish`, {
    force_empty: forceEmpty,
  });
  return toAssessment(r);
}

export interface EditInput {
  summary?: string;
  internalNotes?: string;
  scores?: DraftScoreIn[];
  reason?: string;
}

export async function editAssessment(
  id: string,
  input: EditInput,
): Promise<Assessment> {
  const body: Record<string, unknown> = {};
  if (input.summary !== undefined) body.summary = input.summary;
  if (input.internalNotes !== undefined) body.internal_notes = input.internalNotes;
  if (input.reason !== undefined) body.reason = input.reason;
  if (input.scores !== undefined)
    body.scores = input.scores.map((s) => ({
      skill_id: s.skillId,
      level: s.level,
      note: s.note ?? null,
    }));
  const r = await api.patch<ApiAssessment>(`/assessments/${id}`, body);
  return toAssessment(r);
}

export async function discardDraft(id: string): Promise<void> {
  await api.del(`/assessments/${id}`);
}

export async function getEditHistory(id: string): Promise<AssessmentEdit[]> {
  const r = await api.get<
    Array<{
      id: string;
      edited_by_id: string;
      edited_by_display_name: string;
      edited_at: string;
      changes: Record<string, unknown>;
      reason: string | null;
    }>
  >(`/assessments/${id}/edits`);
  return r.map((e) => ({
    id: e.id,
    editedById: e.edited_by_id,
    editedByDisplayName: e.edited_by_display_name,
    editedAt: e.edited_at,
    changes: e.changes,
    reason: e.reason,
  }));
}
