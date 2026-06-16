import { ArrowUpRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import type { RecentGain } from '../skills-types';

interface Props {
  gains: RecentGain[];
}

export function RecentGainsChips({ gains }: Props) {
  const { t, i18n } = useTranslation();
  if (gains.length === 0) return null;
  const lang = i18n.language === 'id' ? 'id' : 'en';

  return (
    <section className="flex flex-col gap-2">
      <h2 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {t('skills.overview.sectionRecentGains')}
      </h2>
      <ul className="flex flex-wrap gap-1.5">
        {gains.map((g) => {
          const label = lang === 'id' ? g.labelId : g.labelEn;
          return (
            <li key={`${g.skillCode}-${g.at}`}>
              <span
                className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[12px] font-medium"
                style={{
                  backgroundColor: 'rgba(15,169,104,0.10)',
                  color: '#0F6E56',
                }}
              >
                <ArrowUpRight size={12} strokeWidth={2} aria-hidden />
                {t('skills.overview.gainEntry', {
                  label,
                  from: g.from,
                  to: g.to,
                })}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
