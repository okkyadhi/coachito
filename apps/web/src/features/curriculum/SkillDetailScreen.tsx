// Skill detail — hero + collapsed descriptors (native <details> accordion).
//
// All five levels start collapsed (mockup v2 decision); tapping a header
// expands the body.  For admins the body also shows an "Edit descriptor"
// link that opens a Phase B stub sheet ("Coming in next release") — actual
// editing ships in the follow-up release.

import { ChevronDown, ChevronLeft, Pencil } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

import { SecondaryButton } from '@/components/SecondaryButton';

import {
  type Descriptor,
  useCurriculumSkills,
  useCurriculumTiers,
  useSkillDescriptors,
  useTierContext,
} from './curriculum-api';
import { EditDescriptorStubSheet } from './EditDescriptorStubSheet';
import { SendFeedbackSheet } from './SendFeedbackSheet';
import { TierContextSection } from './TierContextSection';
import { useCurriculumPermissions } from './use-curriculum-permissions';

export function SkillDetailScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { skillCode } = useParams<{ skillCode: string }>();
  const perms = useCurriculumPermissions();
  const { data: skills } = useCurriculumSkills();
  const { data: tiers } = useCurriculumTiers();
  const { data: descriptors, isPending } = useSkillDescriptors(skillCode);

  const [editingLevel, setEditingLevel] = useState<number | null>(null);
  const [feedbackOpen, setFeedbackOpen] = useState(false);

  const skill = skills?.find((s) => s.code === skillCode);
  const tierCtxQ = useTierContext(skillCode);

  // Map level → tier name based on the workspace's tier style.
  const tierLabelByLevel = useMemo(() => {
    if (!tiers) return new Map<number, string>();
    const m = new Map<number, string>();
    // Tier display_order is 1-based and matches level for the default
    // padel curriculum (5 levels → 5 main tiers).  For curricula with more
    // tiers (Bronze/Silver split etc.) we just label by the tier whose
    // display_order matches the level.
    for (const t of tiers) {
      if (t.display_order >= 1 && t.display_order <= 5) {
        m.set(
          t.display_order,
          t.name_custom_en ?? t.name_skill_en,
        );
      }
    }
    return m;
  }, [tiers]);

  if (!skillCode) {
    return null;
  }

  return (
    <div className="mx-auto w-full max-w-md px-4 pb-8 pt-3">
      {/* Top bar */}
      <header className="mb-4 flex items-center gap-2">
        <button
          type="button"
          onClick={() => navigate('/settings/curriculum')}
          className="flex min-h-tap min-w-tap items-center text-accent"
          aria-label={t('common.back')}
        >
          <ChevronLeft size={20} strokeWidth={1.75} aria-hidden />
          <span className="text-body">{t('settings.curriculum.title')}</span>
        </button>
      </header>

      {/* Hero */}
      {skill ? (
        <section className="mb-4 flex flex-col gap-2 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
          <span className="self-start rounded-md bg-bg-tertiary px-2 py-0.5 text-footnote text-text-color-secondary">
            {t(`category.${skill.category}`)}
          </span>
          <h1 className="text-h2 text-text-color-primary">{skill.name_en}</h1>
          {skill.description_en ? (
            <p className="text-body text-text-color-secondary">
              {skill.description_en}
            </p>
          ) : null}
          {!skill.is_enabled ? (
            <p className="mt-1 text-footnote text-warning-text">
              {t('settings.curriculum.skill.disabledNote')}
            </p>
          ) : null}
        </section>
      ) : null}

      {/* Tier requirements — only render when there's something to show */}
      {tierCtxQ.data && tierCtxQ.data.length > 0 ? (
        <TierContextSection requirements={tierCtxQ.data} />
      ) : null}

      {/* Descriptors */}
      <section className="flex flex-col gap-2">
        <header className="flex items-baseline justify-between px-1">
          <h3 className="text-section uppercase tracking-wide text-text-color-secondary">
            {t('settings.curriculum.skill.descriptors')}
          </h3>
          <span className="text-footnote text-text-color-tertiary">
            {t('settings.curriculum.skill.tapExpand')}
          </span>
        </header>
        <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
          {isPending ? (
            <div className="p-3 text-body text-text-color-tertiary">
              {t('common.loading')}
            </div>
          ) : descriptors && descriptors.length > 0 ? (
            descriptors.map((d) => (
              <DescriptorAccordion
                key={d.level}
                descriptor={d}
                tierLabel={tierLabelByLevel.get(d.level)}
                canEdit={perms.canEdit}
                onEdit={() => setEditingLevel(d.level)}
              />
            ))
          ) : (
            <div className="p-3 text-body text-text-color-tertiary">
              {t('settings.curriculum.skill.noDescriptors')}
            </div>
          )}
        </div>
      </section>

      {/* Coach feedback CTA */}
      {perms.canSendFeedback ? (
        <div className="mt-5">
          <SecondaryButton onClick={() => setFeedbackOpen(true)}>
            {t('settings.curriculum.feedback.sendAbout', {
              skill: skill?.name_en ?? '',
            })}
          </SecondaryButton>
        </div>
      ) : null}

      {/* Phase B stub */}
      {editingLevel !== null ? (
        <EditDescriptorStubSheet
          level={editingLevel}
          skillName={skill?.name_en ?? ''}
          open
          onClose={() => setEditingLevel(null)}
        />
      ) : null}

      {/* Coach feedback sheet */}
      {feedbackOpen && skill ? (
        <SendFeedbackSheet
          subjectSkillId={skill.id}
          subjectSkillName={skill.name_en}
          open
          onClose={() => setFeedbackOpen(false)}
        />
      ) : null}
    </div>
  );
}

interface AccordionProps {
  descriptor: Descriptor;
  tierLabel: string | undefined;
  canEdit: boolean;
  onEdit: () => void;
}

function DescriptorAccordion({
  descriptor,
  tierLabel,
  canEdit,
  onEdit,
}: AccordionProps) {
  const { t } = useTranslation();
  return (
    <details className="group border-t-[0.5px] border-border-hairline first:border-t-0">
      <summary
        className="flex min-h-tap cursor-pointer list-none items-center justify-between gap-3 p-3 [&::-webkit-details-marker]:hidden"
      >
        <div className="flex flex-1 flex-col gap-0.5">
          <span className="text-body text-text-color-primary">
            {t('settings.curriculum.skill.level', { level: descriptor.level })}
          </span>
          {tierLabel ? (
            <span className="text-footnote text-text-color-tertiary">
              {tierLabel}
            </span>
          ) : null}
        </div>
        <ChevronDown
          size={16}
          strokeWidth={1.75}
          aria-hidden
          className="text-text-color-tertiary transition-transform group-open:rotate-180"
        />
      </summary>
      <div className="border-t-[0.5px] border-border-hairline p-3 pt-2">
        <p className="text-body text-text-color-secondary">
          {descriptor.description_en}
        </p>
        {canEdit ? (
          <button
            type="button"
            onClick={onEdit}
            className="mt-2 inline-flex items-center gap-1 text-body text-accent"
          >
            <Pencil size={14} strokeWidth={1.75} aria-hidden />
            {t('settings.curriculum.skill.edit')}
          </button>
        ) : null}
      </div>
    </details>
  );
}
