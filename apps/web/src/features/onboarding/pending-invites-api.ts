// Authenticated trainee's view of incoming invites that were pre-bound to
// them (typically via a phone match at coach-side trainee creation). Drives
// the accept / decline banner on /home.

import { api } from '@/lib/api';
import { claimInviteWithToken } from './invite-claim';
import type { AuthResult } from '@/features/auth/auth-api';

export interface PendingInvite {
  token: string;
  workspaceName: string;
  workspaceLogoUrl: string | null;
  brandColor: string | null;
  coachDisplayName: string | null;
  role: string;
  expiresAt: string; // ISO
}

interface ApiPendingInvite {
  token: string;
  workspace_name: string;
  workspace_logo_url: string | null;
  brand_color: string | null;
  coach_display_name: string | null;
  role: string;
  expires_at: string;
}

interface ApiPendingInvitesList {
  invites: ApiPendingInvite[];
}

function toPending(i: ApiPendingInvite): PendingInvite {
  return {
    token: i.token,
    workspaceName: i.workspace_name,
    workspaceLogoUrl: i.workspace_logo_url,
    brandColor: i.brand_color,
    coachDisplayName: i.coach_display_name,
    role: i.role,
    expiresAt: i.expires_at,
  };
}

export async function listPendingInvites(): Promise<PendingInvite[]> {
  const res = await api.get<ApiPendingInvitesList>('/invites/pending');
  return res.invites.map(toPending);
}

export async function acceptPendingInvite(
  token: string,
  accessToken: string,
): Promise<AuthResult> {
  return claimInviteWithToken(token, accessToken);
}

export async function declinePendingInvite(token: string): Promise<void> {
  await api.post(`/invites/${encodeURIComponent(token)}/decline`, undefined);
}
