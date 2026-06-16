---
name: Skill + tier names stay English in both locales
description: Product decision — never translate skill or tier names to Indonesian, even in the ID locale
type: feedback
---

**Skill names and tier names are NOT translated to Indonesian.** They render in English in both `en` and `id` locales.

**Why:** Brand-consistent labels read like proper nouns to users — translating "Bronze" → "Perunggu" or "Forehand Volley" → "Voli Forehand" makes the product feel like it's translating concepts the user already knows in English. The padel community in Indonesia uses these terms in English / Spanish anyway (bandeja, víbora, smash, drop shot). Confirmed by the user after I shipped Indonesian translations in steps 5–9.

**How to apply:**

- Tier pills (`TierPill.tsx`) → `t('tiers.{CODE}')` reads from the locale files. Both `en.json` and `id.json` `tiers.*` values must be the same English strings ("Beginner", "Lower Bronze", "Bronze", "Silver", "Gold", "Platinum", "Diamond").
- Tier names from the BE `TierBrief` shape → always read `nameGameEn` (or `nameSkillEn`). Never branch on `locale`. The `nameGameId` / `nameSkillId` fields exist in the schema but currently mirror EN.
- Skill names from `SkillBrief` / `Skill` → always read `nameEn`. Same story: `nameId` exists in the schema for forward-compat but mirrors EN.
- The seed data files [data/skills_padel.json](apps/api/data/skills_padel.json) and [data/tiers.json](apps/api/data/tiers.json) have `name_id = name_en` everywhere. The `seed.py` migration is INSERT-ON-CONFLICT-DO-NOTHING; when the source-of-truth JSON changes, run a SQL `UPDATE skills SET name_id = name_en WHERE workspace_id IS NULL` (and same for tiers) on the live DB.
- Other ID translations (UI chrome, action verbs, time formats) **do** translate — this rule is specific to skill + tier proper nouns.

**Components that previously branched on locale and were changed in step 9:**
- `TraineeProfile/TierProgressCard.tsx` — `tierName()` helper now always returns `nameGameEn`
- `TraineeProfile/BlockingSkillsList.tsx` — skill name + tier name both always EN
- `TraineeProfile/RecentGains.tsx` — `gain.skill.nameEn` only
- `TraineeProfile/AllSkillsAccordion.tsx` — `score.skill.nameEn` only
- `locales/id.json` `tiers.*` — flattened to English

**Components that still branch on locale (correct):** `Avatar` (no — it uses initials, not names), date helpers in `lib/dates.ts` (locale-aware), session focus translation in `today.*`. Anything that's UI copy stays translated.
