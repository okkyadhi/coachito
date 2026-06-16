// Data layer for /curriculum/*.  Thin api wrappers + TanStack Query hooks.
//
// Query keys are scoped by workspaceId so switching tenants invalidates
// everything (matches the pattern in settings-api.ts).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useAuthStore } from '@/features/auth/auth-store';
import { useSportStore } from '@/features/sports/sport-store';
import { useCurrentSport } from '@/features/sports/useCurrentSport';
import { ApiError, api } from '@/lib/api';

// ── Types (mirror Pydantic schemas) ───────────────────────────────

export type SkillCategory = 'technical' | 'tactical' | 'physical' | 'mental';

export interface SkillRow {
  id: string;
  code: string;
  category: SkillCategory;
  name_en: string;
  name_id: string;
  description_en: string | null;
  description_id: string | null;
  display_order: number;
  is_enabled: boolean;
  is_override: boolean;
  /** ISO timestamp of last admin action within the last 7 days, or null. */
  last_changed_at: string | null;
}

interface SkillsResponse {
  skills: SkillRow[];
}

export interface SkillImpact {
  trainee_count: number;
  assessment_count: number;
  in_tier_requirements: boolean;
}

export interface Tier {
  id: string;
  code: string;
  display_order: number;
  name_game_en: string;
  name_game_id: string;
  name_skill_en: string;
  name_skill_id: string;
  name_custom_en: string | null;
  name_custom_id: string | null;
  color_hex: string | null;
  icon_name: string | null;
  is_override: boolean;
}

interface TiersResponse {
  tiers: Tier[];
}

export interface TierNamesPatch {
  name_custom_en?: string;
  name_custom_id?: string;
}

export interface Descriptor {
  level: number;
  description_en: string;
  description_id: string;
}

interface DescriptorsResponse {
  skill_code: string;
  descriptors: Descriptor[];
}

export interface FeedbackNote {
  id: string;
  author_display_name: string;
  skill_code: string | null;
  skill_name_en: string | null;
  body: string;
  created_at: string;
  read_at: string | null;
}

export interface FeedbackInbox {
  notes: FeedbackNote[];
  unread_count: number;
}

export interface FeedbackNoteIn {
  skill_id?: string | null;
  body: string;
}

export interface TierRequirement {
  tier_code: string;
  tier_display_order: number;
  tier_name: string;
  min_level: number;
}

interface TierContextResponse {
  skill_code: string;
  requirements: TierRequirement[];
}

// ── Raw API calls ─────────────────────────────────────────────────

export const curriculumApi = {
  listSkills: (sportId?: string) =>
    api.get<SkillsResponse>(
      `/curriculum/skills${sportId ? `?sport_id=${sportId}` : ''}`,
    ),
  patchSkill: (code: string, isEnabled: boolean) =>
    api.patch<SkillRow>(`/curriculum/skills/${code}`, { is_enabled: isEnabled }),
  getImpact: (code: string) =>
    api.get<SkillImpact>(`/curriculum/skills/${code}/impact`),
  getTierContext: (code: string) =>
    api.get<TierContextResponse>(`/curriculum/skills/${code}/tier-context`),
  getDescriptors: (code: string) =>
    api.get<DescriptorsResponse>(`/skills/${code}/descriptors`),
  listTiers: (sportId?: string) =>
    api.get<TiersResponse>(
      `/curriculum/tiers${sportId ? `?sport_id=${sportId}` : ''}`,
    ),
  patchTier: (code: string, patch: TierNamesPatch) =>
    api.patch<Tier>(`/curriculum/tiers/${code}`, patch),
  sendFeedback: (note: FeedbackNoteIn) =>
    api.post<FeedbackNote>('/curriculum/feedback', note),
  getInbox: () => api.get<FeedbackInbox>('/curriculum/feedback'),
  getMyFeedback: () => api.get<FeedbackInbox>('/curriculum/feedback/mine'),
  markRead: (noteId: string) =>
    api.post<FeedbackNote>(`/curriculum/feedback/${noteId}/read`),
};

// ── Query keys ────────────────────────────────────────────────────

function workspaceKey(): string {
  // Cache buster on workspace switch — the same fetch returns different data
  // depending on which workspace's JWT the api client is sending.
  return useAuthStore.getState().currentWorkspaceId ?? '';
}

function sportKey(): string {
  return useSportStore.getState().byWorkspace[workspaceKey()] ?? '';
}

export const curriculumKeys = {
  skills: () => ['curriculum', 'skills', workspaceKey(), sportKey()] as const,
  tiers: () => ['curriculum', 'tiers', workspaceKey(), sportKey()] as const,
  descriptors: (code: string) =>
    ['curriculum', 'descriptors', code, workspaceKey()] as const,
  impact: (code: string) =>
    ['curriculum', 'impact', code, workspaceKey()] as const,
  tierContext: (code: string) =>
    ['curriculum', 'tier-context', code, workspaceKey()] as const,
  inbox: () => ['curriculum', 'inbox', workspaceKey()] as const,
  myFeedback: () => ['curriculum', 'my-feedback', workspaceKey()] as const,
};

