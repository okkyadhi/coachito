import { AlertTriangle, Check, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'failed';

interface Props {
  status: SaveStatus;
  /** Auto-fade the "saved" indicator after this many ms.  Default 5s per the
   *  offline/sync rules in docs/10. */
  fadeMs?: number;
  onRetry?: () => void;
}

// Compact auto-save indicator placed in the nav bar.  Calm by default —
// fades after a short interval so it doesn't linger and shout success.
export function InlineSavedToast({ status, fadeMs = 5000, onRetry }: Props) {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(status !== 'idle');

  useEffect(() => {
    if (status === 'idle') {
      setVisible(false);
      return;
    }
    setVisible(true);
    if (status !== 'saved') return;
    const timeout = window.setTimeout(() => setVisible(false), fadeMs);
    return () => window.clearTimeout(timeout);
  }, [status, fadeMs]);

  if (!visible) return null;

  if (status === 'saving') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-bg-secondary px-2 py-0.5 text-pill text-text-color-secondary">
        <Loader2 size={12} strokeWidth={2} className="animate-spin" aria-hidden />
        {t('settings.savePill.saving')}
      </span>
    );
  }

  if (status === 'failed') {
    return (
      <button
        type="button"
        onClick={onRetry}
        className="inline-flex items-center gap-1 rounded-full bg-danger-bg px-2 py-0.5 text-pill text-danger-text"
      >
        <AlertTriangle size={12} strokeWidth={2} aria-hidden />
        {t('settings.savePill.failed')}
      </button>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-success-bg px-2 py-0.5 text-pill text-success-text transition-opacity duration-300">
      <Check size={12} strokeWidth={2.5} aria-hidden />
      {t('settings.savePill.saved')}
    </span>
  );
}
