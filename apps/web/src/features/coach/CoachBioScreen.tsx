import { useQuery } from '@tanstack/react-query';
import { ChevronLeft } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Navigate, useNavigate, useParams } from 'react-router-dom';

import { BioAbout } from './components/BioAbout';
import { BioCredentials } from './components/BioCredentials';
import { BioHeader } from './components/BioHeader';
import { BioSpecialties } from './components/BioSpecialties';
import { fetchCoachProfile } from './coach-api';

export function CoachBioScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { coachId } = useParams<{ coachId: string }>();

  const { data, isPending, isError } = useQuery({
    queryKey: ['coach', coachId],
    queryFn: () => fetchCoachProfile(coachId!),
    enabled: !!coachId,
    staleTime: 60 * 1000,
  });

  if (!coachId) return <Navigate to="/coach" replace />;
  if (isError) return <Navigate to="/coach" replace />;
  if (isPending || !data) return <Skeleton />;

  return (
    <main className="mx-auto flex w-full max-w-md flex-col gap-5 px-4 pb-8 pt-3">
      <button
        type="button"
        onClick={() => navigate('/coach')}
        className="-ml-2 flex min-h-[36px] items-center gap-0.5 px-2 py-1 text-caption text-accent"
        aria-label={t('common.back')}
      >
        <ChevronLeft size={18} strokeWidth={2} aria-hidden />
        <span>{t('coach.bio.backLabel')}</span>
      </button>

      <BioHeader coach={data} />

      {data.bio.about ? <BioAbout about={data.bio.about} /> : null}

      <BioCredentials
        yearsCoaching={data.bio.yearsCoaching}
        certifications={data.bio.certifications}
        languages={data.bio.languages}
      />

      <BioSpecialties specialties={data.bio.specialties} />

      <footer className="px-1 text-footnote text-text-color-tertiary">
        {t('coach.bio.coachedCount', { count: data.coachedTraineesCount })}
      </footer>
    </main>
  );
}

function Skeleton() {
  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-4 px-4 pt-6">
      <div className="h-44 rounded-xl bg-bg-primary" />
      <div className="h-32 rounded-xl bg-bg-primary" />
      <div className="h-24 rounded-xl bg-bg-primary" />
    </div>
  );
}
