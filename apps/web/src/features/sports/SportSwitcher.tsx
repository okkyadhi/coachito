import { Check, ChevronDown } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { sportLabel } from './sports-api';
import { useCurrentSport } from './useCurrentSport';

// Chip in the coach shell header that switches the active sport.  Hidden for
// single-sport workspaces (the context is invisible there).  Mirrors the
// WorkspaceSwitcher pill + bottom-sheet pattern.
export function SportSwitcher() {
  const { t, i18n } = useTranslation();
  const { sports, currentSportId, current, isMultiSport, setSport } =
    useCurrentSport();
  const [open, setOpen] = useState(false);

  if (!isMultiSport) return null;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={t('multisport.switcherLabel')}
        className="flex items-center gap-1 rounded-full border-[0.5px] border-border-hairline bg-bg-secondary px-2.5 py-0.5 text-caption text-text-color-primary"
      >
        <span className="truncate">
          {current ? sportLabel(current, i18n.language) : '—'}
        </span>
        <ChevronDown
          size={13}
          strokeWidth={1.75}
          aria-hidden
          className="shrink-0 text-text-color-tertiary"
        />
      </button>

      {open ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={t('multisport.switcherTitle')}
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 sm:items-center"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="flex w-full max-w-md flex-col gap-1 rounded-t-2xl bg-bg-primary p-2 sm:rounded-2xl"
          >
            <h3 className="px-3 py-2 text-section uppercase tracking-wide text-text-color-secondary">
              {t('multisport.switcherTitle')}
            </h3>
            {sports.map((s) => (
              <button
                key={s.sportId}
                type="button"
                onClick={() => {
                  setSport(s.sportId);
                  setOpen(false);
                }}
                className="flex min-h-tap items-center gap-3 rounded-md px-3 py-2 text-left hover:bg-bg-secondary"
              >
                <span className="flex-1 text-body text-text-color-primary">
                  {sportLabel(s, i18n.language)}
                </span>
                {s.sportId === currentSportId ? (
                  <Check
                    size={16}
                    strokeWidth={1.75}
                    aria-hidden
                    className="text-accent"
                  />
                ) : (
                  <span className="size-4" aria-hidden />
                )}
              </button>
            ))}
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="mt-1 min-h-tap rounded-md py-2 text-center text-body text-text-color-secondary"
            >
              {t('common.cancel')}
            </button>
          </div>
        </div>
      ) : null}
    </>
  );
}
