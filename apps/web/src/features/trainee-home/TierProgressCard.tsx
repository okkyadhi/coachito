import { useTranslation } from 'react-i18next';

import type { TraineeTierProgress } from './trainee-home-api';

interface Props {
  progress: TraineeTierProgress;
}

// Trainee variant of tier progress — encouraging, forward-looking copy.
// Different from the coach's TierProgressCard which leads with blocker count.
export function TierProgressCard({ progress }: Props) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language;
  const encouragement =
    locale === 'id' ? progress.encouragementId : progress.encouragementEn;

  const pct = progress.totalRequirements
    ? Math.round((progress.metCount / progress.totalRequirements) * 100)
    : 0;

  // Top-tier ceiling: at MVP only Bronze+ is shipped.  When nextTier is null
  // we show a refining-tone treatment instead of a 100% bar.
  if (progress.nextTierGameEn === null) {
    return (
      <section className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
        <p className="text-h3 text-text-color-primary">{progress.currentTierGameEn}</p>
        <p className="mt-1 text-caption text-text-color-secondary">
          {t('traineeHome.tier.topTier')}
        </p>
      </section>
    );
  }

  const skillsToGo = Math.max(
    progress.totalRequirements - progress.metCount,
    0,
  );

  return (
    <section className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
      <div className="flex items-baseline justify-between">
        <p className="text-h3 text-text-color-primary">{progress.currentTierGameEn}</p>
        <p className="text-caption text-text-color-secondary">
          {progress.nextTierGameEn} · {t('traineeHome.tier.skillsToGo', { count: skillsToGo })}
        </p>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-bg-tertiary">
        <div
          className="h-full rounded-full bg-accent transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="mt-3 text-caption text-text-color-secondary">{encouragement}</p>
    </section>
  );
}
