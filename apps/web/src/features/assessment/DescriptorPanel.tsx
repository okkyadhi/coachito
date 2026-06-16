import { useTranslation } from 'react-i18next';

import type { SkillDescriptors } from './descriptors';

interface Props {
  descriptors: SkillDescriptors;
  value: number | null;
  note: string;
  onChange: (level: number | null) => void;
  onNoteChange: (note: string) => void;
}

// Expanded panel: 5 stacked level cards (tappable to set score) + a note
// textarea.  Currently-selected card is accent-bordered.
export function DescriptorPanel({
  descriptors,
  value,
  note,
  onChange,
  onNoteChange,
}: Props) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-3 px-3 pb-3">
      <div className="flex flex-col gap-2">
        {descriptors.descriptions.map((text, idx) => {
          const level = idx + 1;
          const selected = value === level;
          return (
            <button
              key={level}
              type="button"
              onClick={() => onChange(selected ? null : level)}
              className={[
                'flex gap-3 rounded-md p-3 text-left transition-colors',
                selected
                  ? 'border-[0.5px] border-accent bg-accent-bg'
                  : 'border-[0.5px] border-border-hairline bg-bg-primary',
              ].join(' ')}
            >
              <span
                aria-hidden
                className={[
                  'flex size-6 shrink-0 items-center justify-center rounded-full',
                  'text-[12px] font-medium',
                  selected ? 'bg-accent text-white' : 'bg-bg-tertiary text-text-color-secondary',
                ].join(' ')}
              >
                {level}
              </span>
              <div className="flex flex-col gap-0.5">
                <span
                  className={[
                    'text-caption font-medium',
                    selected ? 'text-accent' : 'text-text-color-primary',
                  ].join(' ')}
                >
                  {t(`assessment.levels.${level}`)}
                </span>
                <span className="text-footnote leading-snug text-text-color-secondary">
                  {text}
                </span>
              </div>
            </button>
          );
        })}
      </div>

      <label className="flex flex-col gap-1.5">
        <span className="text-section text-text-color-secondary">
          {t('assessment.noteLabel')}
        </span>
        <textarea
          rows={2}
          value={note}
          onChange={(e) => onNoteChange(e.target.value)}
          placeholder={t('assessment.notePlaceholder', { skill: descriptors.nameEn })}
          className="resize-y rounded-sm border-[0.5px] border-border-hairline bg-bg-primary p-2 text-body text-text-color-primary placeholder:text-text-color-tertiary focus:border-accent focus:outline-none"
        />
      </label>
    </div>
  );
}
