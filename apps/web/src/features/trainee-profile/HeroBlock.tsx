import { format } from 'date-fns';
import { enUS, id as idLocale } from 'date-fns/locale';
import { useTranslation } from 'react-i18next';

import { Avatar } from '@/components/Avatar';
import { TierPill } from '@/components/TierPill';

import type { TierBrief } from './profile-types';

interface Props {
  displayName: string;
  joinedAt: string;
  tier: TierBrief;
  locale: string;
}

export function HeroBlock({ displayName, joinedAt, tier, locale }: Props) {
  const { t } = useTranslation();
  const df = locale === 'id' ? idLocale : enUS;
  const joinedLabel = format(new Date(joinedAt), 'MMM yyyy', { locale: df });

  return (
    <div className="flex flex-col items-center gap-3 pb-5 pt-2 text-center">
      <Avatar name={displayName} size={64} />
      <h1 className="text-large-title text-text-color-primary">{displayName}</h1>
      <div className="flex items-center gap-2 text-caption text-text-color-secondary">
        <TierPill tier={tier.code} />
        <span aria-hidden>·</span>
        <span>{t('profile.joinedDate', { date: joinedLabel })}</span>
      </div>
    </div>
  );
}
