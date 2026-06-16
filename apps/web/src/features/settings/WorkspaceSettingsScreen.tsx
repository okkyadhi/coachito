import { useQuery } from '@tanstack/react-query';
import { ChevronRight, KeyRound, LogOut, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { InlineSavedToast, type SaveStatus } from '@/components/InlineSavedToast';
import { SecondaryButton } from '@/components/SecondaryButton';
import { useAuthStore } from '@/features/auth/auth-store';

import { BrandingSection } from './BrandingSection';
import { LivePreviewCard } from './LivePreviewCard';
import { PlanBillingCard } from './PlanBillingCard';
import { SportsSection } from './SportsSection';
import { SetPasswordSheet } from './SetPasswordSheet';
import { TiersCurriculumSection } from './TiersCurriculumSection';
import {
  type WorkspacePatch,
  type WorkspaceSettings,
  getMyWorkspace,
  patchMyWorkspace,
} from './settings-api';

const DEBOUNCE_MS = 600;

export function WorkspaceSettingsScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const signOut = useAuthStore((s) => s.signOut);
  const currentWorkspaceId = useAuthStore((s) => s.currentWorkspaceId);
  const role = useAuthStore((s) => s.user?.role ?? null);

  const { data, isPending } = useQuery({
    // Include workspaceId in the key so switching tenants instantly invalidates
    // — no stale "Senayan Padel Club" preview while standing in the personal
    // workspace.
    queryKey: ['workspace-me', currentWorkspaceId],
    queryFn: getMyWorkspace,
    staleTime: 30_000,
  });

  // Local "merged" state — what the user sees + what's currently being typed.
  // We auto-save (debounced) only the diff vs server state.
  const [settings, setSettings] = useState<WorkspaceSettings | null>(null);
  const [status, setStatus] = useState<SaveStatus>('idle');
  const pendingPatchRef = useRef<WorkspacePatch>({});
  const debounceRef = useRef<number | null>(null);
  const latestRef = useRef<WorkspaceSettings | null>(null);

  // Hydrate local state from query.
  useEffect(() => {
    if (data && settings === null) {
      setSettings(data);
      latestRef.current = data;
    }
  }, [data, settings]);

  const flush = useCallback(async () => {
    if (Object.keys(pendingPatchRef.current).length === 0) return;
    const patch = pendingPatchRef.current;
    pendingPatchRef.current = {};
    setStatus('saving');
    try {
      const base = latestRef.current;
      if (!base) return;
      const next = await patchMyWorkspace(base, patch);
      latestRef.current = next;
      setSettings(next);
      setStatus('saved');
    } catch {
      setStatus('failed');
    }
  }, []);

  const queuePatch = useCallback(
    (patch: WorkspacePatch) => {
      pendingPatchRef.current = { ...pendingPatchRef.current, ...patch };
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
      debounceRef.current = window.setTimeout(() => void flush(), DEBOUNCE_MS);
    },
    [flush],
  );

  const handleChange = useCallback(
    (partial: Partial<WorkspaceSettings>) => {
      setSettings((prev) => (prev ? { ...prev, ...partial } : prev));
      const patch: WorkspacePatch = {};
      if (partial.name !== undefined) patch.name = partial.name;
      if (partial.city !== undefined) patch.city = partial.city;
      if (partial.brandColor !== undefined) patch.brand_color = partial.brandColor;
      if (partial.logoUrl !== undefined) patch.logo_url = partial.logoUrl;
      if (partial.tierStyle !== undefined) patch.tier_style = partial.tierStyle;
      if (partial.allowCoachOverrides !== undefined) {
        patch.allow_coach_overrides = partial.allowCoachOverrides;
      }
      if (partial.curriculumId !== undefined) {
        patch.curriculum_id = partial.curriculumId;
      }
      queuePatch(patch);
    },
    [queuePatch],
  );

  const [pwSheetOpen, setPwSheetOpen] = useState(false);
  const [pwHasExisting, setPwHasExisting] = useState(false);
  const [pwToast, setPwToast] = useState(false);

  const handleSignOut = () => {
    signOut();
    navigate('/signin', { replace: true });
  };

  if (isPending || !settings) {
    return <Skeleton />;
  }

  // Inline --accent so the entire scrolled view re-tints to the previewed
  // brand color (matches the design: not just the preview card).
  const rootStyle: React.CSSProperties = settings.brandColor
    ? ({ ['--accent' as never]: settings.brandColor } as React.CSSProperties)
    : {};

  const titleKey =
    settings.type === 'club' ? 'settings.title.club' : 'settings.title.personal';

  // For club workspaces, only the club_admin may mutate branding / tier
  // naming / delete the workspace.  Personal workspaces have a single owner
  // (always the coach), so editing is always allowed there.
  const canEditWorkspace =
    settings.type === 'personal' || role === 'club_admin';

  return (
    <div className="mx-auto w-full max-w-md px-4 pb-8 pt-3" style={rootStyle}>
      {/* Top bar */}
      <header className="mb-4 flex items-center justify-between">
        <h1 className="text-large-title text-text-color-primary">{t(titleKey)}</h1>
        <InlineSavedToast status={status} onRetry={() => void flush()} />
      </header>

      <div className="flex flex-col gap-5">
        <LivePreviewCard settings={settings} />

        <BrandingSection
          settings={settings}
          draft={{}}
          onChange={handleChange}
          readOnly={!canEditWorkspace}
        />

        <TiersCurriculumSection
          settings={settings}
          draft={{}}
          onChange={handleChange}
        />

        <SportsSection readOnly={!canEditWorkspace} />

        <PlanBillingCard settings={settings} />

        {/* Members */}
        <section className="flex flex-col gap-2">
          <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
            {t('settings.members.title')}
          </h3>
          <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
            {settings.type === 'club' ? (
              <MembersRow
                label={t('settings.members.coaches')}
                value={String(settings.coachCount)}
                onClick={() => navigate('/settings/coaches')}
              />
            ) : null}
            <MembersRow
              label={
                settings.type === 'personal'
                  ? t('settings.members.activeTrainees')
                  : t('settings.members.trainees')
              }
              value={String(settings.traineeCount)}
              onClick={() => navigate('/trainees')}
            />
          </div>
        </section>

        {/* Danger zone — admin / personal owner only.  Head coach + coach
            don't see this on a club workspace. */}
        {canEditWorkspace ? (
          <section className="flex flex-col gap-2">
            <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
              {t('settings.danger.title')}
            </h3>
            <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
              <button
                type="button"
                className="flex min-h-tap w-full items-center gap-3 p-3 text-left text-danger-text"
                onClick={() => {
                  /* delete-workspace flow — V1.5 */
                }}
              >
                <Trash2 size={18} strokeWidth={1.75} aria-hidden />
                <span className="flex-1 text-body">
                  {t('settings.danger.delete')}
                </span>
                <ChevronRight size={16} strokeWidth={1.75} aria-hidden />
              </button>
            </div>
          </section>
        ) : null}

        {/* Account */}
        <section className="flex flex-col gap-2">
          <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
            {t('settings.account.title')}
          </h3>
          <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
            <button
              type="button"
              className="flex min-h-tap w-full items-center gap-3 p-3 text-left"
              onClick={() => {
                // The BE doesn't expose whether the user has a password
                // already (PII-minimal), so we let the user say.  If they
                // pick "Change" and they don't actually have one, the
                // request returns 403 and we surface that.
                setPwToast(false);
                setPwSheetOpen(true);
              }}
            >
              <KeyRound size={18} strokeWidth={1.75} aria-hidden className="text-text-color-secondary" />
              <span className="flex-1 text-body text-text-color-primary">
                {pwHasExisting
                  ? t('settings.account.changePassword')
                  : t('settings.account.setPassword')}
              </span>
              <ChevronRight size={16} strokeWidth={1.75} aria-hidden className="text-text-color-tertiary" />
            </button>
          </div>
          {pwToast ? (
            <p className="px-1 text-footnote text-success-text">
              {t('settings.account.passwordSaved')}
            </p>
          ) : null}
        </section>

        <SecondaryButton
          leftIcon={<LogOut size={16} strokeWidth={1.75} aria-hidden />}
          onClick={handleSignOut}
        >
          {t('common.signOut')}
        </SecondaryButton>

        <SetPasswordSheet
          open={pwSheetOpen}
          hasExistingPassword={pwHasExisting}
          onClose={() => setPwSheetOpen(false)}
          onSuccess={() => {
            setPwHasExisting(true);
            setPwSheetOpen(false);
            setPwToast(true);
          }}
        />
      </div>
    </div>
  );
}

interface MembersRowProps {
  label: string;
  value: string;
  onClick?: () => void;
}

function MembersRow({ label, value, onClick }: MembersRowProps) {
  return (
    <button
      type="button"
      disabled={!onClick}
      onClick={onClick}
      className="flex min-h-tap w-full items-center gap-3 border-t-[0.5px] border-border-hairline p-3 text-left first:border-t-0 disabled:cursor-default"
    >
      <span className="flex-1 text-body text-text-color-primary">{label}</span>
      <span className="text-body text-text-color-secondary">{value}</span>
      {onClick ? (
        <ChevronRight
          size={16}
          strokeWidth={1.75}
          className="text-text-color-tertiary"
          aria-hidden
        />
      ) : null}
    </button>
  );
}

function Skeleton() {
  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-4 px-4 pt-6">
      <div className="h-6 w-32 rounded bg-bg-primary" />
      <div className="h-40 rounded-xl bg-bg-primary" />
      <div className="h-32 rounded-xl bg-bg-primary" />
      <div className="h-24 rounded-xl bg-bg-primary" />
    </div>
  );
}
