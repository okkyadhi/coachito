// Coach (read-only) row — chevron only, no toggle.
//
// Disabled skills get muted styling so the coach can still see that the
// admin has turned them off (visibility helps coaches calibrate
// expectations during sessions).

import { ChevronRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { UpdatedBadge } from './UpdatedBadge';
import type { SkillRow } from './curriculum-api';

interface Props {
  skill: SkillRow;
  onOpen: () => void;
}

export function SkillChevronRow({ skill, onOpen }: Props) {
  const { t } = useTranslation();
  return (
    <button
      type="button"
      onClick={onOpen}
      className={[
        'flex min-h-tap w-full items-center gap-3 border-t-[0.5px] border-border-hairline p-3 text-left first:border-t-0',
        skill.is_enabled ? '' : 'opacity-60',
      ].join(' ')}
    >
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="flex items-center gap-2">
          <span className="truncate text-body text-text-color-primary">
            {skill.name_en}
          </span>
          {skill.last_changed_at ? <UpdatedBadge /> : null}
        </span>
        {skill.description_en ? (
          <span className="truncate text-footnote text-text-color-tertiary">
            {skill.description_en}
          </span>
        ) : null}
      </div>
      {!skill.is_enabled ? (
        <span className="text-footnote text-text-color-tertiary">
          {t('settings.curriculum.disabledLabel')}
        </span>
      ) : null}
      <ChevronRight
        size={16}
        strokeWidth={1.75}
        className="text-text-color-tertiary"
        aria-hidden
      />
    </button>
  );
}
