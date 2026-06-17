import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import { enUS, id as idLocale } from 'date-fns/locale';
import { ArrowUp, Bell, Flame } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { useAuthStore } from '@/features/auth/auth-store';
import { NotificationSheet } from '@/features/notifications/NotificationSheet';
import {
  fetchMyNotifications,
  getLastSeenAt,
  setLastSeenAt,
  unreadCount,
} from '@/features/notifications/notifications-api';
import { PendingInvitesBanner } from '@/features/onboarding/PendingInvitesBanner';
import { SportTabs } from '@/features/sports/SportTabs';
import { useCurrentSport } from '@/features/sports/useCurrentSport';
import { SkillRadar } from '@/features/trainee-profile/SkillRadar';

import { AchievementCard } from './AchievementCard';
import { CoachNoteCard } from './CoachNoteCard';
import { NewReportBanner } from './NewReportBanner';
import { SessionFeedbackCard } from './SessionFeedbackCard';
import { FirstRunHome } from './FirstRunHome';
import { TierProgressCard } from './TierProgressCard';
import { UpcomingSession } from './UpcomingSession';
import { fetchTraineeHome } from './trainee-home-api';

export function TraineeHomeScreen() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const locale = (user?.preferredLocale ?? i18n.language) === 'id' ? 'id' : 'en';
  const { currentSportId, isMultiSport } = useCurrentSport();

  const { data: home, isPending } = useQuery({
    queryKey: ['trainee-home', currentSportId],
    queryFn: () => fetchTraineeHome(currentSportId),
  });

  const { data: notifications = [], isLoading: notifLoading } = useQuery({
    queryKey: ['trainee', 'notifications'],
    queryFn: fetchMyNotifications,
    staleTime: 60_000,
  });

  // Bell sheet + unread tracking.
  const [notifOpen, setNotifOpen] = useState(false);
  const [lastSeenAt, setLastSeenAtState] = useState<number>(() =>
    getLastSeenAt(user?.id ?? null),
  );
  // Re-read once the user becomes available (in case it wasn't on first render).
  useEffect(() => {
    setLastSeenAtState(getLastSeenAt(user?.id ?? null));
  }, [user?.id]);
  const unread = useMemo(
    () => unreadCount(notifications, lastSeenAt),
    [notifications, lastSeenAt],
  );
  const openNotifications = () => {
    setNotifOpen(true);
    // Mark everything currently in the list as seen as soon as the sheet opens.
    const now = Date.now();
    setLastSeenAt(user?.id ?? null, now);
    setLastSeenAtState(now);
  };

  if (isPending || !home) return <Skeleton />;

  const firstName = (user?.displayName ?? home.traineeFirstName).split(' ')[0] ?? '';
  const today = new Date();
  const shortDate = format(today, 'EEEE, d MMMM', {
    locale: locale === 'id' ? idLocale : enUS,
  });

  // First-run state per docs/05
  if (!home.hasAssessment) {
    return (
      <div className="mx-auto flex w-full max-w-md flex-col gap-5 px-4 pb-8 pt-4">
        <PendingInvitesBanner />
        <FirstRunHome home={{ ...home, traineeFirstName: firstName }} />
      </div>
    );
  }

  const sessionsThisFortnight = home.rhythmDays14.filter(Boolean).length;

  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-5 px-4 pb-8 pt-4">
      {isMultiSport ? <SportTabs /> : null}
      {/* Greeting */}
      <header className="flex items-start justify-between">
        <div>
          <h1 className="text-large-title text-text-color-primary">
            {t('traineeHome.greeting', { name: firstName })}
          </h1>
          <p className="mt-0.5 text-caption text-text-color-secondary">{shortDate}</p>
        </div>
        <button
          type="button"
          aria-label={t('traineeHome.notifications')}
          onClick={openNotifications}
          className="relative flex size-9 items-center justify-center rounded-full border-[0.5px] border-border-hairline bg-bg-primary active:bg-bg-secondary"
        >
          <Bell size={18} strokeWidth={1.75} className="text-text-color-secondary" aria-hidden />
          {unread > 0 ? (
            <span
              aria-label={t('notifications.unreadCount', { count: unread })}
              className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[10px] font-medium leading-none text-white"
            >
              {unread > 9 ? '9+' : unread}
            </span>
          ) : null}
        </button>
      </header>

      <NotificationSheet
        open={notifOpen}
        items={notifications}
        loading={notifLoading}
        onClose={() => setNotifOpen(false)}
      />

      <PendingInvitesBanner />
      <NewReportBanner />

      {/* Achievement */}
      {home.achievement ? (
        <AchievementCard
          achievement={home.achievement}
          onViewSkill={() => navigate('/progress')}
          onShare={() => {
            const a = home.achievement;
            if (!a) return;
            const text = `I just levelled up: ${a.skillNameEn} — ${t(a.levelLabelKey)} 📈`;
            const url = window.location.origin;
            const nav: Navigator | undefined =
              typeof navigator !== 'undefined' ? navigator : undefined;
            if (nav?.share) {
              void nav.share({ title: t('brand.name'), text, url }).catch(() => {});
            } else if (nav?.clipboard?.writeText) {
              void nav.clipboard.writeText(`${text}\n${url}`);
            }
          }}
        />
      ) : null}

      {/* Tier */}
      {home.tierProgress ? <TierProgressCard progress={home.tierProgress} /> : null}

      {/* Upcoming */}
      <UpcomingSession session={home.upcomingSession} onOpen={() => navigate('/my-sessions')} />

      {/* Coach note */}
      {home.coachNote ? (
        <CoachNoteCard note={home.coachNote} onOpen={() => navigate('/my-sessions')} />
      ) : null}

      {/* Feedback CTA — only renders when there's a published assessment. */}
      <SessionFeedbackCard />

      {/* Radar — reuses the coach SkillRadar component (same SVG, deliberate
          parity with the trainee profile per docs/05 design rationale). */}
      <section className="flex flex-col gap-2">
        <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
          {t('traineeHome.tracking')}
        </h3>
        <SkillRadar averages={home.categoryAverages} />
      </section>

      {/* Wins */}
      {home.recentGains.length > 0 ? (
        <section className="flex flex-col gap-2">
          <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
            {t('traineeHome.wins')}
          </h3>
          <ul className="flex flex-col rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
            {home.recentGains.map((g, idx) => (
              <li
                key={g.skillNameEn}
                className={[
                  'flex items-center gap-3 px-4 py-3',
                  idx > 0 ? 'border-t-[0.5px] border-border-hairline' : '',
                ].join(' ')}
              >
                <span
                  aria-hidden
                  className="flex size-7 items-center justify-center rounded-full"
                  style={{ background: 'var(--color-background-success)' }}
                >
                  <ArrowUp
                    size={14}
                    strokeWidth={2}
                    style={{ color: 'var(--color-text-success)' }}
                    aria-hidden
                  />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-body text-text-color-primary">{g.skillNameEn}</p>
                  <p className="text-caption text-text-color-secondary">
                    {g.fromLevel > 0
                      ? t(`assessment.levels.${g.fromLevel}`)
                      : t('assessment.notRated')}{' '}
                    → {t(`assessment.levels.${g.toLevel}`)}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {/* Rhythm */}
      <section className="flex flex-col gap-2">
        <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
          {t('traineeHome.rhythm.title')}
        </h3>
        <div className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
          <div className="flex items-center gap-2">
            <Flame size={18} strokeWidth={1.75} className="text-accent" aria-hidden />
            <p className="text-body text-text-color-primary">
              {t('traineeHome.rhythm.count', { count: sessionsThisFortnight })}
            </p>
          </div>
          <p className="mt-1 text-caption text-text-color-secondary">
            {t('traineeHome.rhythm.body')}
          </p>
          <div className="mt-3 flex gap-1">
            {home.rhythmDays14.map((active, i) => (
              <span
                key={i}
                aria-hidden
                className={[
                  'h-2 flex-1 rounded-full',
                  active ? 'bg-accent' : 'bg-bg-tertiary',
                ].join(' ')}
              />
            ))}
          </div>
          <p className="mt-3 text-footnote text-text-color-tertiary">
            {t('traineeHome.rhythm.footer')}
          </p>
        </div>
      </section>
    </div>
  );
}

function Skeleton() {
  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-5 px-4 pb-8 pt-4">
      <header className="flex items-start justify-between">
        <div className="flex flex-col gap-1.5">
          <div className="animate-shimmer h-6 w-44 rounded-full" />
          <div className="animate-shimmer h-3 w-32 rounded-full" />
        </div>
        <div className="animate-shimmer size-9 rounded-full" />
      </header>
      <div className="animate-shimmer h-32 rounded-xl" />
      <div className="animate-shimmer h-20 rounded-xl" />
      <div className="animate-shimmer h-28 rounded-xl" />
      <div className="animate-shimmer h-24 rounded-xl" />
    </div>
  );
}
