import { useTranslation } from 'react-i18next';

import { sportLabel } from './sports-api';
import { useCurrentSport } from './useCurrentSport';

// Inline sport switcher for screens that are sport-scoped (Curriculum, Tiers).
// Hidden for single-sport workspaces — no visible change in the common case.
export function SportTabs() {
  const { i18n } = useTranslation();
  const { sports, currentSportId, isMultiSport, setSport } = useCurrentSport();

  if (!isMultiSport) return null;

  return (
    <div
      role="tablist"
      className="flex gap-1 rounded-md border-[0.5px] border-border-hairline bg-bg-tertiary p-1"
    >
      {sports.map((s) => {
        const active = s.sportId === currentSportId;
        return (
          <button
            key={s.sportId}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => setSport(s.sportId)}
            className={[
              'min-h-tap flex-1 rounded-sm px-3 text-[14px] font-medium transition-colors duration-100',
              active
                ? 'border-[0.5px] border-accent bg-bg-primary text-accent'
                : 'text-text-color-secondary',
            ].join(' ')}
          >
            {sportLabel(s, i18n.language)}
          </button>
        );
      })}
    </div>
  );
}
