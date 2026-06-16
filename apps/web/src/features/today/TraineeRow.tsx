import { ChevronRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { Avatar } from '@/components/Avatar';
import { TierPill } from '@/components/TierPill';
import { WorkspaceBadge } from '@/components/WorkspaceBadge';
import { sportLabel, type WorkspaceSport } from '@/features/sports/sports-api';
import { formatRelative, formatTime } from '@/lib/dates';

import type { TodaySession } from './today-api';

interface TraineeRowProps {
  session: TodaySession;
  locale: string;
  sports: WorkspaceSport[];
  isMultiSport: boolean;
}

export function TraineeRow({ session, locale, sports, isMultiSport }: TraineeRowProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const time = formatTime(session.scheduledAt, locale);
  const lastAssessed = session.trainee.lastAssessedAt
    ? formatRelative(session.trainee.lastAssessedAt, locale)
    : t('today.notAssessed');

  const sport = isMultiSport && session.sportId
    ? sports.find((s) => s.sportId === session.sportId)
    : null;

  return (
    <button
      type="button"
      onClick={() => navigate(`/trainees/${session.trainee.id}`)}
      className="flex min-h-tap w-full items-center gap-3 px-4 py-3 text-left"
    >
      <Avatar name={session.trainee.displayName} size={40} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-body font-medium text-text-color-primary">
          {session.trainee.displayName}
        </p>
        <div className="flex flex-wrap items-center gap-1.5">
          <p className="text-caption text-text-color-secondary">
            {time} · {lastAssessed}
          </p>
          <WorkspaceBadge workspace={session.workspace} />
          {sport ? (
            <span className="rounded-full border-[0.5px] border-border-hairline bg-bg-secondary px-2 py-0.5 text-footnote text-text-color-secondary">
              {sportLabel(sport, locale)}
            </span>
          ) : null}
        </div>
      </div>
      {session.trainee.tier ? <TierPill tier={session.trainee.tier} /> : null}
      <ChevronRight
        aria-hidden
        size={18}
        strokeWidth={1.75}
        className="shrink-0 text-text-color-tertiary"
      />
    </button>
  );
}
