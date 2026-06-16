# racademy — Trainee Revamp Plan

> Sequential FE↔BE prompts to add: (1) a clickable, two-level skill drill-down on the trainee's Progress tab, (2) a trainee account/profile page, (3) a public coach bio page reachable from a multi-coach Coach tab.
>
> Format mirrors `docs/15-build-plan.md`. Feed **one step at a time** into Cursor. After each step run the **Verify** block and confirm the **Done when** checklist before advancing.

---

## Scope (locked)

- **View owner:** trainee's own app only. No coach-side UI changes in this revamp.
- **Drill-down depth:** two levels. `/skills` (overview radar over 4 categories) → `/skills/:categoryCode` (sub-radar + skill list for that category). Per-skill detail page is explicitly deferred to V1.5.
- **Trainee profile page:** identity / account only (avatar, name, DOB, parent link, locale, notifications, sign out). Lives on the existing Profile tab. Distinct from `/home` (dashboard).
- **Coach profile page:** public bio (photo, years coaching, certifications, languages, specialties, about-me). Lives at `/coach/:coachId`. Read-only from the trainee side in this scope.
- **Coach tab:** lists every coach who has coached this trainee, most recent first. Each row → coach bio page.
- **Coach bio data shape:** JSONB `bio` column on `workspace_memberships` (workspace-scoped so a coach can self-present differently per club).
- **Radar sparse data:** unassessed axes render as dotted gray spokes; polygon spans assessed axes only. No threshold gating.

## Conventions inherited (silent)

All conventions in `CLAUDE.md` and `docs/01-design-principles.md` apply silently — TS strict, mypy strict, Tailwind tokens only, sentence case, 0.5px hairlines, 44pt tap targets, lucide-react outline icons, EN+ID i18n, RLS-enforced workspace scoping, `current_workspace_id()` GUC on every request, multi-sport-ready (skill ontology by `sport_id`).

## Where this slots into the existing build plan

This revamp assumes Phase 0 (steps 0.1–0.3) and Pairs 1–4 of `docs/15-build-plan.md` are done — auth, workspaces, coach today, add trainee + invite. It then **replaces the trainee-app slice of Pair 7 (steps 13–14)** with the steps below, and adds two new pairs after it. Coach-side screens (`/trainees/:id` from Pair 5) are unchanged.

If Pair 7 has already been built against the old spec, do step T-0 first to remove the stale trainee shell and home before adding the new versions.

---

## Step T-0 — Reset (only if Pair 7 already shipped)

**Goal.** Remove the existing trainee shell, home, and any radar that was built per the old `docs/05-trainee-home.md`, so the new pieces land in a clean tree without conflicting routes or components.

**Skip this step if Pair 7 hasn't been built yet.**

**Files to delete.**

```
apps/web/src/layouts/TraineeShell.tsx
apps/web/src/features/trainee-home/
apps/web/src/features/onboarding/InviteWelcomeScreen.tsx   # keep public landing
```

**Files to keep but plan to rewrite.**

```
apps/web/src/features/onboarding/PublicLandingPage.tsx
apps/web/src/features/onboarding/use-invite-token.ts
```

**Done when.**

- [ ] `pnpm typecheck` shows the deleted-file errors only (will be fixed by subsequent steps).
- [ ] No trainee-shell routes resolve.

---

# Pair A — Skill drill-down (trainee Progress tab)

## Step A1 [FE] — Trainee shell + Progress tab routes + shared SkillRadar primitive

**Goal.** Stand up the trainee shell with its 5-tab bottom nav. Wire the Progress tab to `/skills` and `/skills/:categoryCode`. Build the reusable `<SkillRadar>` SVG component used at both levels.

**Reads.** `docs/01-design-principles.md` (radar style + bottom nav), `docs/padel-skill-framework-v0.md` (the 4 categories and their skills), `docs/05-trainee-home.md` (overall trainee tone).

**Files to create.**

