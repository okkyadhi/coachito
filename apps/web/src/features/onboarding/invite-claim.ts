// Glue between sign-in callbacks and POST /invites/:token/claim.
//
// The invite token is captured by SignInScreen on entry (from the
// ?invite_token=… query param) and stashed in sessionStorage so it survives
// the magic-link / Google round-trip back to the SPA.  Each auth callback
// (MagicLinkLanding, GoogleCallback) calls `consumePendingInvite()` after a
// successful sign-in — that POSTs the claim, returns a new TokenPair with
// `wsid` + `role=trainee` set, and clears the pending token.

import type { AuthResult } from '@/features/auth/auth-api';
import type { AuthUser, WorkspaceRole } from '@/features/auth/auth-store';

const STORAGE_KEY = 'coachito.pendingInviteToken';

interface ApiUser {
  id: string;
  email: string | null;
  display_name: string;
  preferred_locale: string;
  is_minor: boolean;
  current_workspace_id: string | null;
  role: WorkspaceRole | null;
}

interface ApiTokenPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: ApiUser;
}

export function stashPendingInvite(token: string | null): void {
  if (!token) return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, token);
  } catch {
    /* sessionStorage disabled — silently no-op; user just gets coach signup */
  }
}

export function readPendingInvite(): string | null {
  try {
    return window.sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function clearPendingInvite(): void {
  try {
    window.sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    /* no-op */
  }
}

function toUser(u: ApiUser): AuthUser {
  return {
    id: u.id,
    email: u.email,
    displayName: u.display_name,
    preferredLocale: u.preferred_locale,
    isMinor: u.is_minor,
    isPlatformAdmin: (u as { is_platform_admin?: boolean }).is_platform_admin ?? false,
    role: u.role ?? null,
  };
}

export class InviteClaimError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'InviteClaimError';
  }
}

/**
 * Claim an invite using the supplied access token. Returns the post-claim
 * AuthResult (workspace + role updated). Throws InviteClaimError on HTTP
 * failure so callers can surface a real error to the user — unlike
 * `consumePendingInvite`, which swallows errors as best-effort glue.
 */
export async function claimInviteWithToken(
  inviteToken: string,
  accessToken: string,
): Promise<AuthResult> {
  const res = await fetch(
    `/api/invites/${encodeURIComponent(inviteToken)}/claim`,
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
    },
  );
  if (!res.ok) {
    const text = await res.text();
    throw new InviteClaimError(res.status, text || `HTTP ${res.status}`);
  }
  const pair = (await res.json()) as ApiTokenPair;
  return {
    token: pair.access_token,
    refreshToken: pair.refresh_token,
    user: toUser(pair.user),
    workspaceId: pair.user.current_workspace_id,
  };
}

/**
 * If a pending invite token is stashed, claim it with the just-issued access
 * token and return the post-claim TokenPair (which carries `wsid` and
 * `role`).  Returns the original signed-in `AuthResult` when there's no
 * pending token or the claim fails non-fatally.
 */
export async function consumePendingInvite(
  signedIn: AuthResult,
): Promise<AuthResult> {
  const token = readPendingInvite();
  if (!token) return signedIn;

  // Direct fetch — the api wrapper would read the access token from the
  // store, but the store hasn't been updated yet at the moment we claim.
  try {
    const res = await fetch(`/api/invites/${encodeURIComponent(token)}/claim`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${signedIn.token}` },
    });
    if (!res.ok) {
      console.warn('invite claim failed', res.status, await res.text());
      clearPendingInvite();
      return signedIn;
    }
    const pair = (await res.json()) as ApiTokenPair;
    clearPendingInvite();
    return {
      token: pair.access_token,
      refreshToken: pair.refresh_token,
      user: toUser(pair.user),
      workspaceId: pair.user.current_workspace_id,
    };
  } catch (err) {
    console.warn('invite claim failed', err);
    clearPendingInvite();
    return signedIn;
  }
}
