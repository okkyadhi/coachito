// Single source of truth for the 4 skill categories: code ↔ slug ↔ label ↔
// accent. Reference everywhere — don't re-derive in components.

export type CategoryCode = 'technical' | 'tactical' | 'physical' | 'mental';

export interface CategoryMeta {
  code: CategoryCode;
  slug: CategoryCode;
  labelEn: string;
  labelId: string;
  /** Short letter chip for the legend. */
  chip: 'T' | 'C' | 'P' | 'M';
  /** Hue used for the radar polygon when rendered per-category. */
  accent: string;
}

// Category accents are picked to (a) stay distinct from each other and
// (b) coexist with the Coachito clay (#C66B47) accent without clashing.
// Earth-toned palette: slate-blue (sky over clay), forest (court
// surroundings), ochre (sand), plum.  Avoid clay itself — that's the
// primary brand accent and would muddle category vs primary meaning.
export const CATEGORY_META: Record<CategoryCode, CategoryMeta> = {
  technical: {
    code: 'technical',
    slug: 'technical',
    labelEn: 'Technical',
    labelId: 'Teknik',
    chip: 'T',
    accent: '#4A6C82',
  },
  tactical: {
    code: 'tactical',
    slug: 'tactical',
    labelEn: 'Tactical',
    labelId: 'Taktik',
    chip: 'C',
    accent: '#2F7D5A',
  },
  physical: {
    code: 'physical',
    slug: 'physical',
    labelEn: 'Physical',
    labelId: 'Fisik',
    chip: 'P',
    accent: '#B58C4A',
  },
  mental: {
    code: 'mental',
    slug: 'mental',
    labelEn: 'Mental',
    labelId: 'Mental',
    chip: 'M',
    accent: '#6E4A8A',
  },
};

export const CATEGORY_ORDER: CategoryCode[] = [
  'technical',
  'tactical',
  'physical',
  'mental',
];

export function isCategoryCode(s: string | undefined): s is CategoryCode {
  return s === 'technical' || s === 'tactical' || s === 'physical' || s === 'mental';
}

export function categoryLabel(code: CategoryCode, locale: string): string {
  return locale === 'id' ? CATEGORY_META[code].labelId : CATEGORY_META[code].labelEn;
}
