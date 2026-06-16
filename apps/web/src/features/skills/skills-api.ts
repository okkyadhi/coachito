// Real client for the trainee-self Skills endpoints. Backend lives in
// `apps/api/src/skills/me_router.py` and is workspace-scoped via RLS to the
// signed-in trainee.

import { api } from '@/lib/api';

import type { CategoryCode } from '@/lib/category-meta';

import type {
  CategoryBlockers,
  CategoryBreakdown,
  FocusReason,
  SkillsOverview,
} from './skills-types';

interface ApiCategoryScore {
  code: CategoryCode;
  label_en: string;
  label_id: string;
  average: number | null;
  assessed_count: number;
  total_count: number;
}

interface ApiTierBrief {
  code: string;
  label_en: string;
  label_id: string;
}

interface ApiTierProgress {
  current: ApiTierBrief | null;
  next: ApiTierBrief | null;
  blockers_remaining_count: number;
  progress_to_next: number;
}

interface ApiOverall {
  average: number | null;
  assessed_count: number;
  total_count: number;
  last_assessed_at: string | null;
}

interface ApiRecentGain {
  skill_code: string;
  label_en: string;
  label_id: string;
  from_level: number;
  to_level: number;
  at: string;
}

interface ApiFocusSuggestion {
  skill_code: string;
  label_en: string;
  label_id: string;
  current_level: number | null;
  required_level: number | null;
  category: CategoryCode;
  latest_note_en: string | null;
  latest_note_id: string | null;
  reason: FocusReason;
}

interface ApiOverview {
  categories: ApiCategoryScore[];
  overall: ApiOverall;
  tier: ApiTierProgress | null;
  recent_gains: ApiRecentGain[];
  focus_suggestion: ApiFocusSuggestion | null;
  updated_at: string | null;
}

interface ApiSkillScore {
  code: string;
  label_en: string;
  label_id: string;
  label_short_en: string | null;
  label_short_id: string | null;
  latest_score: number | null;
  latest_descriptor_en: string | null;
  latest_descriptor_id: string | null;
  last_assessed_at: string | null;
}

interface ApiBreakdown {
  category: CategoryCode;
  skills: ApiSkillScore[];
  updated_at: string | null;
}

interface ApiBlockers {
  next_tier: { code: string; label_en: string; label_id: string } | null;
  blockers_in_category: {
    skill_code: string;
    required_level: number;
    current_level: number;
  }[];
  blockers_total_count: number;
}

export async function fetchSkillsOverview(sportId?: string | null): Promise<SkillsOverview> {
  const qs = sportId ? `?sport_id=${sportId}` : '';
  const r = await api.get<ApiOverview>(`/skills/me/overview${qs}`);
  return {
    categories: r.categories.map((c) => ({
      category: c.code,
      average: c.average,
      assessedCount: c.assessed_count,
      totalCount: c.total_count,
    })),
    overall: {
      average: r.overall.average,
      assessedCount: r.overall.assessed_count,
      totalCount: r.overall.total_count,
      lastAssessedAt: r.overall.last_assessed_at,
    },
    tier: r.tier
      ? {
          current: r.tier.current
            ? {
                code: r.tier.current.code,
                labelEn: r.tier.current.label_en,
                labelId: r.tier.current.label_id,
              }
            : null,
          next: r.tier.next
            ? {
                code: r.tier.next.code,
                labelEn: r.tier.next.label_en,
                labelId: r.tier.next.label_id,
              }
            : null,
          blockersRemainingCount: r.tier.blockers_remaining_count,
          progressToNext: r.tier.progress_to_next,
        }
      : null,
    recentGains: r.recent_gains.map((g) => ({
      skillCode: g.skill_code,
      labelEn: g.label_en,
      labelId: g.label_id,
      from: g.from_level,
      to: g.to_level,
      at: g.at,
    })),
    focusSuggestion: r.focus_suggestion
      ? {
          skillCode: r.focus_suggestion.skill_code,
          labelEn: r.focus_suggestion.label_en,
          labelId: r.focus_suggestion.label_id,
          currentLevel: r.focus_suggestion.current_level,
          requiredLevel: r.focus_suggestion.required_level,
          category: r.focus_suggestion.category,
          latestNoteEn: r.focus_suggestion.latest_note_en,
          latestNoteId: r.focus_suggestion.latest_note_id,
          reason: r.focus_suggestion.reason,
        }
      : null,
    updatedAt: r.updated_at,
  };
}

export async function fetchCategoryBreakdown(
  code: CategoryCode,
  sportId?: string | null,
): Promise<CategoryBreakdown> {
  const qs = sportId ? `?sport_id=${sportId}` : '';
  const r = await api.get<ApiBreakdown>(`/skills/me/category/${code}${qs}`);
  return {
    category: r.category,
    skills: r.skills.map((s) => ({
      code: s.code,
      labelEn: s.label_en,
      labelId: s.label_id,
      labelShortEn: s.label_short_en,
      labelShortId: s.label_short_id,
      latestScore: s.latest_score,
      latestDescriptorEn: s.latest_descriptor_en,
      latestDescriptorId: s.latest_descriptor_id,
      lastAssessedAt: s.last_assessed_at,
    })),
    updatedAt: r.updated_at,
  };
}

export async function fetchCategoryBlockers(
  code: CategoryCode,
  sportId?: string | null,
): Promise<CategoryBlockers> {
  const qs = sportId ? `?sport_id=${sportId}` : '';
  const r = await api.get<ApiBlockers>(`/skills/me/category/${code}/blockers${qs}`);
  return {
    nextTier: r.next_tier
      ? {
          code: r.next_tier.code,
          labelEn: r.next_tier.label_en,
          labelId: r.next_tier.label_id,
        }
      : null,
    blockersInCategory: r.blockers_in_category.map((b) => ({
      skillCode: b.skill_code,
      requiredLevel: b.required_level,
      currentLevel: b.current_level,
    })),
    blockersTotalCount: r.blockers_total_count,
  };
}
