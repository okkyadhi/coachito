// Coach's outgoing feedback history.
//
// Closes the loop — the admin inbox shows admin "did the coach hear me",
// this screen shows coach "did the admin read me".  ``read_at`` from the
// note (set when admin marks read in their inbox) becomes the "seen by
// admin" indicator here.

import { ChevronLeft } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { useMyFeedback } from './curriculum-api';
import { useCurriculumPermissions } from './use-curriculum-permissions';

export function MyFeedbackScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const perms = useCurriculumPermissions();
  const { data, isPending } = useMyFeedback(true);

  return (
    <div className="mx-auto w-full max-w-md px-4 pb-8 pt-3">
      <header className="mb-4 flex items-center gap-2">
        <button
          type="button"
          onClick={() => navigate('/settings/curriculum')}
          className="flex min-h-tap min-w-tap items-center text-accent"
          aria-label={t('common.back')}
        >
          <ChevronLeft size={20} strokeWidth={1.75} aria-hidden />
          <span className="text-body">{t('settings.curriculum.title')}</span>
        </button>
        <h1 className="ml-2 flex-1 text-large-title text-text-color-primary">
          {t('settings.curriculum.feedback.mineTitle')}
        </h1>
      </header>

      {/* Defensive: admin/owner hitting this URL directly. */}
      {!perms.canSendFeedback && !perms.isLoading ? (
        <p className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-3 text-body text-text-color-secondary">
          {t('settings.curriculum.feedback.mineEmptyOwner')}
        </p>
      ) : isPending ? (
        <div className="rounded-xl bg-bg-primary p-4 text-body text-text-color-tertiary">
          {t('common.loading')}
        </div>
      ) : data && data.notes.length > 0 ? (
        <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
          {data.notes.map((note) => {
            const seen = note.read_at !== null;
            return (
              <div
                key={note.id}
                className="flex flex-col gap-1 border-t-[0.5px] border-border-hairline p-3 first:border-t-0"
              >
                <div className="flex items-baseline justify-between gap-2">
                  {note.skill_name_en ? (
                    <span className="text-footnote text-text-color-tertiary">
                      {t('settings.curriculum.feedback.about', {
                        skill: note.skill_name_en,
                      })}
                    </span>
                  ) : (
                    <span className="text-footnote text-text-color-tertiary">
                      {t('settings.curriculum.feedback.general')}
                    </span>
                  )}
                  <span
                    className={[
                      'rounded-full px-2 py-0.5 text-[10px] font-medium',
                      seen
                        ? 'bg-success-bg text-success-text'
                        : 'bg-bg-tertiary text-text-color-tertiary',
                    ].join(' ')}
                  >
                    {seen
                      ? t('settings.curriculum.feedback.seenByAdmin')
                      : t('settings.curriculum.feedback.awaitingRead')}
                  </span>
                </div>
                <p className="text-body text-text-color-primary">{note.body}</p>
                <span className="text-footnote text-text-color-tertiary">
                  {new Date(note.created_at).toLocaleString()}
                </span>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-6 text-center">
          <p className="text-h3 text-text-color-primary">
            {t('settings.curriculum.feedback.mineEmptyTitle')}
          </p>
          <p className="text-body text-text-color-secondary">
            {t('settings.curriculum.feedback.mineEmptyBody')}
          </p>
        </div>
      )}
    </div>
  );
}
