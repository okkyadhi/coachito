import { api } from '@/lib/api';

export type NotificationKind =
  | 'session_scheduled'
  | 'assessment_published'
  | 'report_ready'
  | 'coach_note';

export interface NotificationItem {
  id: string;
  kind: NotificationKind;
  coachName: string | null;
  body: string | null;
  occurredAt: string;
  link: string | null;
}

interface ApiItem {
  id: string;
  kind: NotificationKind;
  coach_name: string | null;
  body: string | null;
  occurred_at: string;
  link: string | null;
}

interface ApiList {
  items: ApiItem[];
}

export async function fetchMyNotifications(): Promise<NotificationItem[]> {
  const r = await api.get<ApiList>('/trainees/me/notifications');
  return r.items.map((i) => ({
    id: i.id,
    kind: i.kind,
    coachName: i.coach_name,
    body: i.body,
    occurredAt: i.occurred_at,
    link: i.link,
  }));
}

// ── Read-state (client-side) ─────────────────────────────────────
//
// The BE has no notifications table, so "unread" means "occurred after
// the last time the user opened the sheet" — kept in localStorage,
// per-user so a shared browser doesn't leak state.

const LAST_SEEN_PREFIX = 'racademy:notif_last_seen:';

export function getLastSeenAt(userId: string | null): number {
  if (!userId) return 0;
  const raw = localStorage.getItem(LAST_SEEN_PREFIX + userId);
  if (!raw) return 0;
  const n = Number(raw);
  return Number.isFinite(n) ? n : 0;
}

export function setLastSeenAt(userId: string | null, ts: number): void {
  if (!userId) return;
  localStorage.setItem(LAST_SEEN_PREFIX + userId, String(ts));
}

export function unreadCount(
  items: NotificationItem[],
  lastSeenAt: number,
): number {
  if (lastSeenAt <= 0) return items.length;
  return items.filter((i) => new Date(i.occurredAt).getTime() > lastSeenAt)
    .length;
}
