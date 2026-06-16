import { Copy, Share2, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';
import { TextInput } from '@/components/TextInput';
import { ApiError } from '@/lib/api';

import { type CoachRole, type InviteCoachResult, inviteCoach } from './members-api';

interface Props {
  open: boolean;
  onClose: () => void;
  onInvited: (result: InviteCoachResult) => void;
}

export function InviteCoachSheet({ open, onClose, onInvited }: Props) {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [role, setRole] = useState<CoachRole>('coach');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<InviteCoachResult | null>(null);
  const [copied, setCopied] = useState(false);

  if (!open) return null;

  const reset = () => {
    setEmail('');
    setDisplayName('');
    setRole('coach');
    setError(null);
    setResult(null);
    setCopied(false);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const r = await inviteCoach({
        email: email.trim(),
        displayName: displayName.trim(),
        role,
      });
      setResult(r);
      onInvited(r);
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : t('coaches.invite.genericError'),
      );
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.landingUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard might be unavailable — user can long-press the link */
    }
  };

  const handleShare = async () => {
    if (!result) return;
    if (navigator.share) {
      try {
        await navigator.share({
          title: t('coaches.invite.shareTitle'),
          text: t('coaches.invite.shareBody', { name: displayName || '—' }),
          url: result.landingUrl,
        });
      } catch {
        /* user cancelled — ignore */
      }
    } else {
      void handleCopy();
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('coaches.invite.title')}
      className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 sm:items-center"
    >
      <form
        onSubmit={handleSubmit}
        className="flex w-full max-w-md flex-col rounded-t-2xl bg-bg-primary sm:rounded-2xl"
      >
        <header className="flex items-center justify-between border-b-[0.5px] border-border-hairline px-4 py-3">
          <button
            type="button"
            onClick={handleClose}
            aria-label={t('common.cancel')}
            className="flex size-9 items-center justify-center rounded-full text-text-color-secondary"
          >
            <X size={18} strokeWidth={1.75} aria-hidden />
          </button>
          <span className="text-h3 text-text-color-primary">
            {result ? t('coaches.invite.successTitle') : t('coaches.invite.title')}
          </span>
          <span className="size-9" aria-hidden />
        </header>

        {!result ? (
          <>
            <div className="flex flex-col gap-3 p-4">
              <TextInput
                label={t('coaches.invite.nameLabel')}
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
                autoFocus
              />
              <TextInput
                type="email"
                label={t('coaches.invite.emailLabel')}
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <div className="flex flex-col gap-1">
                <span className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
                  {t('coaches.invite.roleLabel')}
                </span>
                <div className="flex gap-2">
                  <RoleChip
                    selected={role === 'coach'}
                    onClick={() => setRole('coach')}
                    label={t('coaches.role.coach')}
                  />
                  <RoleChip
                    selected={role === 'head_coach'}
                    onClick={() => setRole('head_coach')}
                    label={t('coaches.role.head_coach')}
                  />
                </div>
                <p className="px-1 text-footnote text-text-color-tertiary">
                  {role === 'head_coach'
                    ? t('coaches.invite.headHint')
                    : t('coaches.invite.coachHint')}
                </p>
              </div>
              {error ? (
                <div className="rounded-md border-[0.5px] border-danger-text bg-danger-bg p-3">
                  <p className="text-caption text-danger-text">{error}</p>
                </div>
              ) : null}
            </div>
            <footer className="flex flex-col gap-2 border-t-[0.5px] border-border-hairline px-4 py-3">
              <PrimaryButton type="submit" loading={loading}>
                {t('coaches.invite.submitCta')}
              </PrimaryButton>
              <SecondaryButton type="button" onClick={handleClose}>
                {t('common.cancel')}
              </SecondaryButton>
            </footer>
          </>
        ) : (
          <>
            <div className="flex flex-col gap-3 p-4">
              <p className="text-body text-text-color-primary">
                {t('coaches.invite.successBody', { email: result.email })}
              </p>
              <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-secondary p-3">
                <p className="text-footnote text-text-color-tertiary">
                  {t('coaches.invite.linkLabel')}
                </p>
                <p className="mt-1 break-all text-caption text-text-color-primary">
                  {result.landingUrl}
                </p>
              </div>
              <p className="text-footnote text-text-color-tertiary">
                {t('coaches.invite.successHint')}
              </p>
            </div>
            <footer className="flex flex-col gap-2 border-t-[0.5px] border-border-hairline px-4 py-3">
              <PrimaryButton
                type="button"
                onClick={handleShare}
                leftIcon={<Share2 size={16} strokeWidth={1.75} aria-hidden />}
              >
                {t('coaches.invite.shareCta')}
              </PrimaryButton>
              <SecondaryButton
                type="button"
                onClick={handleCopy}
                leftIcon={<Copy size={16} strokeWidth={1.75} aria-hidden />}
              >
                {copied ? t('coaches.invite.copied') : t('coaches.invite.copyCta')}
              </SecondaryButton>
              <button
                type="button"
                onClick={handleClose}
                className="py-2 text-center text-body text-text-color-secondary"
              >
                {t('common.done')}
              </button>
            </footer>
          </>
        )}
      </form>
    </div>
  );
}

interface RoleChipProps {
  selected: boolean;
  onClick: () => void;
  label: string;
}

function RoleChip({ selected, onClick, label }: RoleChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        selected
          ? 'bg-accent/10 flex-1 rounded-lg border-[0.5px] border-accent px-3 py-2 text-body text-accent'
          : 'flex-1 rounded-lg border-[0.5px] border-border-hairline bg-bg-primary px-3 py-2 text-body text-text-color-secondary'
      }
    >
      {label}
    </button>
  );
}
