// Tiny "Updated" pill shown next to a skill name when the admin has
// changed it (toggled or — once Phase B lands — edited a descriptor)
// within the last 7 days.  The BE only returns last_changed_at within
// that window, so any non-null value means "recent" — no client-side
// freshness check needed.

import { useTranslation } from 'react-i18next';

export function UpdatedBadge() {
  const { t } = useTranslation();
  return (
    <span className="shrink-0 rounded-full bg-info-bg px-1.5 py-0.5 text-[10px] font-medium text-info-text">
      {t('settings.curriculum.updatedBadge')}
    </span>
  );
}
