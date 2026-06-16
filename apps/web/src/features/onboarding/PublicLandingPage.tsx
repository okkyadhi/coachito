import { Apple, ChevronRight, PlayCircle, Smartphone } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';

import { detectOS, useInviteToken } from './use-invite-token';

// Browser-rendered public landing for users who tap the invite link without
// the app installed.  No auth.  OS-aware install CTA.  The BE serves a
// server-rendered HTML variant at /i/:token for OG-unfurl; this SPA route
// (/welcome/:token) is what users see when they continue from the unfurl
// CTA into the actual web app.
export function PublicLandingPage() {
  const { t } = useTranslation();
  const { token } = useParams<{ token: string }>();
  const { meta, loading } = useInviteToken(token);
  const os = detectOS();

  if (loading || !meta) {
    return (
      <main className="flex h-screen items-center justify-center bg-bg-primary">
        <p className="text-caption text-text-color-secondary">{t('common.loading')}</p>
      </main>
    );
  }

  if (meta.state !== 'active') {
    const isExpired = meta.state === 'expired';
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-md flex-col items-center justify-center gap-3 bg-bg-primary px-6 text-center">
        <h1 className="text-h2 text-text-color-primary">
          {t(isExpired ? 'inviteWelcome.expiredTitle' : 'inviteWelcome.invalidTitle')}
        </h1>
        <p className="text-caption text-text-color-secondary">
          {t(isExpired ? 'inviteWelcome.expiredBody' : 'inviteWelcome.invalidBody')}
        </p>
        <Link to="/signin" className="mt-2 text-caption text-accent">
          {t('inviteWelcome.signInLink')}
        </Link>
      </main>
    );
  }

  const accentStyle = meta.brandColor
    ? ({ ['--accent' as never]: meta.brandColor } as React.CSSProperties)
    : undefined;
  const initial = (meta.workspaceName[0] ?? 'R').toUpperCase();
  const primaryIsAndroid = os === 'android';
  const primaryIsIos = os === 'ios';

  return (
    <main className="min-h-screen bg-bg-primary" style={accentStyle}>
      <div className="mx-auto flex w-full max-w-md flex-col gap-6 px-6 pb-12 pt-8">
        {/* Header */}
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div
              aria-hidden
              className="flex size-7 items-center justify-center rounded-md bg-accent text-[12px] font-medium text-white"
            >
              {initial}
            </div>
            <span className="text-caption font-medium text-text-color-primary">
              {meta.workspaceName}
            </span>
          </div>
        </header>

        {/* Hero */}
        <section className="flex flex-col items-center gap-3 text-center">
          <div
            aria-hidden
            className="flex size-[72px] items-center justify-center rounded-2xl bg-accent text-white"
          >
            {meta.workspaceLogoUrl ? (
              <img src={meta.workspaceLogoUrl} alt="" className="size-full rounded-2xl object-cover" />
            ) : (
              <Smartphone size={28} strokeWidth={1.5} aria-hidden />
            )}
          </div>
          <h1
            className="mt-2 text-[26px] font-medium text-text-color-primary"
            style={{ fontFamily: 'Georgia, "Times New Roman", serif', letterSpacing: '-0.3px' }}
          >
            {meta.traineeFirstName
              ? t('publicLanding.heroWithName', { name: meta.traineeFirstName })
              : t('publicLanding.heroGeneric')}
          </h1>
          <p className="max-w-[320px] text-caption text-text-color-secondary">
            {t('publicLanding.description', { workspace: meta.workspaceName })}
          </p>
        </section>

        {/* Coach card */}
        {meta.coachDisplayName ? (
          <section className="flex items-center gap-3 rounded-xl border-[0.5px] border-border-hairline bg-bg-secondary p-3">
            <div
              aria-hidden
              className="flex size-10 items-center justify-center rounded-full bg-accent-bg text-accent"
            >
              <span className="text-h3">
                {(meta.coachDisplayName[0] ?? 'C').toUpperCase()}
              </span>
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-body text-text-color-primary">
                {meta.coachDisplayName}
              </p>
              <p className="truncate text-footnote text-text-color-secondary">
                {meta.workspaceName}
              </p>
            </div>
            <span className="rounded-full bg-accent-bg px-2 py-0.5 text-pill text-accent">
              {t('publicLanding.invitedYou')}
            </span>
          </section>
        ) : null}

        {/* OS-detect callout */}
        {(primaryIsAndroid || primaryIsIos) && (
          <p className="rounded-md bg-bg-secondary px-3 py-2 text-caption text-text-color-secondary">
            {t(primaryIsAndroid ? 'publicLanding.osAndroid' : 'publicLanding.osIos')}
          </p>
        )}

        {/* CTAs */}
        <div className="flex flex-col gap-2">
          <PrimaryButton
            leftIcon={
              primaryIsIos ? (
                <Apple size={18} strokeWidth={1.75} aria-hidden />
              ) : (
                <PlayCircle size={18} strokeWidth={1.75} aria-hidden />
              )
            }
            onClick={() => {
              /* Store links not yet published — gracefully fall through to /signin */
              window.location.href = `/signin?invite_token=${encodeURIComponent(meta.token)}`;
            }}
          >
            {t(primaryIsIos ? 'publicLanding.getOnAppStore' : 'publicLanding.getOnPlay')}
          </PrimaryButton>
          {primaryIsIos || primaryIsAndroid ? (
            <SecondaryButton
              leftIcon={
                primaryIsIos ? (
                  <PlayCircle size={16} strokeWidth={1.75} aria-hidden />
                ) : (
                  <Apple size={16} strokeWidth={1.75} aria-hidden />
                )
              }
              onClick={() => {
                window.location.href = `/signin?invite_token=${encodeURIComponent(meta.token)}`;
              }}
            >
              {t(primaryIsIos ? 'publicLanding.alsoAndroid' : 'publicLanding.alsoIos')}
            </SecondaryButton>
          ) : null}
          <Link
            to={`/signin?invite_token=${encodeURIComponent(meta.token)}`}
            className="inline-flex items-center justify-center gap-1 py-2 text-caption text-accent"
          >
            {t('publicLanding.continueInBrowser')}
            <ChevronRight size={14} strokeWidth={2} aria-hidden />
          </Link>
        </div>

        {/* What happens next */}
        <section className="rounded-xl bg-bg-secondary p-4">
          <h3 className="text-section uppercase tracking-wide text-text-color-secondary">
            {t('traineeHome.whatNext.title')}
          </h3>
          <ol className="mt-2 flex flex-col gap-2">
            {(['s1', 's2', 's3'] as const).map((step, idx) => (
              <li key={step} className="flex items-start gap-3">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-accent-bg text-pill text-accent">
                  {idx + 1}
                </span>
                <p className="text-caption text-text-color-primary">
                  {t(`traineeHome.whatNext.${step}`)}
                </p>
              </li>
            ))}
          </ol>
        </section>

        {/* Meta */}
        <div className="flex flex-col gap-1 text-center text-footnote text-text-color-tertiary">
          <p>{t('publicLanding.expiresInDays', { count: meta.expiresInDays })}</p>
          <p>{t('publicLanding.notMe', { name: meta.traineeFirstName ?? '' })}</p>
        </div>

        <footer className="border-t-[0.5px] border-border-hairline pt-4 text-center text-footnote text-text-color-tertiary">
          {t('publicLanding.poweredBy')}
        </footer>
      </div>
    </main>
  );
}
