import { ChevronRight, Sparkles, Trophy } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import type { TierProgress } from '../skills-types';

interface Props {
  tier: TierProgress;
}

export function TierStrip({ tier }: Props) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'id' ? 'id' : 'en';

  // Animate the bar from 0 → target on mount.
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const id = window.setTimeout(
      () => setWidth(Math.max(0, Math.min(1, tier.progressToNext)) * 100),
      40,
    );
    return () => window.clearTimeout(id);
  }, [tier.progressToNext]);

  const currentName =
    tier.current && (lang === 'id' ? tier.current.labelId : tier.current.labelEn);
  const nextName =
    tier.next && (lang === 'id' ? tier.next.labelId : tier.next.labelEn);

  if (tier.next === null) {
    return (
      <section className="flex items-center justify-between rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-3.5">
        <div className="flex items-center gap-2">
          <span className="flex size-7 items-center justify-center rounded-full bg-accent-bg text-accent">
            <Sparkles size={14} strokeWidth={2} aria-hidden />
          </span>
          <span className="text-body text-text-color-primary">
            {t('skills.overview.tier.topTier')}
          </span>
        </div>
        {currentName ? (
          <span className="text-caption text-text-color-secondary">
            {currentName}
          </span>
        ) : null}
      </section>
    );
  }

  const remaining = Math.max(
    tier.blockersRemainingCount,
    0,
  );

  return (
    <section className="flex flex-col gap-2 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-3.5">
      <div className="flex items-center justify-between">
        <div className="flex min-w-0 items-center gap-1.5">
          <span className="inline-flex items-center gap-1 rounded-full bg-accent-bg px-2 py-0.5 text-pill text-accent">
            <Trophy size={12} strokeWidth={2} aria-hidden />
            {currentName ?? '—'}
          </span>
          <ChevronRight
            size={14}
            strokeWidth={1.75}
            className="text-text-color-tertiary"
            aria-hidden
          />
          <span className="truncate text-caption text-text-color-secondary">
            {nextName}
          </span>
        </div>
        <span className="shrink-0 text-caption tabular-nums text-text-color-secondary">
          {Math.round(tier.progressToNext * 100)}%
        </span>
      </div>

      <div
        className="h-1.5 w-full overflow-hidden rounded-full"
        style={{ backgroundColor: 'rgba(0,0,0,0.05)' }}
        aria-hidden
      >
        <div
          className="h-full rounded-full transition-[width] duration-500 ease-out"
          style={{ width: `${width}%`, backgroundColor: 'var(--accent)' }}
        />
      </div>

      <p className="text-footnote text-text-color-tertiary">
        {remaining === 1
          ? t('skills.overview.tier.remainingSingular', { tier: nextName })
          : t('skills.overview.tier.remainingPlural', {
              count: remaining,
              tier: nextName,
            })}
      </p>
    </section>
  );
}