```
apps/web/src/layouts/TraineeShell.tsx                       # top bar + content + 5-tab bottom nav
apps/web/src/components/BottomTabBar.tsx                    # if not already shared with CoachShell — extract & reuse
apps/web/src/features/skills/SkillsOverviewScreen.tsx       # /skills — 4-axis radar over category averages
apps/web/src/features/skills/SkillsCategoryScreen.tsx       # /skills/:categoryCode — sub-radar + skill list
apps/web/src/features/skills/components/SkillRadar.tsx      # the shared SVG primitive
apps/web/src/features/skills/components/SkillBar.tsx        # mini 5-cell score bar per skill
apps/web/src/features/skills/components/CategoryLegend.tsx  # color/letter chip per category
apps/web/src/features/skills/skills-api.ts                  # MOCK: returns category averages + per-skill scores
apps/web/src/features/skills/skills-types.ts                # CategoryScore, SkillScore, RadarAxis, TierBlocker
apps/web/src/lib/category-meta.ts                           # TECH/TACT/PHYS/MENT label + accent + slug map
```

**Routing.**

- `/skills` → `SkillsOverviewScreen` (default landing of the Progress tab).
- `/skills/:categoryCode` → `SkillsCategoryScreen` where `categoryCode ∈ {'technical','tactical','physical','mental'}`.
- 404 on unknown category; back nav returns to `/skills`.

**SkillRadar component contract.**

```ts
type RadarAxis = { code: string; label: string; score: number | null }; // null = unassessed
type SkillRadarProps = {
  axes: RadarAxis[];          // 3–13 axes supported
  max?: number;               // default 5
  size?: number;              // default 280
  unassessedStyle?: 'gray-dotted' | 'hidden';   // default 'gray-dotted'
};
```

Render rules:

- Polygon spans assessed axes only (skip null scores when building the path).
- Unassessed spokes render as 0.5px dotted lines with `stroke: var(--color-border-tertiary)`.
- Labels are sentence case, `text-[11px] font-medium` (medium weight per design system).
- Polygon `fill: var(--accent); fill-opacity: 0.18; stroke: var(--accent); stroke-width: 1.5`.
- Hit-targets on each axis label = 44pt invisible rect. Tapping the **overview radar's** axis or label navigates to that category. Tapping in the **breakdown radar** is inert (no third level in this scope).

**Implementation notes.**

- `category-meta.ts` is the single source of truth for category code ↔ URL slug ↔ EN label ↔ ID label ↔ accent chip color. Reference it everywhere — don't re-derive.
- Mock data in `skills-api.ts`: 4 category averages + 27 per-skill scores with realistic spread, including some `null` to exercise the gray-dotted style.
- Empty state (no assessments at all): render the radar with all 4 axes dotted gray, no polygon, plus an inline card "Your coach hasn't assessed you yet — your radar fills in as you train."
- The breakdown screen reuses the radar primitive over the skills of one category (e.g. 13 Technical skills = 13 axes). Below it: blocking-skills callout (placeholder for now — wired in step A3), then a vertical list of skills with `<SkillBar />` + score pill + skill-name + (if descriptor cached) one-line current descriptor.
- Skill names stay in their original vocab (Bandeja, Víbora, Chiquita) per `docs/11-localization-rules.md`. Don't translate. Apply locale only to the category labels and UI chrome.

**Done when.**

- [ ] `/skills` renders the 4-axis radar with mock data; tapping the "Technical" sector or label navigates to `/skills/technical`.
- [ ] `/skills/technical` renders a 13-axis sub-radar + skill list with `<SkillBar />` per row.
- [ ] Setting half the mock scores to `null` shows dotted gray spokes for those axes; polygon visibly skips them.
- [ ] Setting all scores to `null` shows the empty card and no polygon.
- [ ] Bottom nav routes between Home / Progress / Sessions / Coach / Profile (other tabs render placeholders).

**Verify.**

```bash
pnpm --filter @racademy/web dev
# Manual: /skills → tap each of the 4 category labels in turn → confirm route + URL slug.
# Toggle mock scores in skills-api.ts to all-null, half-null, all-assessed; reload between each.
```

