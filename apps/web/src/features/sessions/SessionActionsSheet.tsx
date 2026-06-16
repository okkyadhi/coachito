import { CheckCircle2, FileEdit, UserX, XCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { useAuthStore } from '@/features/auth/auth-store';

import type { Session } from './sessions-api';

interface Props {
  session: Session;
  onClose: () => void;
  onEdit: () => void;
  onComplete: () => void;
  onNoShow: () => void;
  onCancel: () => void;
}

export function SessionActionsSheet({
  session,
  onClose,
  onEdit,
  onComplete,
  onNoShow,
  onCancel,
}: Props) {
  const { t } = useTranslation();
  const currentUserId = useAuthStore((s) => s.user?.id ?? null);
  // BE-mirrored: only the assigned coach can mutate the session.  Other
  // coaches see view-only on the row + no actions here.
  const isAssignedCoach = session.coach.id === currentUserId;
  const canMark = isAssignedCoach && session.status === 'scheduled';
  const canCancel = isAssignedCoach && session.status === 'scheduled';
  const canEdit = isAssignedCoach;
  return (
    <div
      role="dialog"
      aria-modal="true"
      onClick={onClose}
      className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 sm:items-center"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex w-full max-w-md flex-col gap-1 rounded-t-2xl bg-bg-primary p-2 sm:rounded-2xl"
      >
        <div className="px-3 py-2">
          <p className="text-body text-text-color-primary">
            {session.athlete.displayName}
          </p>
          <p className="text-footnote text-text-color-tertiary">
            {new Date(session.scheduledAt).toLocaleString()}
          </p>
        </div>
        {canEdit ? (
          <button
            type="button"
            onClick={onEdit}
            className="flex min-h-tap items-center gap-3 rounded-md px-3 py-2 text-left text-body text-text-color-primary hover:bg-bg-secondary"
          >
            <FileEdit size={16} strokeWidth={1.75} aria-hidden />
            {t('common.edit')}
          </button>
        ) : null}
        {!isAssignedCoach ? (
          <p className="px-3 py-1 text-footnote text-text-color-tertiary">
            {t('sessions.menu.notAssignedHint', {
              coach: session.coach.displayName,
            })}
          </p>
        ) : null}
        {canMark ? (
          <>
            <button
              type="button"
              onClick={onComplete}
              className="flex min-h-tap items-center gap-3 rounded-md px-3 py-2 text-left text-body text-text-color-primary hover:bg-bg-secondary"
            >
              <CheckCircle2 size={16} strokeWidth={1.75} aria-hidden />
              {t('sessions.complete.cta')}
            </button>
            <button
              type="button"
              onClick={onNoShow}
              className="flex min-h-tap items-center gap-3 rounded-md px-3 py-2 text-left text-body text-text-color-primary hover:bg-bg-secondary"
            >
              <UserX size={16} strokeWidth={1.75} aria-hidden />
              {t('sessions.noShow.cta')}
            </button>
          </>
        ) : null}
        {canCancel ? (
          <button
            type="button"
            onClick={onCancel}
            className="flex min-h-tap items-center gap-3 rounded-md px-3 py-2 text-left text-body text-danger-text hover:bg-danger-bg"
          >
            <XCircle size={16} strokeWidth={1.75} aria-hidden />
            {t('sessions.cancel.cta')}
          </button>
        ) : null}
        <button
          type="button"
          onClick={onClose}
          className="mt-1 min-h-tap rounded-md py-2 text-center text-body text-text-color-secondary"
        >
          {t('common.cancel')}
        </button>
      </div>
    </div>
  );
}
