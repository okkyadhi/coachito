import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Clock,
  Copy,
  MoreHorizontal,
  Plus,
  Shield,
  Trash2,
  UserPlus,
} from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { ConfirmSheet } from '@/components/ConfirmSheet';
import { useAuthStore } from '@/features/auth/auth-store';
import { ApiError } from '@/lib/api';

import { InviteCoachSheet } from './InviteCoachSheet';
import {
  type AnyMemberRole,
  type CoachMember,
  type CoachRole,
  type PendingCoachInvite,
  listMembers,
  removeMember,
  revokeInvite,
  updateMemberRole,
} from './members-api';

export function CoachesScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const myRole = useAuthStore((s) => s.user?.role ?? null);
  const currentWorkspaceId = useAuthStore((s) => s.currentWorkspaceId);
  const canManage = myRole === 'club_admin';

  const { data, isPending, isError } = useQuery({
    queryKey: ['workspace-members', currentWorkspaceId],
    queryFn: listMembers,
  });

  const [inviteOpen, setInviteOpen] = useState(false);
  const [menuFor, setMenuFor] = useState<CoachMember | null>(null);
  const [confirmRemove, setConfirmRemove] = useState<CoachMember | null>(null);
  const [confirmRevoke, setConfirmRevoke] = useState<PendingCoachInvite | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ['workspace-members', currentWorkspaceId] });
    // The settings screen reads counts from the same endpoint — bump its
    // cache too so the Live Preview / Members row reflect immediately.
    void qc.invalidateQueries({ queryKey: ['workspace-me', currentWorkspaceId] });
  };

  const promoteMutation = useMutation({
    mutationFn: ({ id, role }: { id: string; role: CoachRole }) =>
      updateMemberRole(id, role),
    onSuccess: invalidate,
    onError: (e) =>
      setActionError(
        e instanceof ApiError ? e.message : t('coaches.actions.genericError'),
      ),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => removeMember(id),
    onSuccess: invalidate,
    onError: (e) =>
      setActionError(
        e instanceof ApiError ? e.message : t('coaches.actions.genericError'),
      ),
  });

  const revokeMutation = useMutation({
    mutationFn: (id: string) => revokeInvite(id),
    onSuccess: invalidate,
    onError: (e) =>
      setActionError(
        e instanceof ApiError ? e.message : t('coaches.actions.genericError'),
      ),
  });

  if (isPending) {
    return (
      <div className="mx-auto flex w-full max-w-md flex-col gap-4 px-4 pt-6">
        <div className="h-6 w-32 rounded bg-bg-primary" />
        <div className="h-40 rounded-xl bg-bg-primary" />
      </div>
    );
  }
  if (isError || !data) {
    return (
      <div className="mx-auto w-full max-w-md px-4 pt-6">
        <p className="text-body text-danger-text">{t('coaches.loadError')}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-md px-4 pb-8 pt-3">
      <header className="mb-4 flex items-center justify-between">
        <button
          type="button"
          onClick={() => navigate('/settings')}
          className="flex size-9 items-center justify-center rounded-full text-text-color-secondary"
          aria-label={t('common.back')}
        >
          <ArrowLeft size={18} strokeWidth={1.75} aria-hidden />
        </button>
        <h1 className="text-h3 text-text-color-primary">{t('coaches.title')}</h1>
        <span className="size-9" aria-hidden />
      </header>

      {actionError ? (
        <div className="mb-3 rounded-md border-[0.5px] border-danger-text bg-danger-bg p-3">
          <p className="text-caption text-danger-text">{actionError}</p>
        </div>
      ) : null}

      <div className="flex flex-col gap-5">
        {/* Active members */}
        <section className="flex flex-col gap-2">
          <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
            {t('coaches.active.title', { count: data.members.length })}
          </h3>
          <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
            {data.members.map((m) => (
              <CoachRow
                key={m.id}
                member={m}
                canManage={canManage}
                onMenu={() => setMenuFor(m)}
              />
            ))}
          </div>
        </section>

        {/* Pending invites */}
        {data.pendingInvites.length > 0 ? (
          <section className="flex flex-col gap-2">
            <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
              {t('coaches.pending.title', { count: data.pendingInvites.length })}
            </h3>
            <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
              {data.pendingInvites.map((inv) => (
                <PendingRow
                  key={inv.id}
                  invite={inv}
                  canManage={canManage}
                  onRevoke={() => setConfirmRevoke(inv)}
                />
              ))}
            </div>
          </section>
        ) : null}

        {/* Invite CTA */}
        {canManage ? (
          <button
            type="button"
            onClick={() => setInviteOpen(true)}
            className="flex min-h-tap w-full items-center justify-center gap-2 rounded-md bg-accent px-4 py-2.5 text-[14px] font-medium text-white"
          >
            <UserPlus size={16} strokeWidth={1.75} aria-hidden />
            {t('coaches.inviteCta')}
          </button>
        ) : (
          <p className="px-1 text-footnote text-text-color-tertiary">
            {t('coaches.readOnlyHint')}
          </p>
        )}
      </div>

      <InviteCoachSheet
        open={inviteOpen}
        onClose={() => setInviteOpen(false)}
        onInvited={() => invalidate()}
      />

      {/* Member row action menu */}
      {menuFor ? (
        <MemberActionsSheet
          member={menuFor}
          onClose={() => setMenuFor(null)}
          onPromote={(role) => {
            promoteMutation.mutate({ id: menuFor.id, role });
            setMenuFor(null);
          }}
          onRemove={() => {
            setConfirmRemove(menuFor);
            setMenuFor(null);
          }}
        />
      ) : null}

      {confirmRemove ? (
        <ConfirmSheet
          open={true}
          title={t('coaches.remove.title')}
          description={t('coaches.remove.body', { name: confirmRemove.displayName })}
          confirmLabel={t('coaches.remove.confirmCta')}
          destructive
          onCancel={() => setConfirmRemove(null)}
          onConfirm={() => {
            removeMutation.mutate(confirmRemove.id);
            setConfirmRemove(null);
          }}
        />
      ) : null}

      {confirmRevoke ? (
        <ConfirmSheet
          open={true}
          title={t('coaches.revoke.title')}
          description={t('coaches.revoke.body', {
            email: confirmRevoke.email ?? '—',
          })}
          confirmLabel={t('coaches.revoke.confirmCta')}
          destructive
          onCancel={() => setConfirmRevoke(null)}
          onConfirm={() => {
            revokeMutation.mutate(confirmRevoke.id);
            setConfirmRevoke(null);
          }}
        />
      ) : null}
    </div>
  );
}