---

## Step A2 [BE] — Skills aggregate endpoints

**Goal.** Two real endpoints powering the Progress tab. Both are self-scoped (`/skills/me/...`) — they return data for the authenticated trainee only, enforced by RLS.

- `GET /skills/me/overview` → `{ categories: [{code, label_en, label_id, average, assessed_count, total_count}], updated_at }`
- `GET /skills/me/category/:categoryCode` → `{ category, skills: [{code, label, label_id, latest_score, latest_descriptor_en, latest_descriptor_id, last_assessed_at}], updated_at }`

**Reads.** `docs/12-data-model.md` § "Assessments" + § "Performance notes", `docs/padel-skill-framework-v0.md` § 1–2.

**Files to create.**

```
apps/api/src/skills/me_router.py            # the two endpoints above
apps/api/src/skills/me_service.py           # aggregate query + category folding
apps/api/src/skills/me_schemas.py
apps/api/tests/test_skills_me.py
```

**FE changes (same step).** Drop `skills-api.ts` mocks; point at real endpoints via the existing `apiClient.ts`.

**Implementation notes.**

- Use `DISTINCT ON (skill_id)` to get the latest assessment per skill in one query. Average per category = mean of latest scores in that category; `assessed_count` and `total_count` enable the "X of N assessed" affordance.
- Category code mapping is server-side too — return the canonical `TECH/TACT/PHYS/MENT` code plus the locale-resolved label so the FE doesn't have to know the framework.
- RLS: the trainee role policy already restricts athletes/assessments to `user_id = current_user_id()`. Verify a trainee querying these endpoints sees only their own data; a *different* trainee in the same workspace gets 0 rows.
- Cache `Cache-Control: private, max-age=30` — radar doesn't need to be live to the second, but should reflect a new assessment within ~30s without polling.
- Index check: ensure `idx_assessments_athlete_skill_recorded` exists on `(athlete_id, skill_id, recorded_at DESC)` so the DISTINCT ON is index-only.

**Done when.**

- [ ] `curl /skills/me/overview -H "Authorization: Bearer $TRAINEE_JWT"` returns 4 category rows with sensible averages from the dev seed.
- [ ] `curl /skills/me/category/technical` returns 13 rows; skills not yet assessed have `latest_score: null`.
- [ ] Trainee A's JWT cannot return Trainee B's data — covered by `pytest test_skills_me.py::test_rls_isolation`.
- [ ] FE Progress tab now renders live data; toggling DB seed values reflects on next load.

**Verify.**

```bash
docker compose -f infra/docker-compose.yml exec api pytest tests/test_skills_me.py -v
TRAINEE_JWT=$(...)   # mint via dev helper
curl -s localhost:8000/skills/me/overview -H "Authorization: Bearer $TRAINEE_JWT" | jq .
curl -s localhost:8000/skills/me/category/technical -H "Authorization: Bearer $TRAINEE_JWT" | jq '.skills | length'
```

---

## Step A3 [FE+BE] — Tier-blocker callout in category breakdown

**Goal.** On `/skills/:categoryCode`, surface "N of these K skills are blocking your next tier" with those skill rows visually marked. Reuses the tier-calc service already planned for Pair 5 step 10 — exposes it via a new endpoint scoped to a category.

**Reads.** `docs/padel-skill-framework-v0.md` § "Tier requirements", `apps/api/src/athletes/tier_calc.py` (from build plan step 10).

**Files to create.**

```
apps/api/src/skills/me_blockers.py                          # GET /skills/me/category/:code/blockers
apps/api/tests/test_skills_blockers.py
apps/web/src/features/skills/components/BlockerCallout.tsx
apps/web/src/features/skills/components/SkillRow.tsx        # extend: blockerForTier?: TierName prop
```

**Endpoint shape.**

