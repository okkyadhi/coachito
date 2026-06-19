import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ChevronLeft, History } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';

import { Avatar } from '@/components/Avatar';
import { useAuthStore } from '@/features/auth/auth-store';
import { ApiError } from '@/lib/api';
import { useOnlineStatus } from '@/lib/use-online-status';

import type { SkillCategory } from '@/features/trainee-profile/profile-types';

import { CategoryGroup } from './CategoryGroup';
import { EditHistorySheet } from './EditHistorySheet';
import { PublishConfirmSheet } from './PublishConfirmSheet';
import { SessionDetailsStrip } from './SessionDetailsStrip';
import { SessionSummary } from './SessionSummary';
import {
  type DraftScoreIn,
  type SessionFocus,
  detectTierUp,
  editAssessment,
  getBySession,
  publishAssessment,
  saveDraft,
} from './assessment-api';
import { TierUpSheet } from './TierUpSheet';
import {
  getFunnelCounts,
  getSession,
  invalidateSessionCaches,
} from '@/features/sessions/sessions-api';
import { fetchTraineeProfile } from '@/features/trainee-profile/profile-api';
import { SportTabs } from '@/features/sports/SportTabs';
import { SportTag } from '@/features/sports/SportTag';
import { useCurrentSport } from '@/features/sports/useCurrentSport';
import { TierPill } from '@/components/TierPill';
import type { ScoreDiffEntry } from './PublishConfirmSheet';
import { SKILL_DESCRIPTORS, getDescriptors, type SkillDescriptors } from './descriptors';
import { listSkills } from './skills-api';
import { useAssessmentDraft } from './use-assessment-draft';

const CATEGORIES: SkillCategory[] = ['technical', 'tactical', 'physical', 'mental'];

