// Compact pill that flags which sport a session/assessment is for (padel /
// tennis).  Mirrors WorkspaceBadge styling so the meta rows stay consistent.
import { useTranslation } from 'react-i18next';

import { sportLabel } from './sports-api';

interface Props {
  sport: { nameEn: string; nameId: string } | null | undefined;
  className?: string;
}

export function SportTag({ sport, className = '' }: Props) {
  const { i18n } = useTranslation();
  if (!sport) return null;

  return (
    <span
      className={[
        'inline-flex items-center rounded-full border-[0.5px] border-border-hairline',
        'bg-bg-secondary px-2 py-0.5 text-footnote text-text-color-secondary',
        className,
      ].join(' ')}
    >
      {sportLabel(sport, i18n.language)}
    </span>
  );
}
