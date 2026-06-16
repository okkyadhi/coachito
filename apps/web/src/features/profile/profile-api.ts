import { api } from '@/lib/api';

export interface NotificationsPrefs {
  sessionReminders: boolean;
  monthlyReport: boolean;
}

export interface ParentLink {
  id: string;
  displayName: string;
}

export type SummaryStyle = 'encouraging' | 'direct' | 'warm';

export interface MeProfile {
  id: string;
  email: string | null;
  displayName: string;
  avatarUrl: string | null;
  preferredLocale: 'en' | 'id';
  isMinor: boolean;
  dateOfBirth: string | null; // ISO YYYY-MM-DD
  primaryGuardian: ParentLink | null;
  notifications: NotificationsPrefs;
  summaryStyle: SummaryStyle;
}

interface ApiNotifications {
  session_reminders: boolean;
  monthly_report: boolean;
}

interface ApiParent {
  id: string;
  display_name: string;
}

interface ApiMe {
  id: string;
  email: string | null;
  display_name: string;
  avatar_url: string | null;
  preferred_locale: 'en' | 'id';
  is_minor: boolean;
  date_of_birth: string | null;
  primary_guardian: ApiParent | null;
  notifications: ApiNotifications;
  summary_style: SummaryStyle;
}

function fromApi(r: ApiMe): MeProfile {
  return {
    id: r.id,
    email: r.email,
    displayName: r.display_name,
    avatarUrl: r.avatar_url,
    preferredLocale: r.preferred_locale,
    isMinor: r.is_minor,
    dateOfBirth: r.date_of_birth,
    primaryGuardian: r.primary_guardian
      ? { id: r.primary_guardian.id, displayName: r.primary_guardian.display_name }
      : null,
    notifications: {
      sessionReminders: r.notifications.session_reminders,
      monthlyReport: r.notifications.monthly_report,
    },
    summaryStyle: r.summary_style,
  };
}

export async function getMe(): Promise<MeProfile> {
  return fromApi(await api.get<ApiMe>('/users/me'));
}

export interface MePatch {
  displayName?: string;
  avatarUrl?: string | null;
  preferredLocale?: 'en' | 'id';
  notifications?: Partial<{ sessionReminders: boolean; monthlyReport: boolean }>;
  summaryStyle?: SummaryStyle;
}

export async function patchMe(patch: MePatch): Promise<MeProfile> {
  const body: Record<string, unknown> = {};
  if (patch.displayName !== undefined) body.display_name = patch.displayName;
  if (patch.avatarUrl !== undefined) body.avatar_url = patch.avatarUrl;
  if (patch.preferredLocale !== undefined) body.preferred_locale = patch.preferredLocale;
  if (patch.summaryStyle !== undefined) body.summary_style = patch.summaryStyle;
  if (patch.notifications) {
    const n: Record<string, boolean> = {};
    if (patch.notifications.sessionReminders !== undefined)
      n.session_reminders = patch.notifications.sessionReminders;
    if (patch.notifications.monthlyReport !== undefined)
      n.monthly_report = patch.notifications.monthlyReport;
    body.notifications = n;
  }
  return fromApi(await api.patch<ApiMe>('/users/me', body));
}

// ── Avatar upload (presigned POST, mirrors LogoUploader) ─────────

interface PresignResponse {
  url: string;
  fields: Record<string, string>;
  public_url: string;
  key: string;
  expires_at: string;
}

const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/webp'] as const;
const MAX_BYTES = 2 * 1024 * 1024;

export async function uploadAvatar(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<string> {
  if (!(ALLOWED_TYPES as readonly string[]).includes(file.type)) {
    throw new Error('Image must be PNG, JPEG, or WebP.');
  }
  if (file.size > MAX_BYTES) {
    throw new Error(`Image must be under ${MAX_BYTES / 1024 / 1024}MB.`);
  }
  const presign = await api.post<PresignResponse>('/uploads/avatar/sign', {
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
    for (const [k, v] of Object.entries(presign.fields)) fd.append(k, v);
    fd.append('file', file);
    xhr.send(fd);
  });
  return presign.public_url;
}
