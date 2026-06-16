import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import { Logo } from '@/components/Logo';
import { SecondaryButton } from '@/components/SecondaryButton';

import { consumePendingInvite } from '@/features/onboarding/invite-claim';

import { consumeMagicLink } from './auth-api';
import { useAuthStore } from './auth-store';
import { postSignInPath } from './post-signin';

type State = 'pending' | 'invalid';

export function MagicLinkLanding() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const signIn = useAuthStore((s) => s.signIn);
  const [state, setState] = useState<State>('pending');
  // Magic-link consume is a one-shot redis GETDEL. React StrictMode mounts
  // effects twice in dev — without this ref guard the second mount sees a
  // 410 and the user sees "invalid" even though the first call succeeded.
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    const token = params.get('token');
    if (!token) {
      setState('invalid');
      return;
    }
    void (async () => {
      try {
        const signed = await consumeMagicLink(token);
        const result = await consumePendingInvite(signed);
        signIn(result);
        navigate(postSignInPath(result.workspaceId, result.user.role), { replace: true });
      } catch {
        setState('invalid');
      }
    })();
  }, [params, signIn, navigate]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-bg-tertiary px-6">
      <div className="flex w-full max-w-sm flex-col items-center gap-4 text-center">
        <Logo size={64} />
        {state === 'pending' ? (
          <>
            <span
              aria-hidden
              className="inline-block size-5 animate-spin rounded-full border-2 border-text-color-tertiary border-t-accent"
            />
            <p className="text-body text-text-color-secondary">{t('magic.signingIn')}</p>
          </>
        ) : (
          <>
            <h1 className="text-h2 text-text-color-primary">{t('magic.invalidTitle')}</h1>
            <p className="text-body text-text-color-secondary">{t('magic.invalidBody')}</p>
            <Link to="/signin" className="block w-full">
              <SecondaryButton className="w-full">{t('signin.continueWithEmail')}</SecondaryButton>
            </Link>
          </>
        )}
      </div>
    </main>
  );
}
