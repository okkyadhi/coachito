import { useQuery } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';
import { enUS, id as idLocale } from 'date-fns/locale';
import {
  CalendarOff,
  CalendarPlus,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  FileText,
  MessageCircle,
  UserPlus,
} from 'lucide-react';
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
import { fetchTodayExtras, type ActivityKind } from './today-extras-api';

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

  const { data: extras } = useQuery({
    queryKey: ['today-extras'],
    queryFn: fetchTodayExtras,
    staleTime: 60_000,
  });

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

      <InboxCard
        unreadFeedback={unreadFeedback}
        toAssess={toAssess}
        onFeedback={() => navigate('/feedback')}
        onToAssess={() => navigate('/sessions?stage=to_assess')}
      />

      {extras ? (
        <WeekStatsStrip stats={extras.weekStats} className="mt-3" />
      ) : null}

      <div className="mt-5">
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

      {extras && extras.recentActivity.length > 0 ? (
        <RecentActivity
          items={extras.recentActivity}
          locale={locale}
          onOpenTrainees={() => navigate('/trainees')}
          className="mt-6"
        />
      ) : null}

      <QuickActions
        onSchedule={() => navigate('/sessions')}
        onAddTrainee={() => navigate('/trainees/new')}
        onCreateReport={() => navigate('/reports')}
        className="mt-6"
      />
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
      className="pt-6"
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

// ── Inbox card — permanent entry point to Feedback + To-assess ──────
// The legacy banner versions only rendered when count > 0, leaving no
// way to reach either screen on a quiet day.  This card stays put with
// gentle empty-state copy so the affordance never disappears.

function InboxCard({
  unreadFeedback,
  toAssess,
  onFeedback,
  onToAssess,
}: {
  unreadFeedback: number;
  toAssess: number;
  onFeedback: () => void;
  onToAssess: () => void;
}) {
  const { t } = useTranslation();
  return (
    <section className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
      <InboxRow
        icon={MessageCircle}
        label={t('today.inbox.feedback')}
        count={unreadFeedback}
        emptyLabel={t('today.inbox.feedbackEmpty')}
        onClick={onFeedback}
      />
      <div className="border-t-[0.5px] border-border-hairline" />
      <InboxRow
        icon={ClipboardCheck}
        label={t('today.inbox.toAssess')}
        count={toAssess}
        emptyLabel={t('today.inbox.toAssessEmpty')}
        onClick={onToAssess}
      />
    </section>
  );
}

function InboxRow({
  icon: Icon,
  label,
  count,
  emptyLabel,
  onClick,
}: {
  icon: typeof MessageCircle;
  label: string;
  count: number;
  emptyLabel: string;
  onClick: () => void;
}) {
  const hasCount = count > 0;
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex min-h-tap w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-bg-secondary/50"
    >
      <span
        aria-hidden
        className={[
          'flex size-8 items-center justify-center rounded-full',
          hasCount ? 'bg-accent-bg text-accent' : 'bg-bg-secondary text-text-color-tertiary',
        ].join(' ')}
      >
        <Icon size={16} strokeWidth={1.75} aria-hidden />
      </span>
      <span
        className={[
          'flex-1 text-body',
          hasCount ? 'text-text-color-primary' : 'text-text-color-secondary',
        ].join(' ')}
      >
        {label}
      </span>
      {hasCount ? (
        <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-accent px-1.5 text-footnote font-medium text-white">
          {count}
        </span>
      ) : (
        <span className="text-caption text-text-color-tertiary">{emptyLabel}</span>
      )}
      <ChevronRight size={14} strokeWidth={1.75} className="text-text-color-tertiary" aria-hidden />
    </button>
  );
}

// ── This week stats strip ────────────────────────────────────────────

function WeekStatsStrip({
  stats,
  className,
}: {
  stats: { sessions: number; hoursCoached: number; assessmentsPublished: number; traineesCoached: number };
  className?: string;
}) {
  const { t } = useTranslation();
  return (
    <section className={['flex flex-col gap-2', className ?? ''].join(' ')}>
      <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {t('today.thisWeek.title')}
      </h3>
      <div className="grid grid-cols-4 overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
        <StatCell value={String(stats.sessions)} label={t('today.thisWeek.sessions')} />
        <StatCell value={stats.hoursCoached.toFixed(1)} label={t('today.thisWeek.hours')} divider />
        <StatCell value={String(stats.assessmentsPublished)} label={t('today.thisWeek.published')} divider />
        <StatCell value={String(stats.traineesCoached)} label={t('today.thisWeek.trainees')} divider />
      </div>
    </section>
  );
}

