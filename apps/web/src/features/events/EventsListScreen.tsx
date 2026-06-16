import { useQuery } from '@tanstack/react-query';
import { ChevronRight, Plus, Trophy } from 'lucide-react';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { PrimaryButton } from '@/components/PrimaryButton';

import { listEvents } from './events-api';
import type { EventStatus, EventSummary } from './events-types';

const ORDER: EventStatus[] = ['active', 'draft', 'completed', 'cancelled'];

export function EventsListScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const { data, isPending } = useQuery({
    queryKey: ['events', 'list'],
    queryFn: () => listEvents(),
    staleTime: 30 * 1000,
  });

  const grouped = useMemo(() => {
    const m = new Map<EventStatus, EventSummary[]>();
    for (const e of data ?? []) {
      if (!m.has(e.status)) m.set(e.status, []);
      m.get(e.status)!.push(e);
    }
    return m;
  }, [data]);

  return (
    <main className="mx-auto flex w-full max-w-md flex-col gap-4 px-4 pb-24 pt-4">
      <header className="flex items-start justify-between px-1">
        <div>
          <h1 className="text-large-title text-text-color-primary">
            {t('events.title')}
          </h1>
          <p className="mt-0.5 text-caption text-text-color-secondary">
            {t('events.subtitle')}
          </p>
        </div>
      </header>

      {isPending ? <Skeleton /> : null}

      {!isPending && (data?.length ?? 0) === 0 ? <EmptyState /> : null}

      {!isPending && (data?.length ?? 0) > 0
        ? ORDER.filter((s) => (grouped.get(s)?.length ?? 0) > 0).map((s) => (
            <Section
              key={s}
              status={s}
              events={grouped.get(s)!}
              onTap={(id) => navigate(`/events/${id}`)}
            />
          ))
        : null}

      <div className="fixed inset-x-0 bottom-[64px] z-10 px-4">
        <div className="mx-auto max-w-md">
          <PrimaryButton
            leftIcon={<Plus size={18} strokeWidth={2} aria-hidden />}
            onClick={() => navigate('/events/new')}
          >
            {t('events.newCta')}
          </PrimaryButton>
        </div>
      </div>
    </main>
  );
}

function Section({
  status,
  events,
  onTap,
}: {
  status: EventStatus;
  events: EventSummary[];
  onTap: (id: string) => void;
}) {
  const { t } = useTranslation();
  return (
    <section className="flex flex-col gap-2">
      <h2 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {t(`events.statusGroup.${status}`)}
      </h2>
      <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
        {events.map((e, idx) => (
          <EventRow
            key={e.id}
            event={e}
            onTap={() => onTap(e.id)}
            borderTop={idx > 0}
          />
        ))}
      </div>
    </section>
  );
}

function EventRow({
  event,
  onTap,
  borderTop,
}: {
  event: EventSummary;
  onTap: () => void;
  borderTop: boolean;
}) {
  const { t } = useTranslation();
  return (
    <button
      type="button"
      onClick={onTap}
      className={[
        'flex w-full min-h-tap items-center gap-3 p-4 text-left active:bg-bg-secondary',
        borderTop ? 'border-t-[0.5px] border-border-hairline' : '',
      ].join(' ')}
    >
      <div className="min-w-0 flex-1">
        <p className="truncate text-body text-text-color-primary">
          {event.title}
        </p>
        <p className="text-footnote text-text-color-secondary">
          {t(`events.format.${event.format}`)} ·{' '}
          {t('events.courts', { count: event.courtCount })} ·{' '}
          {t('events.players', { count: event.participantsCount })}
        </p>
      </div>
      <ChevronRight
        size={16}
        strokeWidth={1.75}
        className="text-text-color-tertiary"
        aria-hidden
      />
    </button>
  );
}

function EmptyState() {
  const { t } = useTranslation();
  return (
    <section className="flex flex-col items-center gap-3 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-8 text-center">
      <span className="flex size-12 items-center justify-center rounded-full border-[0.5px] border-border-hairline bg-bg-secondary text-text-color-tertiary">
        <Trophy size={20} strokeWidth={1.5} aria-hidden />
      </span>
      <h2 className="text-h3 text-text-color-primary">
        {t('events.emptyTitle')}
      </h2>
      <p className="max-w-[280px] text-caption text-text-color-secondary">
        {t('events.emptyBody')}
      </p>
    </section>
  );
}

function Skeleton() {
  return (
    <div className="flex flex-col gap-3">
      <div className="h-20 rounded-xl bg-bg-primary" />
      <div className="h-20 rounded-xl bg-bg-primary" />
    </div>
  );
}
