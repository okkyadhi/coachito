// Today's sessions for the signed-in coach. Calls GET /sessions/today/all-mine
// which aggregates across every workspace the user coaches in — Today no
// longer requires switching workspace to see the full day. Each session
// carries a workspace blob so the row can render the WorkspaceBadge.

import { api } from '@/lib/api';

import type { TierCode } from '@/components/TierPill';

export type SessionFocus =
  | 'drilling'
  | 'match_play'
  | 'conditioning'
  | 'mental_training'
  | 'technique_focus'
  | 'general';

export interface TodayTrainee {
  id: string;
  displayName: string;
  tier: TierCode | null;
  lastAssessedAt: Date | null;
}

export interface TodayCoach {
  id: string;
  displayName: string;
}

export interface TodayWorkspace {
  id: string;
  name: string;
  type: string;  // 'personal' | 'club'
  brandColor: string | null;
}

export interface TodaySession {
  id: string;
  scheduledAt: Date;
  durationMin: number;
  court: string | null;
  focuses: SessionFocus[];
  sportId: string | null;
  coach: TodayCoach | null;
  trainee: TodayTrainee;
  workspace: TodayWorkspace | null;
}

// ── Wire shapes (snake_case from the API) ────────────────────────

interface ApiTier {
  id: string;
  code: TierCode;
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

// Wire shape of /sessions/today/all-mine — same as SessionOut. We map down to
// the lighter TodaySession TS shape so existing TraineeRow / UpNextCard
// components keep their props.
interface ApiWorkspace {
  id: string;
  name: string;
  type: string;
  brand_color: string | null;
}

interface ApiCrossSession {
  id: string;
  scheduled_at: string;
  duration_min: number;
  court: string | null;
  focuses: SessionFocus[];
  status: string;
  coach: ApiCoach;
  workspace: ApiWorkspace | null;
  athlete: ApiTrainee;  // SessionOut uses "athlete" not "trainee"
}

export async function getTodaySessions(): Promise<TodaySession[]> {
  const rows = await api.get<ApiCrossSession[]>('/sessions/today/all-mine');
  return rows.map((s) => ({
    id: s.id,
    scheduledAt: new Date(s.scheduled_at),
    durationMin: s.duration_min,
    court: s.court,
    focuses: s.focuses ?? [],
    sportId: null,  // /all-mine drops sport_id; trainee profile pulls it on demand
    coach: s.coach ? { id: s.coach.id, displayName: s.coach.display_name } : null,
    trainee: {
      id: s.athlete.id,
      displayName: s.athlete.display_name,
      tier: s.athlete.current_tier ? s.athlete.current_tier.code : null,
      lastAssessedAt: s.athlete.last_assessed_at
        ? new Date(s.athlete.last_assessed_at)
        : null,
    },
    workspace: s.workspace
      ? {
          id: s.workspace.id,
          name: s.workspace.name,
          type: s.workspace.type,
          brandColor: s.workspace.brand_color,
        }
      : null,
  }));
}
