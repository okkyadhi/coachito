// Settings → Curriculum.
//
// Three rendering modes driven by `useCurriculumPermissions()`:
//   - Admin/owner on edit-eligible plan → toggle rows + "Add custom skill"
//     (the latter shown as a disabled "Coming soon" affordance).
//   - Admin/owner on Club Starter → toggle rows are disabled + plan upsell
//     banner across the top.
//   - Coach (any plan) → chevron rows + "Managed by your club admin → Send
//     feedback" banner.

import { ArrowLeft, ChevronLeft, Inbox, Lock, Plus, Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { SportTabs } from '@/features/sports/SportTabs';

import {
  type SkillRow,
  useCurriculumSkills,
  useFeedbackInbox,
  useMyFeedback,
  useToggleSkill,
} from './curriculum-api';
import { DisableSkillSheet } from './DisableSkillSheet';
import { SendFeedbackSheet } from './SendFeedbackSheet';
import { SkillChevronRow } from './SkillChevronRow';
import { SkillToggleRow } from './SkillToggleRow';
import { useCurriculumPermissions } from './use-curriculum-permissions';

const CATEGORY_ORDER: SkillRow['category'][] = [
  'technical',
  'tactical',
  'physical',
  'mental',
];

export function CurriculumScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const perms = useCurriculumPermissions();
  const { data: skills, isPending } = useCurriculumSkills();
  const toggle = useToggleSkill();

  const [query, setQuery] = useState('');
  const [pendingDisable, setPendingDisable] = useState<SkillRow | null>(null);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  // Inbox count drives the admin header badge.  Only fetched when the user
  // is admin/owner — coaches don't have access.
  const inboxQ = useFeedbackInbox(perms.canEditRole);
  const unread = inboxQ.data?.unread_count ?? 0;
  // Coach's outgoing feedback history.  Only fetched for non-admin coaches —
  // owners and admins skip (they receive, they don't send).
  const myFeedbackQ = useMyFeedback(perms.canSendFeedback);
  const mySent = myFeedbackQ.data?.notes.length ?? 0;

  // For admin: one grouped list with toggles, enabled + disabled mixed in
  // each category (they need to see both to enable back).
  // For coach: enabled-only grouped list + a single collapsed section at the
  // bottom for disabled skills (also grouped internally by category).
  const { activeGrouped, disabledGrouped, disabledCount } = useMemo(() => {
    if (!skills) {
      return { activeGrouped: [], disabledGrouped: [], disabledCount: 0 };
    }
    const q = query.trim().toLowerCase();
    const filtered = q
      ? skills.filter(
          (s) =>
            s.name_en.toLowerCase().includes(q) ||
            s.name_id.toLowerCase().includes(q),
        )
      : skills;

    // Admin sees the merged list.  Coach view splits enabled from disabled.
    const wantSplit = !perms.canEditRole;
    const activeSrc = wantSplit ? filtered.filter((s) => s.is_enabled) : filtered;
    const disabledSrc = wantSplit ? filtered.filter((s) => !s.is_enabled) : [];

    const group = (rows: SkillRow[]) => {
      const byCat = new Map<SkillRow['category'], SkillRow[]>();
      for (const s of rows) {
        const list = byCat.get(s.category) ?? [];
        list.push(s);
        byCat.set(s.category, list);
      }
      return CATEGORY_ORDER.filter((c) => byCat.has(c)).map((c) => ({
        category: c,
        items: byCat.get(c)!,
      }));
    };

    return {
      activeGrouped: group(activeSrc),
      disabledGrouped: group(disabledSrc),
      disabledCount: disabledSrc.length,
    };
  }, [skills, query, perms.canEditRole]);

  const handleToggle = (skill: SkillRow, next: boolean) => {
    // Disabling needs preflight confirmation; enabling is one-step.
    if (!next && skill.is_enabled) {
      setPendingDisable(skill);
    } else {
      toggle.mutate({ code: skill.code, isEnabled: next });
    }
  };

  const confirmDisable = () => {
    if (!pendingDisable) return;
    toggle.mutate(
      { code: pendingDisable.code, isEnabled: false },
      { onSuccess: () => setPendingDisable(null) },
    );
  };

  return (
    <div className="mx-auto w-full max-w-md px-4 pb-8 pt-3">
      {/* Top bar */}
      <header className="mb-4 flex items-center gap-2">
        <button
          type="button"
          onClick={() => navigate('/settings')}
          className="flex min-h-tap min-w-tap items-center text-accent"
          aria-label={t('common.back')}
        >
          <ChevronLeft size={20} strokeWidth={1.75} aria-hidden />
          <span className="text-body">{t('nav.settings')}</span>
        </button>
        <h1 className="ml-2 flex-1 text-large-title text-text-color-primary">
          {t('settings.curriculum.title')}
        </h1>
        {perms.canEditRole ? (
          <button
            type="button"
            onClick={() => navigate('/settings/curriculum/feedback')}
            className="relative flex min-h-tap min-w-tap items-center justify-center text-text-color-secondary"
            aria-label={t('settings.curriculum.feedback.inboxTitle')}
          >
            <Inbox size={20} strokeWidth={1.75} aria-hidden />
            {unread > 0 ? (
              <span
                aria-label={t('settings.curriculum.feedback.unreadCount', {
                  count: unread,
                })}
                className="absolute right-1 top-1 min-w-[18px] rounded-full bg-accent px-1 text-center text-[10px] font-medium leading-[18px] text-white"
              >
                {unread}
              </span>
            ) : null}
          </button>
        ) : null}
      </header>

      {/* Sport switcher — only visible when workspace has multiple sports */}
      <div className="mb-4">
        <SportTabs />
      </div>

      {/* Coach view: "managed by admin" banner with feedback CTA + history link */}
      {!perms.canEditRole && !perms.isLoading ? (
        <div className="mb-4 flex flex-col gap-2 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-3">
          <p className="text-body text-text-color-secondary">
            {t('settings.curriculum.managedByAdmin')}
          </p>
          {perms.canSendFeedback ? (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
              <button
                type="button"
                onClick={() => setFeedbackOpen(true)}
                className="text-body text-accent"
              >
                {t('settings.curriculum.feedback.send')} →
              </button>
              {mySent > 0 ? (
                <button
                  type="button"
                  onClick={() => navigate('/settings/curriculum/feedback/mine')}
                  className="text-body text-text-color-secondary"
                >
                  {t('settings.curriculum.feedback.mySentCount', { count: mySent })}
                  {' '}
                  →
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}

      {/* Plan upsell for Club Starter admins */}
      {perms.showPlanUpsell ? (
        <div className="mb-4 flex items-start gap-3 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-3">
          <Lock
            size={16}
            strokeWidth={1.75}
            aria-hidden
            className="mt-0.5 shrink-0 text-text-color-tertiary"
          />
          <div className="flex flex-col gap-1">
            <p className="text-body text-text-color-primary">
              {t('settings.curriculum.proRequired')}
            </p>
            <button
              type="button"
              onClick={() => navigate('/settings')}
              className="self-start text-body text-accent"
            >
              {t('settings.curriculum.upgrade')} →
            </button>
          </div>
        </div>
      ) : null}

      {/* Search */}
      <label className="mb-4 flex items-center gap-2 rounded-md border-[0.5px] border-border-hairline bg-bg-primary px-3 py-2">
        <Search
          size={16}
          strokeWidth={1.75}
          aria-hidden
          className="text-text-color-tertiary"
        />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t('settings.curriculum.search')}
          className="flex-1 bg-transparent text-body text-text-color-primary placeholder:text-text-color-tertiary focus:outline-none"
        />
      </label>

      {/* List */}
      {isPending ? (
        <Skeleton />
      ) : (
        <div className="flex flex-col gap-5">
          {activeGrouped.map((group) => {
            const enabledCount = group.items.filter((s) => s.is_enabled).length;
            return (
              <section key={group.category} className="flex flex-col gap-2">
                <header className="flex items-baseline justify-between px-1">
                  <h3 className="text-section uppercase tracking-wide text-text-color-secondary">
                    {t(`category.${group.category}`)}
                  </h3>
                  {perms.canEditRole ? (
                    <span className="text-footnote text-text-color-tertiary">
                      {t('settings.curriculum.enabledOfTotal', {
                        count: enabledCount,
                        total: group.items.length,
                      })}
                    </span>
                  ) : (
                    <span className="text-footnote text-text-color-tertiary">
                      {t('settings.curriculum.skillCount', {
                        count: group.items.length,
                      })}
                    </span>
                  )}
                </header>
                <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
                  {group.items.map((skill) =>
                    perms.canEdit ? (
                      <SkillToggleRow
                        key={skill.code}
                        skill={skill}
                        onOpen={() =>
                          navigate(`/settings/curriculum/${skill.code}`)
                        }
                        onToggle={(next) => handleToggle(skill, next)}
                        busy={
                          toggle.isPending && toggle.variables?.code === skill.code
                        }
                      />
                    ) : (
                      <SkillChevronRow
                        key={skill.code}
                        skill={skill}
                        onOpen={() =>
                          navigate(`/settings/curriculum/${skill.code}`)
                        }
                      />
                    ),
                  )}
                </div>
              </section>
            );
          })}

          {/* Coach view: disabled skills tucked into a collapsed section */}
          {!perms.canEditRole && disabledCount > 0 ? (
            <details className="group overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
              <summary className="flex min-h-tap cursor-pointer list-none items-center justify-between gap-3 p-3 [&::-webkit-details-marker]:hidden">
                <span className="text-body text-text-color-secondary">
                  {t('settings.curriculum.disabledSection', {
                    count: disabledCount,
                  })}
                </span>
                <span className="text-footnote text-text-color-tertiary transition-transform group-open:rotate-180">
                  ▾
                </span>
              </summary>
              <div className="border-t-[0.5px] border-border-hairline">
                {disabledGrouped.map((group, gi) => (
                  <div
                    key={group.category}
                    className={gi > 0 ? 'border-t-[0.5px] border-border-hairline' : ''}
                  >
                    <div className="bg-bg-tertiary px-3 py-1.5 text-footnote uppercase tracking-wide text-text-color-secondary">
                      {t(`category.${group.category}`)}
                    </div>
                    {group.items.map((skill) => (
                      <SkillChevronRow
                        key={skill.code}
                        skill={skill}
                        onOpen={() =>
                          navigate(`/settings/curriculum/${skill.code}`)
                        }
                      />
                    ))}
                  </div>
                ))}
              </div>
            </details>
          ) : null}

          {/* Add custom skill — disabled "Coming soon" affordance, only for admins */}
          {perms.canEditRole ? (
            <div className="flex items-center justify-between gap-3 rounded-xl border-[0.5px] border-border-hairline bg-bg-tertiary p-3 opacity-80">
              <span className="flex items-center gap-2 text-body text-text-color-tertiary">
                <Plus size={16} strokeWidth={1.75} aria-hidden />
                {t('settings.curriculum.addCustom')}
              </span>
              <span className="rounded-full border-[0.5px] border-border-hairline bg-bg-primary px-2 py-0.5 text-footnote text-text-color-secondary">
                {t('settings.curriculum.addCustomSoon')}
              </span>
            </div>
          ) : null}
        </div>
      )}

      {/* Disable confirmation */}
      {pendingDisable ? (
        <DisableSkillSheet
          skill={pendingDisable}
          open
          onConfirm={confirmDisable}
          onCancel={() => setPendingDisable(null)}
          pending={toggle.isPending}
        />
      ) : null}

      {/* General feedback (no specific skill) */}
      {feedbackOpen ? (
        <SendFeedbackSheet
          open
          onClose={() => setFeedbackOpen(false)}
        />
      ) : null}
    </div>
  );
}

function Skeleton() {
  return (
    <div className="flex flex-col gap-4">
      <div className="h-24 rounded-xl bg-bg-primary" />
      <div className="h-32 rounded-xl bg-bg-primary" />
      <div className="h-32 rounded-xl bg-bg-primary" />
    </div>
  );
}

// Re-export ArrowLeft so the linter doesn't complain about the import above
// (Vite's tree-shake otherwise warns — keeping the icon importable here
// makes future header iterations cheaper).
void ArrowLeft;
