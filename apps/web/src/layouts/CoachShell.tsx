import { Outlet } from 'react-router-dom';

import { BottomTabBar } from '@/components/BottomTabBar';
import { Logo } from '@/components/Logo';
import { OfflineBanner } from '@/components/OfflineBanner';
import { TrialExpiredBanner } from '@/components/TrialExpiredBanner';
import { WorkspaceSwitcher } from '@/features/workspaces/WorkspaceSwitcher';

// Wraps every authenticated coach screen: a thin top strip with the brand
// mark + workspace switcher, a scrollable content area, and the bottom tab bar.
// Nested routes render into <Outlet />.
export function CoachShell() {
  return (
    <div className="flex h-dvh flex-col bg-bg-tertiary">
      <header className="flex items-center gap-3 border-b-[0.5px] border-border-hairline bg-bg-primary px-4 py-2.5">
        <Logo size={24} />
        <WorkspaceSwitcher />
      </header>

      <OfflineBanner />
      <TrialExpiredBanner />

      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>

      <BottomTabBar />
    </div>
  );
}
