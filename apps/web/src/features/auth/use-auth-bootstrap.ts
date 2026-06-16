// On app start, rotate any persisted refresh token to a fresh access pair.
// Without this, a user reopening the app after the 15-minute access expiry
// has a stale token in localStorage and the first real API call 401s.
//
// Guarded with a ref so React StrictMode's double-mount doesn't fire the
// rotation twice (the second call hits the now-revoked old jti and would
// sign the user out).

import { useEffect, useRef, useState } from 'react';

import { refreshTokens } from './auth-api';
import { useAuthStore } from './auth-store';

export function useAuthBootstrap(): { ready: boolean } {
  const [ready, setReady] = useState(false);
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    const state = useAuthStore.getState();
    if (!state.refreshToken) {
      setReady(true);
      return;
    }

    void (async () => {
      try {
        const result = await refreshTokens();
        useAuthStore.getState().signIn({
          token: result.token,
          refreshToken: result.refreshToken,
          user: result.user,
          workspaceId: result.workspaceId,
        });
      } catch {
        useAuthStore.getState().signOut();
      } finally {
        setReady(true);
      }
    })();
  }, []);

  return { ready };
}
