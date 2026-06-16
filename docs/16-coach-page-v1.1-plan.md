# Coach Page v1.1 — Single-PR Implementation Plan

> Source: design review on 2026-05-16. Everything below ships as **one PR**: `feat(coach): v1.1 — funnel, multi-focus, coach attribution, polish`. The work is split into phases for review readability, but it's one branch, one PR, one merge.
>
> Follow `CLAUDE.md` conventions throughout: TS strict, sentence case, 0.5px hairlines, RLS on every tenant table, i18n via `locales/*.json`, no shadows, accent only via `--accent`, two font weights (400/500), tap target ≥ 44px.

---

## Branch and commit

- Branch: `feat/coach-v1.1`
- Commits (one per phase below, conventional-commit style — keeps `git log` readable even though it merges as one PR):
  1. `fix(web): invalidate today-sessions cache on session mutate`
  2. `feat(web): searchable trainee combobox`
  3. `feat(api,db): session_focuses join table + multi-focus API`
  4. `feat(web): multi-focus chip group + display sites`
  5. `feat(api,web): coach attribution + read-only mode on recent sessions`
  6. `feat(api,web): assessment funnel segmented control + counts`
  7. `feat(web,api): session completed + no-show + conflict warning`
  8. `feat(web): up-next correctness, time grouping, auto-save, drafting-coach banner`

---

## Phase 1 — Fix cache invalidation (commit 1)

**Root cause.** `apps/web/src/features/sessions/SessionsScreen.tsx`'s `invalidate()` only touches `['sessions', workspaceId]`. The Home screen queries `['today-sessions']` (in `apps/web/src/features/today/CoachTodayScreen.tsx`), which is never invalidated. `AssessmentScreen.tsx` invalidates `['coach-today']` (wrong key) instead.

**Files**
- `apps/web/src/features/sessions/sessions-api.ts` — add shared helper.
- `apps/web/src/features/sessions/SessionsScreen.tsx`
- `apps/web/src/features/sessions/ScheduleSessionSheet.tsx`
- `apps/web/src/features/assessment/AssessmentScreen.tsx`

**Changes**
1. Add `export function invalidateSessionCaches(qc: QueryClient)` in `sessions-api.ts` that invalidates:
   - `['sessions']` (broad — catches all variants)
   - `['today-sessions']`
   - `['trainee-profile']`
   - `['feedback-inbox']`
   - `['sessions','funnel','counts']` (new in Phase 6)
2. Replace every ad-hoc `qc.invalidateQueries(...)` for session-related keys with this helper.
3. Delete the bogus `['coach-today']` invalidation in `AssessmentScreen.tsx`.

**Acceptance**
- Create a session on `/sessions`, navigate to `/today` — it appears without refresh.
- Cancel a session on `/sessions` — disappears from `/today` immediately.
- Publish an assessment — counts and badges update without refresh.

---

## Phase 2 — Searchable trainee combobox (commit 2)

Replace the plain `<select>` athlete picker in `ScheduleSessionSheet` with a searchable combobox.

**Files**
- New: `apps/web/src/components/TraineeCombobox.tsx`
- `apps/web/src/features/sessions/ScheduleSessionSheet.tsx`
- `apps/web/src/locales/en.json`, `apps/web/src/locales/id.json`

**Component spec**
- Built on Radix `Popover` + native `<input>` (no extra dep).
- Props: `value: string | null`, `onChange: (id: string) => void`, `trainees: SessionTrainee[]`, `placeholder?`, `disabled?`.
- Trigger styled like the existing select (min-h-tap, 0.5px hairline border, accent on focus).
- Opens → input focused → filters `displayName` case-insensitive, accent-stripped.
- Shows `<TierPill>` next to each row.
- "Recent" section pinned at top: last 5 trainees the coach scheduled, stored in `localStorage` key `recent-trainees:<workspaceId>`.
- Empty state: "No trainee matches. Add a new trainee?" → links to `/trainees/new`.
- Keyboard: ↑/↓ navigate, Enter selects, Esc closes.

