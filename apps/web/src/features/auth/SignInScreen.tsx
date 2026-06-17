import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import {
  consumePendingInvite,
  stashPendingInvite,
} from '@/features/onboarding/invite-claim';

import { EditorialHeader } from '@/components/EditorialHeader';
import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';
import { TextInput } from '@/components/TextInput';

import { ApiError } from '@/lib/api';

import { sendMagicLink, signInWithPassword } from './auth-api';
import { useAuthStore } from './auth-store';
import { postSignInPath } from './post-signin';

type View = 'password' | 'magic-sent';

// Email + password as primary path; "Send magic link" as a fallback for users
// who can't remember their password and don't want to do the full forgot/reset
// dance. Google is hidden (disabled via ENABLE_GOOGLE_OAUTH on the backend).
export function SignInScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const signIn = useAuthStore((s) => s.signIn);
  const [searchParams] = useSearchParams();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [view, setView] = useState<View>('password');
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [magicLoading, setMagicLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Capture invite_token (if any) so it survives the auth round-trip.
  useEffect(() => {
    stashPendingInvite(searchParams.get('invite_token'));
  }, [searchParams]);

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    setError(null);
    setPasswordLoading(true);
    try {
      const signed = await signInWithPassword(email.trim(), password);
      const result = await consumePendingInvite(signed);
      signIn(result);
      navigate(postSignInPath(result.workspaceId, result.user.role), {
        replace: true,
      });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('signin.passwordError'));
    } finally {
      setPasswordLoading(false);
    }
  };

  const handleSendMagicLink = async () => {
    if (!email) return;
    setError(null);
    setMagicLoading(true);
    try {
      await sendMagicLink(email.trim());
      setView('magic-sent');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('signin.sendError'));
    } finally {
      setMagicLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col bg-bg-tertiary">
      <div className="mx-auto flex w-full max-w-sm flex-1 flex-col px-6 pb-8 pt-16">
        <EditorialHeader
          title={view === 'magic-sent' ? t('signin.checkYourEmail') : t('signin.title')}
          subtitle={
            view === 'magic-sent'
              ? t('signin.checkYourEmailBody', { email })
              : t('signin.subtitle')
          }
          logoSize={68}
        />

        {view === 'magic-sent' ? (
          <div className="mt-10 flex flex-col gap-3">
            <div className="rounded-lg border-[0.5px] border-border-hairline bg-bg-primary p-4">
              <p className="text-caption text-text-color-secondary">
                {t('signin.checkSpam')}
              </p>
            </div>
            <SecondaryButton onClick={() => setView('password')}>
              {t('signin.backToPassword')}
            </SecondaryButton>
          </div>
        ) : (
          <form onSubmit={handlePasswordLogin} className="mt-10 flex flex-col gap-3">
            <TextInput
              type="email"
              autoComplete="email"
              autoFocus
              required
              label={t('signin.emailLabel')}
              placeholder={t('signin.emailPlaceholder')}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <TextInput
              type="password"
              autoComplete="current-password"
              required
              label={t('signin.passwordLabel')}
              placeholder={t('signin.passwordPlaceholder')}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />

            {error ? (
              <div
                role="alert"
                className="rounded-md border-[0.5px] border-danger-text bg-danger-bg p-3"
              >
                <p className="text-caption text-danger-text">{error}</p>
              </div>
            ) : null}

            <PrimaryButton
              type="submit"
              loading={passwordLoading}
              disabled={!email || !password}
              className="mt-2"
            >
              {t('signin.signInWithPassword')}
            </PrimaryButton>

            <SecondaryButton
              type="button"
              onClick={() => void handleSendMagicLink()}
              loading={magicLoading}
              disabled={!email}
            >
              {t('signin.sendMagicLink')}
            </SecondaryButton>

            <Link
              to="/auth/forgot"
              className="min-h-tap py-2 text-center text-caption text-accent"
            >
              {t('signin.forgotPassword')}
            </Link>
          </form>
        )}

        <div className="flex-1" />

        <div className="mt-6 flex flex-col items-center gap-3">
          <p className="text-center text-footnote text-text-color-tertiary">
            {t('signin.terms')}
          </p>
          <p className="text-footnote text-text-color-secondary">
            {t('signin.noAccount')}{' '}
            <Link to="/signup" className="text-accent">
              {t('signin.signUpLink')}
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
