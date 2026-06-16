import { api } from '@/lib/api';

export type WorkspacePlan = 'free_trial' | 'solo_coach' | 'club_starter' | 'club_pro';
export type WorkspaceType = 'club' | 'personal';
export type BillingStatus = 'trial' | 'paid' | 'lapsed' | 'archived' | 'unknown';

export interface AdminWorkspaceRow {
  id: string;
  name: string;
  type: WorkspaceType;
  plan: WorkspacePlan;
  primary_locale: string;
  city: string | null;
  owner_email: string | null;
  owner_display_name: string;
  trial_ends_at: string | null;
  paid_until: string | null;
  archived_at: string | null;
  created_at: string;
  coach_count: number;
  trainee_count: number;
  last_session_at: string | null;
}

export interface AdminWorkspaceDetail extends AdminWorkspaceRow {
  brand_color: string | null;
  logo_url: string | null;
  tier_style: string;
  active_trainee_quota: number;
  sport_id: string | null;
  updated_at: string;
  billing_status: BillingStatus;
}

export interface AdminWorkspacesListOut {
  total: number;
  workspaces: AdminWorkspaceRow[];
}

export interface AdminWorkspacePatch {
  plan?: WorkspacePlan;
  trial_ends_at?: string | null;
  paid_until?: string | null;
  active_trainee_quota?: number;
  archived?: boolean;
}

export interface AdminUserRow {
  id: string;
  email: string | null;
  display_name: string;
  preferred_locale: string;
  created_at: string;
  last_seen_at: string | null;
  is_platform_admin: boolean;
  workspace_count: number;
  workspace_summary: string;
}

export interface AdminUsersListOut {
  total: number;
  users: AdminUserRow[];
}

export function listAdminWorkspaces(params?: {
  q?: string;
  plan?: string;
  type?: string;
  archived?: boolean;
  limit?: number;
  offset?: number;
}): Promise<AdminWorkspacesListOut> {
  const qs = new URLSearchParams();
  if (params?.q) qs.set('q', params.q);
  if (params?.plan) qs.set('plan', params.plan);
  if (params?.type) qs.set('type', params.type);
  if (params?.archived !== undefined) qs.set('archived', String(params.archived));
  if (params?.limit) qs.set('limit', String(params.limit));
  if (params?.offset) qs.set('offset', String(params.offset));
  return api.get<AdminWorkspacesListOut>(`/admin/workspaces${qs.size ? '?' + qs : ''}`);
}

export function getAdminWorkspace(id: string): Promise<AdminWorkspaceDetail> {
  return api.get<AdminWorkspaceDetail>(`/admin/workspaces/${id}`);
}

export function patchAdminWorkspace(id: string, body: AdminWorkspacePatch): Promise<AdminWorkspaceDetail> {
  return api.patch<AdminWorkspaceDetail>(`/admin/workspaces/${id}`, body);
}

export function listAdminUsers(params?: {
  q?: string;
  limit?: number;
  offset?: number;
}): Promise<AdminUsersListOut> {
  const qs = new URLSearchParams();
  if (params?.q) qs.set('q', params.q);
  if (params?.limit) qs.set('limit', String(params.limit));
  if (params?.offset) qs.set('offset', String(params.offset));
  return api.get<AdminUsersListOut>(`/admin/users${qs.size ? '?' + qs : ''}`);
}

export function resetAdminUserPassword(
  userId: string,
  newPassword: string,
): Promise<{ user_id: string; email: string | null }> {
  return api.post(`/admin/users/${userId}/reset-password`, { new_password: newPassword });
}
