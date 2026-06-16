import { useQuery } from '@tanstack/react-query';
import { ChevronLeft } from 'lucide-react';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigate, useNavigate, useParams } from 'react-router-dom';

import {
  CATEGORY_META,
  type CategoryCode,
  isCategoryCode,
} from '@/lib/category-meta';
import { useCurrentSport } from '@/features/sports/useCurrentSport';

import { BlockerCallout } from './components/BlockerCallout';
import { SkillRadar } from './components/SkillRadar';
import { SkillRow } from './components/SkillRow';
import {
  fetchCategoryBlockers,
  fetchCategoryBreakdown,
} from './skills-api';
import type { RadarAxis } from './skills-types';

export function SkillsCategoryScreen() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { categoryCode } = useParams<{ categoryCode: string }>();
  const lang = i18n.language === 'id' ? 'id' : 'en';
  const { currentSportId } = useCurrentSport();

  if (!isCategoryCode(categoryCode ?? '')) {
    return <Navigate to="/skills" replace />;
  }
  const code = categoryCode as CategoryCode;
  const meta = CATEGORY_META[code];

  const { data, isPending } = useQuery({
    queryKey: ['skills', 'me', 'category', code, currentSportId],
    queryFn: () => fetchCategoryBreakdown(code, currentSportId),
    staleTime: 30 * 1000,
  });

  const { data: blockers } = useQuery({
    queryKey: ['skills', 'me', 'category', code, 'blockers', currentSportId],
    queryFn: () => fetchCategoryBlockers(code, currentSportId),
    staleTime: 30 * 1000,
  });

  const axes: RadarAxis[] = useMemo(() => {
    return (data?.skills ?? []).map((s) => {
      const short = lang === 'id' ? s.labelShortId : s.labelShortEn;
      const axis: RadarAxis = {
        code: s.code,
        label: lang === 'id' ? s.labelId : s.labelEn,
        score: s.latestScore,
      };
      if (short) axis.shortLabel = short;
      return axis;
    });
  }, [data, lang]);

  const blockerByCode = useMemo(() => {
    const m = new Map<string, number>();
    for (const b of blockers?.blockersInCategory ?? []) {
      m.set(b.skillCode, b.requiredLevel);
    }
    return m;
  }, [blockers]);

  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-4 px-4 pb-8 pt-3">
      <header className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => navigate('/skills')}
          aria-label={t('common.back')}
          className="-ml-2 flex size-9 items-center justify-center rounded-full text-text-color-secondary"
        >
          <ChevronLeft size={20} strokeWidth={1.75} aria-hidden />
        </button>
        <h1 className="text-h2 text-text-color-primary">
          {lang === 'id' ? meta.labelId : meta.labelEn}
        </h1>
      </header>

      {isPending ? (
        <Skeleton />
      ) : (
        <>
          <section className="flex flex-col items-center gap-3 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
            <SkillRadar
              axes={axes}
              accent={meta.accent}
              size={340}
              ariaLabel={
                lang === 'id' ? meta.labelId : meta.labelEn
              }
            />
            <p className="text-footnote text-text-color-tertiary">
              {t('skills.category.radarHint', {
                assessed: axes.filter((a) => a.score != null).length,
                total: axes.length,
              })}
            </p>
          </section>

          {blockers && blockers.blockersInCategory.length > 0 ? (
            <BlockerCallout
              category={code}
              accent={meta.accent}
              data={blockers}
            />
          ) : null}

          <section className="flex flex-col gap-2">
            <h2 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
              {t('skills.category.listTitle')}
            </h2>
            <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
              {(data?.skills ?? []).map((s, idx) => (
                <SkillRow
                  key={s.code}
                  skill={s}
                  accent={meta.accent}
                  requiredLevel={blockerByCode.get(s.code)}
                  isFirst={idx === 0}
                />
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function Skeleton() {
  return (
    <>
      <div className="h-72 rounded-xl bg-bg-primary" />
      <div className="h-12 rounded-xl bg-bg-primary" />
      <div className="h-40 rounded-xl bg-bg-primary" />
    </>
  );
}
