import { useMutation } from '@tanstack/react-query';
import { Check, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { ApiError } from '@/lib/api';

import {
  isTrial,
  requestPlanUpgrade,
  type Plan,
  type UpgradeablePlan,
  type WorkspaceSettings,
} from './settings-api';

interface Props {
  open: boolean;
  onClose: () => void;
  settings: WorkspaceSettings;
}

interface PlanCardData {
  code: UpgradeablePlan;
  badge?: 'popular' | 'savings';
  featuresKey: string;
}

const PERSONAL_PLANS: PlanCardData[] = [
  { code: 'solo_coach', featuresKey: 'settings.picker.features.soloCoach' },
  {
    code: 'solo_coach_unlimited',
    badge: 'popular',
    featuresKey: 'settings.picker.features.soloCoachUnlimited',
  },
];

const CLUB_PLANS: PlanCardData[] = [
  { code: 'club_starter', featuresKey: 'settings.picker.features.clubStarter' },
  {
    // 'savings' badge intentionally omitted while pricing is hidden — it
    // showed a "Save Rp …/yr" amount.  Restore when prices go live.
    code: 'club_pro',
    featuresKey: 'settings.picker.features.clubPro',
  },
];

export function PlanPickerSheet({ open, onClose, settings }: Props) {
  const { t } = useTranslation();
  const [submittedPlan, setSubmittedPlan] = useState<Plan | null>(null);

  const mutation = useMutation({
    mutationFn: (plan: UpgradeablePlan) => requestPlanUpgrade(plan),
    onSuccess: (_data, plan) => {
      setSubmittedPlan(plan);
    },
  });

  const handleClose = () => {
    // Reset request state on close so reopening the sheet shows the
    // picker again, not a stale "request sent" banner.
    setSubmittedPlan(null);
    mutation.reset();
    onClose();
  };

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('settings.picker.title')}
      className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 sm:items-center"
      onClick={handleClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[90vh] w-full max-w-md flex-col rounded-t-2xl bg-bg-secondary sm:rounded-2xl"
      >
        <header className="flex items-center justify-between border-b-[0.5px] border-border-hairline bg-bg-primary px-4 py-3 sm:rounded-t-2xl">
          <button
            type="button"
            onClick={handleClose}
            aria-label={t('common.cancel')}
            className="flex size-9 items-center justify-center rounded-full text-text-color-secondary"
          >
            <X size={18} strokeWidth={1.75} aria-hidden />
          </button>
          <span className="text-h3 text-text-color-primary">
            {t('settings.picker.title')}
          </span>
          <span className="size-9" aria-hidden />
        </header>

        <div className="flex flex-col gap-5 overflow-y-auto p-4">
          {submittedPlan ? (
            <div className="rounded-xl border-[0.5px] border-success-text bg-success-bg p-4 text-center">
              <p className="text-body font-medium text-success-text">
                {t('settings.picker.requestSent', {
                  plan: t(`settings.plans.${submittedPlan}`),
                })}
              </p>
              <p className="mt-1 text-caption text-text-color-secondary">
                {t('settings.picker.requestSentBody')}
              </p>
            </div>
          ) : null}

          {mutation.error && !submittedPlan ? (
            <div className="rounded-xl border-[0.5px] border-danger-text bg-danger-bg p-3">
              <p className="text-caption text-danger-text">
                {mutation.error instanceof ApiError
                  ? mutation.error.message
                  : t('settings.picker.requestError')}
              </p>
            </div>
          ) : null}

          <PlanGroup
            title={t('settings.picker.subtitlePersonal')}
            plans={PERSONAL_PLANS}
            settings={settings}
            submittedPlan={submittedPlan}
            pending={mutation.isPending}
            onChoose={(p) => mutation.mutate(p)}
          />
          <PlanGroup
            title={t('settings.picker.subtitleClub')}
            plans={CLUB_PLANS}
            settings={settings}
            submittedPlan={submittedPlan}
            pending={mutation.isPending}
            onChoose={(p) => mutation.mutate(p)}
          />
          <p className="px-1 text-footnote text-text-color-tertiary">
            {t('settings.picker.footer')}
          </p>
        </div>
      </div>
    </div>
  );
}

