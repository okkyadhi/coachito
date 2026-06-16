import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ChevronRight, MessageCircle, Sparkles } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { ConfirmSheet } from '@/components/ConfirmSheet';
import { PrimaryButton } from '@/components/PrimaryButton';
import { SubmitFeedbackSheet } from '@/features/assessment/SubmitFeedbackSheet';
import { api } from '@/lib/api';
import {
  type Feedback,
  listFeedbackForAssessment,
  withdrawFeedback,
} from '@/features/assessment/feedback-api';

interface ApiAssessmentLite {
  id: string;
  session_id: string;
  published_at: string | null;
  edited_at: string | null;
  status: string;
  coach_display_name: string | null;
  session_scheduled_at: string | null;
  session_focus: string | null;
}

async function fetchMyLatest(): Promise<ApiAssessmentLite | null> {
  return api.get<ApiAssessmentLite | null>('/assessments/mine/latest');
}

export function SessionFeedbackCard() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data: latest } = useQuery({
    queryKey: ['trainee-latest-assessment'],
    queryFn: fetchMyLatest,
  });

  const assessmentId = latest?.id ?? null;

  const { data: feedbacks } = useQuery({
    queryKey: ['feedback', assessmentId],
    queryFn: () => listFeedbackForAssessment(assessmentId!),
    enabled: !!assessmentId,
  });

  const mine = (feedbacks ?? []).find((f) => f.canEdit || f.canWithdraw);

  const [sheetOpen, setSheetOpen] = useState(false);
  const [confirmWithdraw, setConfirmWithdraw] = useState(false);

  const withdrawMut = useMutation({
    mutationFn: (id: string) => withdrawFeedback(id),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['feedback', assessmentId] }),
  });

  if (!assessmentId) return null;

  const sessionDate = latest?.session_scheduled_at;
  const dateLabel = sessionDate
    ? new Date(sessionDate).toLocaleDateString()
    : '';
  const coachName = latest?.coach_display_name ?? '';

  return (
    <section className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
      <header className="mb-2 flex items-center gap-2">
        <MessageCircle
          size={16}
          strokeWidth={1.75}
          aria-hidden
          className="text-accent"
        />
        <h3 className="text-h3 text-text-color-primary">
          {t('trainee.feedback.title')}
        </h3>
      </header>

      {/* Session context: coach + date */}
      <p className="text-footnote text-text-color-tertiary">
        {coachName
          ? t('trainee.feedback.context', { coach: coachName, date: dateLabel })
          : dateLabel}
      </p>

      {mine ? (
        <FeedbackSubmittedCard
          feedback={mine}
          onEdit={() => setSheetOpen(true)}
          onWithdraw={() => setConfirmWithdraw(true)}
        />
      ) : (
        <>
          <p className="mt-2 text-body text-text-color-secondary">
            {t('trainee.feedback.body', { date: dateLabel })}
          </p>
          <PrimaryButton
            type="button"
            onClick={() => setSheetOpen(true)}
            className="mt-3"
            leftIcon={<Sparkles size={16} strokeWidth={1.75} aria-hidden />}
          >
            {t('trainee.feedback.cta')}
          </PrimaryButton>
        </>
      )}

      {/* View session details */}
      <button
        type="button"
        onClick={() => navigate(`/my-sessions/${assessmentId}`)}
        className="mt-3 flex w-full items-center justify-between rounded-md border-[0.5px] border-border-hairline px-3 py-2 text-caption text-text-color-secondary"
      >
        <span>{t('trainee.feedback.viewSession')}</span>
        <ChevronRight size={14} strokeWidth={1.75} aria-hidden />
      </button>

      {sheetOpen ? (
        <SubmitFeedbackSheet
          assessmentId={assessmentId}
          initial={mine ?? null}
          onClose={() => setSheetOpen(false)}
          onSubmitted={() => {
            setSheetOpen(false);
            qc.invalidateQueries({ queryKey: ['feedback', assessmentId] });
          }}
        />
      ) : null}

      {confirmWithdraw && mine ? (
        <ConfirmSheet
          open
          title={t('trainee.feedback.withdraw.title')}
          description={t('trainee.feedback.withdraw.body')}
          confirmLabel={t('trainee.feedback.withdraw.confirm')}
          destructive
          onCancel={() => setConfirmWithdraw(false)}
          onConfirm={() => {
            withdrawMut.mutate(mine.id);
            setConfirmWithdraw(false);
          }}
        />
      ) : null}
    </section>
  );
}

function FeedbackSubmittedCard({
  feedback,
  onEdit,
  onWithdraw,
}: {
  feedback: Feedback;
  onEdit: () => void;
  onWithdraw: () => void;
}) {
  const { t } = useTranslation();
  return (
    <>
      <div className="flex items-center gap-2">
        <span className="text-h3 text-text-color-primary">
          {'★'.repeat(feedback.ratingOverall)}
          {'☆'.repeat(5 - feedback.ratingOverall)}
        </span>
        {feedback.isAnonymous ? (
          <span className="text-footnote text-text-color-tertiary">
            {t('trainee.feedback.sharedAnon')}
          </span>
        ) : null}
      </div>
      {feedback.comment ? (
        <p className="mt-1 text-body text-text-color-secondary">
          “{feedback.comment}”
        </p>
      ) : null}
      <div className="mt-3 flex gap-3">
        {feedback.canEdit ? (
          <button
            type="button"
            onClick={onEdit}
            className="text-caption text-accent"
          >
            {t('trainee.feedback.edit')}
          </button>
        ) : null}
        {feedback.canWithdraw ? (
          <button
            type="button"
            onClick={onWithdraw}
            className="text-caption text-danger-text"
          >
            {t('trainee.feedback.withdraw.cta')}
          </button>
        ) : null}
      </div>
    </>
  );
}
