import { formatDistanceToNow } from 'date-fns';
import { enUS, id as idLocale } from 'date-fns/locale';
import {
  Calendar,
  CheckCircle2,
  FileText,
  MessageSquare,
  X,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import type { NotificationItem, NotificationKind } from './notifications-api';

interface Props {
  open: boolean;
  items: NotificationItem[];
  loading: boolean;
  onClose: () => void;
}

const KIND_ICON: Record<NotificationKind, typeof Calendar> = {
  session_scheduled: Calendar,
  coach_note: MessageSquare,
  assessment_published: CheckCircle2,
  report_ready: FileText,
};

export function NotificationSheet({ open, items, loading, onClose }: Props) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const lang = i18n.language === 'id' ? idLocale : enUS;

  if (!open) return null;

  const titleFor = (i: NotificationItem): string => {
    const coach = i.coachName ?? '';
    switch (i.kind) {
      case 'session_scheduled':
        return coach
          ? t('notifications.titles.sessionScheduledWithCoach', { coach })
          : t('notifications.titles.sessionScheduled');
      case 'coach_note':
        return coach
          ? t('notifications.titles.coachNoteFromCoach', { coach })
          : t('notifications.titles.coachNote');
      case 'assessment_published':
        return coach
          ? t('notifications.titles.assessmentFromCoach', { coach })
          : t('notifications.titles.assessment');
      case 'report_ready':
        return t('notifications.titles.reportReady');
    }
  };

  const handleTap = (i: NotificationItem) => {
    if (i.link) navigate(i.link);
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('notifications.title')}
      className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 sm:items-center"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[80vh] w-full max-w-md flex-col rounded-t-2xl bg-bg-secondary sm:rounded-2xl"
      >
        <header className="flex items-center justify-between border-b-[0.5px] border-border-hairline bg-bg-primary px-4 py-3 sm:rounded-t-2xl">
          <button
            type="button"
            onClick={onClose}
            aria-label={t('common.cancel')}
            className="flex size-9 items-center justify-center rounded-full text-text-color-secondary"
          >
            <X size={18} strokeWidth={1.75} aria-hidden />
          </button>
          <span className="text-h3 text-text-color-primary">
            {t('notifications.title')}
          </span>
          <span className="size-9" aria-hidden />
        </header>

        <div className="flex flex-col overflow-y-auto">
          {loading ? (
            <div className="px-4 py-10 text-center text-caption text-text-color-secondary">
              {t('common.loading')}
            </div>
          ) : items.length === 0 ? (
            <div className="px-4 py-10 text-center">
              <p className="text-body text-text-color-primary">
                {t('notifications.emptyTitle')}
              </p>
              <p className="mt-1 text-caption text-text-color-secondary">
                {t('notifications.emptyBody')}
              </p>
            </div>
          ) : (
            items.map((i) => {
              const Icon = KIND_ICON[i.kind];
              return (
                <button
                  key={i.id}
                  type="button"
                  onClick={() => handleTap(i)}
                  disabled={!i.link}
                  className="flex w-full items-start gap-3 border-b-[0.5px] border-border-hairline bg-bg-primary px-4 py-3 text-left last:border-b-0 active:bg-bg-secondary disabled:cursor-default"
                >
                  <div
                    aria-hidden
                    className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-accent-bg text-accent"
                  >
                    <Icon size={16} strokeWidth={1.75} aria-hidden />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-body text-text-color-primary">
                      {titleFor(i)}
                    </p>
                    {i.body ? (
                      <p className="mt-0.5 line-clamp-2 text-footnote text-text-color-secondary">
                        {i.body}
                      </p>
                    ) : null}
                    <p className="mt-0.5 text-caption text-text-color-tertiary">
                      {formatDistanceToNow(new Date(i.occurredAt), {
                        addSuffix: true,
                        locale: lang,
                      })}
                    </p>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
