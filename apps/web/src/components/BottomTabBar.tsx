import { useQuery } from '@tanstack/react-query';
import { BarChart2, ClipboardList, Home, Settings, Trophy, Users } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { NavLink } from 'react-router-dom';

import { getFunnelCounts } from '@/features/sessions/sessions-api';

const tabs = [
  { path: '/today',    labelKey: 'nav.today',    Icon: Home },
  { path: '/trainees', labelKey: 'nav.trainees', Icon: Users },
  { path: '/sessions', labelKey: 'nav.sessions', Icon: ClipboardList },
  { path: '/events',   labelKey: 'nav.events',   Icon: Trophy },
  { path: '/reports',  labelKey: 'nav.reports',  Icon: BarChart2 },
  { path: '/settings', labelKey: 'nav.settings', Icon: Settings },
] as const;

export function BottomTabBar() {
  const { t } = useTranslation();

  // Surface a small dot on the Sessions tab when there's anything to assess.
  const { data: counts } = useQuery({
    queryKey: ['sessions', 'funnel', 'counts'],
    queryFn: () => getFunnelCounts(true),
    staleTime: 30_000,
  });

  return (
    <nav
      aria-label={t('nav.label')}
      className="border-t-[0.5px] border-border-hairline bg-bg-primary"
    >
      <div className="flex">
        {tabs.map(({ path, labelKey, Icon }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              [
                'flex flex-1 flex-col items-center justify-center gap-0.5',
                'min-h-[52px] py-1.5 px-1',
                'text-[10px] font-medium',
                'transition-colors duration-100',
                isActive ? 'text-accent' : 'text-text-color-tertiary',
              ].join(' ')
            }
          >
            {({ isActive }) => (
              <>
                <span className="relative">
                  <Icon size={22} strokeWidth={isActive ? 2 : 1.75} aria-hidden />
                  {path === '/sessions' && counts && counts.toAssess > 0 ? (
                    <span
                      aria-hidden
                      className="absolute -right-1 -top-1 size-2 rounded-full bg-accent"
                    />
                  ) : null}
                </span>
                <span>{t(labelKey)}</span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
