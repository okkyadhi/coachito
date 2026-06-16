import { Construction } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface ComingSoonProps {
  /** i18n key for the screen title (e.g. 'nav.trainees'). */
  titleKey: string;
}

export function ComingSoon({ titleKey }: ComingSoonProps) {
  const { t } = useTranslation();
  return (
    <div className="mx-auto flex w-full max-w-md flex-col items-center gap-3 px-6 pb-6 pt-20 text-center">
      <div className="flex size-[60px] items-center justify-center rounded-full border-[0.5px] border-border-hairline bg-bg-secondary">
        <Construction aria-hidden size={26} strokeWidth={1.5} className="text-text-color-tertiary" />
      </div>
      <h1 className="mt-2 text-h2 text-text-color-primary">{t(titleKey)}</h1>
      <p className="max-w-[260px] text-caption text-text-color-secondary">
        {t('comingSoon.body')}
      </p>
    </div>
  );
}