**i18n additions**
```
sessions.sheet.athletePlaceholder = "Search trainee"
sessions.sheet.athleteEmpty = "No trainee matches"
sessions.sheet.athleteRecent = "Recent"
sessions.sheet.athleteAddNew = "Add a new trainee"
```
Plus ID equivalents.

**Acceptance**
- Typing "an" in a 60-trainee workspace narrows results within one frame.
- Recent trainees appear first when input is empty.
- Mobile keyboard does not push the popover off-screen (iOS Safari).

---

## Phase 3 — Multi-focus: schema + API (commit 3)

A session can have multiple focuses. Use a join table for analytics-friendliness.

**DB migration** (`alembic revision -m "add_session_focuses_join_table"`):
```sql
create table session_focuses (
  session_id uuid not null references sessions(id) on delete cascade,
  focus text not null,
  ordinal smallint not null default 0,
  workspace_id uuid not null,
  primary key (session_id, focus)
);
alter table session_focuses enable row level security;
create policy tenant_isolation on session_focuses
  using (workspace_id = current_setting('app.current_workspace_id')::uuid);
```
- Backfill: one row per existing session from `sessions.focus`.
- Keep `sessions.focus` as nullable + deprecated for one release.

**BE files**
- `apps/api/src/sessions/schemas.py` — change `SessionCreateIn.focus` / `SessionUpdateIn.focus` from `SessionFocus | None` to `list[SessionFocus]` (0–4). Change `SessionOut.focus` from `str | None` to `list[str]` (sorted by `ordinal`).
- `apps/api/src/sessions/service.py` — read/write through the join table.
- `apps/api/src/sessions/router.py` — OpenAPI/docstring update.

**Tests**
- `apps/api/tests/test_sessions.py`: create/update/list with multi-focus; cross-workspace RLS isolation.

---

## Phase 4 — Multi-focus: FE (commit 4)

**Files**
- `apps/web/src/features/sessions/sessions-api.ts` — rename `focus: SessionFocus | null` → `focuses: SessionFocus[]`; update `toSession`.
- `apps/web/src/features/sessions/ScheduleSessionSheet.tsx` — chip group toggles instead of single-select: `setFocuses(prev => prev.includes(f) ? prev.filter(x => x !== f) : [...prev, f])`.
- Display sites — update everywhere `s.focus` is read:
  - `apps/web/src/features/sessions/SessionsScreen.tsx`
  - `apps/web/src/features/today/UpNextCard.tsx`
  - `apps/web/src/features/today/today-api.ts`
  - `apps/web/src/features/trainee-profile/RecentSessions.tsx`
  - PDF report generator (if it renders focus).
- Render rule: join focus labels with ` · `; max 2 visible; `+N` overflow chip when >2.

**Acceptance**
- Create a session with `["drilling", "technique_focus"]`, edit to add `"mental_training"`, all three render on the card.
- Existing sessions still display their original focus post-backfill.
- BE rejects requests with >4 focuses (422).

---

## Phase 5 — Coach attribution + read-only assessment (commit 5)

**BE**
- `apps/api/src/profile/schemas.py` — extend `SessionEntry`:
  ```python
  coach: CoachBrief
  assessment_status: Literal["none", "draft", "published", "edited"] | None
  ```
- `apps/api/src/profile/service.py` — join coach + assessment when building recent sessions.

**FE**
- `apps/web/src/features/trainee-profile/profile-types.ts` — extend `SessionEntry`:
  ```ts
  coach: { id: string; displayName: string };
  assessmentStatus: 'none' | 'draft' | 'published' | 'edited';
  ```
