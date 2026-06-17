import { useQuery } from '@tanstack/react-query';
import { CalendarOff, ClipboardCheck, MessageCircle } from 'lucide-react';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { EmptyState as SharedEmptyState } from '@/components/EmptyState';
import { GroupedTable } from '@/components/GroupedTable';
import { PrimaryButton } from '@/components/PrimaryButton';
import { SkeletonList } from '@/components/Skeleton';
import { useAuthStore } from '@/features/auth/auth-store';
import { getFeedbackInbox } from '@/features/assessment/feedback-api';
import { getFunnelCounts } from '@/features/sessions/sessions-api';
import { useCurrentSport } from '@/features/sports/useCurrentSport';
import { formatFullDate } from '@/lib/dates';

import { TraineeRow } from './TraineeRow';
import { UpNextCard } from './UpNextCard';
import { getTodaySessions } from './today-api';

export function CoachTodayScreen() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const locale = user?.preferredLocale ?? i18n.language ?? 'en';
  const { sports, isMultiSport } = useCurrentSport();

  // Today aggregates across all workspaces the coach is in — see today-api.
  // No more mine/all toggle: privileged users still see their own day here;
  // to see another coach's schedule they switch workspace or use Sessions.
  const { data: sessions = [], isPending } = useQuery({
    queryKey: ['today-sessions', 'all-mine'],
    queryFn: () => getTodaySessions(),
  });

  // Subtle "X workspaces" hint when today's roster spans more than one.
  const workspaceCount = useMemo(() => {
    const ids = new Set<string>();
    for (const s of sessions) {
      if (s.workspace) ids.add(s.workspace.id);
    }
    return ids.size;
  }, [sessions]);

  const { data: inbox = [] } = useQuery({
    queryKey: ['feedback-inbox'],
    queryFn: getFeedbackInbox,
    staleTime: 60_000,
  });
  const unreadFeedback = inbox.filter((i) => !i.readAt).length;

  const { data: funnelCounts } = useQuery({
    queryKey: ['sessions', 'funnel', 'counts'],
    queryFn: () => getFunnelCounts(true),
    staleTime: 30_000,
  });
  const toAssess = funnelCounts?.toAssess ?? 0;

  const greetingName = user?.displayName?.replace(/^Coach\s+/i, '') ?? '';
  // Pick the next future session — not just sessions[0].  (Phase 8a.)
  const now = new Date();
  const upNext = sessions.find((s) => new Date(s.scheduledAt) > now) ?? null;

  return (
    <div className="mx-auto w-full max-w-md px-4 pb-6 pt-5">
      {/* Greeting */}
      <header className="mb-5">
        <h1 className="text-large-title text-text-color-primary">
          {t('today.greeting', { name: greetingName })}
        </h1>
        <p className="mt-1 text-caption text-text-color-secondary">
          {formatFullDate(new Date(), locale)}
          {sessions.length > 0 ? (
            <>
              {' · '}
              {t('today.sessionCount', { count: sessions.length })}
            </>
          ) : null}
          {workspaceCount > 1 ? (
            <>
              {' · '}
              <span className="text-text-color-primary">
                {t('today.workspaceCount', { count: workspaceCount })}
              </span>
            </>
          ) : null}
        </p>
      </header>

      {/* To-assess banner (Phase 6) — funnel-driven nudge before the day's roll. */}
      {toAssess > 0 ? (
        <button
          type="button"
          onClick={() => navigate('/sessions?stage=to_assess')}
          className="animate-fade-in border-accent/40 bg-accent/5 hover:bg-accent/10 mb-3 flex w-full items-center gap-3 rounded-xl border-[0.5px] px-4 py-3 text-left transition-colors"
        >
          <ClipboardCheck
            size={18}
            strokeWidth={1.75}
            aria-hidden
            className="text-accent"
          />
          <span className="flex-1 text-body text-text-color-primary">
            {t('today.toAssessBadge', { count: toAssess })}
          </span>
          <span className="rounded-full bg-accent px-2 py-0.5 text-footnote text-white">
            {toAssess}
          </span>
        </button>
      ) : null}

      {/* Feedback inbox CTA — only when there's at least one unread item, so
          it doesn't clutter the screen for new coaches. */}
      {unreadFeedback > 0 ? (
        <button
          type="button"
          onClick={() => navigate('/feedback')}
          className="animate-fade-in border-accent/40 bg-accent/5 hover:bg-accent/10 mb-5 flex w-full items-center gap-3 rounded-xl border-[0.5px] px-4 py-3 text-left transition-colors"
        >
          <MessageCircle
            size={18}
            strokeWidth={1.75}
            aria-hidden
            className="text-accent"
          />
          <span className="flex-1 text-body text-text-color-primary">
            {t('today.feedbackBadge', { count: unreadFeedback })}
          </span>
          <span className="rounded-full bg-accent px-2 py-0.5 text-footnote text-white">
            {unreadFeedback}
          </span>
        </button>
      ) : null}

      {isPending ? (
        <SkeletonList rows={3} />
      ) : sessions.length === 0 ? (
        <TodayEmpty onSchedule={() => navigate('/sessions')} onAddTrainee={() => navigate('/trainees')} />
      ) : (
        <div className="space-y-5">
          {upNext ? <UpNextCard session={upNext} locale={locale} sports={sports} isMultiSport={isMultiSport} /> : null}
          {/* Time-of-day grouping: Morning / Afternoon / Evening. */}
          {(['morning', 'afternoon', 'evening'] as const).map((bucket) => {
            const bucketSessions = sessions.filter((s) => {
              const h = new Date(s.scheduledAt).getHours();
              return bucket === 'morning'
                ? h < 12
                : bucket === 'afternoon'
                  ? h >= 12 && h < 17
                  : h >= 17;
            });
            if (bucketSessions.length === 0) return null;
            return (
              <GroupedTable
                key={bucket}
                header={t(`today.timeOfDay.${bucket}`)}
              >
                {bucketSessions.map((s) => (
                  <TraineeRow key={s.id} session={s} locale={locale} sports={sports} isMultiSport={isMultiSport} />
                ))}
              </GroupedTable>
            );
          })}
        </div>
      )}
    </div>
  );
}

interface TodayEmptyProps {
  onSchedule: () => void;
  onAddTrainee: () => void;
}

function TodayEmpty({ onSchedule, onAddTrainee }: TodayEmptyProps) {
  const { t } = useTranslation();
  return (
    <SharedEmptyState
      icon={CalendarOff}
      title={t('today.emptyTitle')}
      body={t('today.emptyBody')}
      className="pt-10"
      primaryAction={
        <PrimaryButton onClick={onSchedule}>{t('today.scheduleSession')}</PrimaryButton>
      }
      secondaryAction={
        <button
          type="button"
          onClick={onAddTrainee}
          className="min-h-tap text-caption text-accent"
        >
          {t('today.addTraineeFirst')}
        </button>
      }
    />
  );
}
