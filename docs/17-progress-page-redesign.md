# racademy — Progress Page Redesign + Radar Fix

> Follow-up to `docs/16-trainee-revamp-plan.md` after first-cut implementation feedback:
> 1. **Radar text overlaps** on category breakdowns (13 axes).
> 2. **Progress page reads as a debug view** — not informative or eye-catching.
>
> This plan fixes both. Same format as `docs/15-build-plan.md` — feed one step at a time into Cursor; run the **Verify** block; advance only when **Done when** is green.

---

## Scope (locked)

- **Radar fix:** adaptive label placement + rotation when `n > 6`, short-label field on skills, larger size on breakdown view, reduced internal padding so labels have room to breathe.
- **Progress page (`/skills`) full redesign** — rebuild to match the mockup with: hero header, tier strip, hero stats row, radar card with center stat, category list with per-row progress bars, recent gains chips, next-focus card.
- **Backend extends `/skills/me/overview`** with the data the new page needs (current/next tier, overall average, recent gains, focus suggestion, last assessed). No new endpoints — one fatter call so the page paints in a single round-trip.
- Category breakdown screen (`/skills/:categoryCode`) inherits the radar fix automatically; layout is otherwise unchanged in this round.
- Coach view (`/trainees/:id`) is untouched.

## Out of scope

- Per-skill detail page — still deferred to V1.5.
- Animating polygon morphing on score change — nice-to-have, V1.5.
- Time-series charts (sparklines per category) — V1.5; the mockup uses flat bars.

## Conventions inherited (silent)

All `CLAUDE.md` + `docs/01-design-principles.md` rules apply: TS strict, mypy strict, Tailwind tokens only (no hardcoded hex outside `category-meta.ts`), sentence case, 0.5px hairlines, 44pt tap targets, lucide-react outline icons, EN+ID i18n, skill names stay native vocab (Bandeja / Víbora / Chiquita).

---

# Pair R — Radar overlap fix (FE only)

## Step R1 [FE] — Adaptive `SkillRadar` with rotation, short labels, responsive size

**Goal.** Eliminate label collision on the category breakdown radar (13 axes) without regressing the overview (4 axes). Behavior change is self-contained in `SkillRadar.tsx` plus a one-field extension to `RadarAxis`.

**Reads.** `apps/web/src/features/skills/components/SkillRadar.tsx`, `apps/web/src/features/skills/skills-types.ts`, `apps/web/src/features/skills/SkillsCategoryScreen.tsx`.

**Files to edit.**

```
apps/web/src/features/skills/skills-types.ts            # extend RadarAxis
apps/web/src/features/skills/components/SkillRadar.tsx  # adaptive layout
apps/web/src/features/skills/SkillsCategoryScreen.tsx   # pass shortLabel + bigger size
apps/web/src/features/skills/SkillsOverviewScreen.tsx   # unchanged behavior, but pass max=5 explicitly
```

**Type change.**

```ts
// skills-types.ts
export interface RadarAxis {
  code: string;
  label: string;            // full label (used in tooltips, hit-target titles)
  shortLabel?: string;      // NEW — used as the visible axis label when present
  score: number | null;
}
```

**Adaptive rules inside `SkillRadar.tsx`.**

Pure derivations from `n = axes.length`:

| n     | labelRadius (× maxRadius) | fontSize | rotation        | maxRadius offset |
|-------|---------------------------|----------|-----------------|------------------|
| ≤ 4   | 1.18                      | 11px     | none            | size/2 − 36      |
| 5–6   | 1.22                      | 11px     | none            | size/2 − 44      |
| 7–10  | 1.30                      | 10px     | tangential\*    | size/2 − 52      |
| ≥ 11  | 1.34                      | 10px     | tangential\*    | size/2 − 60      |

\*Tangential rotation = each label is rotated by its spoke angle so the text reads **outward** from the centre, flipped 180° on the bottom half so it never reads upside down. Pseudocode:

```ts
const deg = (angle * 180) / Math.PI;           // angle in degrees from +x axis
const upright = deg > 90 || deg < -90;          // bottom half
const rotation = upright ? deg + 180 : deg;     // flip for readability
// In SVG: transform={`rotate(${rotation} ${x} ${y})`}
// Text-anchor stays 'middle' when rotated.
```