// ── Hooks ─────────────────────────────────────────────────────────

export function useCurriculumSkills() {
  const { currentSportId } = useCurrentSport();
  return useQuery({
    queryKey: curriculumKeys.skills(),
    queryFn: async () =>
      (await curriculumApi.listSkills(currentSportId ?? undefined)).skills,
    staleTime: 30_000,
  });
}

export function useCurriculumTiers() {
  const { currentSportId } = useCurrentSport();
  return useQuery({
    queryKey: curriculumKeys.tiers(),
    queryFn: async () =>
      (await curriculumApi.listTiers(currentSportId ?? undefined)).tiers,
    staleTime: 30_000,
  });
}

export function useSkillDescriptors(code: string | undefined) {
  return useQuery({
    queryKey: curriculumKeys.descriptors(code ?? ''),
    queryFn: async () => (await curriculumApi.getDescriptors(code!)).descriptors,
    enabled: Boolean(code),
    staleTime: 60_000,
  });
}

export function useToggleSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ code, isEnabled }: { code: string; isEnabled: boolean }) =>
      curriculumApi.patchSkill(code, isEnabled),
    // Optimistic update so the toggle flips instantly — slow connections feel
    // snappy and we never show stale state mid-mutation.
    onMutate: async ({ code, isEnabled }) => {
      await qc.cancelQueries({ queryKey: curriculumKeys.skills() });
      const prev = qc.getQueryData<SkillRow[] | undefined>(
        curriculumKeys.skills(),
      );
      qc.setQueryData<SkillRow[] | undefined>(curriculumKeys.skills(), (rows) =>
        rows
          ? rows.map((s) =>
              s.code === code ? { ...s, is_enabled: isEnabled } : s,
            )
          : rows,
      );
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      // Roll back to the snapshot we took in onMutate.
      if (ctx?.prev) {
        qc.setQueryData(curriculumKeys.skills(), ctx.prev);
      }
    },
    onSuccess: (updated) => {
      // Replace the row with what the server returned — keeps `is_override`
      // and any computed fields accurate.
      qc.setQueryData<SkillRow[] | undefined>(
        curriculumKeys.skills(),
        (prev) =>
          prev ? prev.map((s) => (s.code === updated.code ? updated : s)) : prev,
      );
    },
    onSettled: () => {
      // Defensive: if the server response was somehow stale (or other clients
      // mutated in parallel), refetch in the background.
      void qc.invalidateQueries({ queryKey: curriculumKeys.skills() });
    },
  });
}

export function useSkillImpact(code: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: curriculumKeys.impact(code ?? ''),
    queryFn: () => curriculumApi.getImpact(code!),
    enabled: Boolean(code) && enabled,
    staleTime: 0, // always preflight fresh
  });
}

export function useRenameTier() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ code, patch }: { code: string; patch: TierNamesPatch }) =>
      curriculumApi.patchTier(code, patch),
    onSuccess: (updated) => {
      qc.setQueryData<Tier[] | undefined>(curriculumKeys.tiers(), (prev) =>
        prev ? prev.map((t) => (t.code === updated.code ? updated : t)) : prev,
      );
    },
  });
}

export function useSendFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (note: FeedbackNoteIn) => curriculumApi.sendFeedback(note),
    onSuccess: () => {
      // Coach doesn't see the inbox, so nothing to invalidate FE-side.  Admins
      // who happen to be looking at /feedback get a refresh.
      qc.invalidateQueries({ queryKey: curriculumKeys.inbox() });
    },
  });
}

export function useFeedbackInbox(enabled: boolean) {
  return useQuery({
    queryKey: curriculumKeys.inbox(),
    queryFn: () => curriculumApi.getInbox(),
    enabled,
    staleTime: 10_000,
  });
}

export function useMarkFeedbackRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => curriculumApi.markRead(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: curriculumKeys.inbox() });
    },
  });
}

export function useTierContext(code: string | undefined) {
  return useQuery({
    queryKey: curriculumKeys.tierContext(code ?? ''),
    queryFn: async () => (await curriculumApi.getTierContext(code!)).requirements,
    enabled: Boolean(code),
    staleTime: 60_000,
  });
}

export function useMyFeedback(enabled: boolean) {
  return useQuery({
    queryKey: curriculumKeys.myFeedback(),
    queryFn: () => curriculumApi.getMyFeedback(),
    enabled,
    staleTime: 10_000,
  });
}

// ── Helpers ───────────────────────────────────────────────────────

export function isPlanGateError(err: unknown): boolean {
  return err instanceof ApiError && err.status === 402;
}

export function isForbiddenError(err: unknown): boolean {
  return err instanceof ApiError && err.status === 403;
}
