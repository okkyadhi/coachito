// Today screen "empty day" surfaces: this-week stats + recent activity.
// Backed by GET /coaches/me/today-extras.

import { api } from '@/lib/api';

export type ActivityKind =
  | 'assessment_published'
  | 'session_coached'
  | 'report_generated'
  | 'trainee_joined';

export interface WeekStats {
  sessions: number;
  hoursCoached: number;
  assessmentsPublished: number;
  traineesCoached: number;
}

export interface ActivityItem {
  id: string;
  kind: ActivityKind;
  traineeName: string | null;
  detail: string | null;
  occurredAt: string;
}

export interface TodayExtras {
  weekStats: WeekStats;
  recentActivity: ActivityItem[];
}

interface ApiWeekStats {
  sessions: number;
  hours_coached: number;
  assessments_published: number;
  trainees_coached: number;
}

interface ApiActivityItem {
  id: string;
  kind: ActivityKind;
  trainee_name: string | null;
  detail: string | null;
  occurred_at: string;
}

interface ApiTodayExtras {
  week_stats: ApiWeekStats;
  recent_activity: ApiActivityItem[];
}

export async function fetchTodayExtras(): Promise<TodayExtras> {
  const res = await api.get<ApiTodayExtras>('/coaches/me/today-extras');
  return {
    weekStats: {
      sessions: res.week_stats.sessions,
      hoursCoached: res.week_stats.hours_coached,
      assessmentsPublished: res.week_stats.assessments_published,
      traineesCoached: res.week_stats.trainees_coached,
    },
    recentActivity: res.recent_activity.map((a) => ({
      id: a.id,
      kind: a.kind,
      traineeName: a.trainee_name,
      detail: a.detail,
      occurredAt: a.occurred_at,
    })),
  };
}
