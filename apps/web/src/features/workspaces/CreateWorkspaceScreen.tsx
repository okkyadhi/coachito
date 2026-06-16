import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { Logo } from '@/components/Logo';
import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';
import { TextInput } from '@/components/TextInput';
import { useAuthStore } from '@/features/auth/auth-store';
import { ApiError } from '@/lib/api';

import { createWorkspace } from './workspace-api';

type WorkspaceType = 'club' | 'personal';

export function CreateWorkspaceScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const signIn = useAuthStore((s) => s.signIn);
  const signOut = useAuthStore((s) => s.signOut);

  const [type, setType] = useState<WorkspaceType>('club');
  const [name, setName] = useState('');
  const [city, setCity] = useState('');
  const [primaryLocale, setPrimaryLocale] = useState<'en' | 'id'>('id');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setError(null);
    setLoading(true);
    try {
      const trimmedCity = city.trim();
      const result = await createWorkspace({
        type,
        name: name.trim(),
        primaryLocale,
        ...(trimmedCity ? { city: trimmedCity } : {}),
      });
      // Rotate the in-memory tokens to the new pair that carries wsid.
      if (!user) throw new Error('Missing user in store');
      signIn({
        token: result.tokens.accessToken,
        refreshToken: result.tokens.refreshToken,
        user,
        workspaceId: result.tokens.workspaceId,
      });
      navigate('/today', { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('onboarding.createError'));
    } finally {
      setLoading(false);
    }
  };

  const handleSignOut = () => {
    signOut();
    navigate('/signin', { replace: true });
  };

  return (
    <main className="flex min-h-screen flex-col bg-bg-tertiary">
      <div className="mx-auto flex w-full max-w-sm flex-1 flex-col px-6 pb-8 pt-12">
        <div className="flex flex-col items-center gap-3 text-center">
          <Logo size={64} />
          <h1 className="text-large-title text-text-color-primary">
            {t('onboarding.createWorkspaceTitle')}
          </h1>
          <p className="text-body text-text-color-secondary">
            {t('onboarding.createWorkspaceBody')}
          </p>
        </div>

        <form onSubmit={handleCreate} className="mt-8 flex flex-col gap-4">
          {/* Type segmented control */}
          <div>
            <span className="text-section text-text-color-secondary">
              {t('onboarding.typeLabel')}
            </span>
            <div className="mt-1.5 flex gap-2 rounded-md border-[0.5px] border-border-hairline bg-bg-tertiary p-1">
              <button
                type="button"
                onClick={() => setType('club')}
                className={[
                  'flex-1 min-h-tap rounded-sm text-caption transition-colors',
                  type === 'club'
                    ? 'bg-bg-primary text-text-color-primary border-[0.5px] border-border-hairline'
                    : 'text-text-color-secondary',
                ].join(' ')}
              >
                {t('onboarding.typeClub')}
              </button>
              <button
                type="button"
                onClick={() => setType('personal')}
                className={[
                  'flex-1 min-h-tap rounded-sm text-caption transition-colors',
                  type === 'personal'
                    ? 'bg-bg-primary text-text-color-primary border-[0.5px] border-border-hairline'
                    : 'text-text-color-secondary',
                ].join(' ')}
              >
                {t('onboarding.typePersonal')}
              </button>
            </div>
            <p className="mt-1.5 text-footnote text-text-color-tertiary">
              {type === 'club' ? t('onboarding.typeClubHint') : t('onboarding.typePersonalHint')}
            </p>
          </div>

          <TextInput
            label={type === 'club' ? t('onboarding.clubName') : t('onboarding.coachName')}
            placeholder={
              type === 'club'
                ? t('onboarding.clubNamePlaceholder')
                : t('onboarding.coachNamePlaceholder')
            }
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoComplete="organization"
            required
          />

          <TextInput
            label={t('onboarding.cityLabel')}
            placeholder={t('onboarding.cityPlaceholder')}
            value={city}
            onChange={(e) => setCity(e.target.value)}
            autoComplete="address-level2"
          />

          <div>
            <span className="text-section text-text-color-secondary">
              {t('onboarding.localeLabel')}
            </span>
            <div className="mt-1.5 flex gap-2 rounded-md border-[0.5px] border-border-hairline bg-bg-tertiary p-1">
              <button
                type="button"
                onClick={() => setPrimaryLocale('id')}
                className={[
                  'flex-1 min-h-tap rounded-sm text-caption transition-colors',
                  primaryLocale === 'id'
                    ? 'bg-bg-primary text-text-color-primary border-[0.5px] border-border-hairline'
                    : 'text-text-color-secondary',
                ].join(' ')}
              >
                Bahasa Indonesia
              </button>
              <button
                type="button"
                onClick={() => setPrimaryLocale('en')}
                className={[
                  'flex-1 min-h-tap rounded-sm text-caption transition-colors',
                  primaryLocale === 'en'
                    ? 'bg-bg-primary text-text-color-primary border-[0.5px] border-border-hairline'
                    : 'text-text-color-secondary',
                ].join(' ')}
              >
                English
              </button>
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

          <PrimaryButton type="submit" loading={loading} disabled={!name.trim()}>
            {t('onboarding.createCta')}
          </PrimaryButton>
        </form>

        <div className="flex-1" />

        <div className="mt-6 flex flex-col items-center gap-3">
          {user ? (
            <p className="text-footnote text-text-color-tertiary">
              {t('onboarding.signedInAs', { email: user.email ?? user.displayName })}
            </p>
          ) : null}
          <SecondaryButton onClick={handleSignOut}>{t('common.signOut')}</SecondaryButton>
        </div>
      </div>
    </main>
  );
}
