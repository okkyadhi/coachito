import { useTranslation } from 'react-i18next';

import { PrimaryButton } from './PrimaryButton';
import { SecondaryButton } from './SecondaryButton';

interface Props {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel: string;
  destructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmSheet({
  open,
  title,
  description,
  confirmLabel,
  destructive,
  onConfirm,
  onCancel,
}: Props) {
  const { t } = useTranslation();
  if (!open) return null;
  return (
    <div
      role="dialog"
      aria-modal="true"
      onClick={onCancel}
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex w-full max-w-md flex-col gap-3 rounded-t-2xl bg-bg-primary p-4 sm:rounded-2xl"
      >
        <h3 className="text-h3 text-text-color-primary">{title}</h3>
        {description ? (
          <p className="text-body text-text-color-secondary">{description}</p>
        ) : null}
        <div className="mt-2 flex flex-col gap-2">
          <PrimaryButton
            type="button"
            onClick={onConfirm}
            className={destructive ? 'bg-danger-text' : ''}
          >
            {confirmLabel}
          </PrimaryButton>
          <SecondaryButton type="button" onClick={onCancel}>
            {t('common.cancel')}
          </SecondaryButton>
        </div>
      </div>
    </div>
  );
}
