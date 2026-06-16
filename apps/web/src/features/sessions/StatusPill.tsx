import { Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';

/** Inputs the pill needs.  Accepts either a full Session object or a thin
 *  subset, so we can use it from both the Sessions screen and the
 *  trainee-profile Recent Sessions list (which doesn't carry status fields). */
export interface PillSource {
  status?: string;
  assessmentStatus?: 'none' | 'draft' | 'published' | 'edited' | null;
  scheduledAt?: string;
}

export function StatusPill({ session }: { session: PillSource }) {
  const { t } = useTranslation();
  const astat = session.assessmentStatus;

  if (astat === 'published' || astat === 'edited') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-success-bg px-2 py-0.5 text-pill text-success-text">
        <Check size={10} strokeWidth={2} aria-hidden />
        {t('sessions.status.published')}
      </span>
    );
  }
  if (astat === 'draft') {
    return (
      <span className="border-accent/40 bg-accent/5 rounded-full border-[0.5px] px-2 py-0.5 text-pill text-accent">
        {t('sessions.status.draft')}
      </span>
    );
  }
  if (session.status === 'cancelled' || session.status === 'no_show') {
    return (
      <span className="rounded-full bg-bg-secondary px-2 py-0.5 text-pill text-text-color-tertiary">
        {t(
          session.status === 'no_show'
            ? 'sessions.status.noShow'
            : 'sessions.status.cancelled',
        )}
      </span>
    );
  }
  // Past-and-unassessed → "To assess"
  if (
    session.scheduledAt &&
    new Date(session.scheduledAt) < new Date() &&
    session.status !== 'completed' &&
    (astat == null || astat === 'none')
  ) {
    return (
      <span className="rounded-full bg-accent px-2 py-0.5 text-pill text-white">
        {t('sessions.status.toAssess')}
      </span>
    );
  }
  if (session.status === 'completed') {
    return (
      <span className="rounded-full bg-bg-secondary px-2 py-0.5 text-pill text-text-color-tertiary">
        {t('sessions.status.completed')}
      </span>
    );
  }
  return (
    <span className="rounded-full border-[0.5px] border-border-hairline px-2 py-0.5 text-pill text-text-color-tertiary">
      {t('sessions.status.scheduled')}
    </span>
  );
}
