import { ChevronRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { CATEGORY_META, type CategoryCode } from '@/lib/category-meta';

import type { CategoryScore } from '../skills-types';

interface Props {
  score: CategoryScore;
  onTap: (code: CategoryCode) => void;
  borderTop?: boolean;
}

export function CategoryListRow({ score, onTap, borderTop }: Props) {
  const { i18n } = useTranslation();
  const meta = CATEGORY_META[score.category];
  const lang = i18n.language === 'id' ? 'id' : 'en';
  const name = lang === 'id' ? meta.labelId : meta.labelEn;
  const avgPct = ((score.average ?? 0) / 5) * 100;
  const avgLabel = score.average == null ? '—' : score.average.toFixed(1);

  return (
    <button
      type="button"
      onClick={() => onTap(score.category)}
      className={[
        'flex w-full min-h-tap items-center gap-3 px-4 py-3 text-left active:bg-bg-secondary',
        borderTop ? 'border-t-[0.5px] border-border-hairline' : '',
      ].join(' ')}
    >
      <span
        className="flex size-[22px] shrink-0 items-center justify-center rounded-full text-[11px] font-medium text-white"
        style={{ backgroundColor: meta.accent }}
        aria-hidden
      >
        {meta.chip}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-body text-text-color-primary">{name}</p>
        <div
          className="mt-1.5 h-1 w-full overflow-hidden rounded-full"
          style={{ backgroundColor: 'rgba(0,0,0,0.05)' }}
          aria-hidden
        >
          <div
            className="h-full rounded-full"
            style={{ width: `${avgPct}%`, backgroundColor: meta.accent }}
          />
        </div>
      </div>
      <div className="flex flex-col items-end">
        <span className="text-body font-medium tabular-nums text-text-color-primary">
          {avgLabel}
        </span>
        <span className="text-footnote tabular-nums text-text-color-tertiary">
          {score.assessedCount}/{score.totalCount}
        </span>
      </div>
      <ChevronRight
        size={16}
        strokeWidth={1.75}
        className="text-text-color-tertiary"
        aria-hidden
      />
    </button>
  );
}
