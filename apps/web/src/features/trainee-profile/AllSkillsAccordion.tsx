import { ChevronDown } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import type { SkillCategory, SkillScore } from './profile-types';

interface Props {
  skills: SkillScore[];
  locale: string;
}

const ORDERED_CATEGORIES: SkillCategory[] = ['technical', 'tactical', 'physical', 'mental'];

const LEVEL_LABEL: Record<number, string> = {
  1: 'Learning',
  2: 'Developing',
  3: 'Functional',
  4: 'Proficient',
  5: 'Mastery',
};

export function AllSkillsAccordion({ skills, locale }: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState<Set<SkillCategory>>(new Set(['technical']));

  const allOpen = ORDERED_CATEGORIES.every((c) => open.has(c));

  const toggleCategory = (c: SkillCategory) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(c)) next.delete(c);
      else next.add(c);
      return next;
    });

  const toggleAll = () => {
    if (allOpen) setOpen(new Set());
    else setOpen(new Set(ORDERED_CATEGORIES));
  };

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-baseline justify-between px-1">
        <h2 className="text-section uppercase tracking-wide text-text-color-secondary">
          {t('profile.allSkills.title')}
        </h2>
        <button
          type="button"
          onClick={toggleAll}
          className="text-caption text-accent"
        >
          {allOpen ? t('profile.allSkills.collapseAll') : t('profile.allSkills.expandAll')}
        </button>
      </div>

      <div className="flex flex-col gap-3">
        {ORDERED_CATEGORIES.map((category) => (
          <CategoryGroup
            key={category}
            category={category}
            skills={skills.filter((s) => s.skill.category === category)}
            isOpen={open.has(category)}
            onToggle={() => toggleCategory(category)}
            locale={locale}
          />
        ))}
      </div>
    </section>
  );
}

function CategoryGroup({
  category,
  skills,
  isOpen,
  onToggle,
  locale,
}: {
  category: SkillCategory;
  skills: SkillScore[];
  isOpen: boolean;
  onToggle: () => void;
  locale: string;
}) {
  const { t } = useTranslation();
  const ratedCount = skills.filter((s) => s.level != null).length;

  return (
    <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isOpen}
        className="flex min-h-tap w-full items-center justify-between gap-2 px-4 py-3 text-left"
      >
        <span className="text-h3 text-text-color-primary">
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
          {skills
            .sort((a, b) => a.skill.displayOrder - b.skill.displayOrder)
            .map((score) => (
              <SkillRow key={score.skill.id} score={score} locale={locale} />
            ))}
        </div>
      ) : null}
    </div>
  );
}

function SkillRow({ score, locale: _locale }: { score: SkillScore; locale: string }) {
  const { t } = useTranslation();
  // Skill names stay EN in both locales by product convention.
  const name = score.skill.nameEn;
  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <div className="min-w-0 flex-1">
        <p className="truncate text-body text-text-color-primary">{name}</p>
        <p className="text-caption text-text-color-secondary">
          {score.level == null
            ? t('profile.allSkills.notRated')
            : `${score.level} · ${LEVEL_LABEL[score.level] ?? ''}`}
        </p>
      </div>
      <MiniBar level={score.level} />
    </div>
  );
}

function MiniBar({ level }: { level: number | null }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <span
          key={n}
          className={[
            'h-3 w-2 rounded-sm border-[0.5px] border-border-hairline',
            level != null && n <= level ? 'bg-accent' : 'bg-transparent',
          ].join(' ')}
        />
      ))}
    </div>
  );
}
