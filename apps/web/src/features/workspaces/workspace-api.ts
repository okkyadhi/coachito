// Real workspace API. POST /workspaces returns a new JWT pair with wsid set,
// which the caller MUST swap into the auth store before navigating.
import { api } from '@/lib/api';

export interface WorkspaceSportBrief {
  sportId: string;
  sportCode: string;
  nameEn: string;
  nameId: string;
  curriculumId: string | null;
  curriculumCode: string | null;
  isActive: boolean;
}

export interface Workspace {
  id: string;
  sportId: string;
  /** Active sports offered by the workspace (multi-sport). */
  sports: WorkspaceSportBrief[];
  type: 'club' | 'personal';
  name: string;
  slug: string | null;
  city: string | null;
  brandColor: string | null;
  logoUrl: string | null;
  tierStyle: string;
  primaryLocale: string;
  plan: string;
  trialEndsAt: string | null;
  activeTraineeQuota: number;
  ownerUserId: string;
  createdAt: string;
  archivedAt: string | null;
}

export interface WorkspaceMembership {
  workspace: Workspace;
  role: string;
  status: string;
  joinedAt: string | null;
}

export interface TokenBundle {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  workspaceId: string;
}

export interface CreateWorkspaceInput {
  type: 'club' | 'personal';
  name: string;
  city?: string;
  brandColor?: string;
  primaryLocale: 'en' | 'id';
}

// ── Wire shapes (snake_case from the API) ────────────────────────

interface ApiWorkspaceSport {
  sport_id: string;
  sport_code: string;
  name_en: string;
  name_id: string;
  curriculum_id: string | null;
  curriculum_code: string | null;
  is_active: boolean;
}

interface ApiWorkspace {
  id: string;
  sport_id: string;
  sports?: ApiWorkspaceSport[];
  type: 'club' | 'personal';
  name: string;
  slug: string | null;
  city: string | null;
  brand_color: string | null;
  logo_url: string | null;
  tier_style: string;
  primary_locale: string;
  plan: string;
  trial_ends_at: string | null;
  active_trainee_quota: number;
  owner_user_id: string;
  created_at: string;
  archived_at: string | null;
}

interface ApiTokenBundle {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  workspace_id: string;
}

interface ApiCreateOut {
  workspace: ApiWorkspace;
  tokens: ApiTokenBundle;
}

interface ApiMembership {
  workspace: ApiWorkspace;
  role: string;
  status: string;
  joined_at: string | null;
}

function toWorkspace(w: ApiWorkspace): Workspace {
  return {
    id: w.id,
    sportId: w.sport_id,
    sports: (w.sports ?? []).map((s) => ({
      sportId: s.sport_id,
      sportCode: s.sport_code,
      nameEn: s.name_en,
      nameId: s.name_id,
      curriculumId: s.curriculum_id,
      curriculumCode: s.curriculum_code,
      isActive: s.is_active,
    })),
    type: w.type,
    name: w.name,
    slug: w.slug,
    city: w.city,
    brandColor: w.brand_color,
    logoUrl: w.logo_url,
    tierStyle: w.tier_style,
    primaryLocale: w.primary_locale,
    plan: w.plan,
    trialEndsAt: w.trial_ends_at,
    activeTraineeQuota: w.active_trainee_quota,
    ownerUserId: w.owner_user_id,
    createdAt: w.created_at,
    archivedAt: w.archived_at,
  };
}

function toTokens(t: ApiTokenBundle): TokenBundle {
  return {
    accessToken: t.access_token,
    refreshToken: t.refresh_token,
    expiresIn: t.expires_in,
    workspaceId: t.workspace_id,
  };
}

// ── API calls ────────────────────────────────────────────────────

export async function createWorkspace(
  input: CreateWorkspaceInput,
): Promise<{ workspace: Workspace; tokens: TokenBundle }> {
  const res = await api.post<ApiCreateOut>('/workspaces', {
    type: input.type,
    name: input.name,
    city: input.city,
    brand_color: input.brandColor,
    primary_locale: input.primaryLocale,
  });
  return { workspace: toWorkspace(res.workspace), tokens: toTokens(res.tokens) };
}

export async function listMyWorkspaces(): Promise<WorkspaceMembership[]> {
  const res = await api.get<{ workspaces: ApiMembership[] }>('/workspaces/mine');
  return res.workspaces.map((m) => ({
    workspace: toWorkspace(m.workspace),
    role: m.role,
    status: m.status,
    joinedAt: m.joined_at,
  }));
}

export async function switchWorkspace(workspaceId: string): Promise<TokenBundle> {
  const res = await api.post<ApiTokenBundle>(`/workspaces/${workspaceId}/switch`);
  return toTokens(res);
}
