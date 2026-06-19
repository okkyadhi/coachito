import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  endOfMonth,
  endOfWeek,
  isSameDay,
  startOfMonth,
  startOfWeek,
} from 'date-fns';
import { enUS, id as idLocale } from 'date-fns/locale';
import {
  CalendarPlus,
  ChevronRight,
  Clock,
  MapPin,
  MoreHorizontal,
} from 'lucide-react';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { ConfirmSheet } from '@/components/ConfirmSheet';
import { PrimaryButton } from '@/components/PrimaryButton';
import { WorkspaceBadge } from '@/components/WorkspaceBadge';

import {
  CalendarMonth,
  type DayMarks,
  type DayStatus,
  MonthNavigator,
  dayKey,
  navigateMonth,
} from './Calendar';
import { SportTag } from '@/features/sports/SportTag';

import { FocusList } from './FocusList';
import { ScheduleSessionSheet } from './ScheduleSessionSheet';
import { SessionActionsSheet } from './SessionActionsSheet';
import { StatusPill } from './StatusPill';
import {
  type Session,
  cancelSession,
  completeSession,
  invalidateSessionCaches,
  listAllMineSessions,
  markSessionNoShow,
} from './sessions-api';

// Sessions surface, post-redesign: month calendar at the top showing every
// session the coach has across ALL workspaces they coach in (no more
// switching workspaces just to scan the week), agenda for the selected day
// below. Each agenda row carries a workspace badge so the coach can tell
// Club X work from Personal at a glance.
export function SessionsScreen() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const locale = i18n.language === 'id' ? 'id' : 'en';
  const dateFnsLocale = locale === 'id' ? idLocale : enUS;

  const [month, setMonth] = useState<Date>(() => startOfMonth(new Date()));
  const [selectedDate, setSelectedDate] = useState<Date>(() => new Date());

  // Fetch the visible month + spill days from neighbouring months so the
  // dots line up with what the grid renders.
  const { rangeFrom, rangeTo } = useMemo(() => {
    const start = startOfWeek(startOfMonth(month), { weekStartsOn: 0 });
    const end = endOfWeek(endOfMonth(month), { weekStartsOn: 0 });
    // Push end out by one day so server's exclusive upper bound includes the
    // last visible day's full range.
    const exclusiveEnd = new Date(end.getTime() + 24 * 3600 * 1000);
    return {
      rangeFrom: start.toISOString(),
      rangeTo: exclusiveEnd.toISOString(),
    };
  }, [month]);

  const { data: sessions = [], isPending } = useQuery({
    queryKey: ['sessions', 'all-mine', rangeFrom, rangeTo],
    queryFn: () => listAllMineSessions({ from: rangeFrom, to: rangeTo }),
  });

  const marksByDay = useMemo(() => {
    const out = new Map<string, DayMarks>();
    for (const s of sessions) {
      const k = dayKey(new Date(s.scheduledAt));
      const existing = out.get(k) ?? { counts: {} };
      const status: DayStatus =
        s.funnelStage === 'upcoming'
          ? 'upcoming'
          : s.funnelStage === 'to_assess'
            ? 'to_assess'
            : 'done';
      existing.counts[status] = (existing.counts[status] ?? 0) + 1;
      out.set(k, existing);
    }
    return out;
  }, [sessions]);

  const agendaForSelected = useMemo(() => {
    return sessions
      .filter((s) => isSameDay(new Date(s.scheduledAt), selectedDate))
      .sort((a, b) => a.scheduledAt.localeCompare(b.scheduledAt));
  }, [sessions, selectedDate]);

  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Session | null>(null);
  const [actionsTarget, setActionsTarget] = useState<Session | null>(null);
  const [cancelTarget, setCancelTarget] = useState<Session | null>(null);

  const invalidate = () => invalidateSessionCaches(qc);

  const cancelMut = useMutation({
    mutationFn: (id: string) => cancelSession(id),
    onSuccess: invalidate,
  });
  const completeMut = useMutation({
    mutationFn: (id: string) => completeSession(id),
    onSuccess: invalidate,
  });
  const noShowMut = useMutation({
    mutationFn: (id: string) => markSessionNoShow(id),
    onSuccess: invalidate,
  });

  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-4 px-4 pb-8 pt-3">
      <header className="flex items-center justify-between">
        <h1 className="text-large-title text-text-color-primary">
          {t('sessions.title')}
        </h1>
        <button
          type="button"
          onClick={() => setScheduleOpen(true)}
          className="flex min-h-tap items-center gap-1 rounded-md bg-accent px-3 text-caption font-medium text-white"
        >
          <CalendarPlus size={14} strokeWidth={1.75} aria-hidden />
          {t('sessions.scheduleCta')}
        </button>
      </header>

      <section className="flex flex-col gap-2 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-3">
        <MonthNavigator
          month={month}
          onPrev={() => setMonth((m) => navigateMonth(m, -1))}
          onNext={() => setMonth((m) => navigateMonth(m, 1))}
          onToday={() => {
            const now = new Date();
            setMonth(startOfMonth(now));
            setSelectedDate(now);
          }}
        />
        <CalendarMonth
          month={month}
          selectedDate={selectedDate}
          marksByDay={marksByDay}
          onSelect={(d) => {
            setSelectedDate(d);
            // Calendar grid spans weeks that overlap neighbouring months —
            // a tap on a spill day should pull the month into view.
            if (d.getMonth() !== month.getMonth()) {
              setMonth(startOfMonth(d));
            }
          }}
        />
        <div className="flex items-center gap-3 px-1 pt-1 text-footnote text-text-color-tertiary">
          <LegendDot className="bg-accent" label={t('sessions.legend.upcoming')} />
          <LegendDot className="bg-warning-text" label={t('sessions.legend.toAssess')} />
          <LegendDot
            className="bg-text-color-tertiary"
            label={t('sessions.legend.done')}
          />
        </div>
      </section>

      <section className="flex flex-col gap-2">
        <header className="flex items-baseline justify-between px-1">
          <h2 className="text-section uppercase tracking-wide text-text-color-secondary">
            {selectedDate.toLocaleDateString(locale, {
              weekday: 'long',
              day: 'numeric',
              month: 'long',
            })}
          </h2>
          <span className="text-caption text-text-color-tertiary">
            {t('sessions.agendaCount', { count: agendaForSelected.length })}
          </span>
        </header>

        {isPending ? (
          <Skeleton />
        ) : agendaForSelected.length === 0 ? (
          <EmptyDay onSchedule={() => setScheduleOpen(true)} />
        ) : (
          <ul className="flex flex-col gap-2">
            {agendaForSelected.map((s) => (
              <SessionCard
                key={s.id}
                session={s}
                locale={locale}
                onOpen={() =>
                  navigate(`/trainees/${s.athlete.id}/assess?session=${s.id}`)
                }
                onMenu={
                  s.status === 'scheduled' || s.assessmentStatus === 'draft'
                    ? () => setActionsTarget(s)
                    : undefined
                }
              />
            ))}
          </ul>
        )}
      </section>

      {scheduleOpen ? (
        <ScheduleSessionSheet
          open={true}
          initial={null}
          onClose={() => setScheduleOpen(false)}
          onSaved={() => {
            setScheduleOpen(false);
            invalidate();
          }}
        />
      ) : null}
      {editTarget ? (
        <ScheduleSessionSheet
          open={true}
          initial={editTarget}
          onClose={() => setEditTarget(null)}
          onSaved={() => {
            setEditTarget(null);
            invalidate();
          }}
        />
      ) : null}

      {actionsTarget ? (
        <SessionActionsSheet
          session={actionsTarget}
          onClose={() => setActionsTarget(null)}
          onEdit={() => {
            setEditTarget(actionsTarget);
            setActionsTarget(null);
          }}
          onComplete={() => {
            completeMut.mutate(actionsTarget.id);
            setActionsTarget(null);
          }}
          onNoShow={() => {
            noShowMut.mutate(actionsTarget.id);
            setActionsTarget(null);
          }}
          onCancel={() => {
            setCancelTarget(actionsTarget);
            setActionsTarget(null);
          }}
        />
      ) : null}

      {cancelTarget ? (
        <ConfirmSheet
          open
          title={t('sessions.cancel.title')}
          description={t('sessions.cancel.body', {
            name: cancelTarget.athlete.displayName,
          })}
          confirmLabel={t('sessions.cancel.confirm')}
          destructive
          onCancel={() => setCancelTarget(null)}
          onConfirm={() => {
            cancelMut.mutate(cancelTarget.id);
            setCancelTarget(null);
          }}
        />
      ) : null}
      {/* Silence unused-import noise from dateFnsLocale (kept for future use). */}
      <span className="sr-only">{dateFnsLocale.code}</span>
    </div>
  );
}