**Implementation notes.**

- Use `axis.shortLabel ?? axis.label` for the rendered text. The hit-target `<title>` always uses the full `label`.
- Keep the invisible `<rect>` hit-target — but size it from the *rotated* bounding box (or just keep it square at 56×24 and accept that adjacent hit-targets touch — taps still resolve to the closest centre because each `<rect>` is its own click handler).
- When `n ≥ 11`, also slightly shrink vertex dot radius from 2.5 to 2 so the polygon doesn't feel cluttered.
- Add a `compactLabels?: boolean` prop that forces short-label mode regardless of `n` — useful for future contexts (e.g. inline previews).
- Container caller responsibility: `SkillsCategoryScreen` should pass `size={Math.min(360, viewportWidth - 32)}` via a `useViewportWidth` hook (or just `size={340}` for now — phones get the full width with `overflow: visible`).

**SkillsOverviewScreen.tsx change.** No structural change here yet (Pair P does the redesign). Pass `size={260}` explicitly so the overview stays tight while the breakdown gets the full 340.

**Done when.**

- [ ] `/skills/technical` shows 13 axes with no overlap on a 375×667 viewport.
- [ ] Labels along the bottom half are upright (not upside-down).
- [ ] `/skills` (4 axes) renders identically to before this change.
- [ ] Switching language EN ↔ ID: labels reposition cleanly; long ID names ("Pengembalian Servis") fit when shortLabel falls back to label.
- [ ] Tapping any axis label on the overview still navigates to that category.

**Verify.**

```bash
pnpm --filter @racademy/web dev
# Manual on a 375px viewport:
# /skills → confirm overview radar matches the prior layout pixel-for-pixel.
# /skills/technical → no label collision; rotate device, still no collision.
# /skills/tactical, /skills/physical, /skills/mental → no regressions.
```

---

# Pair S — Short labels on the skill data

## Step S1 [BE] — Add `short_label_{en,id}` to skills table + seed

**Goal.** Give every skill a short version of its name (≤ 12 chars, ideally ≤ 10) used by the radar. Long names ("Defensive Lob (Globo)", "Chiquita / Drop Shot") get truncated forms ("Lob", "Drop"). Skills with names already short (Bandeja, Víbora, Smash) reuse the full label.

**Reads.** `docs/12-data-model.md` § "Skills", `docs/padel-skill-framework-v0.md` § 2, `apps/api/data/skills_padel.json` (current seed).

**Files to edit / create.**

```
apps/api/alembic/versions/00ZZ_skills_short_labels.py    # NEW — add columns + backfill
apps/api/data/skills_padel.json                          # EDIT — add short_label_en + short_label_id per skill
apps/api/src/skills/models.py                            # EDIT — add columns to ORM
apps/api/src/skills/me_schemas.py                        # EDIT — add to response shapes
apps/api/src/skills/me_service.py                        # EDIT — select the new columns
apps/api/scripts/seed.py                                 # EDIT — write short labels on conflict
```

**Schema.**

```sql
ALTER TABLE skills
  ADD COLUMN short_label_en VARCHAR(20),
  ADD COLUMN short_label_id VARCHAR(20);
-- Backfill nulls with truncated label in the same migration (idempotent).
UPDATE skills
   SET short_label_en = COALESCE(short_label_en, LEFT(name_en, 12)),
       short_label_id = COALESCE(short_label_id, LEFT(name_id, 12))
 WHERE short_label_en IS NULL OR short_label_id IS NULL;
```

**Short-label proposal (paste into `skills_padel.json`).**

Technical (only the ones longer than 12 chars need a real short form; the rest can repeat the full name):

