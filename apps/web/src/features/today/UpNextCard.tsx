import { CalendarDays, ChevronRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { GroupedTable } from '@/components/GroupedTable';
import { WorkspaceBadge } from '@/components/WorkspaceBadge';
import { sportLabel, type WorkspaceSport } from '@/features/sports/sports-api';
import { formatTime } from '@/lib/dates';

import type { TodaySession } from './today-api';

interface UpNextCardProps {
  session: TodaySession;
  locale: string;
  sports: WorkspaceSport[];
  isMultiSport: boolean;
}

export function UpNextCard({ session, locale, sports, isMultiSport }: UpNextCardProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const time = formatTime(session.scheduledAt, locale);

  const focusLabel =
    session.focuses.length > 0
      ? session.focuses
          .slice(0, 2)
          .map((f) => t(`sessionFocus.${f}`))
          .join(' · ') + (session.focuses.length > 2 ? ` +${session.focuses.length - 2}` : '')
      : null;
  const meta = [session.court, t('today.minutes', { count: session.durationMin }), focusLabel]
    .filter(Boolean)
    .join(' · ');

  const sport = isMultiSport && session.sportId
    ? sports.find((s) => s.sportId === session.sportId)
    : null;

  return (
    <GroupedTable header={t('today.upNext')}>
      <button
        type="button"
        onClick={() => navigate(`/trainees/${session.trainee.id}`)}
        className="flex min-h-tap w-full items-center gap-3 px-4 py-3.5 text-left"
      >
        <span
          aria-hidden
          className="flex size-10 shrink-0 items-center justify-center rounded-full bg-accent-bg text-accent"
        >
          <CalendarDays size={20} strokeWidth={1.75} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-h3 text-text-color-primary">
            {time} · {session.trainee.displayName}
          </p>
          <div className="flex flex-wrap items-center gap-1.5">
            {meta ? (
              <p className="truncate text-caption text-text-color-secondary">{meta}</p>
            ) : null}
            <WorkspaceBadge workspace={session.workspace} />
            {sport ? (
              <span className="rounded-full border-[0.5px] border-border-hairline bg-bg-secondary px-2 py-0.5 text-footnote text-text-color-secondary">
                {sportLabel(sport, locale)}
              </span>
            ) : null}
          </div>
        </div>
        <ChevronRight
          aria-hidden
          size={18}
          strokeWidth={1.75}
          className="shrink-0 text-text-color-tertiary"
        />
      </button>
    </GroupedTable>
  );
}
