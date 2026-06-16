import { format } from 'date-fns';
import { enUS, id as idLocale } from 'date-fns/locale';
import { Building2, Clock, MapPin, Target, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';
import type { AssessmentSessionDetails, SessionFocus } from '@/db/dexie';

interface Props {
  value: AssessmentSessionDetails;
  onChange: (next: AssessmentSessionDetails) => void;
}

const DURATION_OPTIONS = [30, 45, 60, 90, 120] as const;
const FOCUS_OPTIONS: SessionFocus[] = [
  'drilling',
  'match_play',
  'technique_focus',
  'conditioning',
  'mental_training',
  'general',
];

/** Resolves the values shown / sent.  null fields fall back to "right now". */
function effective(v: AssessmentSessionDetails) {
  return {
    scheduledAt: v.scheduledAt ? new Date(v.scheduledAt) : new Date(),
    durationMin: v.durationMin ?? 60,
    court: v.court ?? null,
    focus: v.focus ?? null,
  };
}

export function SessionDetailsStrip({ value, onChange }: Props) {
  const { t, i18n } = useTranslation();
  const dfLocale = i18n.language === 'id' ? idLocale : enUS;
  const [sheetOpen, setSheetOpen] = useState(false);
  const eff = effective(value);

  const today = new Date();
  const isToday =
    eff.scheduledAt.toDateString() === today.toDateString();
  const dateLabel = isToday
    ? `${t('sessionDetails.today')}, ${format(eff.scheduledAt, 'HH:mm', { locale: dfLocale })}`
    : format(eff.scheduledAt, 'd MMM · HH:mm', { locale: dfLocale });

  return (
    <>
      <button
        type="button"
        onClick={() => setSheetOpen(true)}
        className="flex w-full items-center gap-1.5 overflow-x-auto rounded-md border-[0.5px] border-border-hairline bg-bg-primary p-2 text-left"
      >
        <Chip icon={<Clock size={12} aria-hidden />} label={dateLabel} active />
        <Chip
          icon={<Clock size={12} aria-hidden />}
          label={t('sessionDetails.minutes', { count: eff.durationMin })}
          active
        />
        <Chip
          icon={<MapPin size={12} aria-hidden />}
          label={eff.court ?? t('sessionDetails.addCourt')}
          active={eff.court !== null}
        />
        <Chip
          icon={<Target size={12} aria-hidden />}
          label={
            eff.focus
              ? t(`sessionFocus.${eff.focus}`)
              : t('sessionDetails.addFocus')
          }
          active={eff.focus !== null}
        />
      </button>

      {sheetOpen ? (
        <SessionDetailsSheet
          value={value}
          onClose={() => setSheetOpen(false)}
          onConfirm={(next) => {
            onChange(next);
            setSheetOpen(false);
          }}
        />
      ) : null}
    </>
  );
}

function Chip({
  icon,
  label,
  active,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
}) {
  return (
    <span
      className={[
        'inline-flex shrink-0 items-center gap-1 rounded-full border-[0.5px] px-2.5 py-1 text-pill',
        active
          ? 'border-accent bg-accent-bg text-accent'
          : 'border-border-hairline bg-bg-secondary text-text-color-tertiary',
      ].join(' ')}
    >
      {icon}
      {label}
    </span>
  );
}

interface SheetProps {
  value: AssessmentSessionDetails;
  onClose: () => void;
  onConfirm: (next: AssessmentSessionDetails) => void;
}

function SessionDetailsSheet({ value, onClose, onConfirm }: SheetProps) {
  const { t } = useTranslation();
  const eff = effective(value);

  // Pre-fill the form from the effective values so an empty value still
  // shows "now / 60min / blank / blank" the coach can tweak.
  const initialIso = (() => {
    const local = new Date(
      eff.scheduledAt.getTime() - eff.scheduledAt.getTimezoneOffset() * 60_000,
    );
    return local.toISOString().slice(0, 16);
  })();
  const [scheduledLocal, setScheduledLocal] = useState(initialIso);
  const [durationMin, setDurationMin] = useState<number>(eff.durationMin);
  const [court, setCourt] = useState<string>(eff.court ?? '');
  const [focus, setFocus] = useState<SessionFocus | null>(eff.focus);

  const handleSave = () => {
    const isoOut = scheduledLocal ? new Date(scheduledLocal).toISOString() : null;
    onConfirm({
      scheduledAt: isoOut,
      durationMin,
      court: court.trim() === '' ? null : court.trim(),
      focus,
    });
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('sessionDetails.sheetTitle')}
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
          <span className="text-h3 text-text-color-primary">
            {t('sessionDetails.sheetTitle')}
          </span>
          <span className="size-9" aria-hidden />
        </header>

        <div className="flex-1 overflow-y-auto p-4">
          {/* Date & time */}
          <Field
            icon={<Clock size={16} className="text-text-color-secondary" aria-hidden />}
            label={t('sessionDetails.dateTime')}
          >
            <input
              type="datetime-local"
              value={scheduledLocal}
              onChange={(e) => setScheduledLocal(e.target.value)}
              className="w-full rounded-md border-[0.5px] border-border-hairline bg-bg-primary p-2 text-body text-text-color-primary focus:border-accent focus:outline-none"
            />
          </Field>

          {/* Duration */}
          <Field
            icon={<Clock size={16} className="text-text-color-secondary" aria-hidden />}
            label={t('sessionDetails.duration')}
          >
            <div className="flex flex-wrap gap-1.5">
              {DURATION_OPTIONS.map((opt) => {
                const active = durationMin === opt;
                return (
                  <button
                    key={opt}
                    type="button"
                    onClick={() => setDurationMin(opt)}
                    aria-pressed={active}
                    className={[
                      'min-h-[36px] rounded-full border-[0.5px] px-3 text-caption font-medium',
                      active
                        ? 'border-accent bg-accent-bg text-accent'
                        : 'border-border-hairline bg-bg-primary text-text-color-secondary',
                    ].join(' ')}
                  >
                    {t('sessionDetails.minutes', { count: opt })}
                  </button>
                );
              })}
            </div>
          </Field>

          {/* Court */}
          <Field
            icon={<MapPin size={16} className="text-text-color-secondary" aria-hidden />}
            label={t('sessionDetails.court')}
          >
            <input
              type="text"
              value={court}
              onChange={(e) => setCourt(e.target.value)}
              placeholder={t('sessionDetails.courtPlaceholder')}
              maxLength={50}
              className="w-full rounded-md border-[0.5px] border-border-hairline bg-bg-primary p-2 text-body text-text-color-primary placeholder:text-text-color-tertiary focus:border-accent focus:outline-none"
            />
          </Field>

          {/* Focus */}
          <Field
            icon={<Building2 size={16} className="text-text-color-secondary" aria-hidden />}
            label={t('sessionDetails.focus')}
          >
            <div className="flex flex-wrap gap-1.5">
              {FOCUS_OPTIONS.map((opt) => {
                const active = focus === opt;
                return (
                  <button
                    key={opt}
                    type="button"
                    onClick={() => setFocus(active ? null : opt)}
                    aria-pressed={active}
                    className={[
                      'min-h-[36px] rounded-full border-[0.5px] px-3 text-caption font-medium',
                      active
                        ? 'border-accent bg-accent-bg text-accent'
                        : 'border-border-hairline bg-bg-primary text-text-color-secondary',
                    ].join(' ')}
                  >
                    {t(`sessionFocus.${opt}`)}
                  </button>
                );
              })}
            </div>
          </Field>
        </div>

        <footer className="flex flex-col gap-2 border-t-[0.5px] border-border-hairline px-4 py-3">
          <PrimaryButton onClick={handleSave}>
            {t('sessionDetails.save')}
          </PrimaryButton>
          <SecondaryButton onClick={onClose}>{t('common.cancel')}</SecondaryButton>
        </footer>
      </div>
    </div>
  );
}

function Field({
  icon,
  label,
  children,
}: {
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-4">
      <div className="mb-1.5 flex items-center gap-1.5">
        {icon}
        <span className="text-section uppercase tracking-wide text-text-color-secondary">
          {label}
        </span>
      </div>
      {children}
    </div>
  );
}