interface SessionCardProps {
  session: Session;
  locale: string;
  onOpen: () => void;
  onMenu?: (() => void) | undefined;
}

function SessionCard({ session: s, locale, onOpen, onMenu }: SessionCardProps) {
  const { t } = useTranslation();
  const date = new Date(s.scheduledAt);
  const timeLabel = date.toLocaleTimeString(locale, {
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <li className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-3">
      <div className="flex items-start gap-2">
        <button
          type="button"
          onClick={onOpen}
          className="flex flex-1 items-start gap-3 text-left"
        >
          <div className="flex-1">
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-body font-medium text-text-color-primary">
                {s.athlete.displayName}
              </span>
              <span className="text-caption text-text-color-tertiary">
                {timeLabel}
              </span>
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-footnote text-text-color-secondary">
              <span className="inline-flex items-center gap-1">
                <Clock size={12} strokeWidth={1.75} aria-hidden />
                {s.durationMin}m
              </span>
              {s.court ? (
                <span className="inline-flex items-center gap-1">
                  <MapPin size={12} strokeWidth={1.75} aria-hidden />
                  {s.court}
                </span>
              ) : null}
              <FocusList focuses={s.focuses} />
              <StatusPill session={s} />
              <SportTag sport={s.sport} />
              <WorkspaceBadge workspace={s.workspace} />
            </div>
          </div>
          <ChevronRight
            size={16}
            strokeWidth={1.75}
            aria-hidden
            className="mt-1 text-text-color-tertiary"
          />
        </button>
        {onMenu ? (
          <button
            type="button"
            onClick={onMenu}
            aria-label={t('sessions.menu.label', { name: s.athlete.displayName })}
            className="flex size-9 items-center justify-center rounded-full text-text-color-secondary hover:bg-bg-secondary"
          >
            <MoreHorizontal size={16} strokeWidth={1.75} aria-hidden />
          </button>
        ) : null}
      </div>
    </li>
  );
}

function LegendDot({ className, label }: { className: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span aria-hidden className={['inline-block size-1.5 rounded-full', className].join(' ')} />
      {label}
    </span>
  );
}

function Skeleton() {
  return (
    <ul className="flex flex-col gap-2">
      {[0, 1].map((i) => (
        <li
          key={i}
          className="h-20 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary"
        />
      ))}
    </ul>
  );
}

function EmptyDay({ onSchedule }: { onSchedule: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-6 text-center">
      <p className="text-body text-text-color-primary">{t('sessions.emptyDay')}</p>
      <PrimaryButton type="button" onClick={onSchedule} className="mt-2 max-w-[200px]">
        {t('sessions.scheduleCta')}
      </PrimaryButton>
    </div>
  );
}
