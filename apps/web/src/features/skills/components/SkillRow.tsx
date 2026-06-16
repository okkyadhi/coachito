import { useTranslation } from 'react-i18next';

import type { SkillScore } from '../skills-types';
import { SkillBar } from './SkillBar';

interface Props {
  skill: SkillScore;
  accent: string;
  requiredLevel?: number | undefined;
  isFirst?: boolean | undefined;
}

export function SkillRow({ skill, accent, requiredLevel, isFirst }: Props) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'id' ? 'id' : 'en';
  const name = lang === 'id' ? skill.labelId : skill.labelEn;
  const descriptor =
    lang === 'id' ? skill.latestDescriptorId : skill.latestDescriptorEn;
  const isBlocker = requiredLevel != null;

  return (
    <div
      className={[
        'flex flex-col gap-1 p-3',
        isFirst ? '' : 'border-t-[0.5px] border-border-hairline',
      ].join(' ')}
    >
      <div className="flex items-center gap-2">
        {isBlocker ? (
          <span
            className="size-1.5 shrink-0 rounded-full"
            style={{ backgroundColor: accent }}
            aria-label={t('skills.row.blockerDot')}
          />
        ) : null}
        <span className="flex-1 truncate text-body text-text-color-primary">
          {name}
        </span>
        <span
          className="flex size-7 items-center justify-center rounded-full text-caption font-medium"
          style={{
            color: skill.latestScore != null ? accent : 'var(--color-text-tertiary)',
            backgroundColor:
              skill.latestScore != null ? `${accent}1f` : 'transparent',
          }}
        >
          {skill.latestScore ?? '—'}
        </span>
      </div>
      <div className="flex items-center justify-between gap-2">
        <SkillBar
          level={skill.latestScore}
          accent={accent}
          {...(requiredLevel != null ? { requiredLevel } : {})}
        />
        {isBlocker ? (
          <span className="text-footnote text-text-color-tertiary">
            {t('skills.row.needs', { level: requiredLevel })}
          </span>
        ) : null}
      </div>
      {descriptor ? (
        <p className="text-footnote text-text-color-tertiary">{descriptor}</p>
      ) : null}
    </div>
  );
}
