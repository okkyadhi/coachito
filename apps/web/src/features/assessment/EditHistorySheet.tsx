import { useQuery } from '@tanstack/react-query';
import { X } from 'lucide-react';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import { type AssessmentEdit, getEditHistory } from './assessment-api';
import { type SkillDef, listSkills } from './skills-api';

interface Props {
  assessmentId: string;
  onClose: () => void;
}

export function EditHistorySheet({ assessmentId, onClose }: Props) {
  const { t, i18n } = useTranslation();
  const { data, isPending } = useQuery({
    queryKey: ['assessment-edits', assessmentId],
    queryFn: () => getEditHistory(assessmentId),
  });
  const { data: skills } = useQuery({
    queryKey: ['skills'],
    queryFn: () => listSkills(),
    staleTime: 60 * 60 * 1000,
  });
  const skillById = useMemo(() => {
    const map: Record<string, SkillDef> = {};
    for (const s of skills ?? []) map[s.id] = s;
    return map;
  }, [skills]);
  const localeIsId = i18n.language === 'id';

  return (
    <div
      role="dialog"
      aria-modal="true"
      onClick={onClose}
      className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 sm:items-center"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[80vh] w-full max-w-md flex-col rounded-t-2xl bg-bg-primary sm:rounded-2xl"
      >
        <header className="flex items-center justify-between border-b-[0.5px] border-border-hairline px-4 py-3">
          <button
            type="button"
            onClick={onClose}
            aria-label={t('common.cancel')}
            className="flex size-9 items-center justify-center rounded-full text-text-color-secondary"
          >
            <X size={18} strokeWidth={1.75} aria-hidden />
          </button>
          <span className="text-h3 text-text-color-primary">
            {t('assessment.history.title')}
          </span>
          <span className="size-9" aria-hidden />
        </header>
        <div className="flex-1 overflow-y-auto p-4">
          {isPending ? (
            <p className="text-caption text-text-color-secondary">
              {t('common.loading')}
            </p>
          ) : !data || data.length === 0 ? (
            <p className="text-caption text-text-color-secondary">
              {t('assessment.history.empty')}
            </p>
          ) : (
            <ul className="flex flex-col gap-3">
              {data.map((e) => (
                <EditRow
                  key={e.id}
                  edit={e}
                  skillById={skillById}
                  localeIsId={localeIsId}
                />
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function EditRow({
  edit,
  skillById,
  localeIsId,
}: {
  edit: AssessmentEdit;
  skillById: Record<string, SkillDef>;
  localeIsId: boolean;
}) {
  const { t } = useTranslation();
  const changes = edit.changes as {
    summary?: { from: string; to: string };
    internal_notes?: { from: string; to: string };
    scores?: Array<{ skill_id: string; from: number | null; to: number | null }>;
  };
  return (
    <li className="rounded-lg border-[0.5px] border-border-hairline bg-bg-secondary p-3">
      <p className="text-body text-text-color-primary">
        {edit.editedByDisplayName}
      </p>
      <p className="text-footnote text-text-color-tertiary">
        {new Date(edit.editedAt).toLocaleString()}
      </p>
      <ul className="mt-2 flex flex-col gap-1 text-caption text-text-color-secondary">
        {changes.summary ? (
          <li>
            <span className="font-medium">{t('assessment.history.summary')}</span>:
            “{changes.summary.from || '—'}” → “{changes.summary.to}”
          </li>
        ) : null}
        {changes.scores
          ? changes.scores.map((s, i) => {
              const def = skillById[s.skill_id];
              // Skill names stay in English (per CLAUDE.md skill ontology
              // rule) but the API also gives us name_id; pick by current
              // locale so the row reads naturally.
              const skillLabel = def
                ? localeIsId
                  ? def.nameId
                  : def.nameEn
                : `${s.skill_id.slice(0, 8)}…`;
              return (
                <li key={i}>
                  {t('assessment.history.score', {
                    skill: skillLabel,
                    from: s.from ?? '—',
                    to: s.to ?? '—',
                  })}
                </li>
              );
            })
          : null}
      </ul>
    </li>
  );
}
