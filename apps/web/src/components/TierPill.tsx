import { useTranslation } from 'react-i18next';

export type TierCode =
  | 'BEGINNER'
  | 'LOWER_BRONZE'
  | 'BRONZE'
  | 'SILVER'
  | 'GOLD'
  | 'PLATINUM'
  | 'DIAMOND';

interface TierPillProps {
  tier: TierCode;
  className?: string;
}

export function TierPill({ tier, className = '' }: TierPillProps) {
  const { t } = useTranslation();
  return (
    <span
      className={[
        'inline-flex items-center px-2 py-0.5 rounded-full',
        'text-[11px] font-medium',
        'bg-accent-bg text-accent',
        'whitespace-nowrap',
        className,
      ].join(' ')}
    >
      {t(`tiers.${tier}`)}
    </span>
  );
}
