import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';

import { Logo } from '@/components/Logo';
import { PrimaryButton } from '@/components/PrimaryButton';
import { TextInput } from '@/components/TextInput';

import { ApiError } from '@/lib/api';

import { signUpClub, type SportCode } from './auth-api';
import { useAuthStore } from './auth-store';

const SPORTS: SportCode[] = ['padel', 'tennis'];

export function SignUpClubScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const signIn = useAuthStore((s) => s.signIn);

  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [clubName, setClubName] = useState('');
  const [city, setCity] = useState('');
  const [sports, setSports] = useState<Set<SportCode>>(new Set<SportCode>(['padel']));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleSport = (code: SportCode) => {
    setSports((prev) => {
      const next = new Set(prev);
      if (next.has(code)) {
        // Keep at least one sport selected — the backend enforces min_length=1.
        if (next.size > 1) next.delete(code);
      } else {
        next.add(code);
      }
      return next;
    });
  };

  const canSubmit =
    displayName.trim().length >= 2 &&
    email.trim().length > 0 &&
    password.length >= 8 &&
    clubName.trim().length >= 2 &&
    sports.size >= 1;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setError(null);
    setLoading(true);
    try {
      const result = await signUpClub({
        displayName: displayName.trim(),
        email: email.trim(),
        password,
        clubName: clubName.trim(),
        city: city.trim() || null,
        sportCodes: Array.from(sports),
      });
      signIn(result);
      navigate(result.redirectTo, { replace: true });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('signup.genericError'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col bg-bg-tertiary">
      <div className="mx-auto flex w-full max-w-sm flex-1 flex-col px-6 pb-8 pt-12">
        <div className="flex flex-col items-center gap-3 text-center">
          <Logo size={56} />
          <h1 className="text-large-title text-text-color-primary">
            {t('signup.club.title')}
          </h1>
          <p className="text-body text-text-color-secondary">
            {t('signup.club.subtitle')}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-3">
          <TextInput
            type="text"
            autoComplete="name"
            required
            label={t('signup.fields.displayName')}
            placeholder={t('signup.fields.displayNamePlaceholder')}
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
          />
          <TextInput
            type="email"
            autoComplete="email"
            required
            label={t('signin.emailLabel')}
            placeholder={t('signin.emailPlaceholder')}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <TextInput
            type="password"
            autoComplete="new-password"
            required
            label={t('signup.fields.passwordLabel')}
            placeholder={t('signup.fields.passwordHint')}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <TextInput
            type="text"
            required
            label={t('signup.fields.clubName')}
            placeholder={t('signup.fields.clubNamePlaceholder')}
            value={clubName}
            onChange={(e) => setClubName(e.target.value)}
          />
          <TextInput
            type="text"
            label={t('signup.fields.cityOptional')}
            placeholder={t('signup.fields.cityPlaceholder')}
            value={city}
            onChange={(e) => setCity(e.target.value)}
          />

          <div className="mt-2">
            <p className="text-caption text-text-color-secondary">
              {t('signup.fields.sportsLabel')}
            </p>
            <div
              role="group"
              aria-label={t('signup.fields.sportsLabel')}
              className="mt-2 flex gap-2"
            >
              {SPORTS.map((code) => {
                const active = sports.has(code);
                return (
                  <button
                    key={code}
                    type="button"
                    role="checkbox"
                    aria-checked={active}
                    onClick={() => toggleSport(code)}
                    className={`flex-1 min-h-tap rounded-md border-[0.5px] px-4 py-2 text-body transition-colors ${
                      active
                        ? 'border-accent bg-accent/10 text-accent'
                        : 'border-border-hairline bg-bg-primary text-text-color-primary'
                    }`}
                  >
                    {t(`sports.${code}`)}
                  </button>
                );
              })}
            </div>
          </div>

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
            {t('signup.club.cta')}
          </PrimaryButton>
        </form>

        <div className="flex-1" />

        <div className="mt-6 flex flex-col items-center gap-3">
          <p className="text-footnote text-text-color-secondary">
            {t('signup.alreadyHave')}{' '}
            <Link to="/signin" className="text-accent">
              {t('signup.signInLink')}
            </Link>
          </p>
          <Link
            to="/signup"
            className="text-footnote text-text-color-tertiary underline-offset-2 hover:underline"
          >
            {t('common.back')}
          </Link>
        </div>
      </div>
    </main>
  );
}
