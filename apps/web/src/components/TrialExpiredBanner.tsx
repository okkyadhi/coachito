import { useQuery } from '@tanstack/react-query';
import { AlertTriangle } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { PlanPickerSheet } from '@/features/settings/PlanPickerSheet';
import { getMyWorkspace, isTrialLapsed } from '@/features/settings/settings-api';

export function TrialExpiredBanner() {
  const { t } = useTranslation();
  const [sheetOpen, setSheetOpen] = useState(false);

  const { data: settings } = useQuery({
    queryKey: ['workspace-settings'],
    queryFn: getMyWorkspace,
    staleTime: 5 * 60_000,
  });

  if (!settings || !isTrialLapsed(settings)) return null;

  return (
    <>
      <div
        role="status"
        aria-live="polite"
        className="mx-3 mt-2 flex items-center gap-2 rounded-md border-[0.5px] border-warning-text bg-warning-bg px-3 py-2"
      >
        <AlertTriangle
          aria-hidden
          size={16}
          strokeWidth={1.75}
          className="shrink-0 text-warning-text"
        />
        <div className="min-w-0 flex-1">
          <span className="text-[13px] font-medium text-warning-text">
            {t('trial.expiredTitle')}
          </span>
          <span className="text-warning-text/85 ml-1 text-footnote">
            {t('trial.expiredBody')}
          </span>
        </div>
        <button
          type="button"
          onClick={() => setSheetOpen(true)}
          className="shrink-0 text-[13px] font-medium text-warning-text underline underline-offset-2"
        >
          {t('trial.seePlans')}
        </button>
      </div>

      <PlanPickerSheet
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        settings={settings}
      />
    </>
  );
}
