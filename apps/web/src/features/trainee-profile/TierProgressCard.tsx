import { useTranslation } from 'react-i18next';

import type { TierBrief } from './profile-types';

interface Props {
  currentTier: TierBrief;
  nextTier: TierBrief | null;
  metCount: number;
  totalRequirements: number;
  blockingCount: number;
  // Locale is kept on the prop signature for future use (e.g., number/date
  // formatting), but tier names themselves stay English in both locales by
  // product convention.  See memory/coach_trainee_profile.md.
  locale: string;
}

// Always EN — tier names are a brand-consistent label, not translated copy.
function tierName(tier: TierBrief): string {
  return tier.nameGameEn;
}

export function TierProgressCard({
  currentTier,
  nextTier,
  metCount,
  totalRequirements,
  blockingCount,
  locale: _locale,
}: Props) {
  const { t } = useTranslation();
  const pct = totalRequirements > 0 ? Math.min(100, Math.round((metCount / totalRequirements) * 100)) : 0;

  return (
    <section className="flex flex-col gap-3">
      <h2 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {t('profile.tierProgress.title')}
      </h2>

      <div className="flex flex-col gap-4 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
        {nextTier ? (
          <>
            <div className="flex items-center justify-between gap-2 text-caption">
              <span className="text-text-color-secondary">{tierName(currentTier)}</span>
              <span className="text-text-color-primary">{tierName(nextTier)}</span>
            </div>
            <div className="relative h-2 w-full overflow-hidden rounded-full bg-bg-tertiary">
              <div
                className="h-full rounded-full bg-accent"
                style={{ width: `${pct}%` }}
                aria-label={`${pct}%`}
              />
            </div>
            <div className="flex flex-col gap-0.5 text-caption">
              <span className="text-text-color-primary">
                {t('profile.tierProgress.met', { count: metCount, total: totalRequirements })}
              </span>
              {blockingCount > 0 ? (
                <span className="text-text-color-secondary">
                  {t('profile.tierProgress.blocking', {
                    count: blockingCount,
                    tier: tierName(nextTier),
                  })}
                </span>
              ) : null}
            </div>
          </>
        ) : (
          <p className="text-body text-text-color-primary">
            {t('profile.tierProgress.topTier')}
          </p>
        )}
      </div>
    </section>
  );
}
