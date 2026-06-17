export interface CertificationEntry {
  issuer: string;
  name: string;
  year: number;
}

export interface CoachBio {
  headline: string | null;
  about: string | null;
  yearsCoaching: number | null;
  certifications: CertificationEntry[];
  languages: string[];
  specialties: string[];
  photoUrl: string | null;
}

export type CoachRole = 'club_admin' | 'head_coach' | 'coach';

export interface CoachListEntry {
  coachId: string;
  displayName: string;
  avatarUrl: string | null;
  headline: string | null;
  role: CoachRole;
  sessionCount: number;
  lastCoachedAt: string | null;
  nextSessionAt: string | null;
}

export interface CoachListWorkspace {
  id: string;
  name: string;
  type: 'club' | 'personal';
  city: string | null;
  logoUrl: string | null;
  brandColor: string | null;
}

export interface CoachListResult {
  workspace: CoachListWorkspace;
  coaches: CoachListEntry[];
}

export interface CoachProfile {
  coachId: string;
  displayName: string;
  avatarUrl: string | null;
  bio: CoachBio;
  memberSince: string;
  coachedTraineesCount: number;
}
