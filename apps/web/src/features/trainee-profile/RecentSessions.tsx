import { format } from 'date-fns';
import { enUS, id as idLocale } from 'date-fns/locale';
import { ChevronRight, User } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { useAuthStore } from '@/features/auth/auth-store';
import { StatusPill } from '@/features/sessions/StatusPill';

import type { SessionEntry } from './profile-types';

interface Props {
  sessions: SessionEntry[];
  locale: string;
  athleteId: string;
}

export function RecentSessions({ sessions, locale, athleteId }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const currentUserId = useAuthStore((s) => s.user?.id ?? null);
  if (sessions.length === 0) return null;

  const df = locale === 'id' ? idLocale : enUS;

  return (
    <section className="flex flex-col gap-3">
      <h2 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {t('profile.sessions.title')}
      </h2>

      <div className="flex flex-col gap-3">
        {sessions.map((s) => {
          const date = new Date(s.scheduledAt);
          const dateLine = format(date, 'EEE d MMM', { locale: df });
          const timeLine = format(date, locale === 'id' ? 'HH.mm' : 'H:mm', { locale: df });
          const focusLabel =
            s.focuses.length > 0
              ? s.focuses
                  .slice(0, 2)
                  .map((f) => t(`sessionFocus.${f}`))
                  .join(' · ') +
                (s.focuses.length > 2
                  ? ` +${s.focuses.length - 2}`
                  : '')
              : null;
          const isOwn = s.coach.id === currentUserId;
          const target = isOwn
            ? `/trainees/${athleteId}/assess?session=${s.id}`
            : `/trainees/${athleteId}/assess?session=${s.id}&readonly=1`;

          return (
            <button
              key={s.id}
              type="button"
              onClick={() => navigate(target)}
              className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4 text-left hover:bg-bg-secondary"
            >
              <header className="flex items-baseline justify-between gap-2">
                <span className="text-body font-medium text-text-color-primary">
                  {dateLine}
                </span>
                <div className="flex items-baseline gap-2">
                  <span className="text-caption text-text-color-tertiary">{timeLine}</span>
                  <ChevronRight
                    size={14}
                    strokeWidth={1.75}
                    aria-hidden
                    className="text-text-color-tertiary"
                  />
                </div>
              </header>

              <div className="mt-1 flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1 text-footnote text-text-color-secondary">
                  <User size={12} strokeWidth={1.75} aria-hidden />
                  {s.coach.displayName}
                </span>
                <StatusPill
                  session={{
                    status: 'scheduled',
                    assessmentStatus: s.assessmentStatus,
                    scheduledAt: s.scheduledAt,
                  }}
                />
                {focusLabel ? (
                  <span className="rounded-full bg-accent-bg px-2 py-0.5 text-pill text-accent">
                    {focusLabel}
                  </span>
                ) : null}
              </div>

              {s.summary ? (
                <p className="mt-2 text-caption leading-relaxed text-text-color-primary">
                  {s.summary}
                </p>
              ) : null}
              <p className="mt-2 text-footnote text-text-color-tertiary">
                {t('profile.sessions.skillsUpdated', { count: s.skillsUpdated })}
              </p>
            </button>
          );
        })}
      </div>
    </section>
  );
}
