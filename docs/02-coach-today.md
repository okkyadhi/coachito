# Coach · Today

> Coach home screen showing today's scheduled trainees and a quick path into assessing them.

## Purpose

The coach's **default landing screen** when opening the app. Optimized for the most common task: see who's scheduled today, tap to start their assessment. Surfaces the "next session" prominently and lists today's trainee roster as a tappable list.

## Audience

- **Role:** Coach (any level — Head Coach, Coach in a club, Solo Coach in a personal workspace)
- **Workspace types:** Both `club` and `personal`
- **Context:** Opened first thing in the morning, between sessions, or right after a session finishes

## Layout (top to bottom)

1. **Status bar** — system, with workspace name on the right
2. **Greeting block**
   - Large title: "Halo, Coach Novia" / "Hi, Coach Novia" (uses display name)
   - Subtitle: full date — "Sunday, 10 May 2026 · 5 sessions"
3. **"Up next" card** (single grouped row)
   - Calendar icon (accent color)
   - "8:00 · Andi Pratama" / "Court 2 · 60 min · Drilling"
   - Right chevron, taps into trainee profile or assessment
4. **"Trainees today" section**
   - Grouped table of trainees scheduled for today
   - Each row: avatar (initials, accent-bg) + name + "{time} · {last assessed}" + tier pill + chevron
5. **Bottom tab bar** — Today (active) / Trainees / Sessions / Reports / Settings

## Components used

- Grouped table pattern (`01-design-principles.md`)
- Tier pill (MVP variants: `Beginner` / `Lower Bronze` / `Bronze` — Silver+ are post-MVP)
- Avatar circle (initials)
- Bottom tab bar
- Tabler icons: `ti-calendar-event`, `ti-chevron-right`, `ti-home`, `ti-users`, `ti-clipboard-list`, `ti-chart-bar`, `ti-settings`

## Data requirements

| Field | Source | Notes |
|-------|--------|-------|
| Coach display name | `users.display_name` | "Coach Novia" or workspace setting fallback |
| Today's date | Client clock | Format with locale |
| Sessions today (count + list) | `sessions` where `coach_id = current_user` AND `scheduled_at::date = today` | Order by `scheduled_at ASC` |
| Per session: trainee name, time, court, focus, last assessment date | Joined to `trainees`, `assessments` | Last assessment is `MAX(recorded_at)` per trainee |
| Each trainee's current tier | Computed from `assessments` (latest score per skill, matched against `tier_requirements`) | See framework v0 section 9 |

## Interactions

| Action | Result |
|--------|--------|
| Tap "Up next" row | Navigate to trainee profile (NOT directly to assessment — coach may want to review history first) |
| Tap any trainee row | Navigate to trainee profile |
| Tap bottom tab | Switch tab |
| Pull to refresh | Refetch today's data |
| Long-press trainee row (V2) | Quick-action menu: Assess now, Skip, Reschedule |

## States

### Default
As described above. 1+ session scheduled.

### Empty (no sessions today)
See `09-empty-states.md` — "No sessions today" with primary CTA "Schedule session" and link "Add a trainee first" (if no trainees yet).

### Loading
Skeleton list — 3 placeholder trainee rows with avatar circle + 2 lines (`10-error-offline-states.md`).

### Offline
Top banner persists. List shows last cached data. Sync pill on any item modified offline.

## Workspace type adaptations

- **Club:** Status bar shows "Senayan padel club". "Up next" can include any of the coach's club trainees.
- **Personal:** Status bar shows just "PadelCoach" or coach display name. Otherwise identical layout.

## Localization

| EN | ID |
|----|----|
| Today (tab) | Hari ini |
| Trainees (tab) | Trainee |
| Sessions (tab) | Sesi |
| Reports (tab) | Laporan |
| Settings (tab) | Setelan |
| Hi, Coach Novia | Halo, Coach Novia |
| Sunday, 10 May 2026 · 5 sessions | Minggu, 10 Mei 2026 · 5 sesi |
| Up next | Sesi berikutnya |
| Trainees today | Trainee hari ini |
| 8:00 · Andi Pratama | 08.00 · Andi Pratama |
| Court 2 · 60 min · Drilling | Lapangan 2 · 60 menit · Drill |
| 3 days ago | 3 hari lalu |
| Not assessed | Belum dinilai |

Tier names translate (Beginner → Pemula, Lower Bronze → Perunggu Muda, Bronze → Perunggu). See `11-localization-rules.md`. Silver+ are deferred post-MVP.

## Design rationale

**Why "Up next" gets its own card above the list.** Coaches prepping between sessions are looking for one specific trainee. Pulling that single row out of the list eliminates a scan step and removes ambiguity about which session is current.

**Why tap on a trainee row goes to the profile, not directly to the assessment.** Coaches usually want to review history (last session, last summary, what we worked on) *before* starting a new assessment. The profile is the natural staging area. The "New assessment" button on the profile is one tap further but produces better assessments.

**Why we show "last assessed" not "tier" in the row metadata.** Tier is in the right-side pill. The metadata line is more useful as a "freshness" indicator — coaches subconsciously prioritize trainees who haven't been assessed recently.

**Why no aggregate stats or summary at the top.** Coaches don't open Today to look at numbers. They open it to find their next person. Save the dashboard view for the Reports tab.

## Out of MVP scope

- Long-press quick actions (V1.5)
- Drag to reorder sessions (V2)
- Calendar view of the week (V1.5 — handled by Sessions tab)
- Push notification deep-link to a specific upcoming session (V1.5)
- Voice command "Start Andi's assessment" (V2+)

## Open questions

1. When a coach has 8+ sessions today, does the list scroll within the screen, or do we show only the next 4 with a "Show all" expansion? **Recommendation:** show all, list grows the screen — coaches scrolling once is fine.
2. Should we surface trainees with stale assessments ("haven't been rated in 30 days") as a separate section? **Recommendation:** not at MVP — add as a Trainees-tab filter instead.
3. Time zone handling: workspace-level or per-coach? **Recommendation:** workspace-level for MVP, single-tz clubs only.

## Related screens

- `04-coach-assessment.md` — what happens when coach taps into a session
- `03-coach-trainee-profile.md` — what most taps from this screen lead to
- `09-empty-states.md` — no-sessions-today state