- `apps/web/src/features/trainee-profile/RecentSessions.tsx`:
  - Render a small coach line ("Coach · Andre" with `<Avatar size={16}>`).
  - Reuse the `<StatusPill>` from `SessionsScreen` — extract to `apps/web/src/features/sessions/StatusPill.tsx` so both screens import it.
  - `const isOwn = s.coach.id === currentUser.id;`
    - own → `/trainees/:id/assess?session=:sid`
    - not own → `/trainees/:id/assess?session=:sid&readonly=1`
- `apps/web/src/features/assessment/AssessmentScreen.tsx`:
  - Read `readonly` from `useSearchParams`.
  - When `readonly`:
    - Hide Save / Publish buttons (header right side empty).
    - Disable score chips, summary textarea, session-details strip.
    - Banner above the score list: "Read only — assessed by Coach Andre on 12 May."
  - `useAssessmentDraft` stays hydrated, never dirty, no auto-save in this mode.

**Acceptance**
- Coach A opens a session Coach B assessed on Trainee X's profile → cannot edit; banner names Coach B.
- Coach B opens the same session → can edit and publish.
- Coach name on the card matches Recent Gains and the PDF report.

---

## Phase 6 — Assessment funnel segmented control (commit 6)

**Stages**

| Stage | Predicate | Pill |
|---|---|---|
| Upcoming | `status='scheduled'` AND `scheduledAt > now` | hairline + tertiary text |
| To assess | `scheduledAt < now` AND `assessmentStatus IS NULL` AND `status NOT IN ('cancelled','no_show')` | accent bg + accent text |
| Draft | `assessmentStatus = 'draft'` | accent-bg/5 + accent border |
| Published | `assessmentStatus IN ('published','edited')` | success-bg + success-text |
| Cancelled | `status IN ('cancelled','no_show')` | bg-secondary + tertiary text |

**BE**
- `GET /sessions` — add derived `funnel_stage` field on the response (FE and PDF share the logic). Keep existing fields for back-compat.
- `GET /sessions` — accept optional `?stage=upcoming|to_assess|draft|published|cancelled`.
- New: `GET /sessions/funnel/counts` → `{upcoming, to_assess, draft, published, cancelled}`.

**FE**
- New: `apps/web/src/components/SegmentedControl.tsx` — iOS-style single-select with count badges; Tailwind, no library.
- `SessionsScreen.tsx`:
  - Default tab: `to_assess` if its count > 0, else `upcoming`.
  - Replace the "Upcoming / Past" sections with one list driven by selected stage.
  - Sticky segmented control under header (`top-0` + `bg-bg-tertiary`).
- `BottomTabBar.tsx`:
  - `useQuery(['sessions','funnel','counts'])` and show a small count dot on the Sessions tab when `to_assess > 0`.
- `CoachTodayScreen.tsx`:
  - If `to_assess > 0`, surface a row above Up Next: "3 sessions to assess →" linking to `/sessions?stage=to_assess`.

**i18n additions**
```
sessions.funnel.upcoming = "Upcoming"
sessions.funnel.toAssess = "To assess"
sessions.funnel.draft = "Drafts"
sessions.funnel.published = "Published"
sessions.funnel.cancelled = "Cancelled"
today.toAssessBadge_one = "{{count}} session to assess"
today.toAssessBadge_other = "{{count}} sessions to assess"
```

**Acceptance**
- Past session with no assessment is in "To assess" with an accent pill.
- Saving a draft moves it from "To assess" → "Drafts" without refresh.
- Publishing moves it from "Drafts" → "Published".
- Bottom-nav dot disappears when "To assess" count hits 0.

---

## Phase 7 — Completed / no-show / conflict warning (commit 7)

**BE**
- `POST /sessions/{id}/complete` — sets `status='completed'`, `completed_at=now()`.
- `POST /sessions/{id}/no_show` — sets `status='no_show'`.
- `GET /sessions/conflicts?scheduled_at=…&duration_min=…&athlete_id=…&exclude_session_id=…` → `{coachConflicts: Session[], traineeConflicts: Session[]}`.

