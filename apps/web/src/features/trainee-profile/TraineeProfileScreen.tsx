import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  CalendarPlus,
  ChevronLeft,
  ClipboardCheck,
  FileText,
  Radar,
} from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';
import { useAuthStore } from '@/features/auth/auth-store';
import { GenerateReportSheet } from '@/features/reports/GenerateReportSheet';
import { generateReport } from '@/features/reports/reports-api';
import { SportTabs } from '@/features/sports/SportTabs';
import { useCurrentSport } from '@/features/sports/useCurrentSport';

import { AllSkillsAccordion } from './AllSkillsAccordion';
import { BlockingSkillsList } from './BlockingSkillsList';
import { HeroBlock } from './HeroBlock';
import { RecentGains } from './RecentGains';
import { RecentSessions } from './RecentSessions';
import { SkillRadar } from './SkillRadar';
import { StatsGrid } from './StatsGrid';
import { TierProgressCard } from './TierProgressCard';
import { fetchTraineeProfile, hasAnyAssessment } from './profile-api';

export function TraineeProfileScreen() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const user = useAuthStore((s) => s.user);
  const locale = user?.preferredLocale ?? i18n.language ?? 'en';
  const queryClient = useQueryClient();
  const [reportOpen, setReportOpen] = useState(false);
  const { currentSportId, isMultiSport } = useCurrentSport();

  const { data, isPending } = useQuery({
    queryKey: ['trainee-profile', id, currentSportId],
    queryFn: () => fetchTraineeProfile(id ?? '', currentSportId ?? undefined),
    enabled: !!id,
  });

  if (isPending) return <SkeletonProfile />;
  if (!data) return null;

  const hasData = hasAnyAssessment(data);

  return (
    <div className="mx-auto w-full max-w-md px-4 pb-6 pt-3">
      {/* Top nav: < Trainees */}
      <button
        type="button"
        onClick={() => navigate('/trainees')}
        className="-ml-2 mb-1 flex min-h-[36px] items-center gap-0.5 px-2 py-1 text-caption text-accent"
      >
        <ChevronLeft size={18} strokeWidth={2} aria-hidden />
        <span>{t('profile.backLabel')}</span>
      </button>

      <HeroBlock
        displayName={data.trainee.displayName}
        joinedAt={data.trainee.joinedAt}
        tier={data.tierProgress.currentTier}
        locale={locale}
      />

      {isMultiSport ? (
        <div className="mb-4 mt-2">
          <SportTabs />
        </div>
      ) : null}

      <div className="mb-5">
        <StatsGrid
          sessionsCount={data.stats.sessionsCount}
          hoursCoached={data.stats.hoursCoached}
          daysSinceLastSession={data.stats.daysSinceLastSession}
        />
      </div>

      {hasData ? (
        <div className="flex flex-col gap-6">
          <TierProgressCard
            currentTier={data.tierProgress.currentTier}
            nextTier={data.tierProgress.nextTier}
            metCount={data.tierProgress.metCount}
            totalRequirements={data.tierProgress.totalRequirements}
            blockingCount={data.tierProgress.blockingSkills.length}
            locale={locale}
          />
          <BlockingSkillsList
            blockers={data.tierProgress.blockingSkills}
            nextTier={data.tierProgress.nextTier}
            locale={locale}
          />
          <SkillRadar averages={data.categoryAverages} />
          <RecentGains gains={data.recentGains} locale={locale} />
          <AllSkillsAccordion skills={data.allSkills} locale={locale} />
          <RecentSessions
            sessions={data.recentSessions}
            locale={locale}
            athleteId={data.trainee.id}
          />
        </div>
      ) : (
        <EmptyState
          onStartAssessment={() => navigate(`/trainees/${data.trainee.id}/assess`)}
        />
      )}

      {/* In-flow action bar */}
      <div className="mt-6 flex flex-col gap-2">
        <PrimaryButton
          leftIcon={<ClipboardCheck size={18} strokeWidth={1.75} aria-hidden />}
          onClick={() => navigate(`/trainees/${data.trainee.id}/assess`)}
        >
          {t('profile.actions.newAssessment')}
        </PrimaryButton>
        <SecondaryButton
          leftIcon={<CalendarPlus size={18} strokeWidth={1.75} aria-hidden />}
          onClick={() => navigate('/sessions')}
        >
          {t('profile.actions.schedule')}
        </SecondaryButton>
        <SecondaryButton
          leftIcon={<FileText size={18} strokeWidth={1.75} aria-hidden />}
          onClick={() => setReportOpen(true)}
        >
          {t('profile.actions.generateReport')}
        </SecondaryButton>
      </div>

      <GenerateReportSheet
        open={reportOpen}
        initialTraineeId={data.trainee.id}
        initialTraineeName={data.trainee.displayName}
        onClose={() => setReportOpen(false)}
        onConfirm={async (args) => {
          await generateReport(
            args.mode === 'session' && args.sessionId
              ? { traineeId: args.traineeId, sessionId: args.sessionId }
              : {
                  traineeId: args.traineeId,
                  periodStart: args.periodStart ?? '',
                  periodEnd: args.periodEnd ?? '',
                },
          );
          setReportOpen(false);
          void queryClient.invalidateQueries({ queryKey: ['reports'] });
          navigate('/reports');
        }}
      />
    </div>
  );
}

function EmptyState({ onStartAssessment }: { onStartAssessment: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center gap-3 pt-8 text-center">
      <div className="flex size-[60px] items-center justify-center rounded-full border-[0.5px] border-border-hairline bg-bg-secondary">
        <Radar aria-hidden size={26} strokeWidth={1.5} className="text-text-color-tertiary" />
      </div>
      <h2 className="mt-2 text-h3 text-text-color-primary">{t('profile.empty.title')}</h2>
      <p className="max-w-[260px] text-caption text-text-color-secondary">
        {t('profile.empty.body')}
      </p>
      <div className="mt-2 flex w-full max-w-[240px]">
        <PrimaryButton onClick={onStartAssessment}>
          {t('profile.empty.startCta')}
        </PrimaryButton>
      </div>
    </div>
  );
}

function SkeletonProfile() {
  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-5 px-4 pb-6 pt-12">
      <div className="mx-auto size-16 rounded-full bg-bg-primary" />
      <div className="mx-auto h-6 w-40 rounded bg-bg-primary" />
      <div className="grid grid-cols-3 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className={[
              'flex h-20 items-center justify-center',
              i > 0 ? 'border-l-[0.5px] border-border-hairline' : '',
            ].join(' ')}
          >
            <div className="h-3 w-12 rounded bg-bg-tertiary" />
          </div>
        ))}
      </div>
      <div className="h-32 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary" />
      <div className="h-60 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary" />
    </div>
  );
}