interface PlanGroupProps {
  title: string;
  plans: PlanCardData[];
  settings: WorkspaceSettings;
  submittedPlan: Plan | null;
  pending: boolean;
  onChoose: (plan: UpgradeablePlan) => void;
}

function PlanGroup({
  title,
  plans,
  settings,
  submittedPlan,
  pending,
  onChoose,
}: PlanGroupProps) {
  return (
    <div className="flex flex-col gap-2">
      <h4 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {title}
      </h4>
      <div className="flex flex-col gap-3">
        {plans.map((p) => (
          <PlanCard
            key={p.code}
            data={p}
            settings={settings}
            submittedPlan={submittedPlan}
            pending={pending}
            onChoose={onChoose}
          />
        ))}
      </div>
    </div>
  );
}

interface PlanCardProps {
  data: PlanCardData;
  settings: WorkspaceSettings;
  submittedPlan: Plan | null;
  pending: boolean;
  onChoose: (plan: UpgradeablePlan) => void;
}

function PlanCard({
  data,
  settings,
  submittedPlan,
  pending,
  onChoose,
}: PlanCardProps) {
  const { t } = useTranslation();
  // While on trial, settings.plan is the *target* paid plan — don't mark it
  // as "current" or the upgrade button gets disabled and the trial user is
  // stuck.
  const isCurrent = !isTrial(settings) && settings.plan === data.code;
  const isSubmitted = submittedPlan === data.code;
  const planLabel = t(`settings.plans.${data.code}`);
  const price = t(`settings.plans.${data.code}_price`);
  // Feature keys are arrays in the locale JSON — i18next can resolve them
  // via { returnObjects: true }.
  const features = t(data.featuresKey, { returnObjects: true }) as string[];

  const borderClass = isCurrent
    ? 'border-accent'
    : isSubmitted
      ? 'border-success-text'
      : data.badge === 'savings'
        ? 'border-success-text'
        : 'border-border-hairline';

  const buttonDisabled = isCurrent || pending || submittedPlan !== null;
  const buttonLabel = isCurrent
    ? t('settings.picker.currentPlan')
    : isSubmitted
      ? t('settings.picker.requested')
      : pending
        ? t('settings.picker.sending')
        : t('settings.picker.choose');

  return (
    <div
      className={`overflow-hidden rounded-xl border-[0.5px] bg-bg-primary p-4 ${borderClass}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-h3 text-text-color-primary">{planLabel}</p>
            {isCurrent ? (
              <span className="rounded-full bg-accent-bg px-2 py-0.5 text-caption font-medium text-accent">
                {t('settings.picker.currentPlan')}
              </span>
            ) : data.badge === 'popular' ? (
              <span className="rounded-full bg-accent-bg px-2 py-0.5 text-caption font-medium text-accent">
                {t('settings.picker.mostPopular')}
              </span>
            ) : data.badge === 'savings' ? (
              <span className="rounded-full bg-success-bg px-2 py-0.5 text-caption font-medium text-success-text">
                {t('settings.picker.savingsBadge')}
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-body text-text-color-secondary">{price}</p>
        </div>
      </div>

      <ul className="mt-3 flex flex-col gap-1.5">
        {features.map((f) => (
          <li
            key={f}
            className="flex items-start gap-2 text-caption text-text-color-primary"
          >
            <Check
              size={14}
              strokeWidth={2}
              className="mt-0.5 shrink-0 text-accent"
              aria-hidden
            />
            <span>{f}</span>
          </li>
        ))}
      </ul>

      <button
        type="button"
        onClick={() => onChoose(data.code)}
        disabled={buttonDisabled}
        className={
          buttonDisabled
            ? 'mt-4 flex min-h-tap w-full items-center justify-center rounded-lg border-[0.5px] border-border-hairline text-body text-text-color-tertiary'
            : 'mt-4 flex min-h-tap w-full items-center justify-center rounded-lg bg-accent text-body font-medium text-white'
        }
      >
        {buttonLabel}
      </button>
    </div>
  );
}
