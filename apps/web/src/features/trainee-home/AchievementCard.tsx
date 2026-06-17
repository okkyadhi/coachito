import { Award, Share2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';

import type { AchievementSummary } from './trainee-home-api';

interface Props {
  achievement: AchievementSummary;
  onViewSkill: () => void;
  onShare: () => void;
}

// The hero "you levelled up" card.  Filled accent background — the loudest
// piece on the home screen.  Title uses a serif face for emotional weight per
// docs/05 (branded moment, not utilitarian).
export function AchievementCard({ achievement, onViewSkill, onShare }: Props) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language;
  const body = locale === 'id' ? achievement.bodyId : achievement.bodyEn;
  return (
    <section
      className="relative overflow-hidden rounded-xl p-5"
      style={{ background: 'var(--accent-bg)' }}
    >
      <div className="absolute right-4 top-4 flex size-10 items-center justify-center rounded-full bg-bg-primary">
        <Award size={20} strokeWidth={1.75} className="text-accent" aria-hidden />
      </div>

      <p
        className="text-pill uppercase text-accent"
        style={{ letterSpacing: '0.08em' }}
      >
        {t('traineeHome.achievement.tag')}
      </p>
      <h2
        className="mt-1 pr-12 font-display text-[24px] font-normal leading-tight text-text-color-primary"
        style={{ letterSpacing: '-0.2px' }}
      >
        {achievement.skillNameEn} · <span className="italic">{t(achievement.levelLabelKey)}</span>
      </h2>
      <p className="mt-1.5 text-caption text-text-color-secondary">{body}</p>

      <div className="mt-4 flex gap-2">
        <PrimaryButton onClick={onViewSkill}>
          {t('traineeHome.achievement.viewSkill')}
        </PrimaryButton>
        <SecondaryButton
          onClick={onShare}
          leftIcon={<Share2 size={16} strokeWidth={1.75} aria-hidden />}
        >
          {t('traineeHome.achievement.share')}
        </SecondaryButton>
      </div>
    </section>
  );
}
