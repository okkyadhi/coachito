# 21 — Tennis Activation Implementation Plan (V2)

> Engineering plan to activate **tennis** as the platform's second sport — from
> "row exists, inactive" to a fully usable sport a workspace can be created in.
> Companion to `docs/tennis-skill-framework-v0.md` (the curriculum content).
> Written to be executed step-by-step in Cursor + Claude Code.

## How to use this doc

Work the phases in order. Each phase is a reviewable unit — one branch, one PR.
Conventional-commit scopes are noted per phase. Do not start a phase until the
previous one's PR is merged, unless marked *parallel-safe*. Run
`pnpm typecheck && pnpm lint` and `pytest` before every PR (see `CLAUDE.md`).

Curriculum content (skill list, 125 descriptors, tiers, thresholds) is **not**
re-derived here — it lives in `docs/tennis-skill-framework-v0.md`. This plan
turns that content into shipped product.

---

## 0. Context

- **Decision log #2** (`CLAUDE.md`): the platform has been multi-sport-ready
  since day 1 — padel MVP, tennis V2. The refactor cost was paid up front; this
  plan spends the ~3 weeks that investment was meant to save.
- **`CLAUDE.md` MVP scope** lists "Tennis activation (architecture ready, not
  surfaced)" as *out of MVP*. Activating tennis is therefore an explicit,
  deliberate V2 scope expansion — confirm with the product owner before
  starting (this is a "rescope" decision per the `CLAUDE.md` feature process).
- Goal of V2 tennis: a coach can create a **tennis** workspace, add trainees,
  run the 25-skill ITF assessment, see tier progression (Red→Yellow Ball), and
  get the monthly PDF — full feature parity with padel.

---

## 1. Current-state audit

### Already sport-scoped (no change needed — verify only)

The schema and most services already key off `sport_id`. These read sport from
the workspace and should "just work" once tennis data exists:

- `sports`, `curricula`, `skills`, `skill_level_descriptors`, `tiers`,
  `tier_requirements` — all sport-scoped tables (migrations `0001`, `0003`).
- `workspaces.sport_id` + `workspaces.curriculum_id` (NULL = platform default
  for the sport).
- Services referencing `sport`: `assessments/service.py`,
  `athletes/profile.py`, `curriculum/router.py`, `skills/me_service.py`,
  `skills/router.py`, `reports/template.py`.

### Hardcoded to padel — MUST fix (each phase below addresses one)

| Location | Problem | Phase |
|----------|---------|-------|
| `apps/api/src/workspaces/service.py` — `_get_padel_sport_id()` | Workspace creation always forces the padel sport | 4 |
| `apps/api/src/workspaces/schemas.py` — `WorkspaceCreateIn` | No `sport_code` field; caller can't pick a sport | 4 |
| `apps/api/src/ai/prompts/summary_en.py` / `summary_id.py` | Prompt hardcodes "padel coach" | 4 |
| `apps/api/src/invites/router.py` (~lines 83–108) | Invite landing copy hardcodes "padel progress" (EN + ID) | 4 |
| `apps/web/src/features/assessment/descriptors.ts` | Static padel-only descriptor table baked into the FE bundle | 5 |
| `apps/web/src/features/curriculum/SkillDetailScreen.tsx` (~line 47) | Comment + logic assume "5 levels → 5 main tiers" | 5 |
| `apps/web/src/features/settings/settings-api.ts` (~line 71) | Mock string `'APPA padel · v1'` | 5 |

### Seed-data naming inconsistency

`apps/api/data/` currently holds `skills_padel.json` and `descriptors_padel.json`
(sport-suffixed) but `tiers.json` and `tier_requirements.json` (no suffix). Fix
the inconsistency in Phase 1 so the seed loop is uniform.

---

## Phase 1 — Curriculum seed data

**Branch:** `feat/tennis-seed-data` · **scope:** `db` · *parallel-safe with Phase 0 sign-off*

Create the tennis JSON, normalise the padel filenames. No code logic yet.

