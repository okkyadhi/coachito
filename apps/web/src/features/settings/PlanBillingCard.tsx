import { format } from 'date-fns';
import { enUS, id as idLocale } from 'date-fns/locale';
import { ChevronRight, Sparkles, UserCircle2, Users } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import type { Plan, WorkspaceSettings } from './settings-api';

interface Props {
  settings: WorkspaceSettings;
  onManage?: () => void;
  onUpgrade?: () => void;
}

function planIcon(plan: Plan): typeof Sparkles {
  if (plan === 'club_pro') return Sparkles;
  if (plan === 'club_starter') return Users;
  return UserCircle2;
}

export function PlanBillingCard({ settings, onManage, onUpgrade }: Props) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language === 'id' ? idLocale : enUS;
  const Icon = planIcon(settings.plan);

  const renewsLabel = settings.renewsAt
    ? t('settings.plan.renews', {
        date: format(new Date(settings.renewsAt), 'd MMM', { locale }),
      })
    : t('settings.plan.trial');

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
            <p className="text-body text-text-color-primary">
              {t(`settings.plans.${settings.plan}`)}
            </p>
            <p className="text-footnote text-text-color-secondary">
              {t(`settings.plans.${settings.plan}_price`)} · {renewsLabel}
            </p>
          </div>
          <button
            type="button"
            onClick={onManage}
            className="text-caption font-medium text-accent"
          >
            {t('settings.plan.manage')}
          </button>
        </div>
      </div>

      {settings.type === 'personal' ? (
        <button
          type="button"
          onClick={onUpgrade}
          className="flex items-center gap-3 rounded-xl border-[0.5px] border-border-hairline p-4 text-left"
          style={{ background: 'var(--accent-bg)' }}
        >
          <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-bg-primary text-accent">
            <Sparkles size={18} strokeWidth={1.75} aria-hidden />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-body text-text-color-primary">
              {t('settings.upsell.title')}
            </p>
            <p className="mt-0.5 text-caption text-text-color-secondary">
              {t('settings.upsell.body')}
            </p>
          </div>
          <ChevronRight
            size={18}
            strokeWidth={1.75}
            className="text-accent"
            aria-hidden
          />
        </button>
      ) : null}
    </section>
  );
}
