import { ChevronDown } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import type { SkillCategory } from '@/features/trainee-profile/profile-types';

import { SkillRow } from './SkillRow';
import type { SkillDescriptors } from './descriptors';

interface Props {
  category: SkillCategory;
  skills: SkillDescriptors[];
  scores: Record<string, number>;
  notes: Record<string, string>;
  expandedSkill: string | null;
  isOpen: boolean;
  onToggleOpen: () => void;
  onSkillLevelChange: (skillCode: string, level: number | null) => void;
  onSkillNoteChange: (skillCode: string, note: string) => void;
  onSkillExpand: (skillCode: string) => void;
}

export function CategoryGroup({
  category,
  skills,
  scores,
  notes,
  expandedSkill,
  isOpen,
  onToggleOpen,
  onSkillLevelChange,
  onSkillNoteChange,
  onSkillExpand,
}: Props) {
  const { t } = useTranslation();
  const ratedCount = skills.filter((s) => scores[s.skillCode] != null).length;
  const allRated = ratedCount === skills.length;
  const noneRated = ratedCount === 0;

  return (
    <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
      <button
        type="button"
        onClick={onToggleOpen}
        aria-expanded={isOpen}
        className="flex min-h-tap w-full items-center justify-between gap-2 px-4 py-3 text-left"
      >
        <span className="flex items-center gap-2 text-h3 text-text-color-primary">
          <span
            aria-hidden
            className={[
              'inline-block size-1.5 rounded-full transition-colors',
              allRated
                ? 'bg-success-text'
                : noneRated
                  ? 'bg-stone-soft'
                  : 'bg-accent',
            ].join(' ')}
          />
          {t(`profile.categories.${category}`)}
        </span>
        <div className="flex items-center gap-2">
          <span className="text-footnote text-text-color-tertiary">
            {ratedCount}/{skills.length}
          </span>
          <ChevronDown
            size={18}
            strokeWidth={1.75}
            className={[
              'shrink-0 text-text-color-tertiary transition-transform duration-150',
              isOpen ? 'rotate-180' : '',
            ].join(' ')}
            aria-hidden
          />
        </div>
      </button>
      {isOpen ? (
        <div className="[&>*+*]:border-[0.5px] [&>*+*]:border-t [&>*+*]:border-border-hairline">
          {skills.map((skill) => (
            <SkillRow
              key={skill.skillCode}
              descriptors={skill}
              level={scores[skill.skillCode] ?? null}
              note={notes[skill.skillCode] ?? ''}
              expanded={expandedSkill === skill.skillCode}
              onLevelChange={(lvl) => onSkillLevelChange(skill.skillCode, lvl)}
              onNoteChange={(n) => onSkillNoteChange(skill.skillCode, n)}
              onToggleExpanded={() => onSkillExpand(skill.skillCode)}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