| Code               | Full EN                  | short_label_en | short_label_id |
|--------------------|--------------------------|----------------|----------------|
| TECH_FH            | Forehand Drive           | Forehand       | Forehand       |
| TECH_BH            | Backhand Drive           | Backhand       | Backhand       |
| TECH_FH_VOLLEY     | Forehand Volley          | FH volley      | Voli FH        |
| TECH_BH_VOLLEY     | Backhand Volley          | BH volley      | Voli BH        |
| TECH_SERVE         | Serve                    | Serve          | Servis         |
| TECH_RETURN        | Return of Serve          | Return         | Return         |
| TECH_LOB           | Defensive Lob (Globo)    | Lob            | Lob            |
| TECH_BANDEJA       | Bandeja                  | Bandeja        | Bandeja        |
| TECH_VIBORA        | Víbora                   | Víbora         | Víbora         |
| TECH_SMASH         | Smash (Remate)           | Smash          | Smash          |
| TECH_WALL_BACK     | Back Wall Exit           | Back wall      | Dinding bel.   |
| TECH_WALL_SIDE     | Side Wall Play           | Side wall      | Dinding sm.    |
| TECH_DROP          | Chiquita / Drop Shot     | Chiquita       | Chiquita       |

Tactical / Physical / Mental — every label already ≤ 12 chars except a few; same rule, propose in the JSON. Coach advisor can refine later.

**Implementation notes.**

- The migration must be idempotent — re-running the seed after the migration must NOT overwrite a hand-edited short label (use `ON CONFLICT DO NOTHING` for the seed; only the migration backfills nulls).
- Validate `short_label_en` and `short_label_id` length ≤ 20 chars in Pydantic.
- API response: extend `ApiSkillScore` and `ApiCategoryScore` (overview row) — both should expose short labels too, since the overview also passes them into the radar.

**Done when.**

- [ ] `alembic upgrade head` runs cleanly; `\d skills` shows the two new columns.
- [ ] Seed run is idempotent — running twice does not change row count or overwrite values.
- [ ] `SELECT short_label_en FROM skills WHERE code='TECH_LOB'` returns `'Lob'`.
- [ ] `curl /skills/me/category/technical` returns `short_label_en` + `short_label_id` per skill.

**Verify.**

```bash
docker compose -f infra/docker-compose.yml exec api alembic upgrade head
docker compose -f infra/docker-compose.yml exec api python -m scripts.seed
docker compose -f infra/docker-compose.yml exec api python -m scripts.seed   # idempotency check
docker compose -f infra/docker-compose.yml exec postgres psql -U racademy -d racademy -c \
  "SELECT code, short_label_en, short_label_id FROM skills WHERE code IN ('TECH_LOB','TECH_DROP','TECH_FH_VOLLEY');"
```

## Step S2 [FE] — Thread short labels through the API client + radars

**Goal.** Pick up the new field, pass it as `shortLabel` into every `RadarAxis`.

**Files to edit.**

```
apps/web/src/features/skills/skills-types.ts        # add labelShortEn/Id to SkillScore + CategoryScore
apps/web/src/features/skills/skills-api.ts          # map the new fields
apps/web/src/features/skills/SkillsOverviewScreen.tsx
apps/web/src/features/skills/SkillsCategoryScreen.tsx
```

**Type additions.**

```ts
export interface SkillScore {
  code: string;
  labelEn: string;
  labelId: string;
  labelShortEn?: string;     // NEW
  labelShortId?: string;     // NEW
  latestScore: number | null;
  latestDescriptorEn: string | null;
  latestDescriptorId: string | null;
  lastAssessedAt: string | null;
}

export interface CategoryScore {
  category: CategoryCode;
  labelEn?: string;          // NEW — already in API, just thread it through
  labelId?: string;          // NEW
  average: number | null;
  assessedCount: number;
  totalCount: number;
}
```

**Wiring.**

```ts
// SkillsCategoryScreen.tsx, inside the axes useMemo:
const axes: RadarAxis[] = (data?.skills ?? []).map((s) => ({
  code: s.code,
  label: lang === 'id' ? s.labelId : s.labelEn,
  shortLabel: lang === 'id' ? s.labelShortId : s.labelShortEn,
  score: s.latestScore,
}));
```

**Done when.**

- [ ] TS types compile clean; no `any`.
- [ ] Radar on `/skills/technical` shows "Lob", "Chiquita", "FH volley" etc. instead of the long names.
- [ ] Overview radar unchanged (4 categories already fit horizontal text).

**Verify.** Visual; pair with R1.

---

# Pair O — Overview endpoint extension (more data, one call)

## Step O1 [BE] — Extend `/skills/me/overview` to a full progress payload

**Goal.** One endpoint feeds the entire redesigned page. Add `tier`, `overall`, `recent_gains`, `focus_suggestion`, `last_assessed_at` alongside the existing `categories` array.

