import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';

import { Logo } from '@/components/Logo';
import { PhoneInput } from '@/components/PhoneInput';
import { PrimaryButton } from '@/components/PrimaryButton';
import { TextInput } from '@/components/TextInput';

import { ApiError } from '@/lib/api';

import { signUpCoach, type SportCode } from './auth-api';
import { useAuthStore } from './auth-store';

const SPORTS: SportCode[] = ['padel', 'tennis'];

// Strip whitespace + ensure leading "+".  Returns null if the user left
// only the prefix (e.g. "+62") or cleared it.
function normalizePhone(raw: string): string | null {
  const stripped = raw.replace(/\s+/g, '');
  const withPlus = stripped.startsWith('+') ? stripped : `+${stripped}`;
  // "+" alone or "+" + ≤2 digits = country code only; treat as not provided.
  return withPlus.length > 4 ? withPlus : null;
}

export function SignUpCoachScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const signIn = useAuthStore((s) => s.signIn);

  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('+62 ');
  const [password, setPassword] = useState('');
  const [sportCode, setSportCode] = useState<SportCode>('padel');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!displayName.trim() || !email.trim() || password.length < 8) return;
    setError(null);
    setLoading(true);
    try {
      const result = await signUpCoach({
        displayName: displayName.trim(),
        email: email.trim(),
        password,
        sportCode,
        phoneE164: normalizePhone(phone),
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
            {t('signup.coach.title')}
          </h1>
          <p className="text-body text-text-color-secondary">
            {t('signup.coach.subtitle')}
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
          <PhoneInput
            label={t('signup.fields.phoneLabel')}
            placeholder="+62 812 3456 7890"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
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

          <div className="mt-2">
            <p className="text-caption text-text-color-secondary">
              {t('signup.fields.sportLabel')}
            </p>
            <div
              role="radiogroup"
              aria-label={t('signup.fields.sportLabel')}
              className="mt-2 flex gap-2"
            >
              {SPORTS.map((code) => {
                const active = sportCode === code;
                return (
                  <button
                    key={code}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => setSportCode(code)}
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
            disabled={!displayName.trim() || !email.trim() || password.length < 8}
            className="mt-2"
          >
            {t('signup.coach.cta')}
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
