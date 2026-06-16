// Real GET /trainees/me/home — sourced from the new assessment v2 shape.
// v1's hardcoded sample data is gone; the wire shape on the server already
// matches what the FE reads here.

import { api } from '@/lib/api';

import type { CategoryAverage } from '@/features/trainee-profile/profile-types';

export interface AchievementSummary {
  skillCode: string;
  skillNameEn: string;
  levelLabelKey: string;
  bodyEn: string;
  bodyId: string;
}

export interface TraineeTierProgress {
  currentTierGameEn: string;
  nextTierGameEn: string | null;
  metCount: number;
  totalRequirements: number;
  encouragementEn: string;
  encouragementId: string;
}

export interface UpcomingSessionDto {
  id: string;
  scheduledAt: string;
  durationMin: number;
  court: string | null;
  focus: string | null;
  coachDisplayName: string;
}

export interface CoachNoteDto {
  coachDisplayName: string;
  sessionDate: string;
  summary: string;
}

export interface GainDto {
  skillNameEn: string;
  fromLevel: number;
  toLevel: number;
  recordedAt: string;
}

export interface TraineeHome {
  traineeFirstName: string;
  workspaceName: string;
  hasAssessment: boolean;
  achievement: AchievementSummary | null;
  tierProgress: TraineeTierProgress | null;
  upcomingSession: UpcomingSessionDto | null;
  coachNote: CoachNoteDto | null;
  categoryAverages: CategoryAverage[];
  recentGains: GainDto[];
  rhythmDays14: boolean[];
}

// ── Wire shapes ─────────────────────────────────────────────────

interface ApiTierBrief {
  code: string;
  name_game_en: string;
  name_game_id: string;
}

interface ApiTierProgress {
  current_tier: ApiTierBrief | null;
  next_tier: ApiTierBrief | null;
  met_count: number;
  total_requirements: number;
}

interface ApiCategoryAverage {
  category: 'technical' | 'tactical' | 'physical' | 'mental';
  average: number;
  skills_rated: number;
}

interface ApiGain {
  skill_name_en: string;
  from_level: number | null;
  to_level: number;
  recorded_at: string;
}

interface ApiUpcoming {
  id: string;
  scheduled_at: string;
  duration_min: number;
  court: string | null;
  focus: string | null;
  coach_display_name: string;
}

interface ApiCoachNote {
  coach_display_name: string;
  session_date: string;
  summary: string;
}

interface ApiHome {
  trainee_first_name: string;
  workspace_name: string;
  has_assessment: boolean;
  tier_progress: ApiTierProgress | null;
  upcoming_session: ApiUpcoming | null;
  coach_note: ApiCoachNote | null;
  category_averages: ApiCategoryAverage[];
  recent_gains: ApiGain[];
  rhythm_days14: boolean[];
}

export async function fetchTraineeHome(sportId?: string | null): Promise<TraineeHome> {
  const qs = sportId ? `?sport_id=${sportId}` : '';
  const r = await api.get<ApiHome>(`/trainees/me/home${qs}`);
  return {
    traineeFirstName: r.trainee_first_name,
    workspaceName: r.workspace_name,
    hasAssessment: r.has_assessment,
    // Achievement card is derived FE-side from `recent_gains[0]` if present.
    // Skipped at MVP — the existing copy on AchievementCard is encouragement
    // text that we don't yet generate server-side.  Wire it later.
    achievement: null,
    tierProgress: r.tier_progress
      ? {
          currentTierGameEn:
            r.tier_progress.current_tier?.name_game_en ?? 'Beginner',
          nextTierGameEn: r.tier_progress.next_tier?.name_game_en ?? null,
          metCount: r.tier_progress.met_count,
          totalRequirements: r.tier_progress.total_requirements,
          // Encouragement copy: kept on the FE so it can localize without a
          // BE deploy.  We don't have per-trainee copy generation yet.
          encouragementEn: '',
          encouragementId: '',
        }
      : null,
    upcomingSession: r.upcoming_session
      ? {
          id: r.upcoming_session.id,
          scheduledAt: r.upcoming_session.scheduled_at,
          durationMin: r.upcoming_session.duration_min,
          court: r.upcoming_session.court,
          focus: r.upcoming_session.focus,
          coachDisplayName: r.upcoming_session.coach_display_name,
        }
      : null,
    coachNote: r.coach_note
      ? {
          coachDisplayName: r.coach_note.coach_display_name,
          sessionDate: r.coach_note.session_date,
          summary: r.coach_note.summary,
        }
      : null,
    categoryAverages: r.category_averages.map((c): CategoryAverage => ({
      category: c.category,
      average: c.average,
      skillsRated: c.skills_rated,
    })),
    recentGains: r.recent_gains.map((g): GainDto => ({
      skillNameEn: g.skill_name_en,
      fromLevel: g.from_level ?? 0,
      toLevel: g.to_level,
      recordedAt: g.recorded_at,
    })),
    rhythmDays14: r.rhythm_days14,
  };
}
