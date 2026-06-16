import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import { enUS, id as idLocale } from 'date-fns/locale';
import { ChevronRight, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Avatar } from '@/components/Avatar';
import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';
import { listTrainees } from '@/features/trainees/trainees-api';

import { listTraineeSessions } from './reports-api';

interface Props {
  open: boolean;
  onClose: () => void;
  /** Pre-select a trainee and skip the picker — used by the trainee profile
   *  entry point so the coach lands one step closer to "generate". */
  initialTraineeId?: string;
  /** Display name for the pre-selected trainee.  Required when
   *  `initialTraineeId` is set because we don't fetch the trainees list in
   *  that mode. */
  initialTraineeName?: string;
  onConfirm: (args: {
    traineeId: string;
    traineeName: string;
    mode: 'monthly' | 'session';
    sessionId?: string;
    periodStart?: string;
    periodEnd?: string;
  }) => void;
}

// Last 6 months including the previous full month (default selection).
function monthOptions(): { value: string; label: string; start: string; end: string }[] {
  const out: { value: string; label: string; start: string; end: string }[] = [];
  const now = new Date();
  for (let i = 1; i <= 6; i += 1) {
    const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - i, 1));
    const next = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0));
    const value = `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`;
    const label = d.toLocaleString(undefined, { month: 'long', year: 'numeric' });
    out.push({
      value,
      label,
      start: d.toISOString().slice(0, 10),
      end: next.toISOString().slice(0, 10),
    });
  }
  return out;
}

