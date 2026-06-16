import { format } from 'date-fns';
import { enUS, id as idLocale } from 'date-fns/locale';
import { ChevronRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { Avatar } from '@/components/Avatar';
import { formatTime } from '@/lib/dates';

import type { UpcomingSessionDto } from './trainee-home-api';

interface Props {
  session: UpcomingSessionDto | null;
  onOpen?: () => void;
}

function dayBadge(date: Date, locale: 'en' | 'id') {
  // "11 MAY" / "11 MEI"
  return format(date, 'd MMM', { locale: locale === 'id' ? idLocale : enUS }).toUpperCase();
}

function whenLabel(date: Date, locale: 'en' | 'id', t: (k: string) => string): string {
  const now = new Date();
  const diffDays = Math.round(
    (date.getTime() - new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()) /
      (24 * 3600 * 1000),
  );
  const time = formatTime(date, locale);
  if (diffDays === 0) return `${t('traineeHome.upcoming.today')}, ${time}`;
  if (diffDays === 1) return `${t('traineeHome.upcoming.tomorrow')}, ${time}`;
  return `${format(date, 'EEE d MMM', { locale: locale === 'id' ? idLocale : enUS })}, ${time}`;
}

export function UpcomingSession({ session, onOpen }: Props) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language === 'id' ? 'id' : 'en';

  if (session === null) {
    return (
      <section className="flex flex-col gap-2">
        <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
          {t('traineeHome.upcoming.title')}
        </h3>
        <div className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
          <p className="text-body text-text-color-primary">
            {t('traineeHome.upcoming.noneTitle')}
          </p>
          <p className="mt-0.5 text-caption text-text-color-secondary">
            {t('traineeHome.upcoming.noneBody')}
          </p>
        </div>
      </section>
    );
  }

  const date = new Date(session.scheduledAt);
  return (
    <section className="flex flex-col gap-2">
      <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {t('traineeHome.upcoming.title')}
      </h3>
      <button
        type="button"
        onClick={onOpen}
        className="flex items-center gap-3 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-3 text-left"
      >
        <div className="flex size-12 flex-col items-center justify-center rounded-md bg-accent-bg">
          <span
            className="text-[10px] font-medium text-accent"
            style={{ letterSpacing: '0.04em' }}
          >
            {dayBadge(date, locale)}
          </span>
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-body text-text-color-primary">{whenLabel(date, locale, t)}</p>
          <p className="text-caption text-text-color-secondary">
            {[session.court, `${session.durationMin} ${t('today.minutes', { count: session.durationMin })}`, session.focus ? t(`sessionFocus.${session.focus}`) : null]
              .filter(Boolean)
              .join(' · ')}
          </p>
          <div className="mt-1 flex items-center gap-1.5">
            <Avatar name={session.coachDisplayName} size={18} />
            <span className="text-footnote text-text-color-secondary">
              {session.coachDisplayName}
            </span>
          </div>
        </div>
        <ChevronRight size={18} strokeWidth={1.75} className="text-text-color-tertiary" aria-hidden />
      </button>
    </section>
  );
}
