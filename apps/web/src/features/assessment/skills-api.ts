// GET /skills — returns the platform skill set for the active workspace's
// sport.  Cached via TanStack Query at the screen level.

import { api } from '@/lib/api';

export interface SkillDef {
  id: string;
  code: string;
  category: 'technical' | 'tactical' | 'physical' | 'mental';
  nameEn: string;
  nameId: string;
  displayOrder: number;
}

interface ApiSkill {
  id: string;
  code: string;
  category: SkillDef['category'];
  name_en: string;
  name_id: string;
  display_order: number;
}

interface ApiList {
  skills: ApiSkill[];
}

export async function listSkills(sportId?: string): Promise<SkillDef[]> {
  const qs = sportId ? `?sport_id=${sportId}` : '';
  const res = await api.get<ApiList>(`/skills${qs}`);
  return res.skills.map((s) => ({
    id: s.id,
    code: s.code,
    category: s.category,
    nameEn: s.name_en,
    nameId: s.name_id,
    displayOrder: s.display_order,
  }));
}