**FE**
- `SessionCard` (in `SessionsScreen.tsx`) — overflow menu (Radix Dropdown): Edit · Mark completed · Mark no-show · Cancel.
- `ScheduleSessionSheet.tsx` — on datetime `onBlur` call `/sessions/conflicts` and render a yellow inline warning above the date field if any. Non-blocking.

**Acceptance**
- "Completed" moves a session out of Upcoming; still appears in "To assess" if no assessment exists.
- Scheduling a session overlapping an existing one (same trainee or same coach) shows a soft warning, save still works.

**Explicit non-goal:** auto-marking past sessions completed is a server-side scheduled job — V1.2.

---

## Phase 8 — Polish (commit 8)

**8a — Up Next picks the next future session, not `sessions[0]`.**
- `CoachTodayScreen.tsx`: `const upNext = sessions.find(s => s.scheduledAt > new Date()) ?? null;`

**8b — Time-of-day grouping on Today's trainee list.**
- Group Morning (<12) / Afternoon (12–17) / Evening (≥17) via `<GroupedTable header={…}>` per bucket.

**8c — Auto-save assessment draft on idle.**
- `AssessmentScreen.tsx` — debounce 10s after any draft state change → call `handleSaveDraft()` if `draft.isDirty && online`.
- Don't auto-save published assessments.
- Status strip already supports the "Saving…" / "Saved" microcopy.

**8d — "Another coach is drafting" banner** (replaces the hard-coded `isReadOnlyForOthersDraft = false`).
- BE: surface `coach_id` on the assessment via `getBySession`.
- FE: if `draft.coachId && draft.coachId !== currentUser.id && draft.status === 'draft'` → force read-only, banner: "Coach Andre is currently drafting this assessment."

---

## PR description template

```
## What
Coach page v1.1 — addresses review on 2026-05-16. Eight phased commits:
1. Cache invalidation bug (Today not refreshing on session create)
2. Searchable trainee combobox
3. Multi-focus on sessions — schema + API
4. Multi-focus on sessions — UI
5. Coach attribution + read-only assessment for other coaches' sessions
6. Assessment funnel segmented control (Upcoming / To assess / Drafts / Published / Cancelled)
7. Mark completed / no-show + conflict warning
8. Polish: up-next correctness, time-of-day grouping, auto-save draft, drafting-coach banner

## Why
[link to review notes]

## Screens
- Today (before / after)
- Sessions (segmented control)
- Schedule sheet (combobox + multi-focus)
- Trainee profile recent sessions (coach name + status pill)
- Assessment (read-only mode)

## Test plan
- `pnpm typecheck && pnpm lint` clean
- `pytest` clean (new RLS + multi-focus tests)
- Playwright: schedule → assess → publish funnel walk-through
- Manual mobile smoke (iOS Safari, 375px viewport)
```

---

## Non-goals (explicitly deferred)

- Recurring sessions ("repeat weekly") — V1.2
- Block-time / non-trainee events on the schedule — V1.2
- Per-skill "previous level" hint inside the assessment — V1.2
- Pull-to-refresh — V1.2
- Dedicated Assessments bottom-nav tab — V2 (segmented control covers MVP)

---

## Conventions checklist (must hold across every commit)

- `pnpm typecheck` and `pnpm lint` pass before push.
- Every user-facing string in `apps/web/src/locales/en.json` AND `id.json`.
- New BE endpoints have RLS verified via test (assert cross-workspace 404).
- No shadows, no Material, no font weight ≥ 600, tap target ≥ 44px.
- Single accent — `text-accent` / `bg-accent` / `border-accent` only; never hardcode `#378ADD`.
- One PR, eight commits, conventional-commit subjects.

---

## How to use this with Claude CLI in Cursor

```
read docs/16-coach-page-v1.1-plan.md and implement it as one PR on a new branch
feat/coach-v1.1. Work phase by phase, commit at the end of each phase per the
commit list above, run typecheck + lint between phases, do not progress to the
next phase until the current one is clean.
```
