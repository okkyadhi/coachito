import { formatDistanceToNowStrict } from 'date-fns';
import { enUS, id as idLocale } from 'date-fns/locale';
import { useTranslation } from 'react-i18next';

import type { OverallProgress } from '../skills-types';

interface Props {
  overall: OverallProgress;
}

export function HeroStats({ overall }: Props) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'id' ? idLocale : enUS;

  const avgLabel = overall.average == null ? '—' : overall.average.toFixed(1);
  const assessedLabel = `${overall.assessedCount}/${overall.totalCount}`;
  const lastLabel = overall.lastAssessedAt
    ? shortDistance(overall.lastAssessedAt, lang)
    : '—';

  return (
    <section className="grid grid-cols-3 gap-2" aria-label={t('skills.overview.statAria')}>
      <Stat label={t('skills.overview.stat.overall')} value={avgLabel} suffix="/5" />
      <Stat label={t('skills.overview.stat.assessed')} value={assessedLabel} />
      <Stat label={t('skills.overview.stat.last')} value={lastLabel} />
    </section>
  );
}

function Stat({
  label,
  value,
  suffix,
}: {
  label: string;
  value: string;
  suffix?: string;
}) {
  return (
    <div className="flex flex-col items-start justify-between rounded-lg bg-bg-secondary p-2.5">
      <span className="text-footnote text-text-color-secondary">{label}</span>
      <span className="mt-0.5 inline-flex items-baseline gap-0.5">
        <span className="text-[22px] font-medium tabular-nums text-text-color-primary">
          {value}
        </span>
        {suffix ? (
          <span className="text-[12px] tabular-nums text-text-color-tertiary">
            {suffix}
          </span>
        ) : null}
      </span>
    </div>
  );
}

// "2d", "3h", "now" — strict + lower-case unit, no "ago".
function shortDistance(iso: string, locale: Locale): string {
  const raw = formatDistanceToNowStrict(new Date(iso), { locale });
  const dt = new Date(iso).getTime();
  if (Date.now() - dt < 60_000) return 'now';
  // Reduce "2 days" → "2d", "3 hours" → "3h", "5 minutes" → "5m".
  const m = raw.match(/^(\d+)\s*(\S+)/);
  if (!m) return raw;
  const [, n, unit] = m;
  const u = (unit ?? '').toLowerCase();
  if (u.startsWith('sec')) return `${n}s`;
  if (u.startsWith('min') || u.startsWith('men')) return `${n}m`;
  if (u.startsWith('hour') || u.startsWith('jam')) return `${n}h`;
  if (u.startsWith('day')  || u.startsWith('hari')) return `${n}d`;
  if (u.startsWith('week') || u.startsWith('mgu') || u.startsWith('ming')) return `${n}w`;
  if (u.startsWith('month')|| u.startsWith('bln')  || u.startsWith('bul')) return `${n}mo`;
  if (u.startsWith('year') || u.startsWith('thn')  || u.startsWith('tah')) return `${n}y`;
  return raw;
}

type Locale = typeof enUS;
