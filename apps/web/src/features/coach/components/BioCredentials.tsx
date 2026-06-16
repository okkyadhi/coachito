import { useTranslation } from 'react-i18next';

import type { CertificationEntry } from '../coach-types';

interface Props {
  yearsCoaching: number | null;
  certifications: CertificationEntry[];
  languages: string[];
}

const LANGUAGE_LABEL: Record<string, { en: string; id: string }> = {
  en: { en: 'English', id: 'Inggris' },
  id: { en: 'Indonesian', id: 'Indonesia' },
  es: { en: 'Spanish', id: 'Spanyol' },
  ja: { en: 'Japanese', id: 'Jepang' },
  zh: { en: 'Mandarin', id: 'Mandarin' },
};

export function BioCredentials({
  yearsCoaching,
  certifications,
  languages,
}: Props) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'id' ? 'id' : 'en';
  const hasAny =
    yearsCoaching != null || certifications.length > 0 || languages.length > 0;
  if (!hasAny) return null;
  return (
    <section className="flex flex-col gap-2">
      <h2 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {t('coach.bio.credentialsTitle')}
      </h2>
      <div className="flex flex-col gap-3 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
        {yearsCoaching != null ? (
          <div className="flex items-baseline gap-2">
            <span className="text-h2 text-text-color-primary">{yearsCoaching}</span>
            <span className="text-caption text-text-color-secondary">
              {t('coach.bio.yearsCoaching', { count: yearsCoaching })}
            </span>
          </div>
        ) : null}
        {certifications.length > 0 ? (
          <ul className="flex flex-col gap-1">
            {certifications.map((c, i) => (
              <li key={i} className="text-body text-text-color-primary">
                <span className="font-medium">{c.issuer}</span> · {c.name} · {c.year}
              </li>
            ))}
          </ul>
        ) : null}
        {languages.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {languages.map((code) => {
              const label = LANGUAGE_LABEL[code]?.[lang] ?? code.toUpperCase();
              return (
                <span
                  key={code}
                  className="rounded-full border-[0.5px] border-border-hairline bg-bg-secondary px-2 py-0.5 text-pill text-text-color-secondary"
                >
                  {label}
                </span>
              );
            })}
          </div>
        ) : null}
      </div>
    </section>
  );
}
