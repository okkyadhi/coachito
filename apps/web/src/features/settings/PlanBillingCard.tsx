import { format } from 'date-fns';
import { enUS, id as idLocale } from 'date-fns/locale';
import { Sparkles, UserCircle2, Users } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import {
  type Plan,
  type WorkspaceSettings,
  isTrial,
  trialDaysLeft,
} from './settings-api';

interface Props {
  settings: WorkspaceSettings;
  onManage?: () => void;
}

function planIcon(plan: Plan): typeof Sparkles {
  if (plan === 'club_pro' || plan === 'club_starter') return Users;
  if (plan === 'solo_coach_unlimited') return Sparkles;
  return UserCircle2;
}

const TRIAL_WARN_THRESHOLD_DAYS = 7;

export function PlanBillingCard({ settings, onManage }: Props) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language === 'id' ? idLocale : enUS;
  const Icon = planIcon(settings.plan);
  const trial = isTrial(settings);
  const daysLeft = trial ? trialDaysLeft(settings.renewsAt) : null;
  const endingSoon = daysLeft !== null && daysLeft <= TRIAL_WARN_THRESHOLD_DAYS;

  const subline = trial
    ? settings.renewsAt && daysLeft !== null
      ? t('settings.plan.daysLeft', {
          days: Math.max(daysLeft, 0),
          date: format(new Date(settings.renewsAt), 'd MMM', { locale }),
        })
      : t('settings.plans.free_trial_price')
    : `${t(`settings.plans.${settings.plan}_price`)} · ${t('settings.plan.activeStatus')}`;

  return (
    <section className="flex flex-col gap-2">
      <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {t('settings.plan.title')}
      </h3>
      <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
        <div className="flex items-center gap-3 p-3">
          <div
            aria-hidden
            className="flex size-10 items-center justify-center rounded-md bg-accent-bg text-accent"
          >
            <Icon size={20} strokeWidth={1.75} aria-hidden />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="text-body text-text-color-primary">
                {t(`settings.plans.${settings.plan}`)}
              </p>
              {trial ? (
                <span
                  className={
                    endingSoon
                      ? 'rounded-full bg-warning-bg px-2 py-0.5 text-caption font-medium text-warning-text'
                      : 'rounded-full bg-accent-bg px-2 py-0.5 text-caption font-medium text-accent'
                  }
                >
                  {t('settings.plan.trialBadge')}
                </span>
              ) : null}
            </div>
            <p className="text-footnote text-text-color-secondary">{subline}</p>
            {trial && endingSoon ? (
              <p className="mt-0.5 text-caption text-warning-text">
                {t('settings.plan.trialEndingSoon')}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onManage}
            className="text-caption font-medium text-accent"
          >
            {t('settings.plan.viewPlans')}
          </button>
        </div>
      </div>
    </section>
  );
}
