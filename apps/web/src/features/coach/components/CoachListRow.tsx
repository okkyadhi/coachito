import { formatDistanceToNow } from 'date-fns';
import { enUS, id as idLocale } from 'date-fns/locale';
import { ChevronRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { Avatar } from '@/components/Avatar';

import type { CoachListEntry } from '../coach-types';

interface Props {
  entry: CoachListEntry;
  onTap: () => void;
}

export function CoachListRow({ entry, onTap }: Props) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'id' ? idLocale : enUS;
  const upcomingSoon = (() => {
    if (!entry.nextSessionAt) return false;
    const dt = new Date(entry.nextSessionAt).getTime();
    return dt - Date.now() < 7 * 24 * 3600 * 1000;
  })();
  const last = entry.lastCoachedAt
    ? formatDistanceToNow(new Date(entry.lastCoachedAt), {
        addSuffix: true,
        locale: lang,
      })
    : null;
  return (
    <button
      type="button"
      onClick={onTap}
      className="flex w-full items-center gap-3 p-4 text-left first:rounded-t-xl last:rounded-b-xl active:bg-bg-secondary"
    >
      <Avatar name={entry.displayName} src={entry.avatarUrl} size={42} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <p className="truncate text-body text-text-color-primary">
            {entry.displayName}
          </p>
          {upcomingSoon ? (
            <span
              className="size-1.5 shrink-0 rounded-full bg-accent"
              aria-label={t('coach.list.upcomingDot')}
            />
          ) : null}
        </div>
        {entry.headline ? (
          <p className="truncate text-footnote text-text-color-secondary">
            {entry.headline}
          </p>
        ) : null}
        <p className="text-footnote text-text-color-tertiary">
          {t('coach.list.sessionCount', { count: entry.sessionCount })}
          {last ? ` · ${t('coach.list.lastCoached', { ago: last })}` : ''}
        </p>
      </div>
      <ChevronRight
        size={18}
        strokeWidth={1.75}
        className="text-text-color-tertiary"
        aria-hidden
      />
    </button>
  );
}
