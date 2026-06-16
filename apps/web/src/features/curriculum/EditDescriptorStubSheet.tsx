// Phase B stub.  The visible "Edit descriptor" affordance on SkillDetailScreen
// opens this sheet so admins discover the feature even before it ships in
// Phase B (real PATCH endpoint + form).  Keeps the curriculum screens
// shippable now while the descriptor-edit flow gets its own design pass.

import { useTranslation } from 'react-i18next';

import { PrimaryButton } from '@/components/PrimaryButton';

interface Props {
  level: number;
  skillName: string;
  open: boolean;
  onClose: () => void;
}

export function EditDescriptorStubSheet({ level, skillName, open, onClose }: Props) {
  const { t } = useTranslation();
  if (!open) return null;
  return (
    <div
      role="dialog"
      aria-modal="true"
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex w-full max-w-md flex-col gap-3 rounded-t-2xl bg-bg-primary p-4 sm:rounded-2xl"
      >
        <h3 className="text-h3 text-text-color-primary">
          {t('settings.curriculum.skill.editStubTitle', { skill: skillName, level })}
        </h3>
        <p className="text-body text-text-color-secondary">
          {t('settings.curriculum.skill.editSoon')}
        </p>
        <PrimaryButton onClick={onClose}>{t('common.done')}</PrimaryButton>
      </div>
    </div>
  );
}
