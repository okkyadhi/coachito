// Real GET /trainees/{id}/profile — replaces the v1 mock.

import { api } from '@/lib/api';

import type {
  BlockingSkill,
  CategoryAverage,
  GainEntry,
  SessionEntry,
  SkillBrief,
  SkillScore,
  TraineeProfile,
} from './profile-types';
import type { TierCode } from '@/components/TierPill';

// ── Wire shapes ─────────────────────────────────────────────────

interface ApiSkillBrief {
  id: string;
  code: string;
  category: 'technical' | 'tactical' | 'physical' | 'mental';
  name_en: string;
  name_id: string;
  display_order: number;
}

interface ApiTierBrief {
  id: string;
  code: string;
  name_game_en: string;
  name_game_id: string;
}

interface ApiBlockingSkill {
  skill: ApiSkillBrief;
  current_level: number;
  required_level: number;
}

interface ApiGain {
  skill: ApiSkillBrief;
  from_level: number | null;
  to_level: number;
  recorded_at: string;
}

interface ApiSkillScore {
  skill: ApiSkillBrief;
  level: number | null;
  last_rated_at: string | null;
}

interface ApiSessionEntry {
  id: string;
  scheduled_at: string;
  duration_min: number;
  focuses: string[];
  summary: string | null;
  skills_updated: number;
  coach: { id: string; display_name: string };
  assessment_status: 'none' | 'draft' | 'published' | 'edited';
}

interface ApiCategoryAverage {
  category: 'technical' | 'tactical' | 'physical' | 'mental';
  average: number;
  skills_rated: number;
}

interface ApiProfile {
  trainee: {
    id: string;
    display_name: string;
    joined_at: string;
    is_minor: boolean;
  };
  stats: {
    sessions_count: number;
    hours_coached: number;
    days_since_last_session: number | null;
  };
  tier_progress: {
    current_tier: ApiTierBrief;
    next_tier: ApiTierBrief | null;
    met_count: number;
    total_requirements: number;
    blocking_skills: ApiBlockingSkill[];
  };
  category_averages: ApiCategoryAverage[];
  recent_gains: ApiGain[];
  all_skills: ApiSkillScore[];
  recent_sessions: ApiSessionEntry[];
}

// ── Mappers ─────────────────────────────────────────────────────

function toSkill(s: ApiSkillBrief): SkillBrief {
  return {
    id: s.id,
    code: s.code,
    category: s.category,
    nameEn: s.name_en,
    nameId: s.name_id,
    displayOrder: s.display_order,
  };
}

function toTier(t: ApiTierBrief) {
  return {
    id: t.id,
    code: t.code as TierCode,
    nameGameEn: t.name_game_en,
    nameGameId: t.name_game_id,
  };
}

export async function fetchTraineeProfile(
  id: string,
  sportId?: string,
): Promise<TraineeProfile> {
  const qs = sportId ? `?sport_id=${sportId}` : '';
  const r = await api.get<ApiProfile>(`/trainees/${id}/profile${qs}`);
  return {
    trainee: {
      id: r.trainee.id,
      displayName: r.trainee.display_name,
      joinedAt: r.trainee.joined_at,
      isMinor: r.trainee.is_minor,
    },
    stats: {
      sessionsCount: r.stats.sessions_count,
      hoursCoached: r.stats.hours_coached,
      daysSinceLastSession: r.stats.days_since_last_session,
    },
    tierProgress: {
      currentTier: toTier(r.tier_progress.current_tier),
      nextTier: r.tier_progress.next_tier ? toTier(r.tier_progress.next_tier) : null,
      metCount: r.tier_progress.met_count,
      totalRequirements: r.tier_progress.total_requirements,
      blockingSkills: r.tier_progress.blocking_skills.map((b): BlockingSkill => ({
        skill: toSkill(b.skill),
        currentLevel: b.current_level,
        requiredLevel: b.required_level,
      })),
    },
    categoryAverages: r.category_averages.map((c): CategoryAverage => ({
      category: c.category,
      average: c.average,
      skillsRated: c.skills_rated,
    })),
    recentGains: r.recent_gains.map((g): GainEntry => ({
      skill: toSkill(g.skill),
      fromLevel: g.from_level ?? 0,
      toLevel: g.to_level,
      recordedAt: g.recorded_at,
    })),
    allSkills: r.all_skills.map((a): SkillScore => ({
      skill: toSkill(a.skill),
      level: a.level,
      lastRatedAt: a.last_rated_at,
    })),
    recentSessions: r.recent_sessions.map((s): SessionEntry => ({
      id: s.id,
      scheduledAt: s.scheduled_at,
      durationMin: s.duration_min,
      focuses: s.focuses ?? [],
      summary: s.summary,
      skillsUpdated: s.skills_updated,
      coach: { id: s.coach.id, displayName: s.coach.display_name },
      assessmentStatus: s.assessment_status,
    })),
  };
}

// Kept as named export so the screen's MOCK_EMPTY toggle (now ignored) doesn't
// cause an import break. Flip via FE empty-state work later.
export const MOCK_EMPTY = false;

/** True when the trainee has at least one published assessment to render. */
export function hasAnyAssessment(p: TraineeProfile): boolean {
  return p.allSkills.some((s) => s.level !== null);
}
