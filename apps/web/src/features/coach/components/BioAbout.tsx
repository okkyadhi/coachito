import { useState } from 'react';
import { useTranslation } from 'react-i18next';

interface Props {
  about: string;
}

const COLLAPSE_AT = 320;

export function BioAbout({ about }: Props) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const needsCollapse = about.length > COLLAPSE_AT;
  const shown = needsCollapse && !expanded ? about.slice(0, COLLAPSE_AT) + '…' : about;
  return (
    <section className="flex flex-col gap-2">
      <h2 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {t('coach.bio.aboutTitle')}
      </h2>
      <div className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
        <p className="whitespace-pre-line text-body leading-relaxed text-text-color-primary">
          {shown}
        </p>
        {needsCollapse ? (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="mt-2 text-caption text-accent"
          >
            {expanded ? t('coach.bio.readLess') : t('coach.bio.readMore')}
          </button>
        ) : null}
      </div>
    </section>
  );
}
