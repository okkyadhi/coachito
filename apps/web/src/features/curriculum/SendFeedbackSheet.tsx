// Coach feedback to admin.  Simple textarea + send.  No threading (V1).
// Reusable in two places: from a skill detail (subject pre-filled) or
// general "Send feedback" from the curriculum list.

import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';
import { ApiError } from '@/lib/api';

import { useSendFeedback } from './curriculum-api';

interface Props {
  subjectSkillId?: string | null;
  subjectSkillName?: string;
  open: boolean;
  onClose: () => void;
}

export function SendFeedbackSheet({
  subjectSkillId,
  subjectSkillName,
  open,
  onClose,
}: Props) {
  const { t } = useTranslation();
  const send = useSendFeedback();
  const [body, setBody] = useState('');
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const submit = () => {
    setError(null);
    if (body.trim().length === 0) return;
    send.mutate(
      { skill_id: subjectSkillId ?? null, body: body.trim() },
      {
        onSuccess: () => {
          setSent(true);
          setBody('');
          // Auto-close after a short delay so the user sees the confirmation.
          window.setTimeout(onClose, 1200);
        },
        onError: (e) =>
          setError(
            e instanceof ApiError
              ? e.message
              : t('settings.curriculum.feedback.error'),
          ),
      },
    );
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex w-full max-w-md flex-col gap-3 rounded-t-2xl bg-bg-primary p-4 sm:rounded-2xl"
      >
        <h3 className="text-h3 text-text-color-primary">
          {subjectSkillName
            ? t('settings.curriculum.feedback.titleAbout', {
                skill: subjectSkillName,
              })
            : t('settings.curriculum.feedback.title')}
        </h3>

        {sent ? (
          <p className="text-body text-success-text">
            {t('settings.curriculum.feedback.sent')}
          </p>
        ) : (
          <>
            <textarea
              autoFocus
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder={t('settings.curriculum.feedback.placeholder')}
              rows={5}
              maxLength={2000}
              className="rounded-md border-[0.5px] border-border-hairline bg-bg-primary p-3 text-body text-text-color-primary placeholder:text-text-color-tertiary focus:border-accent focus:outline-none"
            />
            <p className="text-footnote text-text-color-tertiary">
              {t('settings.curriculum.feedback.hint')}
            </p>
            {error ? (
              <p role="alert" className="text-footnote text-danger-text">
                {error}
              </p>
            ) : null}
            <div className="mt-1 flex flex-col gap-2">
              <PrimaryButton
                onClick={submit}
                loading={send.isPending}
                disabled={body.trim().length === 0}
              >
                {t('settings.curriculum.feedback.submit')}
              </PrimaryButton>
              <SecondaryButton onClick={onClose}>
                {t('common.cancel')}
              </SecondaryButton>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