```
GET /skills/me/category/:categoryCode/blockers
→ {
    next_tier: { code, label_en, label_id },
    blockers_in_category: [{skill_code, required_level, current_level}],
    blockers_total_count: number              # across all categories
  }
```

**Implementation notes.**

- Reuse `tier_calc.compute_current_and_next()` — don't reimplement. The new endpoint just filters its output to one category.
- The callout copy is encouraging, not shaming: "2 of these 13 are blocking Silver. Focus here." Sentence case, single accent.
- Marked skill rows: add a small accent-colored dot to the left of the skill name + a `→` chevron to the required level on the score bar.
- If the trainee is already at the highest tier or has no `next_tier`, hide the callout entirely.
- This is a separate endpoint (not folded into `/skills/me/category/:code`) so the heavier tier calc is only loaded once the trainee scrolls in — keeps the breakdown's first paint fast.

**Done when.**

- [ ] `curl /skills/me/category/technical/blockers` returns the blockers list for the demo trainee.
- [ ] FE shows the callout above the skill list when blockers exist in this category; hides it when none.
- [ ] Skill rows with `current_level < required_level` show the dot + required-level chevron.
- [ ] Trainee at top tier sees no callout, no errors.

**Verify.**

```bash
docker compose exec api pytest tests/test_skills_blockers.py -v
# Manual: seed a trainee with 11/13 technical skills at L3 → confirm callout reads "2 of these 13 are blocking Silver."
```

---

# Pair B — Trainee account/profile page

## Step B1 [FE] — `/profile` screen with editable identity fields

**Goal.** Build the trainee's own account page on the Profile tab. Read-and-edit for fields the trainee owns (display name, avatar, locale, notifications). Read-only display for fields the workspace owns (date of birth, parent link if minor). Sign out at the bottom.

**Reads.** `docs/01-design-principles.md` (grouped tables, inline saved toast), `docs/06-workspace-settings.md` (settings auto-save pattern — mirror it here), `docs/12-data-model.md` § "Users".

**Files to create.**

```
apps/web/src/features/profile/TraineeProfileScreen.tsx
apps/web/src/features/profile/sections/IdentitySection.tsx          # avatar + display name (editable)
apps/web/src/features/profile/sections/AccountSection.tsx           # email (read-only), locale (editable)
apps/web/src/features/profile/sections/PersonalSection.tsx          # DOB (read-only), parent link (read-only if minor)
apps/web/src/features/profile/sections/NotificationsSection.tsx     # session reminders, monthly report ready
apps/web/src/features/profile/sections/DangerSection.tsx            # sign out (+ delete account placeholder)
apps/web/src/features/profile/profile-api.ts                        # MOCK: getMe, patchMe, presignedAvatarUpload
apps/web/src/features/profile/AvatarUploader.tsx                    # reuse settings/LogoUploader UX
```

**Sections (top → bottom).**

1. **Identity** — avatar (tap → upload), display name (inline editable, auto-save on blur).
2. **Account** — email (read-only, dimmed), preferred locale (segmented EN / ID).
3. **Personal** — date of birth (read-only — owned by workspace admin who added them), parent link (read-only, "Linked to [Parent Name]" with a tap-to-view chevron if minor).
4. **Notifications** — toggle: "Session reminders" (24h before), toggle: "Monthly report ready" (when PDF generated).
5. **Danger** — sign out button (accent text, hairline-bordered card). Delete account is a placeholder link "Contact your coach" for MVP — no self-serve delete.

**Implementation notes.**

- Auto-save on blur for editable fields. Show `<InlineSavedToast />` (from settings work) inline next to the section header for 5s after save.
- Avatar upload mirrors `LogoUploader` from `docs/15-build-plan.md` step 15 — presigned PUT to MinIO/R2, validate type + size client-side before requesting presign.
- Locale toggle calls `PATCH /users/me { preferred_locale }` and updates `i18next` language immediately on success.
- Empty avatar = initials chip on accent background (reuse `<Avatar />` from coach today).
- Notifications toggles are wired to a new `user_notification_prefs` shape (added in step B2). If the BE isn't ready yet, mock them locally.

