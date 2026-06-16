// Trainees API — all endpoints are real BE calls (no mocks).

import { api } from '@/lib/api';

import type { TierCode } from '@/components/TierPill';

export interface TraineeTier {
  id: string;
  code: TierCode;
  nameGameEn: string;
  nameGameId: string;
}

export interface Trainee {
  id: string;
  displayName: string;
  isMinor: boolean;
  joinedAt: string; // ISO date
  lastAssessedAt: string | null;
  currentTier: TraineeTier | null;
}

export interface TraineesListResult {
  trainees: Trainee[];
  nextCursor: string | null;
}

// ── Wire shapes ─────────────────────────────────────────────────

interface ApiTier {
  id: string;
  code: TierCode;
  name_game_en: string;
  name_game_id: string;
}

interface ApiAthlete {
  id: string;
  display_name: string;
  is_minor: boolean;
  joined_at: string;
  last_assessed_at: string | null;
  current_tier: ApiTier | null;
}

interface ApiAthletesList {
  athletes: ApiAthlete[];
  next_cursor: string | null;
}

function toTrainee(a: ApiAthlete): Trainee {
  return {
    id: a.id,
    displayName: a.display_name,
    isMinor: a.is_minor,
    joinedAt: a.joined_at,
    lastAssessedAt: a.last_assessed_at,
    currentTier: a.current_tier
      ? {
          id: a.current_tier.id,
          code: a.current_tier.code,
          nameGameEn: a.current_tier.name_game_en,
          nameGameId: a.current_tier.name_game_id,
        }
      : null,
  };
}

export async function listTrainees(params: {
  q?: string;
  limit?: number;
  cursor?: string;
} = {}): Promise<TraineesListResult> {
  const search = new URLSearchParams();
  if (params.q) search.set('q', params.q);
  if (params.limit != null) search.set('limit', String(params.limit));
  if (params.cursor) search.set('cursor', params.cursor);
  const qs = search.toString();
  const path = qs ? `/trainees?${qs}` : '/trainees';
  const res = await api.get<ApiAthletesList>(path);
  return {
    trainees: res.athletes.map(toTrainee),
    nextCursor: res.next_cursor,
  };
}

// ── createTrainee (real BE call) ────────────────────────────────

export interface CreateTraineeInput {
  name: string;
  phone: string;
  dateOfBirth: string | null;
  parentPhone: string | null;
}

export interface LinkedUser {
  id: string;
  email: string | null;
  displayName: string;
}

export interface CreatedTrainee {
  trainee: {
    id: string;
    displayName: string;
    phone: string;
    parentPhone: string | null;
  };
  invite: {
    code: string;
    expiresAt: string;
    landingUrl: string;
  };
  // Populated when the phone matched a prior claim — coach FE skips wa.me
  // and shows "Linked to {linkedUser.email}" instead. The trainee gets the
  // invite as a pending banner on next app open.
  linkedUser: LinkedUser | null;
}

interface ApiInvite {
  id: string;
  code: string;
  phone_e164: string | null;
  expires_at: string;
  landing_url: string;
}

interface ApiLinkedUser {
  id: string;
  email: string | null;
  display_name: string;
}

interface ApiCreateOut {
  trainee: ApiAthlete;
  invite: ApiInvite;
  linked_user: ApiLinkedUser | null;
}

export async function createTrainee(
  input: CreateTraineeInput,
): Promise<CreatedTrainee> {
  const res = await api.post<ApiCreateOut>('/trainees', {
    name: input.name,
    phone_e164: input.phone,
    ...(input.dateOfBirth ? { date_of_birth: input.dateOfBirth } : {}),
    ...(input.parentPhone ? { parent_phone_e164: input.parentPhone } : {}),
  });

  return {
    trainee: {
      id: res.trainee.id,
      displayName: res.trainee.display_name,
      phone: res.invite.phone_e164 ?? input.phone,
      parentPhone: input.parentPhone,
    },
    invite: {
      code: res.invite.code,
      expiresAt: res.invite.expires_at,
      landingUrl: res.invite.landing_url,
    },
    linkedUser: res.linked_user
      ? {
          id: res.linked_user.id,
          email: res.linked_user.email,
          displayName: res.linked_user.display_name,
        }
      : null,
  };
}