export function AssessmentScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const online = useOnlineStatus();
  const { id: athleteId } = useParams<{ id: string }>();
  const [params] = useSearchParams();
  const sessionIdParam = params.get('session') ?? null;
  const readonlyParam = params.get('readonly') === '1';
  const currentUserId = useAuthStore((s) => s.user?.id ?? null);

  const queryClient = useQueryClient();
  const draft = useAssessmentDraft(athleteId ?? '');
  const { currentSportId, isMultiSport, setSport, current: currentSport } = useCurrentSport();

  // When the assessment is opened from a scheduled session, lock the sport to
  // whatever was set on the session.  This ensures the right skill set loads
  // even if the coach's stored sport differs.
  const sessionQ = useQuery({
    queryKey: ['session', sessionIdParam],
    queryFn: () => getSession(sessionIdParam!),
    enabled: Boolean(sessionIdParam),
    staleTime: 60_000,
  });
  useEffect(() => {
    const sid = sessionQ.data?.sportId;
    if (sid) setSport(sid);
  }, [sessionQ.data?.sportId, setSport]);

  // /skills is sport-scoped — keyed by the active sport so switching sports
  // (or assessing in a workspace that runs both) loads the right skill set.
  const { data: skills } = useQuery({
    queryKey: ['skills', currentSportId],
    queryFn: () => listSkills(currentSportId ?? undefined),
    staleTime: 60 * 60 * 1000,
  });

  const skillIdByCode = useMemo(() => {
    const map: Record<string, string> = {};
    for (const s of skills ?? []) map[s.code] = s.id;
    return map;
  }, [skills]);

  const skillCodeById = useMemo(() => {
    const map: Record<string, string> = {};
    for (const s of skills ?? []) map[s.id] = s.code;
    return map;
  }, [skills]);

  // Build SkillDescriptors per category from the live API skill list.  This
  // is sport-aware: when the sport is tennis the API returns tennis skills.
  // For padel skills the static lookup provides the level text; tennis skills
  // fall back to empty strings (acceptable until a tennis descriptor file lands).
  const skillDescsByCategory = useMemo(() => {
    const result: Partial<Record<SkillCategory, SkillDescriptors[]>> = {};
    for (const s of (skills ?? []).slice().sort((a, b) => a.displayOrder - b.displayOrder)) {
      const staticDesc = getDescriptors(s.code);
      const desc: SkillDescriptors = staticDesc ?? {
        skillCode: s.code,
        category: s.category,
        nameEn: s.nameEn,
        descriptions: ['', '', '', '', ''],
      };
      (result[s.category] ??= []).push(desc);
    }
    return result;
  }, [skills]);

  // "Start from last scores" toggle — when on, a fresh draft pre-fills with
  // the trainee's latest published level per skill, so the coach only needs
  // to bump the ones that changed.  Persisted to localStorage so the
  // preference sticks across screens.
  const [prefillFromLast, setPrefillFromLast] = useState(() => {
    try {
      return window.localStorage.getItem('coachito.assess.prefill') !== '0';
    } catch {
      return true;
    }
  });

  const setPrefillPref = useCallback((next: boolean) => {
    setPrefillFromLast(next);
    try {
      window.localStorage.setItem('coachito.assess.prefill', next ? '1' : '0');
    } catch {
      /* private mode */
    }
  }, []);

  // Hydrate from server if there's an existing assessment for this session.
  useEffect(() => {
    if (!sessionIdParam || !skills) return;
    let active = true;
    void (async () => {
      const existing = await getBySession(sessionIdParam);
      if (!active || !existing) return;
      draft.hydrateFromServer(existing, skillCodeById);
    })();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionIdParam, skills]);

  // Pre-fill scores for a brand-new draft from the trainee's latest
  // published levels.  Fires once when the draft is loaded, empty, and
  // there's no existing assessment for this session (i.e. fresh entry
  // from /trainees/:id/assess).  Skipped when the coach has toggled the
  // preference off.
  const [didPrefill, setDidPrefill] = useState(false);
  const { data: profileForPrefill } = useQuery({
    queryKey: ['trainee-profile', athleteId, currentSportId, 'for-prefill'],
    queryFn: () => fetchTraineeProfile(athleteId!, currentSportId ?? undefined),
    enabled:
      prefillFromLast &&
      !!athleteId &&
      !!skills &&
      draft.loaded &&
      !didPrefill &&
      draft.status === null &&
      Object.keys(draft.scores).length === 0,
  });

  // Trainee profile gives us each skill's current published level — used by
  // the publish sheet to render the score-change diff, and by the tier-up
  // celebration to grab the trainee first name.  Always enabled (and
  // cached) since we read it from publish-time too.
  const { data: profileForDiff } = useQuery({
    queryKey: ['trainee-profile', athleteId, currentSportId, 'for-publish-diff'],
    queryFn: () => fetchTraineeProfile(athleteId!, currentSportId ?? undefined),
    enabled: !!athleteId,
  });
  useEffect(() => {
    if (didPrefill) return;
    if (!prefillFromLast) return;
    if (!profileForPrefill || !skills) return;
    if (draft.status !== null) return; // existing assessment hydrated
    if (Object.keys(draft.scores).length > 0) return;
    let any = false;
    for (const s of profileForPrefill.allSkills) {
      if (s.level != null) {
        draft.setScore(s.skill.code, s.level);
        any = true;
      }
    }
    setDidPrefill(true);
    if (any) {
      // Pre-fill shouldn't mark the form "dirty" in the unsaved-changes
      // sense — these are levels already on the server.  But our `setScore`
      // marks dirty; clear it so back-nav doesn't warn unnecessarily.
      draft.markClean();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileForPrefill, skills, prefillFromLast, didPrefill]);

  const [openCategories, setOpenCategories] = useState<Set<SkillCategory>>(
    new Set(['technical']),
  );
  const [expandedSkill, setExpandedSkill] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [showPublishSheet, setShowPublishSheet] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [tierUpSheet, setTierUpSheet] = useState<{
    tierName: string;
    traineeFirstName: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<
    | {
        kind: 'savedDraft' | 'published' | 'edited';
        toAssessHint?: number;
        tierBecame?: string | null;
      }
    | null
  >(null);
  const [confirmDiscard, setConfirmDiscard] = useState(false);

  // Read-only modes:
  // - Explicit (?readonly=1) — coach opened another coach's assessment for view.
  // - Implicit — assessment exists, coach_id ≠ me (published / edited by another
  //   coach, OR another coach is currently drafting on this session).
  const otherCoachOwnsIt =
    draft.coachId !== null &&
    currentUserId !== null &&
    draft.coachId !== currentUserId;
  const isReadOnlyForOthersDraft =
    otherCoachOwnsIt && draft.status === 'draft';
  const isReadOnly =
    readonlyParam || (otherCoachOwnsIt && draft.status !== null);

  useEffect(() => {
    if (!draft.isDirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [draft.isDirty]);

  // Phase 8c — auto-save the draft after 10s of idle.  Skip for published
  // assessments (those use explicit Save via PATCH) and for read-only view.
  const isPublishedForAutosave =
    draft.status === 'published' || draft.status === 'edited';
  useEffect(() => {
    if (isReadOnly) return;
    if (!draft.isDirty) return;
    if (isPublishedForAutosave) return;
    if (!online) return;
    const timer = window.setTimeout(() => {
      void handleSaveDraft();
    }, 10_000);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    draft.isDirty,
    draft.scores,
    draft.notes,
    draft.summary,
    isReadOnly,
    isPublishedForAutosave,
    online,
  ]);

  const toggleCategory = (c: SkillCategory) => {
    setOpenCategories((prev) => {
      const next = new Set(prev);
      if (next.has(c)) next.delete(c);
      else next.add(c);
      return next;
    });
  };

  const buildScores = useCallback((): DraftScoreIn[] => {
    return Object.entries(draft.scores)
      .filter(([code]) => skillIdByCode[code] != null)
      .map(([code, level]) => ({
        skillId: skillIdByCode[code]!,
        level,
        note: draft.notes[code] ?? null,
      }));
  }, [draft.scores, draft.notes, skillIdByCode]);

  const handleSaveDraft = useCallback(async () => {
    setError(null);
    setSaving(true);
    try {
      const scores = buildScores();
      // PATCH for already-published; otherwise save (or update) draft.
      if (draft.status === 'published' || draft.status === 'edited') {
        if (!draft.assessmentId) return;
        const r = await editAssessment(draft.assessmentId, {
          summary: draft.summary,
          scores,
        });
        draft.hydrateFromServer(r, skillCodeById);
        invalidateSessionCaches(queryClient);
        void queryClient.invalidateQueries({ queryKey: ['trainees'] });
        // Edit UX (Opsi A): if scores changed (BE returns a tier slice only
        // in that case), kick the coach back to the trainee profile so they
        // see the impact.  Summary-only typo fixes stay put — that's the
        // "I noticed a typo and want to keep editing" case.
        if (r.tier) {
          setToast({
            kind: 'edited',
            tierBecame: r.tier.currentTier?.nameGameEn ?? null,
          });
          window.setTimeout(() => {
            navigate(`/trainees/${athleteId}`);
          }, 700);
        } else {
          setToast({ kind: 'edited' });
        }
      } else {
        const r = await saveDraft({
          athleteId: athleteId!,
          sportId: currentSportId,
          sessionId: draft.sessionId ?? sessionIdParam ?? null,
          sessionScheduledAt: draft.sessionDetails.scheduledAt,
          sessionDurationMin: draft.sessionDetails.durationMin,
          sessionCourt: draft.sessionDetails.court,
          sessionFocus: (draft.sessionDetails.focus ?? null) as SessionFocus | null,
          summary: draft.summary,
          scores,
        });
        draft.hydrateFromServer(r, skillCodeById);
        setToast({ kind: 'savedDraft' });
        invalidateSessionCaches(queryClient);
        void queryClient.invalidateQueries({ queryKey: ['trainees'] });
      }
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : t('assessment.genericError'),
      );
    } finally {
      setSaving(false);
    }
  }, [
    athleteId,
    buildScores,
    currentSportId,
    draft,
    navigate,
    queryClient,
    sessionIdParam,
    skillCodeById,
    t,
  ]);

  const handlePublish = useCallback(
    async (opts: { forceEmpty: boolean }) => {
      if (!draft.assessmentId) {
        // Save first to obtain an id, then publish.
        await handleSaveDraft();
      }
      const id = draft.assessmentId;
      if (!id) return;
      setError(null);
      setPublishing(true);
      try {
        const r = await publishAssessment(id, opts.forceEmpty);
        draft.hydrateFromServer(r, skillCodeById);
        setShowPublishSheet(false);
        invalidateSessionCaches(queryClient);
        void queryClient.invalidateQueries({ queryKey: ['trainees'] });

        // Tier-up celebration takes precedence over auto-navigation —
        // coach earned the moment, don't yank them away.
        const promoted = detectTierUp(r);
        if (promoted) {
          // We need a first name for the share copy.  Pull it lazily from
          // the profile data the publish-diff query already fetched; fall
          // back to the assessment's athleteId truncation otherwise.
          const trainee = profileForDiff?.trainee.displayName ?? '';
          const firstName =
            trainee.split(/\s+/)[0] ?? t('assessment.tierUp.traineeFallback');
          setTierUpSheet({
            tierName: promoted.nameGameEn,
            traineeFirstName: firstName,
          });
          return;
        }

        // Publish UX (Opsi A): show a brief toast, then move the coach to
        // the next natural surface.  If they still have sessions to assess,
        // pop them back to the funnel "To assess" list for batch flow.
        // Otherwise, drop them on the trainee's profile to see tier changes.
        let toAssess = 0;
        try {
          const counts = await getFunnelCounts(true);
          toAssess = counts.toAssess;
        } catch {
          /* non-blocking — fall back to profile navigate */
        }
        setToast({
          kind: 'published',
          toAssessHint: toAssess,
          tierBecame: r.tier?.currentTier?.nameGameEn ?? null,
        });
        window.setTimeout(() => {
          if (toAssess > 0) {
            navigate('/sessions?stage=to_assess');
          } else {
            navigate(`/trainees/${athleteId}`);
          }
        }, 900);
      } catch (e) {
        setError(
          e instanceof ApiError ? e.message : t('assessment.genericError'),
        );
      } finally {
        setPublishing(false);
      }
    },
    [
      athleteId,
      draft,
      navigate,
      profileForDiff,
      queryClient,
      skillCodeById,
      handleSaveDraft,
      t,
    ],
  );

  const handleBack = () => {
    if (draft.isDirty) {
      setConfirmDiscard(true);
      return;
    }
    navigate(`/trainees/${athleteId}`);
  };

  const ratedCount = Object.keys(draft.scores).length;
  const isPublished = draft.status === 'published' || draft.status === 'edited';

  const diffs: ScoreDiffEntry[] = useMemo(() => {
    if (!skills) return [];
    // Build {skill_id → previous published level} from the profile.  Use
    // skill.id (the canonical UUID) so the lookup against draft scores is
    // straightforward.
    const prevById = new Map<string, number>();
    if (profileForDiff) {
      for (const s of profileForDiff.allSkills) {
        if (s.level != null) prevById.set(s.skill.id, s.level);
      }
    }
    const nameByCode: Record<string, string> = {};
    for (const s of skills) nameByCode[s.code] = s.nameEn;
    return Object.entries(draft.scores)
      .map(([code, level]): ScoreDiffEntry | null => {
        const skillId = skillIdByCode[code];
        if (!skillId) return null;
        return {
          skillName: nameByCode[code] ?? code,
          from: prevById.get(skillId) ?? null,
          to: level,
        };
      })
      .filter((d): d is ScoreDiffEntry => d !== null);
  }, [draft.scores, profileForDiff, skillIdByCode, skills]);

  // Trainee identity shown in the assessment header — name + current tier.
  // Falls back to the generic title until the profile query resolves.
  const traineeName = profileForDiff?.trainee.displayName ?? t('assessment.title');
  const traineeTier = profileForDiff?.tierProgress.currentTier.code ?? null;

  return (
    <main className="flex h-screen flex-col bg-bg-tertiary">
      <header className="flex items-center border-b-[0.5px] border-border-hairline bg-bg-primary px-2 py-1.5">
        <button
          type="button"
          onClick={handleBack}
          className="flex min-h-tap items-center gap-0.5 px-2 text-caption text-accent"
        >
          <ChevronLeft size={18} strokeWidth={2} aria-hidden />
          <span>{t('common.back')}</span>
        </button>
        <span className="flex-1 text-center text-h3 text-text-color-primary">
          {t('assessment.title')}
        </span>
        <div className="flex items-center">
          {isReadOnly ? null : (
            <>
              <button
                type="button"
                onClick={() => void handleSaveDraft()}
                disabled={
                  saving || publishing || !draft.loaded || !skills ||
                  (!draft.isDirty && !isPublished)
                }
                className="flex min-h-tap items-center px-2 text-caption text-text-color-secondary disabled:opacity-40"
              >
                {saving
                  ? t('assessment.saving')
                  : isPublished
                    ? t('assessment.saveChanges')
                    : t('assessment.saveDraft')}
              </button>
              {!isPublished ? (
                <button
                  type="button"
                  onClick={() => setShowPublishSheet(true)}
                  disabled={
                    saving || publishing || !draft.loaded || !skills ||
                    (ratedCount === 0 && draft.summary.trim().length <= 10)
                  }
                  className="flex min-h-tap items-center px-3 text-caption font-medium text-accent disabled:opacity-40"
                >
                  {t('assessment.publish')}
                </button>
              ) : null}
            </>
          )}
        </div>
      </header>

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto flex w-full max-w-md flex-col gap-5 px-4 pb-32 pt-4">
          <div className="flex items-center gap-3">
            <Avatar name={traineeName} size={44} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-h2 text-text-color-primary">
                {traineeName}
              </p>
              <div className="mt-0.5 flex flex-wrap items-center gap-2">
                <p className="text-caption text-text-color-secondary">
                  {t('assessment.ratedCount', {
                    count: ratedCount,
                    total: skills?.length ?? SKILL_DESCRIPTORS.length,
                  })}
                </p>
                <SportTag sport={currentSport} />
                {traineeTier ? <TierPill tier={traineeTier} /> : null}
              </div>
            </div>
          </div>

          <StatusStrip
            status={draft.status}
            publishedAt={draft.publishedAt}
            editedAt={draft.editedAt}
            traineeViewedAt={draft.traineeViewedAt ?? null}
            isDirty={draft.isDirty}
            saving={saving}
            onShowHistory={() => setShowHistory(true)}
          />

          {/* Sport switcher — hidden when session already has a sport set */}
          {isMultiSport && !isReadOnly && !draft.assessmentId && !sessionIdParam ? (
            <SportTabs />
          ) : null}

          {isReadOnly ? (
            <div className="rounded-lg border-[0.5px] border-border-hairline bg-bg-secondary px-3 py-2">
              <p className="text-caption text-text-color-secondary">
                {isReadOnlyForOthersDraft
                  ? t('sessions.readonly.draftBanner', {
                      coach: draft.coachDisplayName ?? '—',
                    })
                  : t('sessions.readonly.banner', {
                      coach: draft.coachDisplayName ?? '—',
                      date: draft.publishedAt
                        ? new Date(draft.publishedAt).toLocaleDateString()
                        : draft.editedAt
                          ? new Date(draft.editedAt).toLocaleDateString()
                          : '—',
                    })}
              </p>
            </div>
          ) : null}

          <fieldset
            disabled={isReadOnly}
            className="contents disabled:cursor-default"
          >
            <SessionDetailsStrip
              value={draft.sessionDetails}
              onChange={draft.setSessionDetails}
            />
          </fieldset>

          {/* Pre-fill from last scores — only meaningful on a brand-new
              draft.  Hidden when an existing assessment is loaded or in
              read-only mode. */}
          {!isReadOnly && draft.status === null ? (
            <label className="flex items-center gap-2 text-caption text-text-color-secondary">
              <input
                type="checkbox"
                checked={prefillFromLast}
                onChange={(e) => {
                  setPrefillPref(e.target.checked);
                  if (!e.target.checked) {
                    // Reset scores so the toggle has visible effect when
                    // turned off mid-session.
                    for (const code of Object.keys(draft.scores)) {
                      draft.setScore(code, null);
                    }
                    setDidPrefill(true); // prevent re-fire of effect
                  } else {
                    setDidPrefill(false);
                  }
                }}
                className="size-4"
              />
              <span>{t('assessment.prefillFromLast')}</span>
            </label>
          ) : null}

          <div className="flex flex-wrap gap-1.5">
            {[1, 2, 3, 4, 5].map((n) => (
              <span
                key={n}
                className="rounded-full border-[0.5px] border-border-hairline bg-bg-primary px-2.5 py-1 text-pill text-text-color-secondary"
              >
                {n} · {t(`assessment.levels.${n}`)}
              </span>
            ))}
          </div>

          <fieldset
            disabled={isReadOnly}
            className="contents disabled:cursor-default disabled:opacity-90"
          >
            <div className="flex flex-col gap-3">
              {CATEGORIES.map((category) => (
                <CategoryGroup
                  key={category}
                  category={category}
                  skills={skillDescsByCategory[category] ?? []}
                  scores={draft.scores}
                  notes={draft.notes}
                  expandedSkill={expandedSkill}
                  isOpen={openCategories.has(category)}
                  onToggleOpen={() => toggleCategory(category)}
                  onSkillLevelChange={draft.setScore}
                  onSkillNoteChange={draft.setNote}
                  onSkillExpand={(c) =>
                    setExpandedSkill((p) => (p === c ? null : c))
                  }
                />
              ))}
            </div>

            <SessionSummary
              value={draft.summary}
              onChange={draft.setSummary}
              assessmentId={draft.assessmentId}
              canDraft={ratedCount > 0}
            />
          </fieldset>

          {error ? (
            <div className="rounded-md border-[0.5px] border-danger-text bg-danger-bg p-3">
              <p className="text-caption text-danger-text">{error}</p>
            </div>
          ) : null}
        </div>
      </div>

      {toast ? (
        <Toast onDone={() => setToast(null)}>
          {toast.kind === 'savedDraft'
            ? t('assessment.savedDraft')
            : toast.kind === 'published'
              ? toast.toAssessHint && toast.toAssessHint > 0
                ? t('assessment.publishedToAssessHint', {
                    count: toast.toAssessHint,
                  })
                : toast.tierBecame
                  ? t('assessment.publishedTierToast', {
                      tier: toast.tierBecame,
                    })
                  : t('assessment.publishedToast')
              : toast.tierBecame
                ? t('assessment.editedTierToast', { tier: toast.tierBecame })
                : t('assessment.editedToast')}
        </Toast>
      ) : null}

      {showPublishSheet ? (
        <PublishConfirmSheet
          ratedCount={ratedCount}
          summaryChars={draft.summary.length}
          diffs={diffs}
          open={showPublishSheet}
          loading={publishing}
          online={online}
          onCancel={() => setShowPublishSheet(false)}
          onConfirm={(forceEmpty) => void handlePublish({ forceEmpty })}
        />
      ) : null}

      {showHistory && draft.assessmentId ? (
        <EditHistorySheet
          assessmentId={draft.assessmentId}
          onClose={() => setShowHistory(false)}
        />
      ) : null}

      {tierUpSheet ? (
        <TierUpSheet
          open
          traineeFirstName={tierUpSheet.traineeFirstName}
          tierName={tierUpSheet.tierName}
          onClose={() => {
            setTierUpSheet(null);
            // After acknowledging the celebration, route to the trainee
            // profile so the coach sees the new tier in context.
            navigate(`/trainees/${athleteId}`);
          }}
        />
      ) : null}

      {confirmDiscard ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 px-6">
          <div className="w-full max-w-xs rounded-xl bg-bg-primary p-5">
            <h3 className="text-h3 text-text-color-primary">
              {t('assessment.discardConfirm')}
            </h3>
            <p className="mt-1 text-caption text-text-color-secondary">
              {t('assessment.discardConfirmBody')}
            </p>
            <div className="mt-4 flex flex-col gap-2">
              <button
                type="button"
                onClick={async () => {
                  await draft.clearLocal();
                  setConfirmDiscard(false);
                  navigate(`/trainees/${athleteId}`);
                }}
                className="min-h-tap rounded-md border-[0.5px] border-danger-text bg-bg-primary text-[14px] font-medium text-danger-text"
              >
                {t('assessment.discard')}
              </button>
              <button
                type="button"
                onClick={() => setConfirmDiscard(false)}
                className="min-h-tap rounded-md bg-accent text-[14px] font-medium text-white"
              >
                {t('assessment.keepEditing')}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}

// ── Status strip ─────────────────────────────────────────────────

interface StatusStripProps {
  status: 'draft' | 'published' | 'edited' | 'withdrawn' | null;
  publishedAt: string | null;
  editedAt: string | null;
  traineeViewedAt: string | null;
  isDirty: boolean;
  saving: boolean;
  onShowHistory: () => void;
}

function StatusStrip({
  status,
  publishedAt,
  editedAt,
  traineeViewedAt,
  isDirty,
  saving,
  onShowHistory,
}: StatusStripProps) {
  const { t } = useTranslation();
  let dotColor = 'bg-text-color-tertiary';
  let label = t('assessment.status.unsaved');

  if (status === 'draft') {
    dotColor = 'bg-text-color-secondary';
    label = saving
      ? t('assessment.status.saving')
      : isDirty
        ? t('assessment.status.draftDirty')
        : t('assessment.status.draftSaved');
  } else if (status === 'published') {
    dotColor = 'bg-success-text';
    label = t('assessment.status.published', {
      when: publishedAt ? new Date(publishedAt).toLocaleString() : '',
    });
  } else if (status === 'edited') {
    dotColor = 'bg-accent';
    label = t('assessment.status.edited', {
      when: editedAt ? new Date(editedAt).toLocaleString() : '',
    });
  }

  const showHistory = status === 'published' || status === 'edited';
  const showReadReceipt = status === 'published' || status === 'edited';

  return (
    <div className="flex flex-col gap-1 rounded-lg border-[0.5px] border-border-hairline bg-bg-primary px-3 py-2">
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-2 text-caption text-text-color-secondary">
          <span className={`inline-block size-2 rounded-full ${dotColor}`} aria-hidden />
          {label}
        </span>
        {showHistory ? (
          <button
            type="button"
            onClick={onShowHistory}
            className="flex items-center gap-1 text-caption text-accent"
          >
            <History size={14} strokeWidth={1.75} aria-hidden />
            {t('assessment.viewHistory')}
          </button>
        ) : null}
      </div>
      {showReadReceipt ? (
        <span className="text-footnote text-text-color-tertiary">
          {traineeViewedAt
            ? t('assessment.status.traineeViewed', {
                when: new Date(traineeViewedAt).toLocaleString(),
              })
            : t('assessment.status.traineeNotViewed')}
        </span>
      ) : null}
    </div>
  );
}

// ── Toast ────────────────────────────────────────────────────────

function Toast({
  children,
  onDone,
}: {
  children: React.ReactNode;
  onDone: () => void;
}) {
  useEffect(() => {
    const t = window.setTimeout(onDone, 2000);
    return () => window.clearTimeout(t);
  }, [onDone]);
  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 bottom-6 z-30 flex justify-center"
    >
      <div className="rounded-full border-[0.5px] border-border-hairline bg-bg-primary px-4 py-2 text-caption text-text-color-primary">
        {children}
      </div>
    </div>
  );
}
