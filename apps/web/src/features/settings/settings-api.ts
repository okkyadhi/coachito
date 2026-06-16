// Workspace settings data layer.
//
// PATCH /workspaces/me and POST /uploads/logo/sign are real (Step 16 BE).
// `getMyWorkspace` still reads via GET /workspaces/mine so we don't need a
// dedicated /workspaces/me GET — the picker just filters to the active row.

import { useAuthStore } from '@/features/auth/auth-store';
import { api } from '@/lib/api';

export type TierStyle = 'game' | 'skill' | 'custom';
export type WorkspaceType = 'club' | 'personal';
export type Plan = 'free_trial' | 'solo_coach' | 'club_starter' | 'club_pro';

export interface WorkspaceSettings {
  id: string;
  type: WorkspaceType;
  name: string;
  city: string | null;
  brandColor: string | null; // 7-char hex, null → default accent
  logoUrl: string | null;
  tierStyle: TierStyle;
  primaryLocale: 'en' | 'id';
  plan: Plan;
  allowCoachOverrides: boolean;
  curriculumId: string | null;
  curriculumName: string; // resolved label (currently a static placeholder)
  coachCount: number;
  traineeCount: number;
  renewsAt: string | null; // ISO date
}

interface ApiWorkspace {
  id: string;
  type: string;
  name: string;
  slug: string | null;
  city: string | null;
  brand_color: string | null;
  logo_url: string | null;
  tier_style: string;
  primary_locale: string;
  plan: string;
  active_trainee_quota: number;
  trial_ends_at: string | null;
}

interface ApiMineRow {
  workspace: ApiWorkspace;
  role: string;
  status: string;
}

interface ApiMineList {
  workspaces: ApiMineRow[];
}

function toSettings(ws: ApiWorkspace): WorkspaceSettings {
  return {
    id: ws.id,
    type: ws.type === 'personal' ? 'personal' : 'club',
    name: ws.name,
    city: ws.city,
    brandColor: ws.brand_color,
    logoUrl: ws.logo_url,
    tierStyle: (ws.tier_style as TierStyle) ?? 'game',
    primaryLocale: ws.primary_locale === 'en' ? 'en' : 'id',
    plan: (ws.plan as Plan) ?? 'free_trial',
    // BE doesn't expose these yet — Step 16 ships PATCH + the missing fields.
    allowCoachOverrides: false,
    curriculumId: null,
    curriculumName: 'APPA padel · v1',
    coachCount: 0,
    traineeCount: 0,
    renewsAt: ws.trial_ends_at,
  };
}

interface ApiMemberCounts {
  coach_count: number;
  trainee_count: number;
}

export async function getMyWorkspace(): Promise<WorkspaceSettings | null> {
  const list = await api.get<ApiMineList>('/workspaces/mine');
  // Pick the membership for the currently-active workspace — not just the
  // first active one.  Without this, a hybrid coach who switches workspaces
  // would still see the old workspace's settings here.
  const currentId = useAuthStore.getState().currentWorkspaceId;
  const match = currentId
    ? list.workspaces.find(
        (r) => r.status === 'active' && r.workspace.id === currentId,
      )
    : null;
  const active = match ?? list.workspaces.find((r) => r.status === 'active');
  if (!active) return null;
  const base = toSettings(active.workspace);
  // Real counts come from the members endpoint; non-admins still see them.
  try {
    const counts = await api.get<ApiMemberCounts>('/workspaces/me/members');
    base.coachCount = counts.coach_count;
    base.traineeCount = counts.trainee_count;
  } catch {
    // Non-member or transient — leave at 0.
  }
  return base;
}

// ── PATCH /workspaces/me ──────────────────────────────────────────

export interface WorkspacePatch {
  name?: string;
  city?: string | null;
  brand_color?: string | null;
  logo_url?: string | null;
  tier_style?: TierStyle;
  allow_coach_overrides?: boolean;
  curriculum_id?: string | null;
}

interface ApiWorkspaceSettings {
  id: string;
  type: string;
  name: string;
  city: string | null;
  brand_color: string | null;
  logo_url: string | null;
  tier_style: string;
  allow_coach_overrides: boolean;
  curriculum_id: string | null;
  plan: string;
  primary_locale: string;
}

export async function patchMyWorkspace(
  current: WorkspaceSettings,
  patch: WorkspacePatch,
): Promise<WorkspaceSettings> {
  const updated = await api.patch<ApiWorkspaceSettings>('/workspaces/me', patch);
  return {
    ...current,
    id: updated.id,
    type: updated.type === 'personal' ? 'personal' : 'club',
    name: updated.name,
    city: updated.city,
    brandColor: updated.brand_color,
    logoUrl: updated.logo_url,
    tierStyle: (updated.tier_style as TierStyle) ?? current.tierStyle,
    allowCoachOverrides: updated.allow_coach_overrides,
    curriculumId: updated.curriculum_id,
    plan: (updated.plan as Plan) ?? current.plan,
    primaryLocale: updated.primary_locale === 'en' ? 'en' : 'id',
  };
}

// ── Logo upload (real S3 presigned POST) ──────────────────────────
//
// 1. POST /uploads/logo/sign  → policy { url, fields, public_url }
// 2. POST FormData(...fields, file) to policy.url
// 3. Caller PATCH /workspaces/me with public_url as logo_url.
//
// We track progress via XMLHttpRequest because fetch doesn't expose upload
// progress events.  Bucket policy makes the public_url anonymously
// downloadable.

interface PresignResponse {
  url: string;
  fields: Record<string, string>;
  public_url: string;
  key: string;
  expires_at: string;
}

const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/webp'] as const;
const MAX_BYTES = 2 * 1024 * 1024;

export async function uploadLogo(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<string> {
  if (!(ALLOWED_TYPES as readonly string[]).includes(file.type)) {
    throw new Error('Image must be PNG, JPEG, or WebP.');
  }
  if (file.size > MAX_BYTES) {
    throw new Error(`Image must be under ${MAX_BYTES / 1024 / 1024}MB.`);
  }

  const presign = await api.post<PresignResponse>('/uploads/logo/sign', {
    content_type: file.type,
    content_length: file.size,
  });

  await new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', presign.url);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else reject(new Error(`Upload failed (${xhr.status}).`));
    };
    xhr.onerror = () => reject(new Error('Network error during upload.'));
    const fd = new FormData();
    for (const [k, v] of Object.entries(presign.fields)) {
      fd.append(k, v);
    }
    fd.append('file', file);
    xhr.send(fd);
  });

  return presign.public_url;
}
