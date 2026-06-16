import { api } from '@/lib/api';

import type {
  CoachBio,
  CoachListEntry,
  CoachProfile,
} from './coach-types';

interface ApiBio {
  headline: string | null;
  about: string | null;
  years_coaching: number | null;
  certifications: { issuer: string; name: string; year: number }[];
  languages: string[];
  specialties: string[];
  photo_url: string | null;
}

interface ApiListEntry {
  coach_id: string;
  display_name: string;
  avatar_url: string | null;
  headline: string | null;
  session_count: number;
  last_coached_at: string | null;
  next_session_at: string | null;
}

interface ApiList {
  coaches: ApiListEntry[];
}

interface ApiBioOut {
  coach_id: string;
  display_name: string;
  avatar_url: string | null;
  bio: ApiBio;
  member_since: string;
  coached_trainees_count: number;
}

function fromBio(b: ApiBio): CoachBio {
  return {
    headline: b.headline,
    about: b.about,
    yearsCoaching: b.years_coaching,
    certifications: b.certifications ?? [],
    languages: b.languages ?? [],
    specialties: b.specialties ?? [],
    photoUrl: b.photo_url,
  };
}

export async function fetchMyCoaches(): Promise<CoachListEntry[]> {
  const r = await api.get<ApiList>('/trainees/me/coaches');
  return r.coaches.map((c) => ({
    coachId: c.coach_id,
    displayName: c.display_name,
    avatarUrl: c.avatar_url,
    headline: c.headline,
    sessionCount: c.session_count,
    lastCoachedAt: c.last_coached_at,
    nextSessionAt: c.next_session_at,
  }));
}

export async function fetchCoachProfile(coachId: string): Promise<CoachProfile> {
  const r = await api.get<ApiBioOut>(`/coaches/${coachId}`);
  return {
    coachId: r.coach_id,
    displayName: r.display_name,
    avatarUrl: r.avatar_url,
    bio: fromBio(r.bio),
    memberSince: r.member_since,
    coachedTraineesCount: r.coached_trainees_count,
  };
}
