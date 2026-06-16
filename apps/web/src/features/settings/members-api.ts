// Coach management API client.

import { api } from '@/lib/api';

export type AnyMemberRole = 'club_admin' | 'head_coach' | 'coach';
export type CoachRole = 'coach' | 'head_coach';

export interface CoachMember {
  id: string;
  userId: string;
  email: string | null;
  displayName: string;
  role: AnyMemberRole;
  joinedAt: string | null;
  isOwner: boolean;
  isSelf: boolean;
}

export interface PendingCoachInvite {
  id: string;
  email: string | null;
  role: AnyMemberRole;
  inviteCode: string;
  landingUrl: string;
  expiresAt: string;
  invitedAt: string;
}

export interface MembersList {
  members: CoachMember[];
  pendingInvites: PendingCoachInvite[];
  coachCount: number;
  traineeCount: number;
}

interface ApiMember {
  id: string;
  user_id: string;
  email: string | null;
  display_name: string;
  role: AnyMemberRole;
  joined_at: string | null;
  is_owner: boolean;
  is_self: boolean;
}

interface ApiPending {
  id: string;
  email: string | null;
  role: AnyMemberRole;
  invite_code: string;
  landing_url: string;
  expires_at: string;
  invited_at: string;
}

interface ApiMembersList {
  members: ApiMember[];
  pending_invites: ApiPending[];
  coach_count: number;
  trainee_count: number;
}

function toMember(m: ApiMember): CoachMember {
  return {
    id: m.id,
    userId: m.user_id,
    email: m.email,
    displayName: m.display_name,
    role: m.role,
    joinedAt: m.joined_at,
    isOwner: m.is_owner,
    isSelf: m.is_self,
  };
}

function toPending(p: ApiPending): PendingCoachInvite {
  return {
    id: p.id,
    email: p.email,
    role: p.role,
    inviteCode: p.invite_code,
    landingUrl: p.landing_url,
    expiresAt: p.expires_at,
    invitedAt: p.invited_at,
  };
}

export async function listMembers(): Promise<MembersList> {
  const data = await api.get<ApiMembersList>('/workspaces/me/members');
  return {
    members: data.members.map(toMember),
    pendingInvites: data.pending_invites.map(toPending),
    coachCount: data.coach_count,
    traineeCount: data.trainee_count,
  };
}

export interface InviteCoachInput {
  email: string;
  displayName: string;
  role: CoachRole;
}

export interface InviteCoachResult {
  id: string;
  email: string;
  role: CoachRole;
  inviteCode: string;
  landingUrl: string;
  expiresAt: string;
}

interface ApiInviteResult {
  id: string;
  email: string;
  role: CoachRole;
  invite_code: string;
  landing_url: string;
  expires_at: string;
}

export async function inviteCoach(input: InviteCoachInput): Promise<InviteCoachResult> {
  const r = await api.post<ApiInviteResult>('/workspaces/me/members/invite', {
    email: input.email,
    display_name: input.displayName,
    role: input.role,
  });
  return {
    id: r.id,
    email: r.email,
    role: r.role,
    inviteCode: r.invite_code,
    landingUrl: r.landing_url,
    expiresAt: r.expires_at,
  };
}

export async function updateMemberRole(
  membershipId: string,
  role: CoachRole,
): Promise<CoachMember> {
  const r = await api.patch<ApiMember>(
    `/workspaces/me/members/${membershipId}`,
    { role },
  );
  return toMember(r);
}

export async function removeMember(membershipId: string): Promise<void> {
  await api.del(`/workspaces/me/members/${membershipId}`);
}

export async function revokeInvite(inviteId: string): Promise<void> {
  await api.del(`/workspaces/me/members/invites/${inviteId}`);
}
