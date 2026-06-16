import { useTranslation } from 'react-i18next';

interface Props {
  sessionsCount: number;
  hoursCoached: number;
  daysSinceLastSession: number | null;
}

export function StatsGrid({ sessionsCount, hoursCoached, daysSinceLastSession }: Props) {
  const { t } = useTranslation();
  const sinceLabel =
    daysSinceLastSession == null
      ? '—'
      : daysSinceLastSession < 7
      ? `${daysSinceLastSession}d`
      : daysSinceLastSession < 30
      ? `${Math.floor(daysSinceLastSession / 7)}w`
      : `${Math.floor(daysSinceLastSession / 30)}mo`;

  return (
    <div className="grid grid-cols-3 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
      <Stat value={String(sessionsCount)} label={t('profile.stats.sessions')} />
      <Stat
        value={hoursCoached.toFixed(1)}
        label={t('profile.stats.hours')}
        className="border-l-[0.5px] border-border-hairline"
      />
      <Stat
        value={sinceLabel}
        label={t('profile.stats.sinceLast')}
        className="border-l-[0.5px] border-border-hairline"
      />
    </div>
  );
}

function Stat({
  value,
  label,
  className = '',
}: {
  value: string;
  label: string;
  className?: string;
}) {
  return (
    <div className={['flex flex-col items-center px-3 py-4 text-center', className].join(' ')}>
      <span className="text-h2 font-medium text-text-color-primary">{value}</span>
      <span className="mt-0.5 text-footnote text-text-color-secondary">{label}</span>
    </div>
  );
}
