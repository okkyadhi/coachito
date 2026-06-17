import { zodResolver } from '@hookform/resolvers/zod';
import { useQueryClient } from '@tanstack/react-query';
import { Link2, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Controller, useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';

import { GroupedTable } from '@/components/GroupedTable';
import { PhoneInput } from '@/components/PhoneInput';
import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';
import { TextInput } from '@/components/TextInput';
import { useAuthStore } from '@/features/auth/auth-store';
import { ApiError } from '@/lib/api';

import { traineeFormSchema, type TraineeFormInput } from './trainee-form';
import { createTrainee, type LinkedUser } from './trainees-api';
import { buildWhatsAppUrl, firstName } from './whatsapp';

type SubmitMode = 'invite' | 'save';

// Modal-route page (no bottom tab bar).  Coach taps "+" on /trainees → lands
// here.  "Send WhatsApp invite" mints the invite + opens wa.me; "Save without
// invite" just creates the trainee row.
export function AddTraineeScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();

  const locale = user?.preferredLocale === 'id' ? 'id' : 'en';

  const form = useForm<TraineeFormInput>({
    resolver: zodResolver(traineeFormSchema),
    mode: 'onBlur',
    defaultValues: {
      name: '',
      phone: locale === 'id' ? '+62 ' : '+',
      dateOfBirth: '',
      parentPhone: '',
    },
  });

  // When the phone matched an existing user, the create endpoint returns a
  // ``linked_user`` block — we surface it as a confirmation screen instead
  // of opening WhatsApp, since the trainee will see the invite in-app.
  const [linkedSuccess, setLinkedSuccess] = useState<LinkedUser | null>(null);

  const onSubmit = async (mode: SubmitMode, values: TraineeFormInput) => {
    const parsed = traineeFormSchema.parse(values);
    try {
      const result = await createTrainee({
        name: parsed.name,
        phone: parsed.phone,
        dateOfBirth: parsed.dateOfBirth || null,
        parentPhone: parsed.parentPhone || null,
      });

      // Refresh the trainees list so the new row appears on return
      void queryClient.invalidateQueries({ queryKey: ['trainees'] });

      if (result.linkedUser) {
        // Phone matched an existing account — show the confirmation state and
        // let the coach acknowledge before navigating away. No wa.me round-trip.
        setLinkedSuccess(result.linkedUser);
        return;
      }

      if (mode === 'invite') {
        // BE returns the canonical landing URL (workspace-aware host).
        const inviteLink = result.invite.landingUrl;
        const message = t('trainees.inviteMessage', {
          lng: locale,
          name: firstName(parsed.name),
          coach: (user?.displayName ?? '').replace(/^Coach\s+/i, '') || 'Coach',
          workspace: t('trainees.defaultWorkspaceName'),
          link: inviteLink,
        });
        const waUrl = buildWhatsAppUrl(parsed.phone, message);
        if (waUrl) {
          window.open(waUrl, '_blank', 'noopener,noreferrer');
        }
      }

      navigate('/trainees', { replace: true });
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : t('trainees.createError');
      form.setError('root', { message: detail });
    }
  };

  // We render two separate "submit" buttons; both run the same RHF validation
  // but with different submit modes.
  const handleInvite = form.handleSubmit((v) => onSubmit('invite', v));
  const handleSave = form.handleSubmit((v) => onSubmit('save', v));

  const isSubmitting = form.formState.isSubmitting;

  if (linkedSuccess) {
    const masked = (linkedSuccess.email ?? '').replace(/(.).+?(@.*)/, '$1•••$2');
    return (
      <main className="flex h-screen flex-col bg-bg-tertiary">
        <header className="flex items-center border-b-[0.5px] border-border-hairline bg-bg-primary p-2">
          <div className="size-10" />
          <h1 className="flex-1 text-center text-h3 text-text-color-primary">
            {t('trainees.linkedTitle')}
          </h1>
          <div className="size-10" />
        </header>
        <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
          <div className="bg-accent/10 flex size-16 items-center justify-center rounded-full text-accent">
            <Link2 size={28} strokeWidth={1.5} aria-hidden />
          </div>
          <h2 className="mt-4 text-large-title text-text-color-primary">
            {t('trainees.linkedHeadline', { name: linkedSuccess.displayName })}
          </h2>
          <p className="mt-2 max-w-xs text-body text-text-color-secondary">
            {t('trainees.linkedBody', { email: masked })}
          </p>
        </div>
        <div className="border-t-[0.5px] border-border-hairline bg-bg-primary px-4 py-3">
          <div className="mx-auto w-full max-w-md">
            <PrimaryButton
              type="button"
              onClick={() => navigate('/trainees', { replace: true })}
            >
              {t('common.done')}
            </PrimaryButton>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="flex h-screen flex-col bg-bg-tertiary">
      {/* Top bar */}
      <header className="flex items-center border-b-[0.5px] border-border-hairline bg-bg-primary p-2">
        <button
          type="button"
          onClick={() => navigate(-1)}
          aria-label={t('common.cancel')}
          className="flex size-10 items-center justify-center text-accent"
        >
          <X size={20} strokeWidth={2} aria-hidden />
        </button>
        <h1 className="flex-1 text-center text-h3 text-text-color-primary">
          {t('trainees.addTitle')}
        </h1>
        {/* Spacer to balance the X button */}
        <div className="size-10" />
      </header>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto">
        <form className="mx-auto flex w-full max-w-md flex-col gap-5 px-4 py-5">
          {/* Trainee details */}
          <GroupedTable header={t('trainees.detailsSection')}>
            <div className="px-4 py-3">
              <Controller
                control={form.control}
                name="name"
                render={({ field, fieldState }) => (
                  <TextInput
                    label={t('trainees.nameLabel')}
                    placeholder={t('trainees.namePlaceholder')}
                    autoComplete="name"
                    required
                    error={fieldState.error?.message ? t(fieldState.error.message) : undefined}
                    {...field}
                  />
                )}
              />
            </div>
            <div className="px-4 py-3">
              <Controller
                control={form.control}
                name="phone"
                render={({ field, fieldState }) => (
                  <PhoneInput
                    label={t('trainees.phoneLabel')}
                    placeholder={t('trainees.phonePlaceholder')}
                    required
                    error={fieldState.error?.message ? t(fieldState.error.message) : undefined}
                    {...field}
                  />
                )}
              />
            </div>
            <div className="px-4 py-3">
              <Controller
                control={form.control}
                name="dateOfBirth"
                render={({ field, fieldState }) => (
                  <TextInput
                    label={t('trainees.dobLabel')}
                    type="date"
                    error={fieldState.error?.message ? t(fieldState.error.message) : undefined}
                    {...field}
                  />
                )}
              />
            </div>
          </GroupedTable>

          {/* Parent / guardian */}
          <GroupedTable header={t('trainees.parentSection')}>
            <div className="px-4 py-3">
              <Controller
                control={form.control}
                name="parentPhone"
                render={({ field, fieldState }) => (
                  <PhoneInput
                    label={t('trainees.parentPhoneLabel')}
                    placeholder={t('trainees.phonePlaceholder')}
                    error={fieldState.error?.message ? t(fieldState.error.message) : undefined}
                    {...field}
                  />
                )}
              />
            </div>
          </GroupedTable>

          {/* Coaching (read-only at MVP; pickers ship later) */}
          <GroupedTable header={t('trainees.coachingSection')}>
            <div className="flex items-center justify-between px-4 py-3">
              <span className="text-caption text-text-color-secondary">
                {t('trainees.startingTierLabel')}
              </span>
              <span className="text-body text-text-color-primary">
                {t('tiers.BEGINNER')}
              </span>
            </div>
            <div className="flex items-center justify-between px-4 py-3">
              <span className="text-caption text-text-color-secondary">
                {t('trainees.leadCoachLabel')}
              </span>
              <span className="text-body text-text-color-primary">
                {user?.displayName ?? t('trainees.defaultCoachName')}
              </span>
            </div>
          </GroupedTable>

          {form.formState.errors.root ? (
            <div
              role="alert"
              className="rounded-md border-[0.5px] border-danger-text bg-danger-bg p-3"
            >
              <p className="text-caption text-danger-text">
                {form.formState.errors.root.message}
              </p>
            </div>
          ) : null}

          {/* Why these are required */}
          <p className="px-1 text-footnote text-text-color-tertiary">
            {t('trainees.fieldsHint')}
          </p>
        </form>
      </div>

      {/* Sticky action bar */}
      <div className="border-t-[0.5px] border-border-hairline bg-bg-primary px-4 py-3">
        <div className="mx-auto flex w-full max-w-md flex-col gap-2">
          <PrimaryButton
            type="button"
            onClick={() => {
              void handleInvite();
            }}
            loading={isSubmitting}
          >
            {t('trainees.sendWhatsAppInvite')}
          </PrimaryButton>
          <SecondaryButton
            type="button"
            onClick={() => {
              void handleSave();
            }}
            disabled={isSubmitting}
          >
            {t('trainees.saveWithoutInvite')}
          </SecondaryButton>
        </div>
      </div>
    </main>
  );
}
