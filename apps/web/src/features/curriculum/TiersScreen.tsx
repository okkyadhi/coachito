// Settings → Tiers.
//
// Top: dropdown to pick naming style (Game / Skill / Custom).
// Below: one row per tier showing the effective name.  Custom style makes
// names editable inline (tap the row to enter edit mode, tap outside to save).

import { useQueryClient } from '@tanstack/react-query';
import { Check, ChevronDown, ChevronLeft, Pencil, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { useAuthStore } from '@/features/auth/auth-store';
import {
  type TierStyle,
  type WorkspaceSettings,
  getMyWorkspace,
  patchMyWorkspace,
} from '@/features/settings/settings-api';

import { SportTabs } from '@/features/sports/SportTabs';

import { useQuery } from '@tanstack/react-query';
import {
  type Tier,
  useCurriculumTiers,
  useRenameTier,
} from './curriculum-api';
import { useCurriculumPermissions } from './use-curriculum-permissions';

const TIER_OPTIONS: TierStyle[] = ['game', 'skill', 'custom'];

export function TiersScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const perms = useCurriculumPermissions();
  const currentWorkspaceId = useAuthStore((s) => s.currentWorkspaceId);

  const settingsQ = useQuery({
    queryKey: ['workspace-me', currentWorkspaceId],
    queryFn: getMyWorkspace,
    staleTime: 30_000,
  });
  const tiersQ = useCurriculumTiers();
  const renameMut = useRenameTier();

  const [styleDraft, setStyleDraft] = useState<TierStyle | null>(null);
  const tierStyle: TierStyle =
    styleDraft ?? settingsQ.data?.tierStyle ?? 'game';

  // Persist the segmented change via PATCH /workspaces/me — same endpoint
  // the inline settings section uses.
  const onPickStyle = async (next: TierStyle) => {
    if (next === tierStyle) return;
    if (!perms.canEdit || !settingsQ.data) return;
    setStyleDraft(next);
    try {
      const updated = await patchMyWorkspace(settingsQ.data, {
        tier_style: next,
      });
      qc.setQueryData<WorkspaceSettings | null>(
        ['workspace-me', currentWorkspaceId],
        updated,
      );
    } catch {
      setStyleDraft(null);
    }
  };

  return (
    <div className="mx-auto w-full max-w-md px-4 pb-8 pt-3">
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
          {t('settings.tiers.title')}
        </h1>
      </header>

      {/* Sport switcher — only visible when workspace has multiple sports */}
      <div className="mb-4">
        <SportTabs />
      </div>

      {/* Naming style */}
      <section className="mb-4 flex flex-col gap-2">
        <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
          {t('settings.tiers.naming')}
        </h3>
        <div className="relative">
          <select
            value={tierStyle}
            disabled={!perms.canEdit}
            onChange={(e) => void onPickStyle(e.target.value as TierStyle)}
            aria-label={t('settings.tiers.naming')}
            className="min-h-tap w-full appearance-none rounded-xl border-[0.5px] border-border-hairline bg-bg-primary px-3 pr-9 text-body text-text-color-primary focus:outline-none focus:ring-1 focus:ring-accent disabled:cursor-not-allowed disabled:opacity-60"
          >
            {TIER_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {t(`settings.tiers.options.${opt}`)}
              </option>
            ))}
          </select>
          <ChevronDown
            size={16}
            strokeWidth={1.75}
            aria-hidden
            className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-text-color-tertiary"
          />
        </div>
        <p className="px-1 text-footnote text-text-color-tertiary">
          {t(`settings.tiers.namingHint.${tierStyle}`)}
        </p>
      </section>

      {/* Tier rows */}
      <section className="flex flex-col gap-2">
        <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
          {t('settings.tiers.list')}
        </h3>
        <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
          {tiersQ.isPending ? (
            <div className="p-3 text-body text-text-color-tertiary">
              {t('common.loading')}
            </div>
          ) : tiersQ.data && tiersQ.data.length > 0 ? (
            tiersQ.data.map((tier) => (
              <TierRow
                key={tier.code}
                tier={tier}
                tierStyle={tierStyle}
                canEdit={perms.canEdit && tierStyle === 'custom'}
                onSave={(patch) => renameMut.mutateAsync({ code: tier.code, patch })}
              />
            ))
          ) : (
            <div className="p-3 text-body text-text-color-tertiary">
              {t('settings.tiers.empty')}
            </div>
          )}
        </div>
        <p className="px-1 text-footnote text-text-color-tertiary">
          {t('settings.tiers.footnote')}
        </p>
      </section>
    </div>
  );
}

// ── Tier row ──────────────────────────────────────────────────────

interface TierRowProps {
  tier: Tier;
  tierStyle: TierStyle;
  canEdit: boolean;
  onSave: (patch: { name_custom_en: string; name_custom_id?: string }) => Promise<unknown>;
}

function TierRow({ tier, tierStyle, canEdit, onSave }: TierRowProps) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const [saving, setSaving] = useState(false);

  // Reset draft when the row enters edit mode.
  useEffect(() => {
    if (editing) {
      setDraft(currentName(tier, 'custom') ?? '');
    }
  }, [editing, tier]);

  const displayName = currentName(tier, tierStyle) ?? defaultName(tier);

  const commit = async () => {
    const trimmed = draft.trim();
    if (trimmed.length === 0) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      await onSave({ name_custom_en: trimmed });
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex min-h-tap items-center gap-3 border-t-[0.5px] border-border-hairline p-3 first:border-t-0">
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="text-footnote text-text-color-tertiary">
          {t('settings.tiers.tierNumber', { n: tier.display_order })}
        </span>
        {editing ? (
          <input
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void commit();
              if (e.key === 'Escape') setEditing(false);
            }}
            disabled={saving}
            maxLength={50}
            className="rounded-sm border-[0.5px] border-accent bg-bg-primary px-2 py-1 text-body text-text-color-primary focus:outline-none"
          />
        ) : (
          <span className="truncate text-body text-text-color-primary">
            {displayName}
          </span>
        )}
      </div>
      {editing ? (
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setEditing(false)}
            className="flex min-h-tap min-w-tap items-center justify-center text-text-color-tertiary"
            aria-label={t('common.cancel')}
          >
            <X size={18} strokeWidth={1.75} aria-hidden />
          </button>
          <button
            type="button"
            onClick={() => void commit()}
            className="flex min-h-tap min-w-tap items-center justify-center text-accent"
            aria-label={t('common.done')}
          >
            <Check size={18} strokeWidth={1.75} aria-hidden />
          </button>
        </div>
      ) : canEdit ? (
        <button
          type="button"
          onClick={() => setEditing(true)}
          className="flex min-h-tap min-w-tap items-center justify-center text-text-color-tertiary"
          aria-label={t('common.edit')}
        >
          <Pencil size={16} strokeWidth={1.75} aria-hidden />
        </button>
      ) : null}
    </div>
  );
}

function currentName(t: Tier, style: TierStyle): string | null {
  switch (style) {
    case 'game':
      return t.name_game_en;
    case 'skill':
      return t.name_skill_en;
    case 'custom':
      return t.name_custom_en;
  }
}

function defaultName(t: Tier): string {
  return t.name_skill_en;
}
