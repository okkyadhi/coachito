import { useEffect, useState } from 'react';

import { Providers } from '@/app/providers';
import { Router } from '@/app/router';
import { SplashScreen } from '@/components/SplashScreen';
import { useAuthBootstrap } from '@/features/auth/use-auth-bootstrap';
import { useAuthStore } from '@/features/auth/auth-store';
import { startSyncEngine } from '@/features/sync/sync-engine';

// Two min-show modes:
//   - Logged-in / warm cache: 1400ms — quick brand beat, no friction.
//   - First-time / signed-out: 4100ms — full editorial animation including
//     bar fill (0.48s ball drop + 1.18s bounce + 1.3s + 2.8s bar = ~4.1s).
const SPLASH_MIN_MS_RETURNING = 1400;
const SPLASH_MIN_MS_FIRST = 4100;

export default function App() {
  return (
    <Providers>
      <BootstrapGate />
    </Providers>
  );
}

// Rotates the persisted refresh token to fresh access tokens before the router
// mounts.  Without this, the router would render with a stale access token in
// the store and every protected fetch would 401.
function BootstrapGate() {
  const { ready } = useAuthBootstrap();
  const hasRefreshToken = useAuthStore((s) => Boolean(s.refreshToken));
  const [minElapsed, setMinElapsed] = useState(false);

  useEffect(() => {
    const duration = hasRefreshToken ? SPLASH_MIN_MS_RETURNING : SPLASH_MIN_MS_FIRST;
    const t = setTimeout(() => setMinElapsed(true), duration);
    return () => clearTimeout(t);
    // Read once at mount; we don't want the timer to retrigger on signOut.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // The sync engine runs across page lifetime once the app is ready.
  // Drains pending assessments on app start + reconnect + 30s heartbeat.
  useEffect(() => {
    if (!ready) return;
    return startSyncEngine();
  }, [ready]);

  if (!ready || !minElapsed) {
    return <SplashScreen variant="full" />;
  }
  return <Router />;
}
