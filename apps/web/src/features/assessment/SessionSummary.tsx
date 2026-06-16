import { Eye, Loader2, Sparkles, Undo2 } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { ConfirmSheet } from '@/components/ConfirmSheet';

import { draftAssessmentSummary } from './assessment-api';

interface Props {
  value: string;
  onChange: (text: string) => void;
  /** Assessment must be saved at least once (have an id) and have ≥1 scored
   *  skill before the BE will accept a draft request.  Falsy → button hidden. */
  assessmentId: string | null;
  canDraft: boolean;
}

const UNDO_WINDOW_MS = 8_000;

export function SessionSummary({
  value,
  onChange,
  assessmentId,
  canDraft,
}: Props) {
  const { t } = useTranslation();
  const charCount = value.length;

  const [drafting, setDrafting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previous, setPrevious] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const undoTimer = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (undoTimer.current) window.clearTimeout(undoTimer.current);
    };
  }, []);

  const requestDraft = async () => {
    if (!assessmentId) return;
    setError(null);
    setDrafting(true);
    try {
      const r = await draftAssessmentSummary(assessmentId);
      setPrevious(value);
      onChange(r.draft);
      if (undoTimer.current) window.clearTimeout(undoTimer.current);
      undoTimer.current = window.setTimeout(
        () => setPrevious(null),
        UNDO_WINDOW_MS,
      );
    } catch (e) {
      const msg = e instanceof Error ? e.message : '';
      setError(
        msg.includes('configured')
          ? t('assessment.draft.notConfigured')
          : t('assessment.draft.failed'),
      );
    } finally {
      setDrafting(false);
    }
  };

  const handleClick = () => {
    if (!assessmentId || drafting) return;
    if (value.trim().length > 0) {
      setConfirmOpen(true);
      return;
    }
    void requestDraft();
  };

  const undo = () => {
    if (previous === null) return;
    onChange(previous);
    setPrevious(null);
    if (undoTimer.current) window.clearTimeout(undoTimer.current);
  };

  const buttonDisabled = !canDraft || !assessmentId || drafting;
  const titleHint = !canDraft
    ? t('assessment.draft.needsScores')
    : !assessmentId
      ? t('assessment.draft.saveFirst')
      : undefined;

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between px-1">
        <h2 className="text-section uppercase tracking-wide text-text-color-secondary">
          {t('assessment.summary.title')}
        </h2>
        <button
          type="button"
          onClick={handleClick}
          disabled={buttonDisabled}
          className={[
            'flex min-h-tap items-center gap-1 px-2 text-caption font-medium',
            buttonDisabled ? 'text-text-color-tertiary opacity-60' : 'text-accent',
          ].join(' ')}
          {...(titleHint ? { title: titleHint } : {})}
        >
          {drafting ? (
            <Loader2 size={14} strokeWidth={1.75} className="animate-spin" aria-hidden />
          ) : (
            <Sparkles size={14} strokeWidth={1.75} aria-hidden />
          )}
          <span>
            {drafting ? t('assessment.draft.loading') : t('assessment.draft.cta')}
          </span>
        </button>
      </div>

      <div className="flex flex-col gap-2 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-3">
        <textarea
          rows={5}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={t('assessment.summary.placeholder')}
          className="resize-y rounded-sm bg-bg-primary p-2 text-body text-text-color-primary placeholder:text-text-color-tertiary focus:outline-none"
        />
        <div className="flex items-center justify-between gap-2 px-1">
          <span className="flex items-center gap-1.5 text-footnote text-text-color-tertiary">
            <Eye size={12} strokeWidth={1.75} aria-hidden />
            {t('assessment.summary.visibility')}
          </span>
          <span className="text-footnote text-text-color-tertiary">{charCount}</span>
        </div>
      </div>

      {error ? (
        <p className="px-1 text-footnote text-danger-text">{error}</p>
      ) : null}

      {previous !== null ? (
        <div className="flex items-center justify-between rounded-md bg-success-bg px-3 py-1.5">
          <span className="inline-flex items-center gap-1.5 text-caption text-success-text">
            <Sparkles size={12} strokeWidth={2} aria-hidden />
            {t('assessment.draft.successPill')}
          </span>
          <button
            type="button"
            onClick={undo}
            className="inline-flex min-h-tap items-center gap-1 text-caption font-medium text-success-text"
          >
            <Undo2 size={12} strokeWidth={2} aria-hidden />
            {t('assessment.draft.undo')}
          </button>
        </div>
      ) : null}

      <ConfirmSheet
        open={confirmOpen}
        title={t('assessment.draft.confirmReplaceTitle')}
        description={t('assessment.draft.confirmReplaceBody')}
        confirmLabel={t('assessment.draft.confirmReplaceConfirm')}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={() => {
          setConfirmOpen(false);
          void requestDraft();
        }}
      />
    </section>
  );
}
