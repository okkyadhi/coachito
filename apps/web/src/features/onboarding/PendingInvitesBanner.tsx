import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Mail } from 'lucide-react';

import { useAuthStore } from '@/features/auth/auth-store';
import { Avatar } from '@/components/Avatar';
import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';

import {
  acceptPendingInvite,
  declinePendingInvite,
  listPendingInvites,
  type PendingInvite,
} from './pending-invites-api';

// Banner rendered on screens where the user might be greeted by an incoming
// invite (e.g. Trainee Home, Coach Today). Polls every 60s — invites are
// pre-bound to the user via phone match, so they appear without any action
// from the trainee side.
export function PendingInvitesBanner() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((s) => s.token);
  const [pendingToken, setPendingToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [acceptedName, setAcceptedName] = useState<string | null>(null);

  const { data } = useQuery({
    queryKey: ['pendingInvites'],
    queryFn: listPendingInvites,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  const invites = data ?? [];

  const handleAccept = async (invite: PendingInvite) => {
    if (!accessToken) return;
    setError(null);
    setPendingToken(invite.token);
    try {
      // Claim the invite — the BE returns a new TokenPair with wsid set to
      // the joined workspace, but we deliberately DO NOT call signIn() with
      // it. Switching workspace context would yank the trainee out of the
      // workspace they're currently viewing (where their assessments live)
      // into the brand-new one (which has nothing yet). The user can switch
      // via the workspace switcher when they actually want to look.
      await acceptPendingInvite(invite.token, accessToken);
      setAcceptedName(invite.workspaceName);
      await queryClient.invalidateQueries({ queryKey: ['pendingInvites'] });
      // Memberships list drives the switcher — refresh it so the new
      // workspace appears as an option.
      await queryClient.invalidateQueries({ queryKey: ['my-workspaces'] });
    } catch {
      setError(t('pendingInvites.acceptError'));
    } finally {
      setPendingToken(null);
    }
  };

  const handleDecline = async (invite: PendingInvite) => {
    setError(null);
    setPendingToken(invite.token);
    try {
      await declinePendingInvite(invite.token);
      await queryClient.invalidateQueries({ queryKey: ['pendingInvites'] });
    } catch {
      setError(t('pendingInvites.declineError'));
    } finally {
      setPendingToken(null);
    }
  };

  if (invites.length === 0 && !acceptedName) return null;

  if (acceptedName && invites.length === 0) {
    return (
      <section
        aria-live="polite"
        className="flex items-start gap-3 rounded-xl border-[0.5px] border-success-text bg-success-bg p-4"
      >
        <Mail size={16} strokeWidth={1.5} className="mt-0.5 text-success-text" aria-hidden />
        <div className="flex-1">
          <p className="text-body text-text-color-primary">
            {t('pendingInvites.acceptedToast', { workspace: acceptedName })}
          </p>
          <p className="mt-1 text-caption text-text-color-secondary">
            {t('pendingInvites.switcherHint')}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setAcceptedName(null)}
          className="min-h-tap text-caption text-accent"
        >
          {t('common.done')}
        </button>
      </section>
    );
  }

  return (
    <section
      aria-label={t('pendingInvites.title')}
      className="flex flex-col gap-3 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4"
    >
      <div className="flex items-center gap-2">
        <Mail size={16} strokeWidth={1.5} className="text-accent" aria-hidden />
        <h2 className="text-caption font-medium text-text-color-secondary">
          {t('pendingInvites.title')}
        </h2>
      </div>
      <p className="text-caption text-text-color-tertiary">
        {t('pendingInvites.subtitle', { count: invites.length })}
      </p>

      {error ? (
        <div role="alert" className="rounded-md border-[0.5px] border-danger-text bg-danger-bg p-2">
          <p className="text-caption text-danger-text">{error}</p>
        </div>
      ) : null}

      <ul className="flex flex-col gap-3">
        {invites.map((invite) => {
          const busy = pendingToken === invite.token;
          return (
            <li
              key={invite.token}
              className="flex flex-col gap-3 rounded-lg border-[0.5px] border-border-hairline bg-bg-secondary p-3"
            >
              <div className="flex items-start gap-3">
                <Avatar name={invite.workspaceName} size={40} />
                <div className="flex-1">
                  <p className="text-body font-medium text-text-color-primary">
                    {invite.workspaceName}
                  </p>
                  {invite.coachDisplayName ? (
                    <p className="text-caption text-text-color-secondary">
                      {t('pendingInvites.inviteFrom', { coach: invite.coachDisplayName })}
                    </p>
                  ) : null}
                  <p className="mt-0.5 text-footnote text-text-color-tertiary">
                    {t('pendingInvites.asTrainee')}
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                <PrimaryButton
                  type="button"
                  onClick={() => void handleAccept(invite)}
                  loading={busy}
                  disabled={busy}
                  className="flex-1"
                >
                  {t('pendingInvites.accept')}
                </PrimaryButton>
                <SecondaryButton
                  type="button"
                  onClick={() => void handleDecline(invite)}
                  disabled={busy}
                  className="flex-1"
                >
                  {t('pendingInvites.decline')}
                </SecondaryButton>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