**Done when.**

- [ ] `/profile` renders all 5 sections with mock data.
- [ ] Editing display name → blur → "Saved ✓" appears and fades.
- [ ] Locale toggle flips entire UI immediately (i18next listens to user.preferred_locale).
- [ ] Minor trainee shows the parent link row; adult trainee hides it.
- [ ] Sign out clears auth and routes to `/signin`.

**Verify.** Visual click-through; toggle `is_minor` in the mock to confirm parent row appears/disappears.

---

## Step B2 [BE] — `/users/me` PATCH + notification prefs + avatar presign

**Goal.** Real backing for the profile screen. `GET /users/me`, `PATCH /users/me`, `POST /uploads/avatar/sign`. Add a small `user_notification_prefs` table for the two toggles.

**Reads.** `docs/12-data-model.md` § "Users", `docs/15-build-plan.md` step 16 (uploads pattern — mirror it).

**Files to create.**

```
apps/api/alembic/versions/00XX_user_notification_prefs.py    # new table
apps/api/src/users/me_router.py                              # GET, PATCH
apps/api/src/users/me_schemas.py
apps/api/src/users/me_service.py
apps/api/src/uploads/avatar.py                               # POST /uploads/avatar/sign
apps/api/tests/test_users_me.py
```

**Schema additions.**

```sql
CREATE TABLE user_notification_prefs (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  session_reminders   BOOLEAN NOT NULL DEFAULT TRUE,
  monthly_report      BOOLEAN NOT NULL DEFAULT TRUE,
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- RLS: user can read/write own row only.
```

**PATCH /users/me body.**

```jsonc
{
  "display_name": "Andi P.",        // optional
  "avatar_url": "https://...",       // optional, must be from our bucket
  "preferred_locale": "id",          // optional, 'en' | 'id'
  "notifications": {                 // optional, partial
    "session_reminders": false,
    "monthly_report": true
  }
}
```

**Implementation notes.**

- `avatar_url` whitelist: server validates the URL is on our R2/MinIO bucket and HEAD-checks `Content-Type` + `Content-Length` (≤2MB, image/png|jpeg|webp).
- Notifications upsert: `INSERT ... ON CONFLICT (user_id) DO UPDATE SET ...` so the row is created lazily.
- Audit-log every PATCH via the decorator from build plan step 20 if it's landed; otherwise leave a TODO.
- Don't mint a new JWT on profile PATCH (no `wsid` change). Keep the existing token.
- DOB and parent link are NOT writable from this endpoint — they're admin-owned. Return 422 if they appear in the body.

**Done when.**

- [ ] `pytest test_users_me.py` covers: PATCH display name, PATCH locale, PATCH notifications (partial), avatar URL validation, DOB write rejected with 422.
- [ ] FE `/profile` now persists across reload.
- [ ] Toggling "Session reminders" off → DB row reflects it.
- [ ] Avatar upload to MinIO + PATCH → new avatar shows in `<TraineeShell />` top bar.

**Verify.**

```bash
docker compose exec api alembic upgrade head
docker compose exec api pytest tests/test_users_me.py -v
TRAINEE_JWT=...
curl -X PATCH localhost:8000/users/me \
  -H "Authorization: Bearer $TRAINEE_JWT" -H "Content-Type: application/json" \
  -d '{"preferred_locale":"en","notifications":{"session_reminders":false}}'
```

---

# Pair C — Coach tab + public coach bio

## Step C1 [BE] — `coach_bio` JSONB on memberships + dev seed

**Goal.** Extend `workspace_memberships` with a `bio` JSONB column for coach self-presentation. Seed plausible bios for the demo workspace's coaches. Defines the contract step C2 will consume.

**Reads.** `docs/12-data-model.md` § "Workspace memberships".

**Files to create.**

