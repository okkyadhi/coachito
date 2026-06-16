import { useEffect } from 'react';

import { Providers } from '@/app/providers';
import { Router } from '@/app/router';
import { Logo } from '@/components/Logo';
import { useAuthBootstrap } from '@/features/auth/use-auth-bootstrap';
import { startSyncEngine } from '@/features/sync/sync-engine';

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

  // The sync engine runs across page lifetime once the app is ready.
  // Drains pending assessments on app start + reconnect + 30s heartbeat.
  useEffect(() => {
    if (!ready) return;
    return startSyncEngine();
  }, [ready]);

  if (!ready) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center bg-bg-tertiary">
        <Logo size={56} />
      </main>
    );
  }
  return <Router />;
}
