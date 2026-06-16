import { format } from 'date-fns';
import { enUS, id as idLocale } from 'date-fns/locale';
import { useTranslation } from 'react-i18next';

import { Avatar } from '@/components/Avatar';

import type { CoachProfile } from '../coach-types';

interface Props {
  coach: CoachProfile;
}

export function BioHeader({ coach }: Props) {
  const { t, i18n } = useTranslation();
  const since = format(new Date(coach.memberSince), 'MMM yyyy', {
    locale: i18n.language === 'id' ? idLocale : enUS,
  });
  const photo = coach.bio.photoUrl ?? coach.avatarUrl;
  return (
    <header className="flex flex-col items-center gap-3 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-6 text-center">
      <Avatar name={coach.displayName} src={photo} size={88} />
      <div className="flex flex-col gap-0.5">
        <h1 className="text-h2 text-text-color-primary">{coach.displayName}</h1>
        {coach.bio.headline ? (
          <p className="text-body text-text-color-secondary">
            {coach.bio.headline}
          </p>
        ) : null}
        <p className="text-footnote text-text-color-tertiary">
          {t('coach.bio.memberSince', { date: since })}
        </p>
      </div>
    </header>
  );
}
