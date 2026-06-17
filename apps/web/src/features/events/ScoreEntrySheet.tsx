/**
 * Compact score-entry sheet.  Two modes:
 *
 * - Point-target events (e.g. "total 21"): enter one side's score; the
 *   other auto-derives as (target - entered).  A=15 → B=6 for target 21.
 * - Open events (untimed point, normal scoring): two number inputs side
 *   by side.
 *
 * Returns through ``onSubmit`` so the parent does the actual persistence
 * (lets the caller decide whether to invalidate caches, show toasts etc.).
 */

import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';

import { courtDisplayName } from './events-api';
import type { EventSummary, Match } from './events-types';

interface Props {
  open: boolean;
  match: Match | null;
  event: EventSummary;
  nameA: string;
  nameB: string;
  onClose: () => void;
  onSubmit: (scoreA: number, scoreB: number) => Promise<void>;
}

export function ScoreEntrySheet({
  open,
  match,
  event,
  nameA,
  nameB,
  onClose,
  onSubmit,
}: Props) {
  const { t } = useTranslation();
  // Only "race-to-target" point events get the compact grid mode.  In
  // untimed point scoring (no target) both sides can land anywhere, so
  // we fall back to the two-input layout.
  const targetMode =
    event.scoringMode === 'point' && event.scoringTarget != null;
  const target = event.scoringTarget ?? 0;

  // targetMode: one editable input (side A); side B = target - sideA.
  const [a, setA] = useState<string>('');
  const [b, setB] = useState<string>('');
  const [saving, setSaving] = useState(false);

  // Seed values from the existing match score when the sheet opens.
  useEffect(() => {
    if (!open || !match) return;
    if (match.scoreA != null && match.scoreB != null) {
      setA(String(match.scoreA));
      setB(String(match.scoreB));
    } else {
      setA('');
      setB('');
    }
  }, [open, match]);

  const courtLabel = useMemo(() => {
    if (!match) return '';
    return courtDisplayName(
      match.courtNumber,
      event.courtNames,
      (n) => t('events.detail.courtN', { n }),
    );
  }, [match, event.courtNames, t]);

  if (!open || !match) return null;

  // For targetMode: A is editable, B derives from (target - A).
  const parsedA = parseInt(a, 10);
  const derivedB = targetMode && !Number.isNaN(parsedA) ? target - parsedA : null;

  const canSubmit = targetMode
    ? a !== '' && !Number.isNaN(parsedA) && parsedA >= 0 && parsedA <= target
    : a !== '' && b !== '' && !Number.isNaN(parseInt(a, 10)) && !Number.isNaN(parseInt(b, 10));

  const submit = async () => {
    if (!canSubmit) return;
    setSaving(true);
    try {
      if (targetMode) {
        await onSubmit(parsedA, target - parsedA);
      } else {
        await onSubmit(parseInt(a, 10), parseInt(b, 10));
      }
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const status =
    match.scoreA != null
      ? t('events.detail.scored')
      : t('events.detail.notStarted');

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md rounded-t-2xl bg-bg-primary p-5"
      >
        <header className="mb-4 flex items-center justify-between gap-2">
          <h2 className="text-h3 text-text-color-primary">{courtLabel}</h2>
          <span className="rounded-full bg-bg-secondary px-2 py-0.5 text-pill text-text-color-secondary">
            {status}
          </span>
        </header>

        {targetMode ? (
          <div className="flex flex-col gap-3">
            <SideInput
              label={nameA}
              value={a}
              onChange={(v) => {
                setA(v);
                // Keep the open-mode input in sync so seeding still works.
                setB(v !== '' && !Number.isNaN(parseInt(v, 10)) ? String(target - parseInt(v, 10)) : '');
              }}
              max={target}
              placeholder="0"
            />
            <SideInput
              label={nameB}
              value={derivedB != null ? String(derivedB) : ''}
              onChange={() => {/* derived — not editable */}}
              readOnly
              placeholder={String(target)}
            />
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <SideInput label={nameA} value={a} onChange={setA} />
            <SideInput label={nameB} value={b} onChange={setB} />
          </div>
        )}

        <div className="mt-5 flex flex-col gap-2">
          <PrimaryButton onClick={() => void submit()} disabled={!canSubmit || saving}>
            {saving ? t('events.detail.saving') : t('events.detail.saveScore')}
          </PrimaryButton>
          <SecondaryButton onClick={onClose}>{t('common.cancel')}</SecondaryButton>
        </div>
      </div>
    </div>
  );
}

function SideInput({
  label,
  value,
  onChange,
  max = 999,
  placeholder,
  readOnly = false,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  max?: number;
  placeholder?: string;
  readOnly?: boolean;
}) {
  return (
    <div className={[
      'flex items-center justify-between gap-3 rounded-md border-[0.5px] px-3 py-2',
      readOnly
        ? 'border-border-hairline bg-bg-secondary/60'
        : 'border-border-hairline bg-bg-secondary',
    ].join(' ')}>
      <span className={[
        'text-body',
        readOnly ? 'text-text-color-secondary' : 'text-text-color-primary',
      ].join(' ')}>{label}</span>
      <input
        type="number"
        inputMode="numeric"
        min={0}
        max={max}
        value={value}
        placeholder={placeholder}
        readOnly={readOnly}
        onChange={(e) => !readOnly && onChange(e.target.value)}
        className={[
          'w-16 rounded-md border-[0.5px] border-border-hairline px-2 py-1 text-right text-body font-medium tabular-nums focus:outline-none',
          readOnly
            ? 'bg-bg-tertiary text-text-color-secondary cursor-default'
            : 'bg-bg-primary text-text-color-primary',
        ].join(' ')}
      />
    </div>
  );
}
