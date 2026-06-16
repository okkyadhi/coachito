// "Required for" section on SkillDetailScreen.
//
// Tells the coach which tier requirements this skill participates in, at
// what minimum level.  Server already resolves tier_name to the effective
// name per the workspace's tier_style — we just render.
//
// Hidden when there are no requirements (e.g. a skill that's purely
// informational or hasn't been wired into the tier rubric yet).

import { useTranslation } from 'react-i18next';

import type { TierRequirement } from './curriculum-api';

interface Props {
  requirements: TierRequirement[];
}

export function TierContextSection({ requirements }: Props) {
  const { t } = useTranslation();
  return (
    <section className="mb-4 flex flex-col gap-2">
      <header className="flex items-baseline justify-between px-1">
        <h3 className="text-section uppercase tracking-wide text-text-color-secondary">
          {t('settings.curriculum.skill.requiredFor')}
        </h3>
      </header>
      <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
        {requirements.map((req) => (
          <div
            key={req.tier_code}
            className="flex min-h-tap items-center gap-3 border-t-[0.5px] border-border-hairline p-3 first:border-t-0"
          >
            <span className="flex-1 text-body text-text-color-primary">
              {req.tier_name}
            </span>
            <span className="rounded-md bg-bg-tertiary px-2 py-0.5 text-footnote font-medium text-text-color-secondary">
              {t('settings.curriculum.skill.minLevel', { level: req.min_level })}
            </span>
          </div>
        ))}
      </div>
      <p className="px-1 text-footnote text-text-color-tertiary">
        {t('settings.curriculum.skill.requiredForHint')}
      </p>
    </section>
  );
}
