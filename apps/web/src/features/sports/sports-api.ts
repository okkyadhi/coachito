// Multi-sport data layer — workspace sport enablement + the platform catalog.
// Backend: tennis-skill-framework-v0.1 §3.5.

import { api } from '@/lib/api';

export interface WorkspaceSport {
  sportId: string;
  sportCode: string;
  nameEn: string;
  nameId: string;
  curriculumId: string | null;
  curriculumCode: string | null;
  isActive: boolean;
}

export interface PlatformSport {
  sportId: string;
  sportCode: string;
  nameEn: string;
  nameId: string;
}

interface ApiWorkspaceSport {
  sport_id: string;
  sport_code: string;
  name_en: string;
  name_id: string;
  curriculum_id: string | null;
  curriculum_code: string | null;
  is_active: boolean;
}

interface ApiPlatformSport {
  sport_id: string;
  sport_code: string;
  name_en: string;
  name_id: string;
}

function toWorkspaceSport(s: ApiWorkspaceSport): WorkspaceSport {
  return {
    sportId: s.sport_id,
    sportCode: s.sport_code,
    nameEn: s.name_en,
    nameId: s.name_id,
    curriculumId: s.curriculum_id,
    curriculumCode: s.curriculum_code,
    isActive: s.is_active,
  };
}

export async function listWorkspaceSports(): Promise<WorkspaceSport[]> {
  const res = await api.get<{ sports: ApiWorkspaceSport[] }>(
    '/workspaces/me/sports',
  );
  return res.sports.map(toWorkspaceSport);
}

export async function listPlatformSports(): Promise<PlatformSport[]> {
  const res = await api.get<{ sports: ApiPlatformSport[] }>('/sports');
  return res.sports.map((s) => ({
    sportId: s.sport_id,
    sportCode: s.sport_code,
    nameEn: s.name_en,
    nameId: s.name_id,
  }));
}

export async function enableSport(sportId: string): Promise<WorkspaceSport[]> {
  const res = await api.post<{ sports: ApiWorkspaceSport[] }>(
    '/workspaces/me/sports',
    { sport_id: sportId },
  );
  return res.sports.map(toWorkspaceSport);
}

export async function archiveSport(sportId: string): Promise<WorkspaceSport[]> {
  const res = await api.del<{ sports: ApiWorkspaceSport[] }>(
    `/workspaces/me/sports/${sportId}`,
  );
  return res.sports.map(toWorkspaceSport);
}

/** Localised sport name for the active UI locale. */
export function sportLabel(
  s: { nameEn: string; nameId: string },
  locale: string,
): string {
  return locale === 'en' ? s.nameEn : s.nameId;
}
