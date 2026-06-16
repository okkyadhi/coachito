// Real auth API. Calls /api/auth/* via the apiClient.
import { api } from '@/lib/api';

import type { AuthUser, WorkspaceRole } from './auth-store';

interface ApiUser {
  id: string;
  email: string | null;
  display_name: string;
  preferred_locale: string;
  is_minor: boolean;
  is_platform_admin: boolean;
  current_workspace_id: string | null;
  role: WorkspaceRole | null;
}

interface ApiTokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: ApiUser;
}

export interface AuthResult {
  token: string;
  refreshToken: string;
  user: AuthUser;
  workspaceId: string | null;
}

function toUser(u: ApiUser): AuthUser {
  return {
    id: u.id,
    email: u.email,
    displayName: u.display_name,
    preferredLocale: u.preferred_locale,
    isMinor: u.is_minor,
    isPlatformAdmin: u.is_platform_admin ?? false,
    role: u.role ?? null,
  };
}

function toAuthResult(pair: ApiTokenPair): AuthResult {
  return {
    token: pair.access_token,
    refreshToken: pair.refresh_token,
    user: toUser(pair.user),
    workspaceId: pair.user.current_workspace_id,
  };
}

export async function signInWithGoogle(idToken: string): Promise<AuthResult> {
  const pair = await api.post<ApiTokenPair>(
    '/auth/google',
    { id_token: idToken },
    { authenticated: false },
  );
  return toAuthResult(pair);
}

export async function sendMagicLink(email: string): Promise<{ email: string }> {
  await api.post<{ status: string }>('/auth/magic/request', { email }, { authenticated: false });
  return { email };
}

export async function consumeMagicLink(token: string): Promise<AuthResult> {
  const pair = await api.get<ApiTokenPair>(
    `/auth/magic/consume?token=${encodeURIComponent(token)}`,
    { authenticated: false },
  );
  return toAuthResult(pair);
}

export async function refreshTokens(): Promise<AuthResult> {
  const pair = await api.post<ApiTokenPair>('/auth/refresh', undefined, {
    useRefreshToken: true,
  });
  return toAuthResult(pair);
}

// ── Password ─────────────────────────────────────────────────────

export async function signInWithPassword(
  email: string,
  password: string,
): Promise<AuthResult> {
  const pair = await api.post<ApiTokenPair>(
    '/auth/password/login',
    { email, password },
    { authenticated: false },
  );
  return toAuthResult(pair);
}

export async function setPassword(args: {
  currentPassword: string | null;
  newPassword: string;
}): Promise<void> {
  await api.post('/auth/password/set', {
    current_password: args.currentPassword,
    new_password: args.newPassword,
  });
}

// ── Self-signup ──────────────────────────────────────────────────

export type SportCode = 'padel' | 'tennis';

export interface SignUpCoachInput {
  displayName: string;
  email: string;
  password: string;
  sportCode: SportCode;
  phoneE164?: string | null;
}

export interface SignUpClubInput {
  displayName: string;
  email: string;
  password: string;
  clubName: string;
  city: string | null;
  sportCodes: SportCode[];
  phoneE164?: string | null;
}

export interface SignUpResult extends AuthResult {
  redirectTo: string;
}

interface ApiSignupOut extends ApiTokenPair {
  redirect_to: string;
}

function toSignUpResult(pair: ApiSignupOut): SignUpResult {
  return { ...toAuthResult(pair), redirectTo: pair.redirect_to };
}

export async function signUpCoach(input: SignUpCoachInput): Promise<SignUpResult> {
  const pair = await api.post<ApiSignupOut>(
    '/auth/signup/coach',
    {
      display_name: input.displayName,
      email: input.email,
      password: input.password,
      sport_code: input.sportCode,
      phone_e164: input.phoneE164 ?? null,
    },
    { authenticated: false },
  );
  return toSignUpResult(pair);
}

// ── Forgot / reset password ──────────────────────────────────────

export async function requestPasswordReset(email: string): Promise<{ email: string }> {
  await api.post<{ status: string }>(
    '/auth/password/forgot',
    { email },
    { authenticated: false },
  );
  return { email };
}

export async function resetPassword(
  token: string,
  newPassword: string,
): Promise<AuthResult> {
  const pair = await api.post<ApiTokenPair>(
    '/auth/password/reset',
    { token, new_password: newPassword },
    { authenticated: false },
  );
  return toAuthResult(pair);
}

export interface SignUpTraineeInput {
  token: string;
  displayName: string;
  email: string;
  password: string;
}

export async function signUpTraineeViaInvite(
  input: SignUpTraineeInput,
): Promise<AuthResult> {
  const pair = await api.post<ApiTokenPair>(
    `/invites/${encodeURIComponent(input.token)}/signup`,
    {
      display_name: input.displayName,
      email: input.email,
      password: input.password,
    },
    { authenticated: false },
  );
  return toAuthResult(pair);
}

export async function signUpClub(input: SignUpClubInput): Promise<SignUpResult> {
  const pair = await api.post<ApiSignupOut>(
    '/auth/signup/club',
    {
      display_name: input.displayName,
      email: input.email,
      password: input.password,
      club_name: input.clubName,
      city: input.city,
      sport_codes: input.sportCodes,
      phone_e164: input.phoneE164 ?? null,
    },
    { authenticated: false },
  );
  return toSignUpResult(pair);
}
