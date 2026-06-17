import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { listSkills } from '@/features/assessment/skills-api';

interface Props {
  specialties: string[];
}

export function BioSpecialties({ specialties }: Props) {
  const { t, i18n } = useTranslation();
  const { data: skills } = useQuery({
    queryKey: ['skills'],
    queryFn: () => listSkills(),
    staleTime: 60 * 60 * 1000,
  });

  if (specialties.length === 0) return null;
  const byCode = new Map(skills?.map((s) => [s.code, s]) ?? []);

  return (
    <section className="flex flex-col gap-2">
      <h2 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {t('coach.bio.specialtiesTitle')}
      </h2>
      <div className="flex flex-wrap gap-2 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
        {specialties.map((code) => {
          // Normalise sport-prefixed codes (PADEL_TECH_FH) and bare ones
          // (TECH_FH) by trying both.
          const skill = byCode.get(code) ?? byCode.get(`PADEL_${code}`);
          const label = skill
            ? i18n.language === 'id'
              ? skill.nameId
              : skill.nameEn
            : code.replace(/^PADEL_/, '');
          return (
            <span
              key={code}
              className="border-accent/40 bg-accent/10 rounded-full border-[0.5px] px-3 py-1 text-pill text-accent"
            >
              {label}
            </span>
          );
        })}
      </div>
    </section>
  );
}