```
apps/api/alembic/versions/00YY_membership_bio_jsonb.py
apps/api/src/memberships/bio_schemas.py             # Pydantic shape for the JSONB
apps/api/src/memberships/bio_validator.py           # validates the shape on write
apps/api/scripts/dev_seed_demo.py                   # EXTEND: add 3 coaches with full bios
```

**Bio JSONB shape (validated by Pydantic on write).**

```jsonc
{
  "headline": "APPA L2 coach. 8 years on tour.",   // ≤ 120 chars
  "about": "Long-form markdown ≤ 1500 chars...",    // plain text or light markdown
  "years_coaching": 8,                              // integer ≥ 0
  "certifications": [                               // array of {issuer, name, year}
    {"issuer": "APPA", "name": "Level 2", "year": 2021}
  ],
  "languages": ["en", "id", "es"],                  // ISO-639-1 codes
  "specialties": ["TACT_NET_POS", "TECH_BANDEJA"],  // skill codes; FE renders nicely
  "photo_url": "https://..."                        // distinct from users.avatar_url — workspace-scoped
}
```

**Implementation notes.**

- Default for existing rows: empty object `{}`. Bio absence ≠ error; FE renders a minimal card.
- The migration is non-destructive — JSONB column with default `'{}'::jsonb`.
- `bio_validator.py` is reused by step D's PATCH (coach-side bio editing — out of this revamp's scope but a future-proof hook).
- Seed: 3 coaches with realistic bios in EN+ID — at minimum a head coach with full bio, a junior coach with minimal bio, and a coach with empty bio (`{}`) to exercise the empty-state path.

**Done when.**

- [ ] `alembic upgrade head` runs cleanly; `psql \d workspace_memberships` shows the new column.
- [ ] Re-running the dev seed populates 3 bios; idempotent on re-run.
- [ ] Selecting `bio` on an existing membership pre-migration returns `{}`.

**Verify.**

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m scripts.dev_seed_demo
docker compose exec postgres psql -U racademy -d racademy -c \
  "SELECT (bio->>'headline') FROM workspace_memberships WHERE role='coach';"
```

---

## Step C2 [BE] — Coach tab endpoints (past + current coaches, public bio)

**Goal.** Two endpoints powering the Coach tab and the bio page.

- `GET /trainees/me/coaches` → list of every coach who has coached this trainee, ordered by `last_coached_at DESC`.
- `GET /coaches/:coachId` → public-within-workspace coach bio (no PII beyond what they chose to share).

**Reads.** `docs/12-data-model.md` § "Sessions" + § "Workspace memberships", build plan step 6 (sessions seed).

**Files to create.**

```
apps/api/src/trainees/coaches_router.py
apps/api/src/trainees/coaches_service.py
apps/api/src/coaches/router.py
apps/api/src/coaches/schemas.py
apps/api/src/coaches/service.py
apps/api/tests/test_trainee_coaches.py
apps/api/tests/test_coach_bio.py
```

**Endpoint shapes.**

```
GET /trainees/me/coaches
→ {
    coaches: [{
      coach_id, display_name, avatar_url,
      headline,                       # bio.headline or null
      session_count,                  # how many sessions they've coached for this trainee
      last_coached_at,                # ISO ts
      next_session_at                 # ISO ts or null
    }]
  }

GET /coaches/:coachId
→ {
    coach_id, display_name, avatar_url,
    bio: { headline, about, years_coaching, certifications, languages, specialties, photo_url },
    member_since,                     # workspace_memberships.created_at
    coached_trainees_count            # in this workspace
  }
