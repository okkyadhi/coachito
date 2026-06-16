import type { CategoryCode } from '@/lib/category-meta';

export interface CategoryScore {
  category: CategoryCode;
  /** Mean of assessed skill scores in this category, 0–5, or null if none. */
  average: number | null;
  assessedCount: number;
  totalCount: number;
}

export interface OverallProgress {
  average: number | null;
  assessedCount: number;
  totalCount: number;
  lastAssessedAt: string | null;
}

export interface TierBrief {
  code: string;
  labelEn: string;
  labelId: string;
}

export interface TierProgress {
  current: TierBrief | null;
  next: TierBrief | null;
  blockersRemainingCount: number;
  /** 0..1 — fraction of next-tier requirements met. 1.0 when at top tier. */
  progressToNext: number;
}

export interface RecentGain {
  skillCode: string;
  labelEn: string;
  labelId: string;
  from: number;
  to: number;
  at: string;
}

export type FocusReason =
  | 'blocker_for_next_tier'
  | 'oldest_unassessed'
  | 'lowest_score';

export interface FocusSuggestion {
  skillCode: string;
  labelEn: string;
  labelId: string;
  currentLevel: number | null;
  requiredLevel: number | null;
  category: CategoryCode;
  latestNoteEn: string | null;
  latestNoteId: string | null;
  reason: FocusReason;
}

export interface SkillsOverview {
  categories: CategoryScore[];
  overall: OverallProgress;
  tier: TierProgress | null;
  recentGains: RecentGain[];
  focusSuggestion: FocusSuggestion | null;
  /** ISO timestamp of the latest assessment that affected this view. */
  updatedAt: string | null;
}

export interface SkillScore {
  code: string;
  labelEn: string;
  labelId: string;
  labelShortEn: string | null;
  labelShortId: string | null;
  latestScore: number | null;
  latestDescriptorEn: string | null;
  latestDescriptorId: string | null;
  lastAssessedAt: string | null;
}

export interface CategoryBreakdown {
  category: CategoryCode;
  skills: SkillScore[];
  updatedAt: string | null;
}

export interface RadarAxis {
  code: string;
  label: string;
  /** Short label rendered as the visible axis text when present. The full
   *  `label` is still used for tooltips and hit-target titles. */
  shortLabel?: string;
  score: number | null;
}

export interface TierBriefLite {
  code: string;
  labelEn: string;
  labelId: string;
}

export interface TierBlockerEntry {
  skillCode: string;
  requiredLevel: number;
  currentLevel: number;
}

export interface CategoryBlockers {
  nextTier: TierBriefLite | null;
  blockersInCategory: TierBlockerEntry[];
  blockersTotalCount: number;
}
