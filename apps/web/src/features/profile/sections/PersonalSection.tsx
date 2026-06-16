import { ChevronRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface Props {
  dateOfBirth: string | null;
  isMinor: boolean;
  guardianName: string | null;
}

export function PersonalSection({ dateOfBirth, isMinor, guardianName }: Props) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'id' ? 'id' : 'en';
  const dobLabel = dateOfBirth
    ? new Date(dateOfBirth).toLocaleDateString(lang, {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      })
    : '—';

  return (
    <section className="flex flex-col gap-2">
      <div className="px-1">
        <h2 className="text-section uppercase tracking-wide text-text-color-secondary">
          {t('me.personal.title')}
        </h2>
      </div>
      <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
        <div className="flex items-center justify-between p-4">
          <span className="text-body text-text-color-secondary">
            {t('me.personal.dob')}
          </span>
          <span className="text-body text-text-color-primary">{dobLabel}</span>
        </div>
        {isMinor ? (
          <div className="flex items-center justify-between border-t-[0.5px] border-border-hairline p-4">
            <span className="text-body text-text-color-secondary">
              {t('me.personal.parent')}
            </span>
            <span className="flex items-center gap-1 text-body text-text-color-primary">
              {guardianName ?? t('me.personal.parentMissing')}
              <ChevronRight
                size={16}
                strokeWidth={1.75}
                className="text-text-color-tertiary"
                aria-hidden
              />
            </span>
          </div>
        ) : null}
        <p className="border-t-[0.5px] border-border-hairline p-4 text-footnote text-text-color-tertiary">
          {t('me.personal.adminOwnedHint')}
        </p>
      </div>
    </section>
  );
}
