// Bottom-sheet confirmation when admin disables a skill that has active
// assessments or appears in tier requirements.
//
// Always fetches impact when opened — counts can change since the curriculum
// screen was rendered.  If impact is zero AND not in tier requirements, the
// parent skips the sheet entirely and just toggles.

import { AlertTriangle } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';
import { useSkillImpact, type SkillRow } from './curriculum-api';

interface Props {
  skill: SkillRow;
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  pending?: boolean;
}

export function DisableSkillSheet({
  skill,
  open,
  onConfirm,
  onCancel,
  pending,
}: Props) {
  const { t } = useTranslation();
  const { data: impact, isPending } = useSkillImpact(skill.code, open);

  if (!open) return null;

  const trainees = impact?.trainee_count ?? 0;
  const inTier = impact?.in_tier_requirements ?? false;

  return (
    <div
      role="dialog"
      aria-modal="true"
      onClick={onCancel}
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex w-full max-w-md flex-col gap-3 rounded-t-2xl bg-bg-primary p-4 sm:rounded-2xl"
      >
        <h3 className="text-h3 text-text-color-primary">
          {t('settings.curriculum.disable.title', { skill: skill.name_en })}
        </h3>

        {isPending ? (
          <p className="text-body text-text-color-tertiary">
            {t('common.loading')}
          </p>
        ) : (
          <div className="flex flex-col gap-2 text-body text-text-color-secondary">
            <p>
              {trainees > 0
                ? t('settings.curriculum.disable.body', { count: trainees })
                : t('settings.curriculum.disable.bodyNone')}
            </p>
            <ul className="flex flex-col gap-1 pl-1">
              <li className="flex gap-2">
                <span aria-hidden>•</span>
                <span>{t('settings.curriculum.disable.effect1')}</span>
              </li>
              <li className="flex gap-2">
                <span aria-hidden>•</span>
                <span>{t('settings.curriculum.disable.effect2')}</span>
              </li>
              {inTier ? (
                <li className="flex gap-2 text-warning-text">
                  <AlertTriangle size={14} strokeWidth={1.75} aria-hidden />
                  <span>{t('settings.curriculum.disable.effect3')}</span>
                </li>
              ) : null}
            </ul>
          </div>
        )}

        <div className="mt-2 flex flex-col gap-2">
          <PrimaryButton
            onClick={onConfirm}
            loading={pending ?? false}
            className="bg-danger-text"
          >
            {t('settings.curriculum.disable.confirm')}
          </PrimaryButton>
          <SecondaryButton onClick={onCancel}>
            {t('common.cancel')}
          </SecondaryButton>
        </div>
      </div>
    </div>
  );
}
