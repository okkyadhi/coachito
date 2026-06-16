import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ChevronLeft, Clock, MapPin, Sparkles, User } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

import { useAuthStore } from '@/features/auth/auth-store';
import {
  type AssessmentScore,
  getAssessment,
  markAssessmentViewed,
} from '@/features/assessment/assessment-api';
import {
  type Feedback,
  listFeedbackForAssessment,
} from '@/features/assessment/feedback-api';
import { SubmitFeedbackSheet } from '@/features/assessment/SubmitFeedbackSheet';
import { listSkills } from '@/features/assessment/skills-api';

export function TraineeSessionDetailScreen() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const qc = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const locale = user?.preferredLocale ?? i18n.language ?? 'en';

  const { data: assessment, isPending } = useQuery({
    queryKey: ['trainee-assessment', assessmentId],
    queryFn: () => getAssessment(assessmentId!),
    enabled: !!assessmentId,
  });

  const { data: skills } = useQuery({
    queryKey: ['skills'],
    queryFn: () => listSkills(),
    staleTime: 60 * 60 * 1000,
  });

  const { data: feedbacks } = useQuery({
    queryKey: ['feedback', assessmentId],
    queryFn: () => listFeedbackForAssessment(assessmentId!),
    enabled: !!assessmentId,
  });

  const [sheetOpen, setSheetOpen] = useState(false);

  // Fire-and-forget read-receipt the first time the trainee opens this
  // detail.  Idempotent server-side; we ignore failures.
  useEffect(() => {
    if (!assessmentId) return;
    void markAssessmentViewed(assessmentId).catch(() => {
      /* non-blocking */
    });
  }, [assessmentId]);

  if (isPending || !assessment || !skills) {
    return (
      <div className="mx-auto flex w-full max-w-md flex-col gap-4 px-4 pt-6">
        <div className="h-6 w-32 rounded bg-bg-primary" />
        <div className="h-40 rounded-xl bg-bg-primary" />
      </div>
    );
  }

  const skillById = Object.fromEntries(skills.map((s) => [s.id, s]));
  const groups: Record<string, AssessmentScore[]> = {
    technical: [],
    tactical: [],
    physical: [],
    mental: [],
  };
  for (const s of assessment.scores) {
    const def = skillById[s.skillId];
    if (def) groups[def.category]?.push(s);
  }

  const sessionDate = assessment.session_scheduled_at as unknown as
    | string
    | undefined;
  const dateLabel = sessionDate
    ? new Date(sessionDate).toLocaleString(locale, {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '';

  const mine = (feedbacks ?? []).find((f) => f.canEdit || f.canWithdraw);

  return (
    <main className="mx-auto flex w-full max-w-md flex-col gap-5 px-4 pb-8 pt-3">
      <header className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => navigate(-1)}
          aria-label={t('common.back')}
          className="flex size-9 items-center justify-center rounded-full text-text-color-secondary"
        >
          <ChevronLeft size={18} strokeWidth={1.75} aria-hidden />
        </button>
        <h1 className="text-h2 text-text-color-primary">
          {t('traineeSession.title')}
        </h1>
      </header>

      {/* Session meta */}
      <section className="flex flex-col gap-2 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
        <p className="text-h3 text-text-color-primary">{dateLabel}</p>
        <div className="mt-1 flex flex-wrap gap-3 text-caption text-text-color-secondary">
          <span className="inline-flex items-center gap-1">
            <User size={14} strokeWidth={1.75} aria-hidden />
            {assessment.coach_display_name ?? '—'}
          </span>
          {assessment.session_duration_min ? (
            <span className="inline-flex items-center gap-1">
              <Clock size={14} strokeWidth={1.75} aria-hidden />
              {t('traineeSession.minutes', {
                count: assessment.session_duration_min,
              })}
            </span>
          ) : null}
          {assessment.session_court ? (
            <span className="inline-flex items-center gap-1">
              <MapPin size={14} strokeWidth={1.75} aria-hidden />
              {assessment.session_court}
            </span>
          ) : null}
          {assessment.session_focus ? (
            <span className="rounded-full bg-accent-bg px-2 py-0.5 text-pill text-accent">
              {t(`sessionFocus.${assessment.session_focus}`)}
            </span>
          ) : null}
        </div>
        {assessment.status === 'edited' ? (
          <p className="mt-1 text-footnote text-text-color-tertiary">
            {t('traineeSession.editedNote')}
          </p>
        ) : null}
      </section>

      {/* Coach summary */}
      {assessment.summary ? (
        <section className="flex flex-col gap-2">
          <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
            {t('traineeSession.coachNote', {
              coach: assessment.coach_display_name ?? '',
            })}
          </h3>
          <div className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
            <p className="text-body leading-relaxed text-text-color-primary">
              {assessment.summary}
            </p>
          </div>
        </section>
      ) : null}

      {/* Skills */}
      {assessment.scores.length > 0 ? (
        <section className="flex flex-col gap-2">
          <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
            {t('traineeSession.scoredSkills', {
              count: assessment.scores.length,
            })}
          </h3>
          <div className="flex flex-col gap-3">
            {(['technical', 'tactical', 'physical', 'mental'] as const).map(
              (cat) =>
                groups[cat] && groups[cat].length > 0 ? (
                  <SkillGroup
                    key={cat}
                    category={cat}
                    rows={groups[cat]}
                    skillById={skillById}
                  />
                ) : null,
            )}
          </div>
        </section>
      ) : (
        <p className="px-1 text-caption text-text-color-tertiary">
          {t('traineeSession.noScores')}
        </p>
      )}

      {/* Feedback */}
      <section className="flex flex-col gap-2">
        <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
          {t('trainee.feedback.title')}
        </h3>
        <div className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
          {mine ? (
            <FeedbackRecap feedback={mine} onEdit={() => setSheetOpen(true)} />
          ) : (
            <>
              <p className="text-body text-text-color-secondary">
                {t('trainee.feedback.body', { date: dateLabel })}
              </p>
              <button
                type="button"
                onClick={() => setSheetOpen(true)}
                className="mt-3 inline-flex min-h-tap items-center gap-2 rounded-md bg-accent px-4 py-2 text-[14px] font-medium text-white"
              >
                <Sparkles size={16} strokeWidth={1.75} aria-hidden />
                {t('trainee.feedback.cta')}
              </button>
            </>
          )}
        </div>
      </section>

      {sheetOpen ? (
        <SubmitFeedbackSheet
          assessmentId={assessment.id}
          initial={mine ?? null}
          onClose={() => setSheetOpen(false)}
          onSubmitted={() => {
            setSheetOpen(false);
            qc.invalidateQueries({ queryKey: ['feedback', assessment.id] });
            qc.invalidateQueries({ queryKey: ['trainee-assessment-list'] });
          }}
        />
      ) : null}
    </main>
  );
}

