import { ChevronRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { Avatar } from '@/components/Avatar';
import { TierPill } from '@/components/TierPill';
import { formatRelative } from '@/lib/dates';

import type { Trainee } from './trainees-api';

interface Props {
  trainee: Trainee;
  locale: string;
}

export function TraineeListRow({ trainee, locale }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const meta = trainee.lastAssessedAt
    ? formatRelative(new Date(trainee.lastAssessedAt), locale)
    : t('today.notAssessed');

  return (
    <button
      type="button"
      onClick={() => navigate(`/trainees/${trainee.id}`)}
      className="flex min-h-tap w-full items-center gap-3 px-4 py-3 text-left"
    >
      <Avatar name={trainee.displayName} size={40} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-body font-medium text-text-color-primary">
          {trainee.displayName}
        </p>
        <p className="truncate text-caption text-text-color-secondary">{meta}</p>
      </div>
      {trainee.currentTier ? <TierPill tier={trainee.currentTier.code} /> : null}
      <ChevronRight
        aria-hidden
        size={18}
        strokeWidth={1.75}
        className="shrink-0 text-text-color-tertiary"
      />
    </button>
  );
}
