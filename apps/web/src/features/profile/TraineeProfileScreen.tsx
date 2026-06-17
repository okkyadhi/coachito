import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ChevronRight, FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { useAuthStore } from '@/features/auth/auth-store';
import { fetchMyReports } from '@/features/trainee-reports/reports-api';

import { AccountSection } from './sections/AccountSection';
import { DangerSection } from './sections/DangerSection';
import { IdentitySection } from './sections/IdentitySection';
import { NotificationsSection } from './sections/NotificationsSection';
import { PersonalSection } from './sections/PersonalSection';
import { getMe, patchMe, type MePatch, type MeProfile } from './profile-api';

export function TraineeProfileScreen() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const signOut = useAuthStore((s) => s.signOut);
  const role = useAuthStore((s) => s.user?.role ?? null);

  const { data, isPending } = useQuery({
    queryKey: ['me'],
    queryFn: getMe,
    staleTime: 60 * 1000,
  });

  // Reports row only shows once the trainee has at least one report.
  // Dedup'd cache with the list screen — opening /me/reports later will
  // reuse this data.  Skipped for coach / admin users; they have their
  // own /reports surface under the coach shell.
  const isTrainee = role === 'trainee' || role === 'parent';
  const { data: reports } = useQuery({
    queryKey: ['trainee', 'me', 'reports'],
    queryFn: fetchMyReports,
    enabled: isTrainee,
    staleTime: 60 * 1000,
  });

  const mutation = useMutation({
    mutationFn: (patch: MePatch) => patchMe(patch),
    onSuccess: (next) => {
      qc.setQueryData(['me'], next);
      // Flip i18next + persisted user state when locale changes server-side.
      if (i18n.language !== next.preferredLocale) {
        void i18n.changeLanguage(next.preferredLocale);
      }
      const auth = useAuthStore.getState();
      if (auth.user) {
        auth.signIn({
          token: auth.token!,
          refreshToken: auth.refreshToken!,
          user: { ...auth.user, displayName: next.displayName, preferredLocale: next.preferredLocale },
          workspaceId: auth.currentWorkspaceId,
        });
      }
    },
  });

  const onSave = async (patch: MePatch) => {
    await mutation.mutateAsync(patch);
  };

  const onSignOut = () => {
    signOut();
    navigate('/signin', { replace: true });
  };

  if (isPending || !data) return <Skeleton />;
  const me: MeProfile = data;

  return (
    <main className="mx-auto flex w-full max-w-md flex-col gap-5 px-4 pb-8 pt-4">
      <header className="px-1">
        <h1 className="text-large-title text-text-color-primary">
          {t('me.title')}
        </h1>
      </header>

      <IdentitySection
        displayName={me.displayName}
        avatarUrl={me.avatarUrl}
        onSave={onSave}
      />

      <AccountSection
        email={me.email}
        preferredLocale={me.preferredLocale}
        summaryStyle={me.summaryStyle}
        showSummaryStyle={role !== 'trainee' && role !== 'parent'}
        onSave={onSave}
      />

      <PersonalSection
        dateOfBirth={me.dateOfBirth}
        isMinor={me.isMinor}
        guardianName={me.primaryGuardian?.displayName ?? null}
      />

      {isTrainee && (reports?.length ?? 0) > 0 ? (
        <ReportsLink count={reports!.length} onTap={() => navigate('/me/reports')} />
      ) : null}

      <NotificationsSection
        prefs={me.notifications}
        onSave={(n) => onSave({ notifications: n })}
      />

      <DangerSection onSignOut={onSignOut} />
    </main>
  );
}

function ReportsLink({
  count,
  onTap,
}: {
  count: number;
  onTap: () => void;
}) {
  const { t } = useTranslation();
  return (
    <section className="flex flex-col gap-2">
      <h2 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {t('trainee.reports.title')}
      </h2>
      <button
        type="button"
        onClick={onTap}
        className="flex min-h-tap w-full items-center gap-3 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4 text-left active:bg-bg-secondary"
      >
        <span
          className="flex size-9 shrink-0 items-center justify-center rounded-full bg-accent-bg text-accent"
          aria-hidden
        >
          <FileText size={18} strokeWidth={1.75} />
        </span>
        <div className="flex-1">
          <p className="text-body text-text-color-primary">
            {t('trainee.reports.title')}
          </p>
          <p className="text-footnote text-text-color-secondary">
            {t('trainee.reports.subtitle')}
          </p>
        </div>
        <span className="text-caption tabular-nums text-text-color-tertiary">
          {count}
        </span>
        <ChevronRight
          size={16}
          strokeWidth={1.75}
          className="text-text-color-tertiary"
          aria-hidden
        />
      </button>
    </section>
  );
}

function Skeleton() {
  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-4 px-4 pt-6">
      <div className="h-7 w-36 rounded bg-bg-primary" />
      <div className="h-24 rounded-xl bg-bg-primary" />
      <div className="h-32 rounded-xl bg-bg-primary" />
      <div className="h-24 rounded-xl bg-bg-primary" />
      <div className="h-24 rounded-xl bg-bg-primary" />
    </div>
  );
}