```

**Implementation notes.**

- "Coached" = appears as `coach_user_id` on a `sessions` row that involved this athlete (join through `session_participants` or equivalent — see build plan step 6).
- Order: most recent `last_coached_at` first. Active session within next 7 days bubbles to the top regardless.
- RLS on `/coaches/:coachId`: requestor must share at least one workspace with the coach. Don't expose bios across workspace boundaries.
- Specialty rendering is FE responsibility — server returns codes, FE maps to labels via the skill ontology.
- `coached_trainees_count` is workspace-scoped, never global.

**Done when.**

- [ ] `pytest test_trainee_coaches.py test_coach_bio.py` green.
- [ ] `/trainees/me/coaches` returns 1+ rows for a demo trainee who has had sessions.
- [ ] Same endpoint returns `[]` for a freshly-invited trainee with no sessions yet.
- [ ] `/coaches/:coachId` returns 404 for a coach in a different workspace.

**Verify.**

```bash
docker compose exec api pytest tests/test_trainee_coaches.py tests/test_coach_bio.py -v
curl -s localhost:8000/trainees/me/coaches -H "Authorization: Bearer $TRAINEE_JWT" | jq '.coaches | length'
COACH_ID=$(curl -s localhost:8000/trainees/me/coaches -H "Authorization: Bearer $TRAINEE_JWT" | jq -r '.coaches[0].coach_id')
curl -s localhost:8000/coaches/$COACH_ID -H "Authorization: Bearer $TRAINEE_JWT" | jq .
```

---

## Step C3 [FE] — Coach tab list + coach bio page

**Goal.** Wire the Coach tab to `/coach` (list of coaches) and `/coach/:coachId` (single bio). Mobile-first, sentence case, accent for actionable rows.

**Reads.** `docs/01-design-principles.md`, `docs/09-empty-states.md` (define a new entry for "no coaches yet" — see Step C4 doc updates).

**Files to create.**

```
apps/web/src/features/coach/CoachListScreen.tsx           # /coach — list of past+current coaches
apps/web/src/features/coach/CoachBioScreen.tsx            # /coach/:coachId — full bio
apps/web/src/features/coach/components/CoachListRow.tsx
apps/web/src/features/coach/components/BioHeader.tsx      # photo + name + headline
apps/web/src/features/coach/components/BioAbout.tsx       # about-me prose
apps/web/src/features/coach/components/BioCredentials.tsx # years + certs + languages
apps/web/src/features/coach/components/BioSpecialties.tsx # skill-code chips → resolved labels
apps/web/src/features/coach/coach-api.ts
apps/web/src/features/coach/coach-types.ts
```

**`/coach` list row layout.**

- Avatar (40px) | display name (15px medium) + headline (12px regular, secondary color) | session count + "last coached 3d ago" | chevron.
- Active "today" or "this week" coaches get a small accent dot next to their name.
- Empty state: card with friendly copy + "You'll see your coaches here after your first session."

**`/coach/:coachId` page layout.**

1. **Hero** — photo (or initials), display name, headline, "Member since 2024" subtitle.
2. **About** — prose, max 6 lines collapsed with "Read more" expand.
3. **Credentials** — years coaching (large numeral), certifications list (issuer · name · year), languages as chips.
4. **Specialties** — skill chips, accent-bordered, with English/Spanish skill name (e.g. "Bandeja", "Net positioning"). Tapping a chip is inert in this scope (could navigate to `/skills/:cat?highlight=:skill` in V1.5).
5. **Footer** — "Coached X trainees in [Workspace]" stat.

**Implementation notes.**

- Bio fields can be empty (`{}`); each section component renders nothing if its data is missing — no half-empty sections.
- Photo fallback: initials on accent background, same as `<Avatar />` primitive.
- All copy in i18n: `t('coach.list.emptyTitle')`, `t('coach.bio.aboutTitle')`, etc. Skill labels stay native vocab per `docs/11-localization-rules.md`.

**Done when.**

- [ ] `/coach` shows the demo trainee's 3 seeded coaches, ordered by recency.
- [ ] Tapping any row navigates to `/coach/:coachId`.
- [ ] Coach with minimal bio renders only the sections that have data.
- [ ] Empty-state trainee (no sessions) sees the friendly empty card.
- [ ] Locale toggle flips chrome labels but leaves skill names native.

**Verify.** Click-through with EN + ID locales, plus the empty-state path (delete the demo trainee's sessions and reload).

---

## Step C4 — Doc updates (spec catches up to implementation)

**Goal.** Keep `docs/` authoritative. Append new sections rather than rewriting old ones in case Pair 5 (coach view) still references the original specs.

**Files to create / edit.**

```
docs/16-trainee-progress-drilldown.md    # NEW — covers /skills overview + /skills/:cat + radar behavior
docs/17-trainee-profile-page.md          # NEW — covers /profile fields, edit semantics, notifications
docs/18-coach-bio-page.md                # NEW — covers /coach list + /coach/:id bio, bio JSONB shape
docs/12-data-model.md                    # EDIT — append: workspace_memberships.bio, user_notification_prefs
docs/09-empty-states.md                  # EDIT — add: trainee /coach empty, /skills empty (no assessments)
docs/11-localization-rules.md            # EDIT — add: coach bio fields don't auto-translate; skill chips stay native
docs/README.md                           # EDIT — list the 3 new docs in the table
```

**Implementation notes.**

- Each new doc follows the structure of `docs/02-coach-today.md`: Purpose · Data requirements · Components · Interactions · States · Empty states · Localization · Design rationale.
- Don't rewrite `docs/05-trainee-home.md`; it still describes the Home tab. The Progress tab is a sibling, not a replacement.
- For the data model edits, paste only the new column + new table into the existing file at the right section — don't reorder existing content.

**Done when.**

- [ ] 3 new docs exist and are listed in `docs/README.md`.
- [ ] `docs/12-data-model.md` shows the bio column on the memberships table and the notification prefs table.
- [ ] `docs/09-empty-states.md` and `docs/11-localization-rules.md` reflect the new screens.

---

# Verification (end-to-end after Pair C)

A single click-through that proves the revamp lands:

1. Sign in as a fresh trainee (claim invite, land on `/home`).
2. Tap **Progress** → `/skills` renders 4-axis radar with empty/gray spokes (no assessments yet).
3. In a second window, sign in as a coach → assess 8 of 13 technical skills + 2 tactical → save.
4. Back in the trainee window, reload → radar now has a partial polygon; the technical sector is the strongest.
5. Tap **Technical** → `/skills/technical` shows 13-axis sub-radar, 8 filled + 5 dotted gray. Below: "X of these 13 are blocking Silver" callout, skill list with marked rows.
6. Tap **Profile** → `/profile` shows identity, account, notifications. Edit display name → "Saved" toast → reload preserves it. Toggle locale to ID → entire chrome flips, skill names stay native.
7. Tap **Coach** → `/coach` shows the coach who just assessed you. Tap their row → bio page renders with photo, headline, credentials, specialties.
8. Sign out from `/profile` → routes to `/signin`.

If any step fails, the issue is in that pair's BE↔FE contract — don't advance past it.

---

# Out of scope for this revamp (explicit)

So they don't get scope-crept in mid-build:

- Per-skill detail page (`/skills/:cat/:skill` with score history sparkline) — deferred to V1.5.
- Coach-side editing of their own bio (`/coach/me/edit`) — coach's bio is seeded for now; editing UI is V1.5.
- Coach-side viewing of trainee profile or progress — the existing `docs/03-coach-trainee-profile.md` covers this and is untouched by this revamp.
- Parent-specific app or screens — parents still receive PDF only.
- Multi-workspace coach bio editing — out of scope; one bio per membership row covers it.
- Trainee → trainee browsing — trainees only see their own data and their own coaches; no roster.

---

# Suggested order of work (calendar view)

If a solo dev runs this end-to-end at the pace of `docs/15-build-plan.md`:

| Pair | Steps | Calendar estimate |
|------|-------|-------------------|
| A    | A1 → A2 → A3 | ~5 working days |
| B    | B1 → B2 | ~3 working days |
| C    | C1 → C2 → C3 → C4 | ~4 working days |

~2 weeks total, assuming Pairs 1–6 of the existing build plan have landed. If they haven't, do those first — this revamp depends on auth, workspaces, sessions, and assessments existing as real data.
