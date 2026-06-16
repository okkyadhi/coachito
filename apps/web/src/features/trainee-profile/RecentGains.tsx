import { ArrowUp } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { formatRelative } from '@/lib/dates';

import type { GainEntry } from './profile-types';

interface Props {
  gains: GainEntry[];
  locale: string;
}

export function RecentGains({ gains, locale }: Props) {
  const { t } = useTranslation();
  if (gains.length === 0) return null;

  return (
    <section className="flex flex-col gap-3">
      <h2 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {t('profile.gains.title')}
      </h2>

      <div className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary [&>*+*]:border-[0.5px] [&>*+*]:border-t [&>*+*]:border-border-hairline">
        {gains.map((g, idx) => (
          <Row key={`${g.skill.id}-${idx}`} gain={g} locale={locale} />
        ))}
      </div>
    </section>
  );
}

function Row({ gain, locale }: { gain: GainEntry; locale: string }) {
  const { t } = useTranslation();
  // Skill names stay EN in both locales by product convention.
  const name = gain.skill.nameEn;
  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <span
        aria-hidden
        className="flex size-7 shrink-0 items-center justify-center rounded-full bg-success-bg text-success-text"
      >
        <ArrowUp size={14} strokeWidth={2.2} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-body text-text-color-primary">{name}</p>
        <p className="text-caption text-text-color-secondary">
          {t('profile.gains.entry', { from: gain.fromLevel, to: gain.toLevel })}
        </p>
      </div>
      <span className="text-footnote text-text-color-tertiary">
        {formatRelative(new Date(gain.recordedAt), locale)}
      </span>
    </div>
  );
}
