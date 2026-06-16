// Reports data layer.  Real GET /reports + POST /reports + GET /reports/:id
// (BE step 18).  Generation is async on the server — the FE polls the list
// every few seconds while at least one row is still generating.

import { api } from '@/lib/api';

export type ReportStatus = 'pending' | 'generating' | 'completed' | 'failed';

export interface Report {
  id: string;
  traineeId: string;
  traineeName: string;
  periodStart: string;
  periodEnd: string;
  status: ReportStatus;
  generatedAt: string | null;
  viewCount: number;
  pdfUrl: string | null;
}

interface ApiReport {
  id: string;
  athlete_id: string;
  trainee_name: string;
  period_start: string;
  period_end: string;
  status: ReportStatus;
  generated_at: string | null;
  view_count: number;
  pdf_url: string | null;
}

interface ApiList {
  reports: ApiReport[];
}

interface ApiCreateOut {
  report: ApiReport;
  job_id: string;
}

function toReport(r: ApiReport): Report {
  return {
    id: r.id,
    traineeId: r.athlete_id,
    traineeName: r.trainee_name,
    periodStart: r.period_start,
    periodEnd: r.period_end,
    status: r.status,
    generatedAt: r.generated_at,
    viewCount: r.view_count,
    pdfUrl: r.pdf_url,
  };
}

export async function listReports(): Promise<Report[]> {
  const res = await api.get<ApiList>('/reports');
  return res.reports.map(toReport);
}

export interface GenerateReportInput {
  traineeId: string;
  // Provide exactly one of: (periodStart + periodEnd) for monthly, or
  // sessionId for a single-session report.  The BE derives the period from
  // sessions.scheduled_at when sessionId is set.
  sessionId?: string;
  periodStart?: string;
  periodEnd?: string;
}

export async function generateReport(input: GenerateReportInput): Promise<Report> {
  const body: Record<string, string> = { athlete_id: input.traineeId };
  if (input.sessionId) body.session_id = input.sessionId;
  if (input.periodStart) body.period_start = input.periodStart;
  if (input.periodEnd) body.period_end = input.periodEnd;
  const res = await api.post<ApiCreateOut>('/reports', body);
  return toReport(res.report);
}

// ── Per-trainee sessions (for the picker) ─────────────────────

export interface TraineeSession {
  id: string;
  scheduledAt: string;
  durationMin: number;
  court: string | null;
  focus: string | null;
  status: string;
}

interface ApiSession {
  id: string;
  scheduled_at: string;
  duration_min: number;
  court: string | null;
  focus: string | null;
  status: string;
}

interface ApiSessionsList {
  sessions: ApiSession[];
}

export async function listTraineeSessions(
  traineeId: string,
): Promise<TraineeSession[]> {
  const res = await api.get<ApiSessionsList>(
    `/trainees/${encodeURIComponent(traineeId)}/sessions`,
  );
  return res.sessions.map((s) => ({
    id: s.id,
    scheduledAt: s.scheduled_at,
    durationMin: s.duration_min,
    court: s.court,
    focus: s.focus,
    status: s.status,
  }));
}

export async function incrementViewCount(id: string): Promise<void> {
  await api.post(`/reports/${id}/view`);
}

/** True when at least one row is still in flight — the UI uses this to
 *  decide whether to keep polling. */
export function anyPending(reports: Report[]): boolean {
  return reports.some((r) => r.status === 'pending' || r.status === 'generating');
}
