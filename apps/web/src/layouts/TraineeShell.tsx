import { BarChart2, Home, MessageCircle, Trophy, User } from 'lucide-react';
import { CalendarDays } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { NavLink, Outlet } from 'react-router-dom';

import { Logo } from '@/components/Logo';
import { OfflineBanner } from '@/components/OfflineBanner';
import { Wordmark } from '@/components/Wordmark';
import { WorkspaceSwitcher } from '@/features/workspaces/WorkspaceSwitcher';

// Trainee-side equivalent of CoachShell.  5-tab nav (Home / Progress /
// Sessions / Coach / Profile) per docs/05-trainee-home.md.
export function TraineeShell() {
  return (
    <div className="flex h-screen flex-col bg-bg-tertiary">
      <header className="flex items-center justify-between gap-3 border-b-[0.5px] border-border-hairline bg-bg-primary px-4 py-2.5">
        <div className="flex items-center gap-2">
          <Logo size={24} />
          <Wordmark size={16} />
        </div>
        {/* Hidden by the component itself when the trainee belongs to a
            single workspace — only shown for multi-club trainees. */}
        <WorkspaceSwitcher />
      </header>

      <OfflineBanner />

      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>

      <TraineeTabBar />
    </div>
  );
}

const TABS = [
  { path: '/home',         labelKey: 'traineeNav.home',     Icon: Home },
  { path: '/skills',       labelKey: 'traineeNav.progress', Icon: BarChart2 },
  { path: '/my-sessions',  labelKey: 'traineeNav.sessions', Icon: CalendarDays },
  { path: '/events',       labelKey: 'traineeNav.events',   Icon: Trophy },
  { path: '/coach',        labelKey: 'traineeNav.coach',    Icon: MessageCircle },
  { path: '/me',           labelKey: 'traineeNav.profile',  Icon: User },
] as const;

function TraineeTabBar() {
  const { t } = useTranslation();
  return (
    <nav
      aria-label={t('nav.label')}
      className="border-t-[0.5px] border-border-hairline bg-bg-primary"
    >
      <div className="flex">
        {TABS.map(({ path, labelKey, Icon }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              [
                'flex flex-1 flex-col items-center justify-center gap-0.5',
                'min-h-[52px] py-1.5 px-1 text-[10px] font-medium',
                'transition-colors duration-100',
                isActive ? 'text-accent' : 'text-text-color-tertiary',
              ].join(' ')
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={22} strokeWidth={isActive ? 2 : 1.75} aria-hidden />
                <span>{t(labelKey)}</span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
