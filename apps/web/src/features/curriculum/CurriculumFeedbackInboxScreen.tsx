// Admin inbox for curriculum feedback notes from coaches.
//
// Unread first, then newest.  Tap a note to mark read (idempotent on the BE).
// Empty state is meaningful for a fresh club — "no feedback yet" tells the
// admin the channel is live but nobody's used it.

import { ChevronLeft } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import {
  useFeedbackInbox,
  useMarkFeedbackRead,
} from './curriculum-api';
import { useCurriculumPermissions } from './use-curriculum-permissions';

export function CurriculumFeedbackInboxScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const perms = useCurriculumPermissions();
  const { data, isPending } = useFeedbackInbox(perms.canEditRole);
  const markRead = useMarkFeedbackRead();

  if (!perms.canEditRole && !perms.isLoading) {
    // Defense in depth — the route isn't exposed to coaches, but if they
    // navigate here directly we shouldn't 500.
    return (
      <div className="mx-auto w-full max-w-md px-4 pt-6">
        <p className="text-body text-text-color-secondary">
          {t('settings.curriculum.feedback.adminOnly')}
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-md px-4 pb-8 pt-3">
      <header className="mb-4 flex items-center gap-2">
        <button
          type="button"
          onClick={() => navigate('/settings')}
          className="flex min-h-tap min-w-tap items-center text-accent"
          aria-label={t('common.back')}
        >
          <ChevronLeft size={20} strokeWidth={1.75} aria-hidden />
          <span className="text-body">{t('nav.settings')}</span>
        </button>
        <h1 className="ml-2 flex-1 text-large-title text-text-color-primary">
          {t('settings.curriculum.feedback.inboxTitle')}
        </h1>
      </header>

      {isPending ? (
        <div className="rounded-xl bg-bg-primary p-4 text-body text-text-color-tertiary">
          {t('common.loading')}
        </div>
      ) : data && data.notes.length > 0 ? (
        <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
          {data.notes.map((note) => {
            const unread = note.read_at === null;
            return (
              <button
                key={note.id}
                type="button"
                onClick={() => unread && markRead.mutate(note.id)}
                className="flex w-full flex-col gap-1 border-t-[0.5px] border-border-hairline p-3 text-left first:border-t-0"
              >
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-body text-text-color-primary">
                    {note.author_display_name}
                  </span>
                  {unread ? (
                    <span
                      aria-label={t('settings.curriculum.feedback.unread')}
                      className="size-2 shrink-0 rounded-full bg-accent"
                    />
                  ) : (
                    <span className="text-footnote text-text-color-tertiary">
                      {t('settings.curriculum.feedback.seen')}
                    </span>
                  )}
                </div>
                {note.skill_name_en ? (
                  <span className="text-footnote text-text-color-tertiary">
                    {t('settings.curriculum.feedback.about', {
                      skill: note.skill_name_en,
                    })}
                  </span>
                ) : null}
                <p className="text-body text-text-color-secondary">{note.body}</p>
                <span className="text-footnote text-text-color-tertiary">
                  {new Date(note.created_at).toLocaleString()}
                </span>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-6 text-center">
          <p className="text-h3 text-text-color-primary">
            {t('settings.curriculum.feedback.emptyTitle')}
          </p>
          <p className="text-body text-text-color-secondary">
            {t('settings.curriculum.feedback.emptyBody')}
          </p>
        </div>
      )}
    </div>
  );
}
