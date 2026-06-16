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

export interface CoachListEntry {
  coachId: string;
  displayName: string;
  avatarUrl: string | null;
  headline: string | null;
  sessionCount: number;
  lastCoachedAt: string | null;
  nextSessionAt: string | null;
}

export interface CoachProfile {
  coachId: string;
  displayName: string;
  avatarUrl: string | null;
  bio: CoachBio;
  memberSince: string;
  coachedTraineesCount: number;
}