**Reads.** `apps/api/src/skills/me_service.py`, `apps/api/src/athletes/tier_calc.py` (from build plan step 10), `apps/api/src/athletes/profile.py`.

**Files to edit.**

```
apps/api/src/skills/me_schemas.py       # EDIT — extend OverviewOut
apps/api/src/skills/me_service.py       # EDIT — compose the new fields
apps/api/src/skills/me_router.py        # EDIT — no signature change; just pass-through
apps/api/tests/test_skills_me.py        # EDIT — assert new fields present + shape
```

**Response shape.**

```jsonc
{
  "categories": [
    { "code": "technical", "label_en": "Technical", "label_id": "Teknik",
      "average": 3.4, "assessed_count": 12, "total_count": 13 },
    // … tactical, physical, mental
  ],
  "overall": {
    "average": 3.2,                       // mean of all assessed skills (not mean of category means)
    "assessed_count": 19,
    "total_count": 27,
    "last_assessed_at": "2026-05-15T08:23:11Z"
  },
  "tier": {
    "current": { "code": "bronze", "label_en": "Bronze", "label_id": "Perunggu" },
    "next":    { "code": "silver", "label_en": "Silver", "label_id": "Perak" } | null,
    "blockers_remaining_count": 8,        // total across categories
    "progress_to_next": 0.38               // 0..1, fraction of next-tier requirements met
  } | null,
  "recent_gains": [                       // last 14 days, score deltas > 0, max 4
    { "skill_code": "TECH_BANDEJA", "label_en": "Bandeja", "label_id": "Bandeja",
      "from": 3, "to": 4, "at": "2026-05-14T07:00:00Z" }
  ],
  "focus_suggestion": {                   // null if no blockers or top tier
    "skill_code": "TECH_VIBORA",
    "label_en": "Víbora",
    "label_id": "Víbora",
    "current_level": 2,
    "required_level": 3,
    "category": "technical",
    "latest_note_en": "Add side spin earlier in the swing.",
    "latest_note_id": null,
    "reason": "blocker_for_next_tier"      // enum: 'blocker_for_next_tier' | 'oldest_unassessed' | 'lowest_score'
  } | null,
  "updated_at": "2026-05-15T08:23:11Z"
}
```

**Computation rules.**

- `overall.average` = mean of `latest_score` across all 27 skills (`null` scores excluded). Round to 1 decimal in the JSON; client decides display.
- `tier.progress_to_next` = `met_requirements / total_requirements_for_next_tier` from `tier_calc`. If at top tier, `next` is `null` and `progress_to_next` is `1.0`.
- `recent_gains`: window = `now - interval '14 days'`. For each skill, find the assessment immediately prior to the most recent one in the window; if its score was lower than the most recent, emit one entry. Sort by `at DESC`. Cap at 4.
- `focus_suggestion`: prefer a skill from the blocker list (lowest `current_level` first; tie-break by oldest `last_assessed_at`). Fallback: oldest unassessed skill. Fallback again: lowest-scored skill. Only `null` if the trainee is at the top tier with all skills assessed at 5.
- All in a single transaction; reuse helpers from `tier_calc` and `me_service` — don't duplicate logic.

**Performance.**

- One trip to DB ideally. Compose with 3 queries: (a) latest scores per skill via `DISTINCT ON`, (b) recent assessments in last 14 days, (c) tier requirements for current/next tier. Keep p95 < 80 ms on dev hardware.
- Cache `Cache-Control: private, max-age=20`.

**Done when.**

- [ ] `curl /skills/me/overview` returns the full shape with realistic values from the dev seed.
- [ ] At top tier, `tier.next` is `null` and `focus_suggestion` is `null`.
- [ ] At zero assessments, `overall.average` is `null`, `recent_gains` is `[]`, `tier.current` is `null`, `tier.next` is the lowest tier, `focus_suggestion.reason` is `'oldest_unassessed'`.
- [ ] `pytest test_skills_me.py` covers: full payload shape, top-tier edge case, zero-assessment edge case, recent-gains window boundary.

**Verify.**

