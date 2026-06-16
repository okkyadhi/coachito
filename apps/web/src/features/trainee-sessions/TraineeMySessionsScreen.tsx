import { useQuery } from '@tanstack/react-query';
import { CalendarOff, ChevronRight, Clock, MapPin } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { useAuthStore } from '@/features/auth/auth-store';
import { type Session, listMySessions } from '@/features/sessions/sessions-api';

export function TraineeMySessionsScreen() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const locale = user?.preferredLocale ?? i18n.language ?? 'en';

  const { data: sessions, isPending } = useQuery({
    queryKey: ['trainee-mine-sessions'],
    queryFn: () => listMySessions('all'),
  });

  if (isPending) {
    return (
      <div className="mx-auto flex w-full max-w-md flex-col gap-4 px-4 pt-6">
        <div className="h-6 w-32 rounded bg-bg-primary" />
        <div className="h-24 rounded-xl bg-bg-primary" />
      </div>
    );
  }

  const all = sessions ?? [];
  const upcoming = all.filter(
    (s) =>
      s.status === 'scheduled' && new Date(s.scheduledAt) >= new Date(),
  );
  const past = all.filter((s) => !upcoming.includes(s));

  return (
    <main className="mx-auto flex w-full max-w-md flex-col gap-5 px-4 pb-8 pt-3">
      <h1 className="text-large-title text-text-color-primary">
        {t('traineeSessions.title')}
      </h1>

      {all.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <CalendarOff
            size={32}
            strokeWidth={1.5}
            aria-hidden
            className="text-text-color-tertiary"
          />
          <p className="text-body text-text-color-primary">
            {t('traineeSessions.emptyTitle')}
          </p>
          <p className="text-caption text-text-color-secondary">
            {t('traineeSessions.emptyBody')}
          </p>
        </div>
      ) : null}

      {upcoming.length > 0 ? (
        <section className="flex flex-col gap-2">
          <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
            {t('traineeSessions.upcoming')}
          </h3>
          <ul className="flex flex-col gap-2">
            {upcoming.map((s) => (
              <SessionRow
                key={s.id}
                session={s}
                locale={locale}
                onOpen={() => {
                  /* upcoming sessions have no assessment yet — view only */
                }}
              />
            ))}
          </ul>
        </section>
      ) : null}

      {past.length > 0 ? (
        <section className="flex flex-col gap-2">
          <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
            {t('traineeSessions.past')}
          </h3>
          <ul className="flex flex-col gap-2">
            {past.map((s) => (
              <SessionRow
                key={s.id}
                session={s}
                locale={locale}
                onOpen={() => {
                  if (s.assessmentId)
                    navigate(`/my-sessions/${s.assessmentId}`);
                }}
              />
            ))}
          </ul>
        </section>
      ) : null}
    </main>
  );
}

interface SessionRowProps {
  session: Session;
  locale: string;
  onOpen: () => void;
}

function SessionRow({ session: s, locale, onOpen }: SessionRowProps) {
  const { t } = useTranslation();
  const date = new Date(s.scheduledAt);
  const dateLabel = date.toLocaleDateString(locale, {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  });
  const timeLabel = date.toLocaleTimeString(locale, {
    hour: '2-digit',
    minute: '2-digit',
  });
  const isClickable =
    s.assessmentStatus === 'published' || s.assessmentStatus === 'edited';

  return (
    <li>
      <button
        type="button"
        onClick={onOpen}
        disabled={!isClickable}
        className="flex w-full items-start gap-3 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4 text-left disabled:cursor-default"
      >
        <div className="flex-1">
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-body font-medium text-text-color-primary">
              {dateLabel}
            </span>
            <span className="text-caption text-text-color-tertiary">
              {timeLabel}
            </span>
          </div>
          <p className="mt-1 text-footnote text-text-color-secondary">
            {s.coach.displayName}
            {s.focuses.length > 0
              ? ` · ${s.focuses
                  .slice(0, 2)
                  .map((f) => t(`sessionFocus.${f}`))
                  .join(' · ')}${s.focuses.length > 2 ? ` +${s.focuses.length - 2}` : ''}`
              : ''}
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-footnote text-text-color-tertiary">
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
            <TraineeStatusPill session={s} />
          </div>
        </div>
        {isClickable ? (
          <ChevronRight
            size={16}
            strokeWidth={1.75}
            aria-hidden
            className="mt-1 text-text-color-tertiary"
          />
        ) : null}
      </button>
    </li>
  );
}

function TraineeStatusPill({ session }: { session: Session }) {
  const { t } = useTranslation();
  if (session.status === 'cancelled') {
    return (
      <span className="rounded-full bg-bg-secondary px-2 py-0.5 text-pill text-text-color-tertiary">
        {t('sessions.status.cancelled')}
      </span>
    );
  }
  if (
    session.assessmentStatus === 'published' ||
    session.assessmentStatus === 'edited'
  ) {
    return (
      <span className="rounded-full bg-success-bg px-2 py-0.5 text-pill text-success-text">
        {t('traineeSessions.viewable')}
      </span>
    );
  }
  if (session.status === 'completed') {
    return (
      <span className="rounded-full border-[0.5px] border-border-hairline px-2 py-0.5 text-pill text-text-color-tertiary">
        {t('traineeSessions.awaitingNotes')}
      </span>
    );
  }
  return (
    <span className="border-accent/40 bg-accent/5 rounded-full border-[0.5px] px-2 py-0.5 text-pill text-accent">
      {t('sessions.status.scheduled')}
    </span>
  );
}
