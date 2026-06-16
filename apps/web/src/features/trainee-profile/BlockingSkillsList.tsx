import { useTranslation } from 'react-i18next';

import type { BlockingSkill, TierBrief } from './profile-types';

interface Props {
  blockers: BlockingSkill[];
  nextTier: TierBrief | null;
  // Kept on the signature for future date/number formatting; skill + tier
  // names themselves stay English in both locales by product convention.
  locale: string;
}

export function BlockingSkillsList({ blockers, nextTier, locale: _locale }: Props) {
  const { t } = useTranslation();
  if (!nextTier || blockers.length === 0) return null;

  return (
    <section className="flex flex-col gap-3">
      <h2 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {t('profile.blockers.title', { tier: nextTier.nameGameEn })}
      </h2>

      <div className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary [&>*+*]:border-[0.5px] [&>*+*]:border-t [&>*+*]:border-border-hairline">
        {blockers.map((b) => (
          <Row key={b.skill.id} blocker={b} />
        ))}
      </div>
    </section>
  );
}

function Row({ blocker }: { blocker: BlockingSkill }) {
  const { t } = useTranslation();
  const name = blocker.skill.nameEn;
  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <div className="min-w-0 flex-1">
        <p className="truncate text-body text-text-color-primary">{name}</p>
        <p className="text-caption text-text-color-secondary">
          {t('profile.blockers.gap', {
            current: blocker.currentLevel,
            required: blocker.requiredLevel,
          })}
        </p>
      </div>
      <GapBar current={blocker.currentLevel} required={blocker.requiredLevel} />
    </div>
  );
}

// Dual-color bar: solid-gray for filled, accent-bg semi-transparent for the
// "you need to be one cell further" target, empty otherwise.
function GapBar({ current, required }: { current: number; required: number }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => {
        let className = 'h-3 w-2 rounded-sm border-[0.5px] border-border-hairline';
        if (n <= current) className += ' bg-text-color-tertiary';
        else if (n <= required) className += ' bg-accent-bg';
        else className += ' bg-transparent';
        return <span key={n} className={className} />;
      })}
    </div>
  );
}
