import { Target } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import type { FocusSuggestion, TierProgress } from '../skills-types';

interface Props {
  focus: FocusSuggestion;
  tier: TierProgress | null;
}

export function FocusCard({ focus, tier }: Props) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'id' ? 'id' : 'en';
  const label = lang === 'id' ? focus.labelId : focus.labelEn;
  const note = lang === 'id' ? focus.latestNoteId : focus.latestNoteEn;
  const nextTier = tier?.next;
  const nextName = nextTier
    ? lang === 'id' ? nextTier.labelId : nextTier.labelEn
    : null;

  const showBody =
    focus.currentLevel != null && focus.requiredLevel != null && nextName;

  return (
    <section
      className="flex gap-3 rounded-xl border-[0.5px] border-border-hairline p-3.5"
      style={{ backgroundColor: 'var(--accent-bg)' }}
    >
      <span
        className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-accent text-white"
        aria-hidden
      >
        <Target size={14} strokeWidth={2} />
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <p className="text-body font-medium text-text-color-primary">
          {t('skills.overview.focus.title', { label })}
        </p>
        <p className="text-caption text-text-color-secondary">
          {showBody
            ? t('skills.overview.focus.body', {
                current: focus.currentLevel,
                required: focus.requiredLevel,
                tier: nextName,
              })
            : t('skills.overview.focus.bodyNoNote')}
        </p>
        {note ? (
          <p className="mt-1 text-caption italic text-text-color-secondary">
            {t('skills.overview.focus.noteQuote', { note })}
          </p>
        ) : null}
      </div>
    </section>
  );
}