- [ ] Rename `apps/api/data/tiers.json` → `tiers_padel.json`
- [ ] Rename `apps/api/data/tier_requirements.json` → `tier_requirements_padel.json`
- [ ] Create `apps/api/data/skills_tennis.json` — **25** rows. Codes, categories,
      names, `short_label_*`, `display_order` from
      `tennis-skill-framework-v0.md` §2. `name_en == name_id` for shot names
      (they don't translate); `short_label_*` ≤ 14 chars (see `0026` migration).
- [ ] Create `apps/api/data/descriptors_tennis.json` — **125** rows (25 × 5).
      `description_en` verbatim from framework §4. `description_id` — draft a
      translation, then flag for native-ID-speaker review (Phase 6 / framework
      §13). Do not block the seed on perfect ID copy.
- [ ] Create `apps/api/data/tiers_tennis.json` — **7** rows from framework §6
      (codes `RED`, `ORANGE`, `GREEN`, `YELLOW`, `ITN_9`, `ITN_7`, `ITN_5`;
      `name_game_*`, `name_skill_*`, `color_hex`, `icon_name`).
- [ ] Create `apps/api/data/tier_requirements_tennis.json` — graduation
      thresholds from framework §7. **MVP**: include `ORANGE`, `GREEN`,
      `YELLOW` blocks (Red has none). **Deferred** blocks (`ITN_9`, `ITN_7`,
      `ITN_5`) — include them in the file but they are inert until those tiers
      ship; the "all skills meet minimum" deferred rows that say "All technical
      skills" must be expanded to explicit `skill_code` entries.
- [ ] Validate every `skill_code` in `tier_requirements_tennis.json` and
      `descriptors_tennis.json` exists in `skills_tennis.json` (no typos).

**Acceptance:** `python -c "import json; ..."` count check — 25 skills, 125
descriptors, 7 tiers; all requirement skill codes resolve.

---

## Phase 2 — Seed script refactor

**Branch:** `feat/tennis-seed-script` · **scope:** `db`

Make `apps/api/scripts/seed.py` sport-agnostic so it seeds padel and tennis from
the same loop. Today it is a single hardcoded padel pass.

- [ ] Introduce a sport-config list, e.g.:
      ```python
      SPORTS = [
          {"code": "padel",  "curriculum_code": "padel-default-appa",
           "curriculum_name_en": "Padel Default (APPA-aligned)", ...},
          {"code": "tennis", "curriculum_code": "tennis-default-itf",
           "curriculum_name_en": "Tennis Default (ITF-aligned)", ...},
      ]
      ```
- [ ] Loop each sport: resolve `sport_id`, upsert its `curricula` row, then load
      `skills_{code}.json`, `descriptors_{code}.json`, `tiers_{code}.json`,
      `tier_requirements_{code}.json`.
- [ ] Keep idempotency intact. Conflict targets stay the partial unique indexes
      from migration `0008` (`uq_skills_platform_code`,
      `uq_descriptors_platform_level`, `uq_tiers_platform_code`,
      `uq_curricula_platform_code`). Tennis tier codes (`RED`, …) and skill
      codes (`TENNIS_*`) never collide with padel — the conflict targets include
      `sport_id`.
- [ ] Per-sport counts in the seed's stdout summary (so re-runs are auditable).
- [ ] Re-run the seed twice locally; confirm row counts are unchanged on the
      second run (idempotency).

**Watch out:** the seed currently inserts the `tennis` sport row with
`is_active = FALSE` and `ON CONFLICT (code) DO NOTHING`. Re-running the seed will
**not** flip `is_active` — that is deliberately handled by a migration in
Phase 3, not the seed.

**Acceptance:** fresh `docker compose ... down -v && up -d`, `alembic upgrade
head`, `python -m scripts.seed` — tennis curriculum, 25 skills, 125 descriptors,
7 tiers, all requirements seeded; second run is a no-op.

---

## Phase 3 — Activate the sport row

**Branch:** `feat/tennis-activate-sport` · **scope:** `db`

- [ ] New migration `apps/api/alembic/versions/0030_activate_tennis.py`:
      `UPDATE sports SET is_active = TRUE WHERE code = 'tennis'`. `downgrade()`
      sets it back to `FALSE`.
- [ ] **Recommended gating:** keep this migration on a branch / unmerged (or
      apply it only in the rollout step, Phase 9) until the curriculum is
      advisor-validated. Code and data for tennis can land while `is_active`
      stays `FALSE` — the sport picker (Phase 5) only shows active sports, so
      tennis stays invisible to users until the flag flips. This lets Phases
      1–8 merge safely without exposing an unvalidated curriculum.

**Acceptance:** with the migration applied, `SELECT code, is_active FROM sports`
shows tennis active; with it reverted, inactive.

---

## Phase 4 — Backend: sport selection

**Branch:** `feat/tennis-backend` · **scope:** `api`

Let workspace creation choose a sport, and de-hardcode padel in API copy.

- [ ] `workspaces/schemas.py` — add `sport_code: Literal["padel", "tennis"] =
      "padel"` to `WorkspaceCreateIn` (default keeps existing clients working).
- [ ] `workspaces/service.py` — replace `_get_padel_sport_id()` with
      `_get_sport_id(db, code)`; validate the sport exists **and**
      `is_active = TRUE` (reject inactive sports with a 422/400). Pass
      `sport_code` through `create_workspace_with_owner(...)`.
- [ ] `workspaces/router.py` — thread `sport_code` from the request body into
      the service call.
- [ ] Add **`GET /sports`** (public, no auth or auth-light) returning active
      sports `[{code, name_en, name_id}]` — the FE sport picker needs it
      (Phase 5). Register in `main.py`.
- [ ] Confirm `workspaces.curriculum_id` left `NULL` resolves to the sport's
      platform-default curriculum everywhere it's read. If any query assumes
      padel, fix it. Audit: `assessments/service.py`, `athletes/profile.py`,
      `skills/me_service.py`, `curriculum/router.py`, the tier calculation
      (`calculate_tier`, see `docs/12-data-model.md` §"Tier of an athlete").
- [ ] `ai/prompts/summary_en.py` + `summary_id.py` — parametrise the sport word
      ("padel coach" / "pelatih padel" → "tennis coach" / "pelatih tenis"). Pass
      the workspace's sport name into the prompt builder.
- [ ] `invites/router.py` — parametrise the sport word in the landing copy
      (EN + ID, ~lines 83–108) the same way.

**Tests:** create-tennis-workspace test; assert the workspace gets the tennis
`sport_id` and the tennis default curriculum resolves; assert creating a
workspace for an **inactive** sport is rejected.

**Acceptance:** `POST /workspaces {sport_code: "tennis"}` succeeds (once tennis
is active) and the new workspace surfaces tennis skills/tiers via existing
endpoints.

---

## Phase 5 — Frontend: sport picker & de-hardcode

**Branch:** `feat/tennis-web` · **scope:** `web`

- [ ] **Workspace creation flow** — add a sport step (Padel / Tennis). Fetch
      `GET /sports`; render only active sports. If only one sport is active,
      skip the step and default silently (so the UI doesn't regress for
      padel-only state). Send `sport_code` in the create payload.
- [ ] **`features/assessment/descriptors.ts`** — this static table is padel-only
      and will show wrong/empty descriptors for tennis. Two options:
      - **(A) preferred** — make descriptors API-driven. The curriculum / skills
        endpoints already return descriptors per workspace sport; drop the
        static table and read from the API (cache via TanStack Query +
        IndexedDB so the offline-first assessment flow still works).
      - **(B) fallback** — if the offline-first assessment must keep a static
        bundle, split into `descriptors.padel.ts` / `descriptors.tennis.ts` and
        select by the active workspace's sport.
      Pick (A) unless offline constraints force (B); record the choice in the PR.
- [ ] **`features/curriculum/SkillDetailScreen.tsx`** (~line 47) — remove the
      "5 levels → 5 main tiers" assumption; derive tier count from the tiers the
      API returns for the workspace (padel ships 3 MVP tiers, tennis ships 4).
- [ ] **`features/settings/settings-api.ts`** (~line 71) — replace the mock
      `'APPA padel · v1'` with the real curriculum name from the API.
- [ ] Audit any padel-specific imagery/illustration (court graphics, empty-state
      art). Make sport-aware or use neutral art. Keep the iOS design language
      unchanged (`docs/01-design-principles.md`).
- [ ] Tier badge component — confirm it renders tennis tier `color_hex` /
      `icon_name` (Red/Orange/Green/Yellow) with no padel-specific styling.

**Acceptance:** create a tennis workspace in the UI; assessment screen lists the
25 tennis skills with correct descriptors; tier badge shows Red Ball; no padel
copy or imagery leaks into a tennis workspace.

---

## Phase 6 — Localization

**Branch:** `feat/tennis-i18n` · **scope:** `web` · *parallel-safe with Phase 5*

- [ ] `apps/web/src/locales/en.json` + `id.json` — add: tennis sport name, the
      sport-picker copy, tennis tier names (game style = ball colours, skill
      style = Starter/Developing/Rallying/Match Ready).
- [ ] Tennis **shot names do not translate** — "slice", "lob", "drop shot",
      "overhead", "approach", "volley", "forehand", "backhand" stay English in
      the ID locale (framework §11). This mirrors the padel rule (Spanish terms
      stay) — same mechanism, different vocabulary. Skill names live in
      curriculum data, not locale files (`CLAUDE.md` convention).
- [ ] Native-Indonesian-speaker review of the 125 `description_id` strings in
      `descriptors_tennis.json` and the tennis tier labels. Per `CLAUDE.md`,
      copy-tone review is a human step — schedule it, don't skip it.
- [ ] Update `docs/11-localization-rules.md` with a tennis section (what
      translates, what stays English).

**Acceptance:** switch locale to ID inside a tennis workspace — UI translates,
shot names stay English, no missing-key fallbacks.

---

## Phase 7 — PDF reports

**Branch:** `feat/tennis-reports` · **scope:** `api` · *parallel-safe with Phase 5/6*

- [ ] Verify `reports/template.py` + `templates/report.html` / `report.css`
      render tennis tier badges/colours and the 4-category radar (the radar is
      category-average based, so already sport-agnostic — confirm, don't assume).
- [ ] Verify the report's curriculum/tier labels come from data, not hardcoded
      padel strings.
- [ ] Add a tennis PDF smoke test alongside `scripts/test_pdf_smoke.py`.

**Acceptance:** generate a monthly PDF for a tennis trainee — correct tier,
correct skill names, no padel artefacts.

---

## Phase 8 — Testing

**Branch:** `feat/tennis-tests` · **scope:** `api` + `web`

- [ ] Seed test — assert tennis seeds 25 skills, 125 descriptors, 7 tiers, and
      that re-running is idempotent.
- [ ] Tier-calculation unit test — feed synthetic tennis skill scores, assert
      Red→Orange→Green→Yellow graduation and blocking-skill output match
      framework §7 thresholds.
- [ ] E2E happy path for tennis — mirror `apps/api/tests/test_e2e_happy_path.py`:
      create tennis workspace → add trainee → assess skills → cross a tier
      threshold → generate monthly PDF.
- [ ] Web: assessment-flow test for a tennis workspace (25 skills render,
      descriptors load, offline save works).
- [ ] Full gate green: `pnpm typecheck`, `pnpm lint`, `pnpm test`, `pytest`.

---

## Phase 9 — Rollout

**Branch:** `chore/tennis-launch` · **scope:** `infra` / `db`

- [ ] **Advisor validation** — an ITF-certified coach reviews the 125
      descriptors and tier thresholds (framework §13). Apply edits via a data
      migration or a re-seed, not by hand-editing prod.
- [ ] Native-ID-speaker sign-off on ID copy (Phase 6) complete.
- [ ] Apply migration `0030_activate_tennis.py` to staging; smoke-test the full
      tennis happy path.
- [ ] Apply `0030` to production. Tennis becomes selectable the moment
      `is_active` flips — confirm the sport picker shows it.
- [ ] Optional: pilot with 1–2 tennis clubs before broad announcement (mirrors
      the padel pilot approach).
- [ ] Update `CLAUDE.md` — move "Tennis activation" from *Out of MVP* to shipped;
      add a decision-log row for the V2 tennis scope expansion.

---

## File change summary

| File | Phase | Change |
|------|-------|--------|
| `apps/api/data/tiers.json` → `tiers_padel.json` | 1 | rename |
| `apps/api/data/tier_requirements.json` → `..._padel.json` | 1 | rename |
| `apps/api/data/skills_tennis.json` | 1 | new (25) |
| `apps/api/data/descriptors_tennis.json` | 1 | new (125) |
| `apps/api/data/tiers_tennis.json` | 1 | new (7) |
| `apps/api/data/tier_requirements_tennis.json` | 1 | new |
| `apps/api/scripts/seed.py` | 2 | sport-agnostic loop |
| `apps/api/alembic/versions/0030_activate_tennis.py` | 3 | new migration |
| `apps/api/src/workspaces/schemas.py` | 4 | `sport_code` field |
| `apps/api/src/workspaces/service.py` | 4 | sport lookup by code |
| `apps/api/src/workspaces/router.py` | 4 | thread `sport_code` |
| `apps/api/src/main.py` | 4 | register `GET /sports` |
| `apps/api/src/ai/prompts/summary_en.py` / `summary_id.py` | 4 | parametrise sport word |
| `apps/api/src/invites/router.py` | 4 | parametrise sport word |
| `apps/web/.../onboarding` (workspace create flow) | 5 | sport-picker step |
| `apps/web/src/features/assessment/descriptors.ts` | 5 | API-driven or per-sport |
| `apps/web/src/features/curriculum/SkillDetailScreen.tsx` | 5 | dynamic tier count |
| `apps/web/src/features/settings/settings-api.ts` | 5 | real curriculum name |
| `apps/web/src/locales/en.json` / `id.json` | 6 | tennis strings |
| `docs/11-localization-rules.md` | 6 | tennis section |
| `apps/api/src/reports/template.py` + templates | 7 | verify sport-agnostic |
| `apps/api/tests/` (+ web tests) | 8 | tennis seed / tier / E2E |
| `CLAUDE.md` | 9 | scope + decision-log update |

---

## Risks & watch-outs

- **Unvalidated curriculum exposure** — the v0 descriptors are built from public
  ITF knowledge, not advisor-validated. Keep `is_active = FALSE` (Phase 3) until
  validation is done so no pilot sees unvalidated content.
- **`descriptors.ts` static table** — the single biggest FE refactor. It exists
  for the offline-first assessment flow; changing it to API-driven must not
  break courtside-offline assessment. Test offline explicitly.
- **`curriculum_id` NULL resolution** — workspaces store `NULL` for the platform
  default; every read path must resolve "default curriculum for *this sport*",
  not "the padel default". This is the most likely place a hidden padel
  assumption hides. Audit carefully in Phase 4.
- **Tier count assumption** — padel ships 3 MVP tiers, tennis ships 4. Any UI
  that hardcodes a tier count (progress bars, `SkillDetailScreen`) will break.
- **Scope** — activating tennis is a deliberate V2 expansion beyond the locked
  MVP. Get explicit product sign-off before Phase 1 (`CLAUDE.md` feature
  process).

---

## Out of scope for this plan

- Doubles-specific tennis skills (framework §14 — singles-first v0).
- The ITN On-Court Assessment as a measured drill battery (framework §12).
- Drill library, match metrics, custom per-club tennis skills (all post-V2).
- New screens or design work — tennis reuses every padel screen via
  conditional data; no new layouts. If a screen needs redesign, that's a
  separate human-led design task (`CLAUDE.md` "Out of scope for Claude Code").

---

*Companion: `docs/tennis-skill-framework-v0.md` (curriculum content).
Build-plan conventions follow `docs/15-build-plan.md`.*
