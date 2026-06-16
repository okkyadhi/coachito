import { Target } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import type { CategoryCode } from '@/lib/category-meta';

import type { CategoryBlockers } from '../skills-types';

interface Props {
  category: CategoryCode;
  accent: string;
  data: CategoryBlockers;
}

export function BlockerCallout({ accent, data }: Props) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'id' ? 'id' : 'en';
  if (!data.nextTier) return null;
  const tierLabel =
    lang === 'id' ? data.nextTier.labelId : data.nextTier.labelEn;
  return (
    <section
      className="flex items-start gap-3 rounded-xl border-[0.5px] border-border-hairline p-4"
      style={{ backgroundColor: `${accent}10` }}
    >
      <span
        className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full text-white"
        style={{ backgroundColor: accent }}
        aria-hidden
      >
        <Target size={14} strokeWidth={2} />
      </span>
      <div className="flex flex-col gap-0.5">
        <p className="text-body text-text-color-primary">
          {t('skills.blockers.headline', {
            count: data.blockersInCategory.length,
            tier: tierLabel,
          })}
        </p>
        <p className="text-caption text-text-color-secondary">
          {t('skills.blockers.subline')}
        </p>
      </div>
    </section>
  );
}
