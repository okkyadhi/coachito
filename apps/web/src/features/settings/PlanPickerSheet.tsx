import { Check, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { openUpgradeChat } from '@/lib/wa-support';

import type { Plan, WorkspaceSettings } from './settings-api';

interface Props {
  open: boolean;
  onClose: () => void;
  settings: WorkspaceSettings;
}

interface PlanCardData {
  code: Plan;
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
    code: 'club_pro',
    badge: 'savings',
    featuresKey: 'settings.picker.features.clubPro',
  },
];

export function PlanPickerSheet({ open, onClose, settings }: Props) {
  const { t } = useTranslation();

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('settings.picker.title')}
      className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 sm:items-center"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[90vh] w-full max-w-md flex-col rounded-t-2xl bg-bg-secondary sm:rounded-2xl"
      >
        <header className="flex items-center justify-between border-b-[0.5px] border-border-hairline bg-bg-primary px-4 py-3 sm:rounded-t-2xl">
          <button
            type="button"
            onClick={onClose}
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
          <PlanGroup
            title={t('settings.picker.subtitlePersonal')}
            plans={PERSONAL_PLANS}
            settings={settings}
          />
          <PlanGroup
            title={t('settings.picker.subtitleClub')}
            plans={CLUB_PLANS}
            settings={settings}
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
}

function PlanGroup({ title, plans, settings }: PlanGroupProps) {
  return (
    <div className="flex flex-col gap-2">
      <h4 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {title}
      </h4>
      <div className="flex flex-col gap-3">
        {plans.map((p) => (
          <PlanCard key={p.code} data={p} settings={settings} />
        ))}
      </div>
    </div>
  );
}

interface PlanCardProps {
  data: PlanCardData;
  settings: WorkspaceSettings;
}

function PlanCard({ data, settings }: PlanCardProps) {
  const { t } = useTranslation();
  const isCurrent = settings.plan === data.code;
  const planLabel = t(`settings.plans.${data.code}`);
  const price = t(`settings.plans.${data.code}_price`);
  // Feature keys are arrays in the locale JSON — i18next can resolve them
  // via { returnObjects: true }.
  const features = t(data.featuresKey, { returnObjects: true }) as string[];

  const handleChoose = () => {
    openUpgradeChat(settings.name, planLabel);
  };

  const borderClass = isCurrent
    ? 'border-accent'
    : data.badge === 'savings'
      ? 'border-success-text'
      : 'border-border-hairline';

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
        onClick={handleChoose}
        disabled={isCurrent}
        className={
          isCurrent
            ? 'mt-4 flex min-h-tap w-full items-center justify-center rounded-lg border-[0.5px] border-border-hairline text-body text-text-color-tertiary'
            : 'mt-4 flex min-h-tap w-full items-center justify-center rounded-lg bg-accent text-body font-medium text-white'
        }
      >
        {isCurrent ? t('settings.picker.currentPlan') : t('settings.picker.choose')}
      </button>
    </div>
  );
}