// ── Row components ────────────────────────────────────────────────

interface CoachRowProps {
  member: CoachMember;
  canManage: boolean;
  onMenu: () => void;
}

function CoachRow({ member, canManage, onMenu }: CoachRowProps) {
  const { t } = useTranslation();
  const showActions = canManage && !member.isOwner && !member.isSelf;
  return (
    <div className="flex min-h-tap items-center gap-3 border-t-[0.5px] border-border-hairline p-3 first:border-t-0">
      <RoleBadge role={member.role} />
      <div className="flex flex-1 flex-col">
        <span className="text-body text-text-color-primary">
          {member.displayName}
          {member.isSelf ? (
            <span className="ml-1 text-footnote text-text-color-tertiary">
              · {t('coaches.you')}
            </span>
          ) : null}
        </span>
        {member.email ? (
          <span className="text-footnote text-text-color-tertiary">
            {member.email}
          </span>
        ) : null}
      </div>
      <span className="text-footnote text-text-color-secondary">
        {t(`coaches.role.${member.role}`)}
      </span>
      {showActions ? (
        <button
          type="button"
          onClick={onMenu}
          aria-label={t('coaches.menu.label', { name: member.displayName })}
          className="flex size-9 items-center justify-center rounded-full text-text-color-secondary"
        >
          <MoreHorizontal size={18} strokeWidth={1.75} aria-hidden />
        </button>
      ) : (
        <span className="size-9" aria-hidden />
      )}
    </div>
  );
}

interface PendingRowProps {
  invite: PendingCoachInvite;
  canManage: boolean;
  onRevoke: () => void;
}