export function GenerateReportSheet({
  open,
  onClose,
  initialTraineeId,
  initialTraineeName,
  onConfirm,
}: Props) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language === 'id' ? idLocale : enUS;
  const months = monthOptions();
  const [traineeId, setTraineeId] = useState<string | null>(
    initialTraineeId ?? null,
  );
  const [mode, setMode] = useState<'monthly' | 'session'>('monthly');
  const [monthValue, setMonthValue] = useState<string>(months[0]?.value ?? '');
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Only fetch the trainee list when we need it to render a picker.  Coming
  // in from a trainee profile, we already know who the report is for —
  // skip the round trip and skip the section entirely.
  const lockedToTrainee = initialTraineeId != null;
  const traineesQ = useQuery({
    queryKey: ['trainees', null],
    queryFn: () => listTrainees({}),
    enabled: open && !lockedToTrainee,
    staleTime: 30_000,
  });
  const trainees = traineesQ.data?.trainees ?? [];

  const sessionsQ = useQuery({
    queryKey: ['trainee-sessions', traineeId],
    queryFn: () => listTraineeSessions(traineeId as string),
    enabled: open && mode === 'session' && traineeId !== null,
    staleTime: 30_000,
  });
  const sessions = sessionsQ.data ?? [];

  const handleSubmit = () => {
    if (!traineeId) return;
    const displayName = lockedToTrainee
      ? (initialTraineeName ?? '')
      : (trainees.find((t) => t.id === traineeId)?.displayName ?? '');
    if (mode === 'monthly') {
      const period = months.find((m) => m.value === monthValue);
      if (!period) return;
      onConfirm({
        traineeId,
        traineeName: displayName,
        mode: 'monthly',
        periodStart: period.start,
        periodEnd: period.end,
      });
    } else {
      if (!sessionId) return;
      onConfirm({
        traineeId,
        traineeName: displayName,
        mode: 'session',
        sessionId,
      });
    }
    if (!lockedToTrainee) setTraineeId(null);
    setSessionId(null);
  };

  if (!open) return null;

  const canSubmit =
    traineeId !== null &&
    (mode === 'monthly' ? monthValue !== '' : sessionId !== null);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('reports.sheet.title')}
      className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 sm:items-center"
    >
      <div className="flex max-h-[85vh] w-full max-w-md flex-col rounded-t-2xl bg-bg-primary sm:rounded-2xl">
        <header className="flex items-center justify-between border-b-[0.5px] border-border-hairline px-4 py-3">
          <button
            type="button"
            onClick={onClose}
            aria-label={t('common.cancel')}
            className="flex size-9 items-center justify-center rounded-full text-text-color-secondary"
          >
            <X size={18} strokeWidth={1.75} aria-hidden />
          </button>
          <span className="text-h3 text-text-color-primary">{t('reports.sheet.title')}</span>
          <span className="size-9" aria-hidden />
        </header>

        <div className="flex-1 overflow-y-auto p-4">
          {/* Mode toggle */}
          <div
            role="radiogroup"
            aria-label={t('reports.sheet.modeLabel')}
            className="flex gap-1 rounded-md border-[0.5px] border-border-hairline bg-bg-tertiary p-1"
          >
            {(['monthly', 'session'] as const).map((m) => {
              const active = mode === m;
              return (
                <button
                  key={m}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => setMode(m)}
                  className={[
                    'min-h-tap flex-1 rounded-sm text-[14px] font-medium transition-colors duration-100',
                    active
                      ? 'border-[0.5px] border-accent bg-bg-primary text-accent'
                      : 'text-text-color-secondary',
                  ].join(' ')}
                >
                  {t(`reports.sheet.mode_${m}`)}
                </button>
              );
            })}
          </div>

          {/* Trainee picker — only when launched without a pre-selected
              trainee.  From the trainee profile we already know who; rendering
              the picker would be redundant and overwhelming for clubs with
              many trainees. */}
          {!lockedToTrainee ? (
            <>
              <h3 className="mt-5 px-1 text-section uppercase tracking-wide text-text-color-secondary">
                {t('reports.sheet.trainee')}
              </h3>
              <div className="mt-2 overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
                {traineesQ.isPending ? (
                  <p className="px-4 py-6 text-caption text-text-color-secondary">
                    {t('common.loading')}
                  </p>
                ) : trainees.length === 0 ? (
                  <p className="px-4 py-6 text-caption text-text-color-secondary">
                    {t('reports.sheet.noTrainees')}
                  </p>
                ) : (
                  trainees.map((tr, i) => {
                    const selected = traineeId === tr.id;
                    return (
                      <button
                        key={tr.id}
                        type="button"
                        onClick={() => {
                          setTraineeId(tr.id);
                          setSessionId(null);
                        }}
                        aria-pressed={selected}
                        className={[
                          'flex min-h-tap w-full items-center gap-3 px-4 py-3 text-left',
                          i > 0 ? 'border-t-[0.5px] border-border-hairline' : '',
                          selected ? 'bg-accent-bg' : '',
                        ].join(' ')}
                      >
                        <Avatar name={tr.displayName} size={36} />
                        <span
                          className={[
                            'flex-1 truncate text-body',
                            selected ? 'text-accent' : 'text-text-color-primary',
                          ].join(' ')}
                        >
                          {tr.displayName}
                        </span>
                        {selected ? (
                          <ChevronRight
                            size={16}
                            strokeWidth={2}
                            className="text-accent"
                            aria-hidden
                          />
                        ) : null}
                      </button>
                    );
                  })
                )}
              </div>
            </>
          ) : (
            // Tiny "for: {name}" affordance so the coach has visible
            // confirmation of which trainee they're generating for.
            <p className="mt-3 px-1 text-caption text-text-color-tertiary">
              {t('reports.sheet.forTrainee', {
                name: initialTraineeName ?? '',
              })}
            </p>
          )}

          {/* Monthly: period chips */}
          {mode === 'monthly' ? (
            <>
              <h3 className="mt-5 px-1 text-section uppercase tracking-wide text-text-color-secondary">
                {t('reports.sheet.period')}
              </h3>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {months.map((m) => {
                  const active = monthValue === m.value;
                  return (
                    <button
                      key={m.value}
                      type="button"
                      onClick={() => setMonthValue(m.value)}
                      aria-pressed={active}
                      className={[
                        'min-h-[36px] rounded-full border-[0.5px] px-3 text-caption font-medium',
                        active
                          ? 'border-accent bg-accent-bg text-accent'
                          : 'border-border-hairline bg-bg-primary text-text-color-secondary',
                      ].join(' ')}
                    >
                      {m.label}
                    </button>
                  );
                })}
              </div>
            </>
          ) : (
            <>
              <h3 className="mt-5 px-1 text-section uppercase tracking-wide text-text-color-secondary">
                {t('reports.sheet.session')}
              </h3>
              <div className="mt-2 overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
                {traineeId === null ? (
                  <p className="px-4 py-6 text-caption text-text-color-secondary">
                    {t('reports.sheet.pickTraineeFirst')}
                  </p>
                ) : sessionsQ.isPending ? (
                  <p className="px-4 py-6 text-caption text-text-color-secondary">
                    {t('common.loading')}
                  </p>
                ) : sessions.length === 0 ? (
                  <p className="px-4 py-6 text-caption text-text-color-secondary">
                    {t('reports.sheet.noSessions')}
                  </p>
                ) : (
                  sessions.map((s, i) => {
                    const selected = sessionId === s.id;
                    const dateLabel = format(
                      new Date(s.scheduledAt),
                      'EEE d MMM · HH:mm',
                      { locale },
                    );
                    const meta = [s.court, s.focus, `${s.durationMin}m`]
                      .filter(Boolean)
                      .join(' · ');
                    return (
                      <button
                        key={s.id}
                        type="button"
                        onClick={() => setSessionId(s.id)}
                        aria-pressed={selected}
                        className={[
                          'flex min-h-tap w-full flex-col items-start gap-0.5 px-4 py-3 text-left',
                          i > 0 ? 'border-t-[0.5px] border-border-hairline' : '',
                          selected ? 'bg-accent-bg' : '',
                        ].join(' ')}
                      >
                        <span
                          className={[
                            'text-body',
                            selected ? 'text-accent' : 'text-text-color-primary',
                          ].join(' ')}
                        >
                          {dateLabel}
                        </span>
                        {meta ? (
                          <span className="text-footnote text-text-color-secondary">
                            {meta}
                          </span>
                        ) : null}
                      </button>
                    );
                  })
                )}
              </div>
            </>
          )}
        </div>

        <footer className="flex flex-col gap-2 border-t-[0.5px] border-border-hairline px-4 py-3">
          <PrimaryButton onClick={handleSubmit} disabled={!canSubmit}>
            {t('reports.sheet.generate')}
          </PrimaryButton>
          <SecondaryButton onClick={onClose}>{t('common.cancel')}</SecondaryButton>
        </footer>
      </div>
    </div>
  );
}
