import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Logo } from '@/components/Logo';
import { PrimaryButton } from '@/components/PrimaryButton';
import { TextInput } from '@/components/TextInput';

import { ApiError } from '@/lib/api';

import { requestPasswordReset } from './auth-api';

export function ForgotPasswordScreen() {
  const { t } = useTranslation();

  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setError(null);
    setLoading(true);
    try {
      await requestPasswordReset(email.trim());
      setSent(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('forgot.error'));
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
            {sent ? t('forgot.sentTitle') : t('forgot.title')}
          </h1>
          <p className="text-body text-text-color-secondary">
            {sent ? t('forgot.sentBody', { email }) : t('forgot.subtitle')}
          </p>
        </div>

        {sent ? (
          <div className="mt-10 flex flex-col gap-3">
            <div className="rounded-lg border-[0.5px] border-border-hairline bg-bg-primary p-4">
              <p className="text-caption text-text-color-secondary">
                {t('forgot.checkSpam')}
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                setSent(false);
                setEmail('');
              }}
              className="min-h-tap text-caption text-accent"
            >
              {t('forgot.tryAnother')}
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-10 flex flex-col gap-3">
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
              disabled={!email}
              className="mt-2"
            >
              {t('forgot.cta')}
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
