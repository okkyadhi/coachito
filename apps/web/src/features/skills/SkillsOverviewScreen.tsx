import { useQuery } from '@tanstack/react-query';
import { Radar } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import {
  CATEGORY_META,
  CATEGORY_ORDER,
  type CategoryCode,
} from '@/lib/category-meta';
import { SportTabs } from '@/features/sports/SportTabs';
import { useCurrentSport } from '@/features/sports/useCurrentSport';

import { CategoryListRow } from './components/CategoryListRow';
import { FocusCard } from './components/FocusCard';
import { HeroStats } from './components/HeroStats';
import { RadarCard } from './components/RadarCard';
import { RecentGainsChips } from './components/RecentGainsChips';
import { TierStrip } from './components/TierStrip';
import { fetchSkillsOverview } from './skills-api';
import type {
  CategoryScore,
  OverallProgress,
  RadarAxis,
  SkillsOverview,
} from './skills-types';

const EMPTY_OVERALL: OverallProgress = {
  average: null,
  assessedCount: 0,
  totalCount: 0,
  lastAssessedAt: null,
};

const EMPTY_CATEGORIES: CategoryScore[] = CATEGORY_ORDER.map((c) => ({
  category: c,
  average: null,
  assessedCount: 0,
  totalCount: 0,
}));

export function SkillsOverviewScreen() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const lang = i18n.language === 'id' ? 'id' : 'en';
  const { currentSportId, isMultiSport } = useCurrentSport();

  const { data, isPending } = useQuery({
    queryKey: ['skills', 'me', 'overview', currentSportId],
    queryFn: () => fetchSkillsOverview(currentSportId),
    staleTime: 20 * 1000,
  });

  if (isPending) return <Skeleton />;

  const view: SkillsOverview = data ?? {
    categories: EMPTY_CATEGORIES,
    overall: EMPTY_OVERALL,
    tier: null,
    recentGains: [],
    focusSuggestion: null,
    updatedAt: null,
  };

  const anyAssessed = view.overall.assessedCount > 0;
  const onPick = (code: CategoryCode) => navigate(`/skills/${code}`);

  const axes: RadarAxis[] = CATEGORY_ORDER.map((code) => {
    const c = view.categories.find((x) => x.category === code);
    return {
      code,
      label: lang === 'id' ? CATEGORY_META[code].labelId : CATEGORY_META[code].labelEn,
      score: c?.average ?? null,
    };
  });

  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-3 px-4 pb-8 pt-4">
      <header className="px-1">
        <h1 className="text-[28px] font-medium -tracking-tight text-text-color-primary">
          {t('skills.overview.title')}
        </h1>
        <p className="mt-0.5 text-caption text-text-color-secondary">
          {t('skills.overview.subtitle')}
        </p>
      </header>

      {isMultiSport ? <SportTabs /> : null}

      {anyAssessed && view.tier ? (
        <TierStrip tier={view.tier} />
      ) : (
        <EmptyHero />
      )}

      <HeroStats overall={view.overall} />

      <RadarCard axes={axes} overall={view.overall} onPick={onPick} />

      <section className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
        {CATEGORY_ORDER.map((code, idx) => {
          const score =
            view.categories.find((c) => c.category === code) ??
            EMPTY_CATEGORIES[idx]!;
          return (
            <CategoryListRow
              key={code}
              score={score}
              onTap={onPick}
              borderTop={idx > 0}
            />
          );
        })}
      </section>

      <RecentGainsChips gains={view.recentGains} />

      {view.focusSuggestion ? (
        <FocusCard focus={view.focusSuggestion} tier={view.tier} />
      ) : null}
    </div>
  );
}

function EmptyHero() {
  const { t } = useTranslation();
  return (
    <section className="flex items-start gap-3 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-full border-[0.5px] border-border-hairline bg-bg-secondary text-text-color-tertiary">
        <Radar size={18} strokeWidth={1.5} aria-hidden />
      </span>
      <div className="flex flex-col gap-0.5">
        <h2 className="text-h3 text-text-color-primary">
          {t('skills.overview.emptyHeroTitle')}
        </h2>
        <p className="text-caption text-text-color-secondary">
          {t('skills.overview.emptyHeroBody')}
        </p>
      </div>
    </section>
  );
}

function Skeleton() {
  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-3 px-4 pt-4">
      <div className="px-1">
        <div className="h-7 w-32 rounded bg-bg-primary" />
        <div className="mt-1 h-3 w-40 rounded bg-bg-primary" />
      </div>
      <div className="h-20 rounded-xl bg-bg-primary" />
      <div className="grid grid-cols-3 gap-2">
        <div className="h-16 rounded-lg bg-bg-primary" />
        <div className="h-16 rounded-lg bg-bg-primary" />
        <div className="h-16 rounded-lg bg-bg-primary" />
      </div>
      <div className="h-72 rounded-xl bg-bg-primary" />
      <div className="h-56 rounded-xl bg-bg-primary" />
      <div className="h-20 rounded-xl bg-bg-primary" />
    </div>
  );
}
