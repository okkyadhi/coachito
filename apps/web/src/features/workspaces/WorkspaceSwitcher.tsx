import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Building2, Check, ChevronDown, User } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { type WorkspaceRole, useAuthStore } from '@/features/auth/auth-store';
import { ApiError } from '@/lib/api';

import {
  type WorkspaceMembership,
  listMyWorkspaces,
  switchWorkspace,
} from './workspace-api';

// Pill that shows the active workspace name + a sheet to switch between
// workspaces the user is a member of.  Hidden entirely when there's only
// one membership (most users — only "hybrid" coaches see this in MVP).
export function WorkspaceSwitcher() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const currentId = useAuthStore((s) => s.currentWorkspaceId);
  const doSwitch = useAuthStore((s) => s.switchWorkspace);

  const { data } = useQuery({
    queryKey: ['my-workspaces'],
    queryFn: listMyWorkspaces,
    staleTime: 60_000,
  });

  const [open, setOpen] = useState(false);
  const [switching, setSwitching] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const active = (data ?? []).filter((m) => m.status === 'active');
  const current = active.find((m) => m.workspace.id === currentId);

  // Single-workspace users: show static name, no chevron, no tap target.
  if (active.length <= 1) {
    return (
      <span className="truncate text-body text-text-color-primary">
        {current?.workspace.name ?? t('switcher.fallback')}
      </span>
    );
  }

  const handlePick = async (m: WorkspaceMembership) => {
    if (m.workspace.id === currentId) {
      setOpen(false);
      return;
    }
    setError(null);
    setSwitching(m.workspace.id);
    try {
      const tokens = await switchWorkspace(m.workspace.id);
      doSwitch({
        token: tokens.accessToken,
        refreshToken: tokens.refreshToken,
        workspaceId: tokens.workspaceId,
        role: (m.role as WorkspaceRole) ?? null,
      });
      // Reset all tenant-scoped query caches.
      qc.clear();
      setOpen(false);
      // For trainee/parent, route to /home; for any coach role, /today.
      const dest =
        m.role === 'trainee' || m.role === 'parent' ? '/home' : '/today';
      navigate(dest, { replace: true });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('switcher.error'));
    } finally {
      setSwitching(null);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex max-w-[200px] items-center gap-1 rounded-md px-1 py-0.5 text-body text-text-color-primary hover:bg-bg-secondary"
        aria-label={t('switcher.pillLabel')}
      >
        <span className="truncate">
          {current?.workspace.name ?? t('switcher.fallback')}
        </span>
        <ChevronDown
          size={14}
          strokeWidth={1.75}
          aria-hidden
          className="shrink-0 text-text-color-tertiary"
        />
      </button>

      {open ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={t('switcher.sheetTitle')}
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 sm:items-center"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="flex w-full max-w-md flex-col gap-1 rounded-t-2xl bg-bg-primary p-2 sm:rounded-2xl"
          >
            <h3 className="px-3 py-2 text-section uppercase tracking-wide text-text-color-secondary">
              {t('switcher.sheetTitle')}
            </h3>
            {active.map((m) => (
              <WorkspaceRow
                key={m.workspace.id}
                membership={m}
                isCurrent={m.workspace.id === currentId}
                isSwitching={switching === m.workspace.id}
                onPick={() => void handlePick(m)}
              />
            ))}
            {error ? (
              <p className="px-3 py-2 text-caption text-danger-text">{error}</p>
            ) : null}
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="mt-1 min-h-tap rounded-md py-2 text-center text-body text-text-color-secondary"
            >
              {t('common.cancel')}
            </button>
          </div>
        </div>
      ) : null}
    </>
  );
}

interface WorkspaceRowProps {
  membership: WorkspaceMembership;
  isCurrent: boolean;
  isSwitching: boolean;
  onPick: () => void;
}

function WorkspaceRow({
  membership,
  isCurrent,
  isSwitching,
  onPick,
}: WorkspaceRowProps) {
  const { t } = useTranslation();
  const { workspace, role } = membership;
  const Icon = workspace.type === 'club' ? Building2 : User;
  return (
    <button
      type="button"
      onClick={onPick}
      disabled={isSwitching}
      className="flex min-h-tap items-center gap-3 rounded-md px-3 py-2 text-left hover:bg-bg-secondary disabled:opacity-60"
    >
      <div
        className="flex size-9 items-center justify-center rounded-md text-white"
        style={{ background: workspace.brandColor ?? 'var(--accent)' }}
      >
        <Icon size={16} strokeWidth={1.75} aria-hidden />
      </div>
      <div className="flex flex-1 flex-col">
        <span className="text-body text-text-color-primary">
          {workspace.name}
        </span>
        <span className="text-footnote text-text-color-tertiary">
          {t(`switcher.type.${workspace.type}`)} · {t(`coaches.role.${role}`)}
        </span>
      </div>
      {isSwitching ? (
        <span
          aria-hidden
          className="border-text-color-tertiary/40 inline-block size-4 animate-spin rounded-full border-2 border-t-text-color-tertiary"
        />
      ) : isCurrent ? (
        <Check
          size={16}
          strokeWidth={1.75}
          aria-hidden
          className="text-accent"
        />
      ) : (
        <span className="size-4" aria-hidden />
      )}
    </button>
  );
}