```bash
docker compose exec api pytest tests/test_skills_me.py -v
TRAINEE_JWT=...
curl -s localhost:8000/skills/me/overview -H "Authorization: Bearer $TRAINEE_JWT" | jq '{overall, tier, focus_suggestion, recent_gains: (.recent_gains | length)}'
```

## Step O2 [FE] — Extend overview types + API client

**Goal.** Surface the new payload in `SkillsOverview` so the page can render it without further fetches.

**Files to edit.**

```
apps/web/src/features/skills/skills-types.ts
apps/web/src/features/skills/skills-api.ts
```

**Type additions (camelCase).**

```ts
export interface OverallProgress {
  average: number | null;
  assessedCount: number;
  totalCount: number;
  lastAssessedAt: string | null;
}

export interface TierBrief {
  code: string;
  labelEn: string;
  labelId: string;
}

export interface TierProgress {
  current: TierBrief | null;
  next: TierBrief | null;
  blockersRemainingCount: number;
  progressToNext: number;          // 0..1
}

export interface RecentGain {
  skillCode: string;
  labelEn: string;
  labelId: string;
  from: number;
  to: number;
  at: string;
}

export type FocusReason =
  | 'blocker_for_next_tier'
  | 'oldest_unassessed'
  | 'lowest_score';

export interface FocusSuggestion {
  skillCode: string;
  labelEn: string;
  labelId: string;
  currentLevel: number | null;
  requiredLevel: number | null;
  category: CategoryCode;
  latestNoteEn: string | null;
  latestNoteId: string | null;
  reason: FocusReason;
}

export interface SkillsOverview {
  categories: CategoryScore[];
  overall: OverallProgress;
  tier: TierProgress | null;
  recentGains: RecentGain[];
  focusSuggestion: FocusSuggestion | null;
  updatedAt: string | null;
}
```

Update `fetchSkillsOverview` to map snake_case → camelCase for every new field.

**Done when.**

- [ ] TS compiles. Existing consumers of `SkillsOverview.categories` still work.
- [ ] React Query cache key remains `['skills', 'me', 'overview']`.

---

# Pair P — Progress page redesign (the visual rebuild)

## Step P1 [FE] — Rebuild `SkillsOverviewScreen` per mockup

**Goal.** Replace the current minimal layout with the full mockup: header → tier strip → hero stats → radar card with center stat → category list with bars → recent gains chips → focus card.

**Reads.** This doc; `docs/01-design-principles.md`; reference mockup in chat.

**Files to create.**

```
apps/web/src/features/skills/components/TierStrip.tsx
apps/web/src/features/skills/components/HeroStats.tsx
apps/web/src/features/skills/components/RadarCard.tsx          # wraps SkillRadar with center stat overlay
apps/web/src/features/skills/components/CategoryListRow.tsx    # tappable row with progress bar
apps/web/src/features/skills/components/RecentGainsChips.tsx
apps/web/src/features/skills/components/FocusCard.tsx
```

**Files to edit.**

```
apps/web/src/features/skills/SkillsOverviewScreen.tsx          # full rewrite
apps/web/src/features/skills/components/CategoryLegend.tsx     # DELETE — replaced by CategoryListRow
apps/web/src/i18n/en.json
apps/web/src/i18n/id.json
```

**Layout (top → bottom, all inside `max-w-md mx-auto px-4 pb-8 pt-4`, gap-3 between sections).**

1. **Header** — `<h1>Progress</h1>` (28px medium, `-tracking-tight`), caption underneath ("Your skill journey").
2. **TierStrip** — full-width card, hairline-bordered, padding `p-3.5`. Inside:
   - Top row: pill with `lucide-react Trophy` icon + current tier name (accent-on-accent-bg), chevron-right icon, next tier name (secondary color). Right side: "8 of 13" in `tabular-nums`.
   - Progress bar: 6px tall, `bg-black/5` track, `bg-[var(--accent)]` fill, `width: ${progressToNext * 100}%`.
   - Footer caption: "X skills to {next.label} — closer than ever." (i18n key with count + tier interpolation).
   - If `tier.next == null`: replace bar + caption with "Top tier reached" and a `Sparkles` icon.
