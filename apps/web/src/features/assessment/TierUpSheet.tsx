// Celebration moment when publishing pushes a trainee to a higher tier.
// Auto-dismisses after the navigate delay; the share button opens the
// native share sheet (or copies the message text as a fallback).

import { PartyPopper, Share2, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';

interface Props {
  open: boolean;
  traineeFirstName: string;
  tierName: string;
  /** Public assessment link for parents / trainee — used by the share copy. */
  shareUrl?: string;
  onClose: () => void;
}

export function TierUpSheet({
  open,
  traineeFirstName,
  tierName,
  shareUrl,
  onClose,
}: Props) {
  const { t } = useTranslation();
  if (!open) return null;

  const shareText = t('assessment.tierUp.shareText', {
    name: traineeFirstName,
    tier: tierName,
  });

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: t('assessment.tierUp.shareTitle', { tier: tierName }),
          text: shareText,
          ...(shareUrl ? { url: shareUrl } : {}),
        });
      } catch {
        /* user cancelled */
      }
    } else if (navigator.clipboard) {
      try {
        await navigator.clipboard.writeText(
          shareUrl ? `${shareText} ${shareUrl}` : shareText,
        );
      } catch {
        /* clipboard unavailable */
      }
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('assessment.tierUp.title', { tier: tierName })}
      className="animate-overlay fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center"
    >
      <div className="animate-celebrate flex w-full max-w-md flex-col items-center rounded-t-2xl bg-bg-primary px-4 py-6 sm:rounded-2xl">
        <button
          type="button"
          onClick={onClose}
          aria-label={t('common.cancel')}
          className="absolute right-3 top-3 flex size-9 items-center justify-center rounded-full text-text-color-secondary"
        >
          <X size={18} strokeWidth={1.75} aria-hidden />
        </button>

        <div className="mb-4 flex size-16 items-center justify-center rounded-full bg-accent-bg text-accent">
          <PartyPopper size={32} strokeWidth={1.5} aria-hidden />
        </div>

        <h2
          className="mb-1 text-center font-display text-[26px] font-normal leading-tight text-text-color-primary"
          style={{ letterSpacing: '-0.3px' }}
        >
          {t('assessment.tierUp.title', { tier: tierName })}
        </h2>
        <p className="mb-5 max-w-[280px] text-center text-body text-text-color-secondary">
          {t('assessment.tierUp.body', {
            name: traineeFirstName,
            tier: tierName,
          })}
        </p>

        <div className="flex w-full flex-col gap-2">
          <PrimaryButton
            type="button"
            onClick={handleShare}
            leftIcon={<Share2 size={16} strokeWidth={1.75} aria-hidden />}
          >
            {t('assessment.tierUp.shareCta')}
          </PrimaryButton>
          <SecondaryButton type="button" onClick={onClose}>
            {t('assessment.tierUp.dismiss')}
          </SecondaryButton>
        </div>
      </div>
    </div>
  );
}
