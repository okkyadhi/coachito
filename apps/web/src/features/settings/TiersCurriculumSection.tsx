import { ChevronRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { Switch } from '@/components/Switch';

import type { WorkspaceSettings } from './settings-api';

interface Props {
  settings: WorkspaceSettings;
  draft: Partial<WorkspaceSettings>;
  onChange: (patch: Partial<WorkspaceSettings>) => void;
}

export function TiersCurriculumSection({ settings, draft, onChange }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const allowOverrides =
    draft.allowCoachOverrides ?? settings.allowCoachOverrides;

  return (
    <section className="flex flex-col gap-2">
      <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {t('settings.tiers.title')}
      </h3>
      <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
        {/* Curriculum nav — opens the full editing screen */}
        <button
          type="button"
          className="flex min-h-tap w-full items-center gap-3 border-t-[0.5px] border-border-hairline p-3 text-left"
          onClick={() => navigate('/settings/curriculum')}
        >
          <span className="flex-1 text-body text-text-color-primary">
            {t('settings.curriculum.title')}
          </span>
          <ChevronRight
            size={16}
            strokeWidth={1.75}
            className="text-text-color-tertiary"
            aria-hidden
          />
        </button>

        {/* Tiers nav — naming + renaming live here */}
        <button
          type="button"
          className="flex min-h-tap w-full items-center gap-3 border-t-[0.5px] border-border-hairline p-3 text-left"
          onClick={() => navigate('/settings/tiers')}
        >
          <span className="flex-1 text-body text-text-color-primary">
            {t('settings.tiers.list')}
          </span>
          <ChevronRight
            size={16}
            strokeWidth={1.75}
            className="text-text-color-tertiary"
            aria-hidden
          />
        </button>

        {/* Allow coach overrides */}
        <label className="flex min-h-tap cursor-pointer items-center gap-3 border-t-[0.5px] border-border-hairline p-3">
          <span className="flex-1 text-body text-text-color-secondary">
            {t('settings.tiers.allowOverrides')}
          </span>
          <Switch
            checked={allowOverrides}
            onChange={(v) => onChange({ allowCoachOverrides: v })}
          />
        </label>
      </div>
    </section>
  );
}