3. **HeroStats** — `grid grid-cols-3 gap-2`. Three secondary-surface cards (`bg-[var(--color-background-secondary)] rounded-lg p-2.5`):
   - Overall: label "Overall" (11px secondary) + value (22px medium tabular) + "/5" subscript (12px tertiary).
   - Assessed: label "Assessed" + "{n}/{total}" same treatment.
   - Last: label "Last" + relative-time short ("2d", "3h", "now"); use `date-fns/formatDistanceToNowStrict` then strip the unit to 1 char.
4. **RadarCard** — hairline-bordered card containing the radar with the **overall average overlaid in the centre**:
   - Use the existing `<SkillRadar size={260} axes={overviewAxes} accent="var(--accent)" onAxisTap={onPick} />`.
   - Overlay a `<div>` absolutely centered with the `overall.average` (22px medium tabular) + "overall" caption (10px tertiary).
   - For each of the 4 vertex dots, override fill to that category's accent (pass `accent` per-vertex via a small extension or color the dots from the consumer — see notes).
   - Caption underneath: "Tap a category to explore" (11px tertiary, centered).
5. **CategoryListRow** repeated 4× inside a single hairline-bordered card. Each row:
   - Left: 22px round chip (`bg-{category.accent}` `text-white`) with category letter.
   - Middle: category name (14px) on top, 4px progress bar below (`bg-black/5` track, `bg-{category.accent}` fill, `width: ${(average ?? 0) / 5 * 100}%`).
   - Right: `{average.toFixed(1)}` (14px medium tabular) on top, `{assessedCount}/{totalCount}` (11px tertiary tabular) below.
   - Chevron-right icon, `text-black/25`.
   - Whole row is a `<button>`; navigates to `/skills/${code}`. `min-h-tap`.
6. **RecentGainsChips** — section label "Recent gains" (11px medium uppercase tracked tertiary), then `<ul>` of pills:
   - `bg-[rgba(15,169,104,0.10)] text-[#0F6E56]` (success ramp), `rounded-full px-2.5 py-1 text-[12px]`.
   - Each pill: `lucide ArrowUpRight` 12px + `{skill.label} {from}→{to}`.
   - If `recentGains.length === 0`: render nothing (no empty state needed — the focus card carries the page).
7. **FocusCard** — hairline-bordered card, `bg-[var(--accent-bg)]`, `p-3.5`:
   - Row 1: 26px round chip with `Target` icon, accent bg, white icon. Next to it: "Focus on {skill.label}" (14px medium).
   - Row 2: "Last assessed at level {currentLevel}. Reach level {requiredLevel} to unlock {nextTier.label}." (12px secondary).
   - If `latestNote`: append italicized quote (12px secondary, `font-italic`).
   - If `focusSuggestion == null`: hide the card entirely.

**Implementation notes.**

- All new strings go through `t('skills.overview.…')` keys (see i18n diff below). Number values use the `count` interpolation pattern so plurals work in EN/ID.
- The radar vertex-dot color override is the only thing that needs a tiny `SkillRadar` extension: add an optional `vertexAccents?: Record<string, string>` prop keyed by axis code; falls back to `accent` when absent.
- The progress bar inside `TierStrip` should animate from 0 → target width once on mount using a CSS transition (`transition-[width] duration-500 ease-out`). Subtle, not Framer Motion-heavy.
- Empty state (no assessments at all): keep the page structure but show a friendly hero card replacing the tier strip ("Your radar fills in as you train"), hide the gains section, and the focus card auto-suggests `oldest_unassessed`. Don't render an empty radar with no polygon and no helpful text.
- Loading state: skeleton matching the layout (tier strip + 3 metric cards + radar square + 4 list rows). Don't show the old single-bar skeleton.

**i18n keys to add (`en.json` excerpt).**

```jsonc
{
  "skills": {
    "overview": {
      "title": "Progress",
      "subtitle": "Your skill journey",
      "tier": {
        "currentToNext": "{{current}} → {{next}}",
        "remainingPlural": "{{count}} skills to {{tier}} — closer than ever.",
        "remainingSingular": "1 skill to {{tier}} — almost there.",
        "topTier": "Top tier reached"
      },
      "stat": {
        "overall": "Overall",
        "assessed": "Assessed",
        "last": "Last",
        "noAssessment": "—"
      },
      "radar": {
        "centerCaption": "overall",
        "tapHint": "Tap a category to explore"
      },
      "sectionByCategory": "By category",
      "sectionRecentGains": "Recent gains",
      "gainEntry": "{{label}} {{from}}→{{to}}",
      "focus": {
        "title": "Focus on {{label}}",
        "body": "Last assessed at level {{current}}. Reach level {{required}} to unlock {{tier}}.",
        "bodyNoNote": "Recommended next focus.",
        "noteQuote": "\"{{note}}\""
      },
      "emptyHeroTitle": "Your radar fills in as you train",
      "emptyHeroBody": "Once your coach scores you, this page lights up."
    }
  }
}
```

