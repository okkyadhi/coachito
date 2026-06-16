// Trainee feedback API client (assessment v2).

import { api } from '@/lib/api';

export type SubmitterRole = 'trainee' | 'parent';

export interface Feedback {
  id: string;
  assessmentId: string;
  submitterRole: SubmitterRole;
  submitterDisplayName: string | null;
  isAnonymous: boolean;
  ratingOverall: number;
  ratingFairness: number | null;
  comment: string | null;
  submittedAt: string;
  editedAt: string | null;
  readAt: string | null;
  canEdit: boolean;
  canWithdraw: boolean;
}

export interface FeedbackInboxItem {
  id: string;
  assessmentId: string;
  athleteDisplayName: string | null;
  submitterRole: SubmitterRole;
  isAnonymous: boolean;
  ratingOverall: number;
  ratingFairness: number | null;
  comment: string | null;
  submittedAt: string;
  readAt: string | null;
  sessionScheduledAt: string | null;
  sessionFocus: string | null;
}

interface ApiFeedback {
  id: string;
  assessment_id: string;
  submitter_role: SubmitterRole;
  submitter_display_name: string | null;
  is_anonymous: boolean;
  rating_overall: number;
  rating_fairness: number | null;
  comment: string | null;
  submitted_at: string;
  edited_at: string | null;
  read_at: string | null;
  can_edit: boolean;
  can_withdraw: boolean;
}

interface ApiInboxItem {
  id: string;
  assessment_id: string;
  athlete_display_name: string | null;
  submitter_role: SubmitterRole;
  is_anonymous: boolean;
  rating_overall: number;
  rating_fairness: number | null;
  comment: string | null;
  submitted_at: string;
  read_at: string | null;
  session_scheduled_at: string | null;
  session_focus: string | null;
}

function toFeedback(f: ApiFeedback): Feedback {
  return {
    id: f.id,
    assessmentId: f.assessment_id,
    submitterRole: f.submitter_role,
    submitterDisplayName: f.submitter_display_name,
    isAnonymous: f.is_anonymous,
    ratingOverall: f.rating_overall,
    ratingFairness: f.rating_fairness,
    comment: f.comment,
    submittedAt: f.submitted_at,
    editedAt: f.edited_at,
    readAt: f.read_at,
    canEdit: f.can_edit,
    canWithdraw: f.can_withdraw,
  };
}

function toInbox(i: ApiInboxItem): FeedbackInboxItem {
  return {
    id: i.id,
    assessmentId: i.assessment_id,
    athleteDisplayName: i.athlete_display_name,
    submitterRole: i.submitter_role,
    isAnonymous: i.is_anonymous,
    ratingOverall: i.rating_overall,
    ratingFairness: i.rating_fairness,
    comment: i.comment,
    submittedAt: i.submitted_at,
    readAt: i.read_at,
    sessionScheduledAt: i.session_scheduled_at,
    sessionFocus: i.session_focus,
  };
}

export interface SubmitFeedbackInput {
  ratingOverall: number;
  ratingFairness?: number | null;
  comment?: string | null;
  isAnonymous?: boolean;
}

export async function submitFeedback(
  assessmentId: string,
  input: SubmitFeedbackInput,
): Promise<Feedback> {
  const r = await api.post<ApiFeedback>(
    `/assessments/${assessmentId}/feedback`,
    {
      rating_overall: input.ratingOverall,
      rating_fairness: input.ratingFairness ?? null,
      comment: input.comment ?? null,
      is_anonymous: input.isAnonymous ?? false,
    },
  );
  return toFeedback(r);
}

export async function listFeedbackForAssessment(
  assessmentId: string,
): Promise<Feedback[]> {
  const r = await api.get<ApiFeedback[]>(
    `/assessments/${assessmentId}/feedback`,
  );
  return r.map(toFeedback);
}

export async function editFeedback(
  id: string,
  input: SubmitFeedbackInput,
): Promise<Feedback> {
  const r = await api.patch<ApiFeedback>(`/feedback/${id}`, {
    rating_overall: input.ratingOverall,
    rating_fairness: input.ratingFairness ?? null,
    comment: input.comment ?? null,
    is_anonymous: input.isAnonymous ?? false,
  });
  return toFeedback(r);
}

export async function withdrawFeedback(id: string): Promise<void> {
  await api.del(`/feedback/${id}`);
}

export async function markFeedbackRead(id: string): Promise<Feedback> {
  const r = await api.post<ApiFeedback>(`/feedback/${id}/read`);
  return toFeedback(r);
}

export async function getFeedbackInbox(): Promise<FeedbackInboxItem[]> {
  const r = await api.get<ApiInboxItem[]>(`/feedback/inbox`);
  return r.map(toInbox);
}
