// Shape of the coach-trainee profile.  Backed by the real
// GET /trainees/{id}/profile endpoint.

import type { TierCode } from '@/components/TierPill';

export type SkillCategory = 'technical' | 'tactical' | 'physical' | 'mental';

export interface TierBrief {
  id: string;
  code: TierCode;
  nameGameEn: string;
  nameGameId: string;
}

export interface SkillBrief {
  id: string;
  code: string;
  category: SkillCategory;
  nameEn: string;
  nameId: string;
  displayOrder: number;
}

export interface SkillScore {
  skill: SkillBrief;
  level: number | null;   // 1-5, null if never assessed
  lastRatedAt: string | null;
}

export interface BlockingSkill {
  skill: SkillBrief;
  currentLevel: number;
  requiredLevel: number;
}

export interface GainEntry {
  skill: SkillBrief;
  fromLevel: number;
  toLevel: number;
  recordedAt: string;
}

export interface SessionEntry {
  id: string;
  scheduledAt: string;
  durationMin: number;
  focuses: string[];
  summary: string | null;
  skillsUpdated: number;
  // Phase 5 — coach attribution + assessment status on each session row.
  coach: { id: string; displayName: string };
  assessmentStatus: 'none' | 'draft' | 'published' | 'edited';
}

export interface CategoryAverage {
  category: SkillCategory;
  average: number;        // 1.0–5.0; 0 means no data
  skillsRated: number;
}

export interface TraineeProfile {
  trainee: {
    id: string;
    displayName: string;
    joinedAt: string;     // ISO date
    isMinor: boolean;
  };
  stats: {
    sessionsCount: number;
    hoursCoached: number; // float, e.g. 18.5
    daysSinceLastSession: number | null;
  };
  tierProgress: {
    currentTier: TierBrief;
    nextTier: TierBrief | null;
    metCount: number;
    totalRequirements: number;
    blockingSkills: BlockingSkill[];
  };
  categoryAverages: CategoryAverage[];
  recentGains: GainEntry[];
  allSkills: SkillScore[];
  recentSessions: SessionEntry[];
}