function PendingRow({ invite, canManage, onRevoke }: PendingRowProps) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(invite.landingUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable */
    }
  };
  return (
    <div className="flex min-h-tap items-center gap-3 border-t-[0.5px] border-border-hairline p-3 first:border-t-0">
      <div className="flex size-9 items-center justify-center rounded-full bg-bg-secondary">
        <Clock size={16} strokeWidth={1.75} aria-hidden className="text-text-color-tertiary" />
      </div>
      <div className="flex flex-1 flex-col">
        <span className="text-body text-text-color-primary">
          {invite.email ?? '—'}
        </span>
        <span className="text-footnote text-text-color-tertiary">
          {t(`coaches.role.${invite.role}`)} · {t('coaches.pending.label')}
        </span>
      </div>
      <button
        type="button"
        onClick={handleCopy}
        aria-label={t('coaches.pending.copyLabel')}
        className="flex size-9 items-center justify-center rounded-full text-text-color-secondary"
      >
        <Copy
          size={16}
          strokeWidth={1.75}
          aria-hidden
          className={copied ? 'text-success-text' : ''}
        />
      </button>
      {canManage ? (
        <button
          type="button"
          onClick={onRevoke}
          aria-label={t('coaches.pending.revokeLabel')}
          className="flex size-9 items-center justify-center rounded-full text-danger-text"
        >
          <Trash2 size={16} strokeWidth={1.75} aria-hidden />
        </button>
      ) : (
        <span className="size-9" aria-hidden />
      )}
    </div>
  );
}

function RoleBadge({ role }: { role: AnyMemberRole }) {
  return (
    <div
      className={
        role === 'club_admin'
          ? 'bg-accent/10 flex size-9 items-center justify-center rounded-full text-accent'
          : role === 'head_coach'
            ? 'flex size-9 items-center justify-center rounded-full bg-bg-secondary text-text-color-primary'
            : 'flex size-9 items-center justify-center rounded-full bg-bg-secondary text-text-color-tertiary'
      }
    >
      <Shield size={16} strokeWidth={1.75} aria-hidden />
    </div>
  );
}

// ── Member actions bottom sheet ───────────────────────────────────

interface MemberActionsSheetProps {
  member: CoachMember;
  onClose: () => void;
  onPromote: (role: CoachRole) => void;
  onRemove: () => void;
}

function MemberActionsSheet({
  member,
  onClose,
  onPromote,
  onRemove,
}: MemberActionsSheetProps) {
  const { t } = useTranslation();
  // Only coach ↔ head_coach toggle.  club_admin is owner-locked.
  const canToggle = member.role === 'coach' || member.role === 'head_coach';
  const targetRole: CoachRole = member.role === 'coach' ? 'head_coach' : 'coach';
  return (
    <div
      role="dialog"
      aria-modal="true"
      onClick={onClose}
      className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 sm:items-center"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex w-full max-w-md flex-col gap-1 rounded-t-2xl bg-bg-primary p-2 sm:rounded-2xl"
      >
        <div className="px-3 py-2">
          <p className="text-body text-text-color-primary">{member.displayName}</p>
          {member.email ? (
            <p className="text-footnote text-text-color-tertiary">{member.email}</p>
          ) : null}
        </div>
        {canToggle ? (
          <button
            type="button"
            onClick={() => onPromote(targetRole)}
            className="flex min-h-tap items-center gap-3 rounded-md px-3 py-2 text-left text-body text-text-color-primary hover:bg-bg-secondary"
          >
            <Plus size={16} strokeWidth={1.75} aria-hidden />
            {targetRole === 'head_coach'
              ? t('coaches.menu.promoteHead')
              : t('coaches.menu.demoteCoach')}
          </button>
        ) : null}
        <button
          type="button"
          onClick={onRemove}
          className="flex min-h-tap items-center gap-3 rounded-md px-3 py-2 text-left text-body text-danger-text hover:bg-danger-bg"
        >
          <Trash2 size={16} strokeWidth={1.75} aria-hidden />
          {t('coaches.menu.remove')}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="mt-1 min-h-tap rounded-md py-2 text-center text-body text-text-color-secondary"
        >
          {t('common.cancel')}
        </button>
      </div>
    </div>
  );
}
