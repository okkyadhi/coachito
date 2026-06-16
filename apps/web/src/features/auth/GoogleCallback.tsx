import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { Logo } from '@/components/Logo';

import { consumePendingInvite } from '@/features/onboarding/invite-claim';

import { signInWithGoogle } from './auth-api';
import { useAuthStore } from './auth-store';
import { postSignInPath } from './post-signin';

// Real implementation will validate the `code` query param against the BE.
// Mock just shimmers, signs in, and redirects.
export function GoogleCallback() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const signIn = useAuthStore((s) => s.signIn);
  // Same StrictMode guard as MagicLinkLanding: id_token exchange is one-shot.
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    void (async () => {
      // The real GSI integration will pull `id_token` from the redirect
      // fragment; until then we route through the same call with an empty
      // token and let the BE fail predictably.
      const params = new URLSearchParams(window.location.hash.slice(1));
      const idToken = params.get('id_token') ?? '';
      try {
        const signed = await signInWithGoogle(idToken);
        const result = await consumePendingInvite(signed);
        signIn(result);
        navigate(postSignInPath(result.workspaceId, result.user.role), { replace: true });
      } catch {
        navigate('/signin', { replace: true });
      }
    })();
  }, [navigate, signIn]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-bg-tertiary px-6">
      <div className="flex w-full max-w-sm flex-col items-center gap-4 text-center">
        <Logo size={64} />
        <span
          aria-hidden
          className="inline-block size-5 animate-spin rounded-full border-2 border-text-color-tertiary border-t-accent"
        />
        <p className="text-body text-text-color-secondary">{t('common.loading')}</p>
      </div>
    </main>
  );
}
