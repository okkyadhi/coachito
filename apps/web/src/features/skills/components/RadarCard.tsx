import { useTranslation } from 'react-i18next';

import {
  CATEGORY_META,
  CATEGORY_ORDER,
  type CategoryCode,
} from '@/lib/category-meta';

import type { OverallProgress, RadarAxis } from '../skills-types';
import { SkillRadar } from './SkillRadar';

interface Props {
  axes: RadarAxis[];
  overall: OverallProgress;
  onPick: (code: CategoryCode) => void;
}

export function RadarCard({ axes, overall, onPick }: Props) {
  const { t } = useTranslation();

  // Each of the 4 overview vertices is the category's accent.
  const vertexAccents: Record<string, string> = {};
  for (const c of CATEGORY_ORDER) {
    vertexAccents[c] = CATEGORY_META[c].accent;
  }

  const centerValue = overall.average == null ? '—' : overall.average.toFixed(1);

  return (
    <section className="flex flex-col items-center gap-2 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
      <div className="relative">
        <SkillRadar
          axes={axes}
          size={260}
          accent="var(--accent)"
          vertexAccents={vertexAccents}
          onAxisTap={(code) => onPick(code as CategoryCode)}
          ariaLabel={t('skills.overview.radarLabel')}
        />
        <div
          className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center"
          aria-hidden
        >
          <span className="text-[22px] font-medium tabular-nums text-text-color-primary">
            {centerValue}
          </span>
          <span className="-mt-0.5 text-[10px] uppercase tracking-wide text-text-color-tertiary">
            {t('skills.overview.radar.centerCaption')}
          </span>
        </div>
      </div>
      <p className="text-footnote text-text-color-tertiary">
        {t('skills.overview.radar.tapHint')}
      </p>
    </section>
  );
}
