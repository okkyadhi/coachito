import { useQueryClient } from '@tanstack/react-query';
import { CheckCircle2 } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';

import { useAuthStore } from '@/features/auth/auth-store';
import { postSignInPath } from '@/features/auth/post-signin';

import { InviteClaimError, claimInviteWithToken, stashPendingInvite } from './invite-claim';
import { useInviteToken } from './use-invite-token';

// In-app welcome shown after the trainee taps the invite link with the app
// installed (Step 4a in docs/07).  Pre-signin: carries the workspace branding
// + coach attribution + sign-in CTAs.  After sign-in the user lands on /home
// (role-based dispatch in post-signin.ts).
export function InviteWelcomeScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { token } = useParams<{ token: string }>();
  const { meta, loading } = useInviteToken(token);
  const authToken = useAuthStore((s) => s.token);
  const authUser = useAuthStore((s) => s.user);
  const doSignIn = useAuthStore((s) => s.signIn);
  const doSignOut = useAuthStore((s) => s.signOut);
  const [accepting, setAccepting] = useState(false);
  const [acceptError, setAcceptError] = useState<string | null>(null);

  if (loading) {
    return (
      <main className="flex h-screen items-center justify-center bg-bg-tertiary">
        <p className="text-caption text-text-color-secondary">{t('common.loading')}</p>
      </main>
    );
  }

  if (!meta || meta.state !== 'active') {
    const isExpired = meta?.state === 'expired';
    return (
      <main className="mx-auto flex h-screen w-full max-w-md flex-col items-center justify-center gap-3 bg-bg-tertiary px-6 text-center">
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

  const accent = meta.brandColor ?? undefined;
  const initial = (meta.workspaceName[0] ?? 'R').toUpperCase();

  return (
    <main
      className="mx-auto flex h-screen w-full max-w-md flex-col bg-bg-primary px-6 pb-8 pt-12"
      style={accent ? ({ ['--accent' as never]: accent } as React.CSSProperties) : undefined}
    >
      <div className="flex flex-1 flex-col items-center justify-center gap-4 text-center">
        {/* Logo square */}
        <div
          aria-hidden
          className="flex size-[72px] items-center justify-center rounded-2xl bg-accent text-white"
        >
          {meta.workspaceLogoUrl ? (
            <img
              src={meta.workspaceLogoUrl}
              alt=""
              className="size-full rounded-2xl object-cover"
            />
          ) : (
            <span className="text-h2 text-white">{initial}</span>
          )}
        </div>

        <h1 className="text-h2 text-text-color-primary">
          {meta.traineeFirstName
            ? t('inviteWelcome.greetingWithName', { name: meta.traineeFirstName })
            : t('inviteWelcome.greetingGeneric')}
        </h1>
        <p className="max-w-[300px] text-caption text-text-color-secondary">
          {t('inviteWelcome.subtitle', {
            coach: meta.coachDisplayName ?? t('inviteWelcome.yourCoach'),
            workspace: meta.workspaceName,
          })}
        </p>

        {/* Invite card */}
        <div className="mt-4 flex w-full items-center gap-3 rounded-xl border-[0.5px] border-border-hairline bg-bg-secondary p-3 text-left">
          <div
            aria-hidden
            className="flex size-9 items-center justify-center rounded-md bg-accent text-[14px] font-medium text-white"
          >
            {initial}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-body text-text-color-primary">
              {meta.workspaceName}
            </p>
            <p className="truncate text-footnote text-text-color-secondary">
              {t('inviteWelcome.invitedBy', {
                coach: meta.coachDisplayName ?? t('inviteWelcome.yourCoach'),
              })}
            </p>
          </div>
          <CheckCircle2 size={20} strokeWidth={1.75} className="text-accent" aria-hidden />
        </div>
      </div>

      <div className="flex flex-col gap-2">
        {authToken ? (
          <>
            <p className="mb-1 text-center text-footnote text-text-color-secondary">
              {t('inviteWelcome.signedInAs', {
                email: authUser?.email ?? authUser?.displayName ?? '',
              })}
            </p>
            <PrimaryButton
              loading={accepting}
              onClick={async () => {
                setAcceptError(null);
                setAccepting(true);
                try {
                  const result = await claimInviteWithToken(
                    meta.token,
                    authToken,
                  );
                  doSignIn(result);
                  qc.clear();
                  navigate(
                    postSignInPath(result.workspaceId, result.user.role),
                    { replace: true },
                  );
                } catch (err) {
                  if (err instanceof InviteClaimError) {
                    if (err.status === 410)
                      setAcceptError(t('inviteWelcome.expiredBody'));
                    else if (err.status === 404)
                      setAcceptError(t('inviteWelcome.invalidBody'));
                    else setAcceptError(err.message || t('inviteWelcome.acceptError'));
                  } else {
                    setAcceptError(t('inviteWelcome.acceptError'));
                  }
                } finally {
                  setAccepting(false);
                }
              }}
            >
              {t('inviteWelcome.acceptCta')}
            </PrimaryButton>
            <SecondaryButton
              onClick={() => {
                stashPendingInvite(meta.token);
                doSignOut();
                navigate(`/signin?invite_token=${encodeURIComponent(meta.token)}`);
              }}
            >
              {t('inviteWelcome.useDifferentAccount')}
            </SecondaryButton>
            {acceptError ? (
              <p className="mt-2 text-center text-caption text-danger-text">
                {acceptError}
              </p>
            ) : null}
          </>
        ) : (
          <>
            <PrimaryButton
              onClick={() => {
                stashPendingInvite(meta.token);
                navigate(`/invite/${encodeURIComponent(meta.token)}/signup`);
              }}
            >
              {t('inviteWelcome.createAccountCta')}
            </PrimaryButton>
            <SecondaryButton
              onClick={() => {
                stashPendingInvite(meta.token);
                navigate(`/signin?invite_token=${encodeURIComponent(meta.token)}`);
              }}
            >
              {t('inviteWelcome.haveAccountCta')}
            </SecondaryButton>
            <p className="mt-2 text-center text-footnote text-text-color-tertiary">
              {t('signin.terms')}
            </p>
          </>
        )}
      </div>
    </main>
  );
}
