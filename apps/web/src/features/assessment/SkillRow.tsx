import { Info } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { DescriptorPanel } from './DescriptorPanel';
import { SegmentedScore } from './SegmentedScore';
import type { SkillDescriptors } from './descriptors';

interface Props {
  descriptors: SkillDescriptors;
  level: number | null;
  note: string;
  expanded: boolean;
  onLevelChange: (level: number | null) => void;
  onNoteChange: (note: string) => void;
  onToggleExpanded: () => void;
}

export function SkillRow({
  descriptors,
  level,
  note,
  expanded,
  onLevelChange,
  onNoteChange,
  onToggleExpanded,
}: Props) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-2.5 p-3">
      <div className="flex items-center gap-2">
        <span className="flex-1 text-body text-text-color-primary">{descriptors.nameEn}</span>
        <ScorePill level={level} />
        <button
          type="button"
          onClick={onToggleExpanded}
          aria-label={
            expanded ? t('assessment.hideDescriptors') : t('assessment.showDescriptors')
          }
          aria-expanded={expanded}
          className={[
            'flex size-9 items-center justify-center rounded-full transition-colors',
            expanded ? 'bg-accent-bg text-accent' : 'text-text-color-tertiary',
          ].join(' ')}
        >
          <Info size={18} strokeWidth={1.75} aria-hidden />
        </button>
      </div>

      <SegmentedScore
        value={level}
        onChange={onLevelChange}
        ariaLabel={`${descriptors.nameEn} score`}
      />

      {expanded ? (
        <DescriptorPanel
          descriptors={descriptors}
          value={level}
          note={note}
          onChange={onLevelChange}
          onNoteChange={onNoteChange}
        />
      ) : null}
    </div>
  );
}

function ScorePill({ level }: { level: number | null }) {
  const { t } = useTranslation();
  if (level == null) {
    return (
      <span className="whitespace-nowrap rounded-full bg-bg-tertiary px-2 py-0.5 text-pill text-text-color-tertiary">
        {t('assessment.notRated')}
      </span>
    );
  }
  return (
    <span className="whitespace-nowrap rounded-full bg-accent-bg px-2 py-0.5 text-pill text-accent">
      {level} · {t(`assessment.levels.${level}`)}
    </span>
  );
}
