import { LogOut } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface Props {
  onSignOut: () => void;
}

export function DangerSection({ onSignOut }: Props) {
  const { t } = useTranslation();
  return (
    <section className="flex flex-col gap-2">
      <div className="px-1">
        <h2 className="text-section uppercase tracking-wide text-text-color-secondary">
          {t('me.danger.title')}
        </h2>
      </div>
      <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
        <button
          type="button"
          onClick={onSignOut}
          className="flex w-full items-center gap-3 p-4 text-left text-body text-accent"
        >
          <LogOut size={18} strokeWidth={1.75} aria-hidden />
          {t('common.signOut')}
        </button>
        <p className="border-t-[0.5px] border-border-hairline p-4 text-footnote text-text-color-tertiary">
          {t('me.danger.deleteHint')}
        </p>
      </div>
    </section>
  );
}