function StatCell({ value, label, divider }: { value: string; label: string; divider?: boolean }) {
  return (
    <div
      className={[
        'flex flex-col items-start px-3 py-3',
        divider ? 'border-l-[0.5px] border-border-hairline' : '',
      ].join(' ')}
    >
      <span className="font-display text-[22px] leading-none text-text-color-primary">{value}</span>
      <span className="mt-1 text-[10px] uppercase tracking-wide text-text-color-tertiary">
        {label}
      </span>
    </div>
  );
}

// ── Recent activity feed ────────────────────────────────────────────

const ACTIVITY_ICON: Record<ActivityKind, typeof MessageCircle> = {
  assessment_published: CheckCircle2,
  session_coached: CalendarOff,
  report_generated: FileText,
  trainee_joined: UserPlus,
};

function RecentActivity({
  items,
  locale,
  onOpenTrainees,
  className,
}: {
  items: { id: string; kind: ActivityKind; traineeName: string | null; detail: string | null; occurredAt: string }[];
  locale: string;
  onOpenTrainees: () => void;
  className?: string;
}) {
  const { t } = useTranslation();
  const lang = locale === 'id' ? idLocale : enUS;
  return (
    <section className={['flex flex-col gap-2', className ?? ''].join(' ')}>
      <div className="flex items-center justify-between px-1">
        <h3 className="text-section uppercase tracking-wide text-text-color-secondary">
          {t('today.recent.title')}
        </h3>
        <button
          type="button"
          onClick={onOpenTrainees}
          className="text-caption text-accent"
        >
          {t('today.recent.viewAll')}
        </button>
      </div>
      <ul className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
        {items.map((it, idx) => {
          const Icon = ACTIVITY_ICON[it.kind];
          const title =
            it.kind === 'trainee_joined'
              ? t('today.recent.joined', { name: it.traineeName ?? '' })
              : t(`today.recent.${it.kind}`, { name: it.traineeName ?? '' });
          return (
            <li
              key={it.id}
              className={[
                'flex items-start gap-3 px-4 py-3',
                idx > 0 ? 'border-t-[0.5px] border-border-hairline' : '',
              ].join(' ')}
            >
              <span
                aria-hidden
                className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-accent-bg text-accent"
              >
                <Icon size={14} strokeWidth={1.75} aria-hidden />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-body text-text-color-primary">{title}</p>
                <p className="mt-0.5 text-caption text-text-color-tertiary">
                  {formatDistanceToNow(new Date(it.occurredAt), {
                    addSuffix: true,
                    locale: lang,
                  })}
                </p>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

// ── Quick actions strip ─────────────────────────────────────────────

function QuickActions({
  onSchedule,
  onAddTrainee,
  onCreateReport,
  className,
}: {
  onSchedule: () => void;
  onAddTrainee: () => void;
  onCreateReport: () => void;
  className?: string;
}) {
  const { t } = useTranslation();
  return (
    <section className={['flex flex-col gap-2', className ?? ''].join(' ')}>
      <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {t('today.quickActions.title')}
      </h3>
      <div className="grid grid-cols-3 gap-2">
        <QuickActionTile
          icon={CalendarPlus}
          label={t('today.quickActions.schedule')}
          onClick={onSchedule}
        />
        <QuickActionTile
          icon={UserPlus}
          label={t('today.quickActions.addTrainee')}
          onClick={onAddTrainee}
        />
        <QuickActionTile
          icon={FileText}
          label={t('today.quickActions.report')}
          onClick={onCreateReport}
        />
      </div>
    </section>
  );
}

function QuickActionTile({
  icon: Icon,
  label,
  onClick,
}: {
  icon: typeof CalendarPlus;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex min-h-tap flex-col items-start gap-2 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-3 text-left transition-colors hover:bg-bg-secondary/50 active:scale-[0.99]"
    >
      <span
        aria-hidden
        className="flex size-7 items-center justify-center rounded-full bg-accent-bg text-accent"
      >
        <Icon size={14} strokeWidth={1.75} aria-hidden />
      </span>
      <span className="text-caption text-text-color-primary">{label}</span>
    </button>
  );
}
