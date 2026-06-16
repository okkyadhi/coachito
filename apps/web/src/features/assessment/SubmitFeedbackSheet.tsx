import { X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';
import { ApiError } from '@/lib/api';

import {
  type Feedback,
  editFeedback,
  submitFeedback,
} from './feedback-api';

interface Props {
  assessmentId: string;
  initial: Feedback | null;
  onClose: () => void;
  onSubmitted: () => void;
}

const RATING_LABELS = ['😞', '🙁', '😐', '🙂', '😄'];

export function SubmitFeedbackSheet({
  assessmentId,
  initial,
  onClose,
  onSubmitted,
}: Props) {
  const { t } = useTranslation();
  const [overall, setOverall] = useState<number>(initial?.ratingOverall ?? 0);
  const [fairness, setFairness] = useState<number | null>(
    initial?.ratingFairness ?? null,
  );
  const [comment, setComment] = useState<string>(initial?.comment ?? '');
  const [anonymous, setAnonymous] = useState(initial?.isAnonymous ?? false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (overall === 0) {
      setError(t('trainee.feedback.sheet.overallRequired'));
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const input = {
        ratingOverall: overall,
        ratingFairness: fairness,
        comment: comment.trim() || null,
        isAnonymous: anonymous,
      };
      if (initial) await editFeedback(initial.id, input);
      else await submitFeedback(assessmentId, input);
      onSubmitted();
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : t('trainee.feedback.sheet.genericError'),
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('trainee.feedback.sheet.title')}
      className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 sm:items-center"
    >
      <form
        onSubmit={submit}
        className="flex w-full max-w-md flex-col rounded-t-2xl bg-bg-primary sm:rounded-2xl"
      >
        <header className="flex items-center justify-between border-b-[0.5px] border-border-hairline px-4 py-3">
          <button
            type="button"
            onClick={onClose}
            aria-label={t('common.cancel')}
            className="flex size-9 items-center justify-center rounded-full text-text-color-secondary"
          >
            <X size={18} strokeWidth={1.75} aria-hidden />
          </button>
          <span className="text-h3 text-text-color-primary">
            {t('trainee.feedback.sheet.title')}
          </span>
          <span className="size-9" aria-hidden />
        </header>

        <div className="flex flex-col gap-4 p-4">
          <div className="flex flex-col gap-2">
            <span className="text-body text-text-color-primary">
              {t('trainee.feedback.sheet.overallLabel')}
            </span>
            <div className="flex justify-between gap-1">
              {RATING_LABELS.map((emoji, i) => {
                const value = i + 1;
                const selected = overall === value;
                return (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setOverall(value)}
                    className={
                      selected
                        ? 'bg-accent/10 flex-1 rounded-lg border-[0.5px] border-accent py-3 text-h2'
                        : 'flex-1 rounded-lg border-[0.5px] border-border-hairline bg-bg-primary py-3 text-h2 opacity-60'
                    }
                    aria-label={t(`trainee.feedback.sheet.rating.${value}`)}
                  >
                    {emoji}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <span className="text-body text-text-color-primary">
              {t('trainee.feedback.sheet.fairnessLabel')}
            </span>
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5].map((n) => {
                const selected = fairness === n;
                return (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setFairness(selected ? null : n)}
                    className={
                      selected
                        ? 'bg-accent/10 flex-1 rounded-full border-[0.5px] border-accent px-3 py-1 text-caption text-accent'
                        : 'flex-1 rounded-full border-[0.5px] border-border-hairline bg-bg-primary px-3 py-1 text-caption text-text-color-secondary'
                    }
                  >
                    {n}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label
              htmlFor="feedback-comment"
              className="text-body text-text-color-primary"
            >
              {t('trainee.feedback.sheet.commentLabel')}
            </label>
            <textarea
              id="feedback-comment"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              maxLength={500}
              rows={3}
              className="rounded-md border-[0.5px] border-border-hairline bg-bg-primary p-3 text-body text-text-color-primary"
            />
            <p className="text-right text-footnote text-text-color-tertiary">
              {comment.length}/500
            </p>
          </div>

          <label className="flex items-start gap-3">
            <input
              type="checkbox"
              checked={anonymous}
              onChange={(e) => setAnonymous(e.target.checked)}
              className="mt-1"
            />
            <span className="flex-1">
              <span className="block text-body text-text-color-primary">
                {t('trainee.feedback.sheet.anonymousLabel')}
              </span>
              <span className="block text-footnote text-text-color-tertiary">
                {t('trainee.feedback.sheet.anonymousHint')}
              </span>
            </span>
          </label>

          {error ? (
            <div className="rounded-md border-[0.5px] border-danger-text bg-danger-bg p-3">
              <p className="text-caption text-danger-text">{error}</p>
            </div>
          ) : null}
        </div>

        <footer className="flex flex-col gap-2 border-t-[0.5px] border-border-hairline px-4 py-3">
          <PrimaryButton type="submit" loading={loading}>
            {initial
              ? t('trainee.feedback.sheet.updateCta')
              : t('trainee.feedback.sheet.submitCta')}
          </PrimaryButton>
          <SecondaryButton type="button" onClick={onClose} disabled={loading}>
            {t('common.cancel')}
          </SecondaryButton>
        </footer>
      </form>
    </div>
  );
}
