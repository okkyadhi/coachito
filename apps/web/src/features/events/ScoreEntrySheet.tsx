/**
 * Compact score-entry sheet.  Three scoring layouts:
 *
 * totalMode  — point+target or normal_total:
 *   Grid of buttons 0..target for side A.  Side B auto-derives as
 *   (target − A) and is shown below.  A=15 → B=6 when target=21.
 *
 * firstToMode — normal_first_to:
 *   Pick winner (Team A | Team B), then pick loser's score from a
 *   0..(target−1) grid.  Winner auto-gets the target.
 *
 * openMode  — no target set (untimed point or normal):
 *   Two numeric inputs side by side.
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

  const target = event.scoringTarget ?? 0;
  const totalMode =
    event.scoringTarget != null &&
    (event.scoringMode === 'point' || event.scoringMode === 'normal_total');
  const firstToMode =
    event.scoringMode === 'normal_first_to' && event.scoringTarget != null;

  // totalMode: which score side A tapped (null = not yet selected)
  const [pickedA, setPickedA] = useState<number | null>(null);

  // firstToMode: who won, and what the loser scored
  const [winner, setWinner] = useState<'A' | 'B' | null>(null);
  const [loserScore, setLoserScore] = useState<number | null>(null);

  // openMode: free text inputs
  const [a, setA] = useState<string>('');
  const [b, setB] = useState<string>('');

  const [saving, setSaving] = useState(false);

  // Seed existing scores when the sheet opens.
  useEffect(() => {
    if (!open || !match) return;
    if (match.scoreA != null && match.scoreB != null) {
      const sa = match.scoreA;
      const sb = match.scoreB;
      if (totalMode) {
        setPickedA(sa);
      } else if (firstToMode) {
        if (sa === target) {
          setWinner('A');
          setLoserScore(sb);
        } else if (sb === target) {
          setWinner('B');
          setLoserScore(sa);
        }
      } else {
        setA(String(sa));
        setB(String(sb));
      }
    } else {
      setPickedA(null);
      setWinner(null);
      setLoserScore(null);
      setA('');
      setB('');
    }
  }, [open, match]); // eslint-disable-line react-hooks/exhaustive-deps

  const courtLabel = useMemo(() => {
    if (!match) return '';
    return courtDisplayName(
      match.courtNumber,
      event.courtNames,
      (n) => t('events.detail.courtN', { n }),
    );
  }, [match, event.courtNames, t]);

  if (!open || !match) return null;

  const canSubmit = totalMode
    ? pickedA != null
    : firstToMode
      ? winner != null && loserScore != null
      : a !== '' && b !== '' && !Number.isNaN(parseInt(a, 10)) && !Number.isNaN(parseInt(b, 10));

  const submit = async () => {
    if (!canSubmit) return;
    setSaving(true);
    try {
      if (totalMode && pickedA != null) {
        await onSubmit(pickedA, target - pickedA);
      } else if (firstToMode && winner != null && loserScore != null) {
        const sa = winner === 'A' ? target : loserScore;
        const sb = winner === 'B' ? target : loserScore;
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

        {totalMode ? (
          <>
            {/* Side A score grid — tap to select; side B derives automatically */}
            <div className="mb-3 flex items-center justify-between px-0.5">
              <span className="text-body font-medium text-text-color-primary">{nameA}</span>
              {pickedA != null && (
                <span className="text-body font-medium tabular-nums text-accent">
                  {pickedA}
                </span>
              )}
            </div>
            <ScoreGrid
              count={target + 1}
              selected={pickedA}
              onSelect={setPickedA}
            />
            {/* Side B derived score */}
            <div className="mt-3 flex items-center justify-between rounded-md border-[0.5px] border-border-hairline bg-bg-secondary px-3 py-2.5">
              <span className="text-body text-text-color-secondary">{nameB}</span>
              <span className="text-body font-medium tabular-nums text-text-color-secondary">
                {pickedA != null ? target - pickedA : '—'}
              </span>
            </div>
          </>
        ) : firstToMode ? (
          <>
            {/* Winner picker */}
            <p className="mb-2 text-section uppercase tracking-wide text-text-color-secondary">
              {t('events.detail.pickWinner')}
            </p>
            <div className="mb-4 flex gap-2">
              <SideButton label={nameA} active={winner === 'A'} onClick={() => setWinner('A')} />
              <SideButton label={nameB} active={winner === 'B'} onClick={() => setWinner('B')} />
            </div>
            {/* Loser score grid */}
            <p className="mb-2 text-section uppercase tracking-wide text-text-color-secondary">
              {t('events.detail.loserScore', { target })}
            </p>
            <ScoreGrid
              count={target}
              selected={loserScore}
              onSelect={setLoserScore}
              disabled={winner == null}
            />
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

/** Numbered tap-button grid.  Used for both score pickers. */
function ScoreGrid({
  count,
  selected,
  onSelect,
  disabled = false,
}: {
  count: number;
  selected: number | null;
  onSelect: (n: number) => void;
  disabled?: boolean;
}) {
  return (
    <div className="grid grid-cols-6 gap-2">
      {Array.from({ length: count }, (_, i) => i).map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onSelect(n)}
          disabled={disabled}
          className={[
            'flex aspect-square items-center justify-center rounded-lg border-[0.5px]',
            'text-body font-medium tabular-nums transition-colors',
            disabled
              ? 'border-border-hairline bg-bg-secondary text-text-color-tertiary opacity-50'
              : selected === n
                ? 'border-accent bg-accent text-white'
                : 'border-border-hairline bg-bg-secondary text-text-color-primary',
          ].join(' ')}
        >
          {n}
        </button>
      ))}
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