interface SkillGroupProps {
  category: 'technical' | 'tactical' | 'physical' | 'mental';
  rows: AssessmentScore[];
  skillById: Record<
    string,
    { id: string; code: string; nameEn: string; nameId: string }
  >;
}

function SkillGroup({ category, rows, skillById }: SkillGroupProps) {
  const { t, i18n } = useTranslation();
  return (
    <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
      <header className="border-b-[0.5px] border-border-hairline bg-bg-secondary px-4 py-2">
        <span className="text-section uppercase tracking-wide text-text-color-secondary">
          {t(`category.${category}`)}
        </span>
      </header>
      {rows.map((r) => {
        const def = skillById[r.skillId];
        const name =
          def && i18n.language === 'id' ? def.nameId : (def?.nameEn ?? '—');
        return (
          <div
            key={r.skillId}
            className="flex items-center gap-3 border-t-[0.5px] border-border-hairline p-3 first:border-t-0"
          >
            <span className="flex-1 text-body text-text-color-primary">
              {name}
            </span>
            <span className="bg-accent/10 flex size-7 items-center justify-center rounded-full text-caption font-medium text-accent">
              {r.level}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function FeedbackRecap({
  feedback,
  onEdit,
}: {
  feedback: Feedback;
  onEdit: () => void;
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
        <p className="mt-1 text-body italic text-text-color-secondary">
          “{feedback.comment}”
        </p>
      ) : null}
      {feedback.canEdit ? (
        <button
          type="button"
          onClick={onEdit}
          className="mt-2 text-caption text-accent"
        >
          {t('trainee.feedback.edit')}
        </button>
      ) : null}
    </>
  );
}
