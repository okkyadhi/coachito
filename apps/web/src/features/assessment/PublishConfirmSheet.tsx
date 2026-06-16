import { ArrowDown, ArrowUp, Minus, Plus, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';

export interface ScoreDiffEntry {
  skillName: string;
  from: number | null; // null = first time this skill is scored
  to: number;
}

interface Props {
  open: boolean;
  loading: boolean;
  online: boolean;
  ratedCount: number;
  summaryChars: number;
  diffs: ScoreDiffEntry[];
  onCancel: () => void;
  onConfirm: (forceEmpty: boolean) => void;
}

export function PublishConfirmSheet({
  open,
  loading,
  online,
  ratedCount,
  summaryChars,
  diffs,
  onCancel,
  onConfirm,
}: Props) {
  const { t } = useTranslation();
  const [forceEmpty, setForceEmpty] = useState(false);

  if (!open) return null;

  const empty = ratedCount === 0 && summaryChars <= 10;
  const ups = diffs.filter((d) => d.from !== null && d.to > d.from).length;
  const downs = diffs.filter((d) => d.from !== null && d.to < d.from).length;
  const news = diffs.filter((d) => d.from === null).length;
  const unchanged = diffs.filter((d) => d.from !== null && d.to === d.from)
    .length;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('assessment.publishConfirm.title')}
      className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 sm:items-center"
    >
      <div className="flex w-full max-w-md flex-col rounded-t-2xl bg-bg-primary sm:rounded-2xl">
        <header className="flex items-center justify-between border-b-[0.5px] border-border-hairline px-4 py-3">
          <button
            type="button"
            onClick={onCancel}
            aria-label={t('common.cancel')}
            className="flex size-9 items-center justify-center rounded-full text-text-color-secondary"
          >
            <X size={18} strokeWidth={1.75} aria-hidden />
          </button>
          <span className="text-h3 text-text-color-primary">
            {t('assessment.publishConfirm.title')}
          </span>
          <span className="size-9" aria-hidden />
        </header>
        <div className="flex flex-col gap-3 p-4">
          <p className="text-body text-text-color-primary">
            {t('assessment.publishConfirm.summary', {
              count: ratedCount,
              chars: summaryChars,
            })}
          </p>

          {/* Score-change diff vs the trainee's previous published level.
              Helps coach catch a misclick before broadcasting to parents. */}
          {diffs.length > 0 ? (
            <div className="flex flex-col gap-2 rounded-lg border-[0.5px] border-border-hairline bg-bg-secondary p-3">
              <div className="flex flex-wrap gap-2 text-pill">
                {ups > 0 ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-success-bg px-2 py-0.5 text-success-text">
                    <ArrowUp size={10} strokeWidth={2} aria-hidden />
                    {t('assessment.publishConfirm.diff.ups', { count: ups })}
                  </span>
                ) : null}
                {news > 0 ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-accent-bg px-2 py-0.5 text-accent">
                    <Plus size={10} strokeWidth={2} aria-hidden />
                    {t('assessment.publishConfirm.diff.news', { count: news })}
                  </span>
                ) : null}
                {downs > 0 ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-warning-bg px-2 py-0.5 text-warning-text">
                    <ArrowDown size={10} strokeWidth={2} aria-hidden />
                    {t('assessment.publishConfirm.diff.downs', { count: downs })}
                  </span>
                ) : null}
                {unchanged > 0 ? (
                  <span className="inline-flex items-center gap-1 rounded-full border-[0.5px] border-border-hairline bg-bg-primary px-2 py-0.5 text-text-color-tertiary">
                    <Minus size={10} strokeWidth={2} aria-hidden />
                    {t('assessment.publishConfirm.diff.unchanged', {
                      count: unchanged,
                    })}
                  </span>
                ) : null}
              </div>
              {/* List up to the 5 most-significant changes (ups + downs +
                  news) so the coach can spot misclicks at a glance. */}
              <ul className="flex flex-col gap-0.5 text-caption text-text-color-secondary">
                {diffs
                  .filter(
                    (d) => d.from === null || d.to !== d.from,
                  )
                  .slice(0, 5)
                  .map((d, i) => (
                    <li key={i} className="flex items-center justify-between">
                      <span className="truncate">{d.skillName}</span>
                      <span className="shrink-0 tabular-nums">
                        {d.from ?? '—'} → {d.to}
                        {d.from !== null && d.to > d.from ? ' ↑' : ''}
                        {d.from !== null && d.to < d.from ? ' ↓' : ''}
                        {d.from === null ? ' ✦' : ''}
                      </span>
                    </li>
                  ))}
              </ul>
            </div>
          ) : null}

          <p className="text-footnote text-text-color-tertiary">
            {t('assessment.publishConfirm.notifyHint')}
          </p>
          {!online ? (
            <div className="rounded-md border-[0.5px] border-danger-text bg-danger-bg p-3">
              <p className="text-caption text-danger-text">
                {t('assessment.publishConfirm.offline')}
              </p>
            </div>
          ) : null}
          {empty ? (
            <label className="flex items-start gap-2 text-caption text-text-color-secondary">
              <input
                type="checkbox"
                checked={forceEmpty}
                onChange={(e) => setForceEmpty(e.target.checked)}
                className="mt-1"
              />
              <span>{t('assessment.publishConfirm.forceEmpty')}</span>
            </label>
          ) : null}
        </div>
        <footer className="flex flex-col gap-2 border-t-[0.5px] border-border-hairline px-4 py-3">
          <PrimaryButton
            type="button"
            onClick={() => onConfirm(forceEmpty)}
            loading={loading}
            disabled={!online || (empty && !forceEmpty)}
          >
            {t('assessment.publish')}
          </PrimaryButton>
          <SecondaryButton type="button" onClick={onCancel} disabled={loading}>
            {t('common.cancel')}
          </SecondaryButton>
        </footer>
      </div>
    </div>
  );
}
