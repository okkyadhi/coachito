import { CloudOff } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { useOnlineStatus } from '@/lib/use-online-status';

// Pattern 1 from docs/10-error-offline-states.md: amber banner, calm tone,
// persists until reconnected.  Mounted globally in CoachShell so it appears
// on every authenticated screen.
export function OfflineBanner() {
  const { t } = useTranslation();
  const online = useOnlineStatus();
  if (online) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="mx-3 mt-2 flex items-start gap-2 rounded-md border-[0.5px] border-warning-text bg-warning-bg px-3 py-2"
    >
      <CloudOff
        aria-hidden
        size={16}
        strokeWidth={1.75}
        className="mt-0.5 shrink-0 text-warning-text"
      />
      <div className="flex flex-col">
        <span className="text-[13px] font-medium text-warning-text">{t('offline.title')}</span>
        <span className="text-warning-text/85 text-footnote">{t('offline.body')}</span>
      </div>
    </div>
  );
}