(`id.json` mirrors the same keys in Indonesian — tier names translate, skill names don't, per `docs/11-localization-rules.md`.)

**Done when.**

- [ ] `/skills` renders all 7 sections from the mockup for a trainee with realistic data.
- [ ] Top-tier trainee: tier strip swaps to "Top tier reached"; focus card hidden.
- [ ] Zero-assessment trainee: empty hero card replaces tier strip; radar shows dotted spokes only; focus card surfaces the oldest unassessed skill.
- [ ] Locale toggle EN ↔ ID flips all chrome including tier labels and plural forms; skill names stay native.
- [ ] Tapping any category row OR any radar axis label navigates to `/skills/:categoryCode`.
- [ ] No layout shift on first paint (loading skeleton matches final layout).
- [ ] Lighthouse a11y ≥ 95 on the page (44pt tap targets, contrast on accent pills).

**Verify.**

```bash
pnpm --filter @racademy/web dev
# Manual on a 375px viewport:
# /skills with demo trainee data → screenshot, diff against mockup in chat.
# Toggle locale → confirm Indonesian renders correctly with plural forms.
# Delete demo trainee assessments → reload → empty-hero treatment.
```

---

# Pair D — Doc updates

## Step D1 — Update specs to reflect the redesign

**Goal.** Keep `docs/` authoritative.

**Files to edit / create.**

```
docs/05-trainee-home.md                 # EDIT — add cross-ref: Progress tab spec moved to docs/17
docs/12-data-model.md                   # EDIT — add skills.short_label_en/id columns
docs/16-trainee-revamp-plan.md          # EDIT — append "Superseded by docs/17" note on Pair A Step A1
docs/README.md                          # EDIT — list docs/17 in the table
```

`docs/17-progress-page-redesign.md` (this file) becomes the canonical spec for `/skills`. Don't rewrite `docs/16` — it's a build-time artifact; just annotate.

**Done when.**

- [ ] `docs/README.md` table lists docs/17 with a one-line description.
- [ ] `docs/12-data-model.md` shows the two new columns under the skills table.
- [ ] `docs/16-trainee-revamp-plan.md` Pair A Step A1 has a callout: "Layout superseded by `docs/17-progress-page-redesign.md` (mockup-driven rebuild)."

---

# End-to-end verification

After Pair P + D land, this single click-through proves the redesign:

1. Sign in as a demo trainee with mid-progress data (`scripts/dev_seed_demo.py`).
2. `/skills` — confirm header, tier strip with animating bar, three hero metrics, radar with overall stat in the center, 4 category rows with bars, ~3 recent gain chips, focus card on Víbora.
3. Tap any category row → land on `/skills/{category}` → confirm radar labels are short, non-overlapping, rotated tangentially.
4. Tap back → return to `/skills` with no flicker.
5. Open in Indonesian → confirm "Perunggu → Perak", "Fokus pada Víbora", and that the gain chips read "Bandeja 3→4" (no localization of the skill name).
6. Wipe demo assessments → reload → confirm empty-hero replaces tier strip and the focus card suggests an oldest-unassessed skill.

If any of these steps fails, the failing pair owns the bug — don't advance.

---

# Suggested calendar

If one dev runs this end-to-end at the same pace as `docs/15-build-plan.md`:

| Pair | Steps      | Estimate |
|------|------------|----------|
| R    | R1         | ~1 day   |
| S    | S1 → S2    | ~1 day   |
| O    | O1 → O2    | ~1.5 days |
| P    | P1         | ~2 days  |
| D    | D1         | ~0.5 day |

~5–6 working days total. The radar fix (R1) is independent and shippable on its own if the bigger redesign needs to wait.
