// Single source of truth for "can this user edit the curriculum?".
//
// Solo coaches own their personal workspace → admin-equivalent.
// Club admins are admin.  Coaches/head_coaches are read-only.
// Plan gate: only club_pro / solo_coach / free_trial can mutate (Club
// Starter sees read-only + an upsell).

import { useQuery } from '@tanstack/react-query';

import { useAuthStore } from '@/features/auth/auth-store';
import { getMyWorkspace } from '@/features/settings/settings-api';

export interface CurriculumPerms {
  /** True when the user's role allows mutating curriculum (admin or owner). */
  canEditRole: boolean;
  /** True when the workspace plan allows mutating curriculum. */
  canEditPlan: boolean;
  /** True when both role and plan allow mutating — only this gates affordances. */
  canEdit: boolean;
  /** True when canEditRole but blocked by plan — show upsell rather than hide. */
  showPlanUpsell: boolean;
  /** True for coaches who can send feedback notes (i.e. not the owner). */
  canSendFeedback: boolean;
  /** Plan code, exposed so screens can render plan-specific copy. */
  plan: string | null;
  /** Loading state — settings hasn't hydrated yet. */
  isLoading: boolean;
}

const EDIT_PLANS = new Set(['club_pro', 'solo_coach', 'free_trial']);

export function useCurriculumPermissions(): CurriculumPerms {
  const role = useAuthStore((s) => s.user?.role ?? null);
  const currentWorkspaceId = useAuthStore((s) => s.currentWorkspaceId);
  const { data, isPending } = useQuery({
    queryKey: ['workspace-me', currentWorkspaceId],
    queryFn: getMyWorkspace,
    staleTime: 30_000,
  });

  const isOwner = data?.type === 'personal';
  const canEditRole = role === 'club_admin' || isOwner;
  const plan = data?.plan ?? null;
  const canEditPlan = plan !== null && EDIT_PLANS.has(plan);
  const canEdit = canEditRole && canEditPlan;
  // Coaches send feedback to admins; owners have no separate admin to ping.
  const canSendFeedback =
    !isOwner && (role === 'coach' || role === 'head_coach');

  return {
    canEditRole,
    canEditPlan,
    canEdit,
    showPlanUpsell: canEditRole && !canEditPlan,
    canSendFeedback,
    plan,
    isLoading: isPending,
  };
}
