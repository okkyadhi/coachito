import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { PrimaryButton } from '@/components/PrimaryButton';
import { TextInput } from '@/components/TextInput';

import { signUpTraineeViaInvite } from '@/features/auth/auth-api';
import { useAuthStore } from '@/features/auth/auth-store';
import { postSignInPath } from '@/features/auth/post-signin';
import { ApiError } from '@/lib/api';

import { clearPendingInvite } from './invite-claim';
import { useInviteToken } from './use-invite-token';

// Trainee self-signup via invite token. POSTs /invites/:token/signup which
// creates the user + claims the invite atomically and returns a workspace-
// scoped TokenPair, so we sign in directly.
export function InviteSignupScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { token } = useParams<{ token: string }>();
  const { meta, loading: metaLoading } = useInviteToken(token);
  const signIn = useAuthStore((s) => s.signIn);

  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!token) {
    return (
      <main className="flex h-screen items-center justify-center bg-bg-tertiary">
        <p className="text-caption text-text-color-secondary">
          {t('inviteWelcome.invalidTitle')}
        </p>
      </main>
    );
  }

  if (metaLoading) {
    return (
      <main className="flex h-screen items-center justify-center bg-bg-tertiary">
        <p className="text-caption text-text-color-secondary">
          {t('common.loading')}
        </p>
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!displayName || !email || !password) return;
    setError(null);
    setSubmitting(true);
    try {
      const result = await signUpTraineeViaInvite({
        token,
        displayName: displayName.trim(),
        email: email.trim(),
        password,
      });
      clearPendingInvite();
      signIn(result);
      navigate(postSignInPath(result.workspaceId, result.user.role), {
        replace: true,
      });
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) setError(t('inviteSignup.emailTakenError'));
        else if (err.status === 410 || err.status === 404)
          setError(t('inviteSignup.inviteInvalidError'));
        else setError(err.message || t('inviteSignup.genericError'));
      } else {
        setError(t('inviteSignup.genericError'));
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main
      className="mx-auto flex min-h-screen w-full max-w-md flex-col bg-bg-tertiary px-6 pb-8 pt-12"
      style={accent ? ({ ['--accent' as never]: accent } as React.CSSProperties) : undefined}
    >
      <div className="flex flex-col items-center gap-3 text-center">
        <h1 className="text-large-title text-text-color-primary">
          {t('inviteSignup.title')}
        </h1>
        <p className="max-w-[320px] text-body text-text-color-secondary">
          {meta.workspaceName
            ? t('inviteSignup.subtitleWithWorkspace', { workspace: meta.workspaceName })
            : t('inviteSignup.subtitle')}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="mt-10 flex flex-col gap-3">
        <TextInput
          autoComplete="name"
          autoFocus
          required
          label={t('inviteSignup.displayNameLabel')}
          placeholder={t('inviteSignup.displayNamePlaceholder')}
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
        />
        <TextInput
          type="email"
          autoComplete="email"
          required
          label={t('inviteSignup.emailLabel')}
          placeholder={t('inviteSignup.emailPlaceholder')}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <TextInput
          type="password"
          autoComplete="new-password"
          required
          label={t('inviteSignup.passwordLabel')}
          placeholder={t('inviteSignup.passwordPlaceholder')}
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
          loading={submitting}
          disabled={!displayName || !email || password.length < 8}
          className="mt-2"
        >
          {submitting ? t('inviteSignup.submitting') : t('inviteSignup.submit')}
        </PrimaryButton>
      </form>

      <div className="flex-1" />

      <div className="mt-6 flex flex-col items-center gap-3">
        <p className="text-center text-footnote text-text-color-tertiary">
          {t('signin.terms')}
        </p>
        <p className="text-footnote text-text-color-secondary">
          {t('inviteSignup.alreadyHave')}{' '}
          <Link to={`/signin?invite_token=${encodeURIComponent(token)}`} className="text-accent">
            {t('inviteSignup.signInLink')}
          </Link>
        </p>
      </div>
    </main>
  );
}
