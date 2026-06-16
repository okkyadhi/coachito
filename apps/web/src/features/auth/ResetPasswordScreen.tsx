import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import { Logo } from '@/components/Logo';
import { PrimaryButton } from '@/components/PrimaryButton';
import { TextInput } from '@/components/TextInput';

import { ApiError } from '@/lib/api';

import { resetPassword } from './auth-api';
import { useAuthStore } from './auth-store';
import { postSignInPath } from './post-signin';

export function ResetPasswordScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const signIn = useAuthStore((s) => s.signIn);
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';

  const [newPassword, setNewPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const missingToken = !token;
  const mismatch = confirm.length > 0 && confirm !== newPassword;
  const canSubmit =
    !missingToken && newPassword.length >= 8 && !mismatch;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setError(null);
    setLoading(true);
    try {
      const result = await resetPassword(token, newPassword);
      signIn(result);
      navigate(postSignInPath(result.workspaceId, result.user.role), {
        replace: true,
      });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('reset.error'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col bg-bg-tertiary">
      <div className="mx-auto flex w-full max-w-sm flex-1 flex-col px-6 pb-8 pt-16">
        <div className="flex flex-col items-center gap-4 text-center">
          <Logo size={72} />
          <h1 className="text-large-title text-text-color-primary">
            {t('reset.title')}
          </h1>
          <p className="text-body text-text-color-secondary">
            {missingToken ? t('reset.missingToken') : t('reset.subtitle')}
          </p>
        </div>

        {missingToken ? (
          <div className="mt-10 flex flex-col gap-3">
            <Link to="/auth/forgot" className="block">
              <PrimaryButton className="w-full">
                {t('reset.requestNew')}
              </PrimaryButton>
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-10 flex flex-col gap-3">
            <TextInput
              type="password"
              autoComplete="new-password"
              autoFocus
              required
              label={t('reset.newPasswordLabel')}
              placeholder={t('reset.newPasswordHint')}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
            <TextInput
              type="password"
              autoComplete="new-password"
              required
              label={t('reset.confirmLabel')}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />

            {mismatch ? (
              <p className="text-caption text-danger-text">
                {t('reset.mismatch')}
              </p>
            ) : null}
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
              loading={loading}
              disabled={!canSubmit}
              className="mt-2"
            >
              {t('reset.cta')}
            </PrimaryButton>
          </form>
        )}

        <div className="flex-1" />

        <div className="mt-6 flex flex-col items-center gap-3">
          <p className="text-footnote text-text-color-secondary">
            <Link to="/signin" className="text-accent">
              {t('forgot.backToSignIn')}
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
