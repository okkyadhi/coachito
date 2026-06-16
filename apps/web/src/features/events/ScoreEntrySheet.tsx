/**
 * Compact score-entry sheet.  Two modes:
 *
 * - Point-target events (e.g. "race to 21"): pick the winning side first,
 *   then tap the loser's score from a 0..(target-1) grid.  The winner
 *   auto-gets the target.
 * - Open events (untimed point, normal scoring): two number inputs side
 *   by side — same as the inline editor.
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

  const [winner, setWinner] = useState<'A' | 'B' | null>(null);
  const [loserScore, setLoserScore] = useState<number | null>(null);
  const [a, setA] = useState<string>('');
  const [b, setB] = useState<string>('');
  const [saving, setSaving] = useState(false);

  // Seed values from the existing match score when the sheet opens.
  useEffect(() => {
    if (!open || !match) return;
    if (match.scoreA != null && match.scoreB != null) {
      if (targetMode) {
        if (match.scoreA === target) {
          setWinner('A');
          setLoserScore(match.scoreB);
        } else if (match.scoreB === target) {
          setWinner('B');
          setLoserScore(match.scoreA);
        }
      }
      setA(String(match.scoreA));
      setB(String(match.scoreB));
    } else {
      setWinner(null);
      setLoserScore(null);
      setA('');
      setB('');
    }
  }, [open, match, target, targetMode]);

  const courtLabel = useMemo(() => {
    if (!match) return '';
    return courtDisplayName(
      match.courtNumber,
      event.courtNames,
      (n) => t('events.detail.courtN', { n }),
    );
  }, [match, event.courtNames, t]);

  if (!open || !match) return null;

  const canSubmit = targetMode
    ? winner != null && loserScore != null
    : a !== '' && b !== '' && !Number.isNaN(parseInt(a, 10)) && !Number.isNaN(parseInt(b, 10));

  const submit = async () => {
    if (!canSubmit) return;
    setSaving(true);
    try {
      if (targetMode) {
        const sa = winner === 'A' ? target : (loserScore ?? 0);
        const sb = winner === 'B' ? target : (loserScore ?? 0);
        await onSubmit(sa, sb);
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
          <>
            <p className="mb-2 text-section uppercase tracking-wide text-text-color-secondary">
              {t('events.detail.pickWinner')}
            </p>
            <div className="mb-4 flex gap-2">
              <SideButton
                label={nameA}
                active={winner === 'A'}
                onClick={() => setWinner('A')}
              />
              <SideButton
                label={nameB}
                active={winner === 'B'}
                onClick={() => setWinner('B')}
              />
            </div>

            <p className="mb-2 text-section uppercase tracking-wide text-text-color-secondary">
              {t('events.detail.loserScore', { target })}
            </p>
            <div className="grid grid-cols-6 gap-2">
              {Array.from({ length: target }, (_, i) => i).map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setLoserScore(n)}
                  disabled={winner == null}
                  className={[
                    'flex aspect-square items-center justify-center rounded-lg border-[0.5px] text-body font-medium tabular-nums transition-colors',
                    winner == null
                      ? 'border-border-hairline bg-bg-secondary text-text-color-tertiary opacity-50'
                      : loserScore === n
                        ? 'border-accent bg-accent text-white'
                        : 'border-border-hairline bg-bg-secondary text-text-color-primary',
                  ].join(' ')}
                >
                  {n}
                </button>
              ))}
            </div>
          </>
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

function SideButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'flex-1 rounded-lg border-[0.5px] px-3 py-3 text-body font-medium transition-colors',
        active
          ? 'border-accent bg-accent text-white'
          : 'border-border-hairline bg-bg-secondary text-text-color-primary',
      ].join(' ')}
    >
      {label}
    </button>
  );
}

function SideInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border-[0.5px] border-border-hairline bg-bg-secondary px-3 py-2">
      <span className="text-body text-text-color-primary">{label}</span>
      <input
        type="number"
        inputMode="numeric"
        min={0}
        max={999}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-16 rounded-md border-[0.5px] border-border-hairline bg-bg-primary px-2 py-1 text-right text-body font-medium tabular-nums text-text-color-primary focus:outline-none"
      />
    </div>
  );
}
