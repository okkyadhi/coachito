import { api } from '@/lib/api';

export interface TraineeReport {
  id: string;
  periodStart: string; // YYYY-MM-DD
  periodEnd: string;
  isSessionReport: boolean;
  generatedAt: string; // ISO
  pdfUrl: string;
  viewCount: number;
  coachDisplayName: string;
}

interface ApiReport {
  id: string;
  period_start: string;
  period_end: string;
  is_session_report: boolean;
  generated_at: string;
  pdf_url: string;
  view_count: number;
  coach_display_name: string;
}

interface ApiList {
  reports: ApiReport[];
}

export async function fetchMyReports(): Promise<TraineeReport[]> {
  const r = await api.get<ApiList>('/trainees/me/reports');
  return r.reports.map((x) => ({
    id: x.id,
    periodStart: x.period_start,
    periodEnd: x.period_end,
    isSessionReport: x.is_session_report,
    generatedAt: x.generated_at,
    pdfUrl: x.pdf_url,
    viewCount: x.view_count,
    coachDisplayName: x.coach_display_name,
  }));
}
