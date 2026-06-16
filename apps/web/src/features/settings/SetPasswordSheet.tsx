import { X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';
import { TextInput } from '@/components/TextInput';
import { setPassword } from '@/features/auth/auth-api';
import { ApiError } from '@/lib/api';

interface Props {
  open: boolean;
  /** True when the user already has a password set — server then requires
   *  the current one for the change to go through.  We mirror that here so
   *  the UX matches and the request shape is right. */
  hasExistingPassword: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function SetPasswordSheet({
  open,
  hasExistingPassword,
  onClose,
  onSuccess,
}: Props) {
  const { t } = useTranslation();
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (newPw.length < 8) {
      setError(t('setPassword.minLengthError'));
      return;
    }
    if (newPw !== confirmPw) {
      setError(t('setPassword.mismatchError'));
      return;
    }
    setLoading(true);
    try {
      await setPassword({
        currentPassword: hasExistingPassword ? currentPw : null,
        newPassword: newPw,
      });
      onSuccess();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('setPassword.genericError'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('setPassword.title')}
      className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 sm:items-center"
    >
      <form
        onSubmit={handleSubmit}
        className="flex w-full max-w-md flex-col rounded-t-2xl bg-bg-primary sm:rounded-2xl"
      >
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
            {hasExistingPassword
              ? t('setPassword.titleChange')
              : t('setPassword.title')}
          </span>
          <span className="size-9" aria-hidden />
        </header>

        <div className="flex flex-col gap-3 p-4">
          {hasExistingPassword ? (
            <TextInput
              type="password"
              label={t('setPassword.currentPasswordLabel')}
              autoComplete="current-password"
              value={currentPw}
              onChange={(e) => setCurrentPw(e.target.value)}
              required
            />
          ) : null}
          <TextInput
            type="password"
            label={t('setPassword.newPasswordLabel')}
            autoComplete="new-password"
            value={newPw}
            onChange={(e) => setNewPw(e.target.value)}
            required
            minLength={8}
          />
          <TextInput
            type="password"
            label={t('setPassword.confirmPasswordLabel')}
            autoComplete="new-password"
            value={confirmPw}
            onChange={(e) => setConfirmPw(e.target.value)}
            required
          />
          <p className="text-footnote text-text-color-tertiary">
            {t('setPassword.hint')}
          </p>
          {error ? (
            <div className="rounded-md border-[0.5px] border-danger-text bg-danger-bg p-3">
              <p className="text-caption text-danger-text">{error}</p>
            </div>
          ) : null}
        </div>

        <footer className="flex flex-col gap-2 border-t-[0.5px] border-border-hairline px-4 py-3">
          <PrimaryButton type="submit" loading={loading}>
            {hasExistingPassword
              ? t('setPassword.updateCta')
              : t('setPassword.setCta')}
          </PrimaryButton>
          <SecondaryButton type="button" onClick={onClose}>
            {t('common.cancel')}
          </SecondaryButton>
        </footer>
      </form>
    </div>
  );
}
