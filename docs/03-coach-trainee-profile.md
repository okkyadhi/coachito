# Coach · Trainee Profile

> Coach view of a single trainee. The staging area before assessment, the reference during planning, the source of truth for "where is this trainee at right now?"

## Purpose

Aggregates everything a coach needs to know about a single trainee in one screen: identity, tier progress, what's blocking the next tier, the radar of skill averages, recent gains, the full skill grid, and the chronological session feed.

This is the **most-visited screen** in the coach app. It's both:
- A pre-assessment briefing (read history → start new assessment)
- A coaching-decisions reference (what should we work on next)
- An accountability surface (parents asking the coach for an update)

## Audience

- **Role:** Coach
- **Workspace types:** Both
- **Context:** Tapped from Today, Trainees list, search, or notification

## Layout (top to bottom)

1. **Top nav bar**
   - Left: `< Trainees` (back action, accent color)
   - Right: `⋯` more menu (Edit trainee, Archive, Share with parent)
2. **Hero block**
   - Large avatar (64×64, initials, accent-bg)
   - Name (24px, weight 500)
   - Meta line: tier pill + "Joined Sep 2025"
3. **Stats grid** (3-column, hairline-divided)
   - 42 Sessions
   - 18.5 Hours coached
   - 3d Since last
4. **Tier progress card**
   - "Lower Bronze ────●────── Bronze"
   - Progress bar
   - "10 of 18 skills met"
   - "8 skills below threshold for Bronze"
   - At MVP the ceiling is Bronze; a trainee already at Bronze sees a "Top tier for current curriculum" treatment with no next-tier bar
5. **"To reach Bronze, focus on" section** (blocking skills)
   - Up to 5 rows: skill name + "{current} → {required}" + dual-color bar showing the gap
6. **Skill profile section**
   - 4-axis radar SVG (Technical, Tactical, Physical, Mental)
   - Legend column with category averages
7. **Recent gains section**
   - 2–4 rows of skill level-ups with up-arrow icon (success color), skill name, "{from} → {to}", "When"
8. **All skills section**
   - Header with "Expand all" link
   - 4 collapsible category groups (Technical default open)
   - Each skill row: name + 5-cell mini bar + "{level} {label}" — "Not rated" if absent
9. **Recent sessions section**
   - 3–5 chronological session cards: date + time + focus pill + summary + "X skills updated"
10. **Action bar (in-flow, not pinned)**
    - Primary: "New assessment"
    - Secondary: "Schedule"
11. **Bottom tab bar** — Trainees tab active

## Components used

- Avatar (large variant, 64×64)
- Tier pill
- Stat cell with hairline divider
- Progress bar (`progress-track` + `progress-fill`)
- Dual-color bar (`bar-cell.current` gray, `bar-cell.target` accent semi-transparent, rest empty)
- 4-axis radar SVG (concentric squared rings + axis lines + data polygon)
- 5-cell mini skill bar
- Collapsible group with chevron
- Session card with focus pill
- Tabler icons: `ti-arrow-up`, `ti-chevron-right`, `ti-chevron-up/down`, `ti-clipboard-check`, `ti-calendar-plus`, `ti-dots`

## Data requirements

| Field | Source | Notes |
|-------|--------|-------|
| Trainee identity | `trainees` table | name, joined_date, tier, photo |
| Sessions count | `COUNT(sessions WHERE trainee_id = X)` | Total, all time |
| Hours coached | `SUM(sessions.duration_min) / 60` | Total |
| Days since last session | `NOW() - MAX(sessions.scheduled_at)` | Display as "3d", "2w" |
| Current tier + progress | Computed via `tier_calculation` (framework v0 §9) | Returns current tier, next tier, met count, total count, blocking skills |
| Category averages | `AVG(latest_score)` grouped by category | For radar |
| Recent gains | `assessments` where `level > previous_level` for same skill, ordered by `recorded_at DESC LIMIT 4` | Compare with prior assessment of same skill |
| All skills with current scores | Latest `assessments.level` per `skill_id` | NULL if never rated |
| Recent sessions | `sessions` with their summary text, focus tag, count of skills assessed | Last 5, ordered DESC |

## Interactions

| Action | Result |
|--------|--------|
| Tap back | Navigate to previous screen (Trainees list or Today) |
| Tap `⋯` | Sheet with Edit / Archive / Share with parent / Resend invite |
| Tap "Expand all" | Open all 4 category groups; toggles to "Collapse all" |
| Tap category header | Toggle that category open/closed |
| Tap skill row | Navigate to skill detail view (V2 — for MVP, no action) |
| Tap session card | Navigate to that session's full detail view |
| Tap "New assessment" | Start assessment screen for current trainee, prefilled with last scores |
| Tap "Schedule" | Open scheduling sheet (V2 — for MVP, opens external calendar app) |

## States

### Default
Has prior assessments and sessions. As described.

### Empty (no assessments yet)
See `09-empty-states.md` — single empty state replaces Tier progress, Blockers, Radar, Recent gains, All skills, Sessions sections. Shows "No assessments yet" with primary CTA "Start first assessment". Hero + stats grid + action bar still present (stats show 0/0).

### Loading
Skeleton: hero + skeleton stats + skeleton bars + skeleton list.

### Offline
Cached profile shown with offline banner at top. "New assessment" still works (writes go to local queue).

## Workspace type adaptations

No structural differences. Trainee profile is the same for solo and club. Solo coach's profile renders identically — just doesn't show "added by [other coach]" anywhere.

## Localization

| EN | ID |
|----|----|
| Trainees | Trainee |
| Joined Sep 2025 | Bergabung Sep 2025 |
| Sessions | Sesi |
| Hours coached | Jam coaching |
| Since last | Sejak terakhir |
| Tier progress | Progres tier |
| Beginner / Lower Bronze / Bronze | Pemula / Perunggu Muda / Perunggu |
| 10 of 18 skills met | 10 dari 18 skill terpenuhi |
| 8 skills below threshold for Bronze | 8 skill belum mencapai Perunggu |
| To reach Bronze, focus on | Untuk capai Perunggu, fokus ke |
| Skill profile | Profil skill |
| Technical / Tactical / Physical / Mental | (untranslated — categories stay English) |
| Recent gains | Kenaikan terbaru |
| Last week | Minggu lalu |
| 2 weeks ago | 2 minggu lalu |
| All skills | Semua skill |
| Expand all / Collapse all | Buka semua / Tutup semua |
| Not rated | Belum dinilai |
| Recent sessions | Sesi terbaru |
| Drilling / Match play / Conditioning | Drill / Pertandingan / Kondisioning |
| {N} skills updated | {N} skill diperbarui |
| New assessment | Penilaian baru |
| Schedule | Jadwalkan |

Skill names (Forehand drive, Bandeja, Smash, etc.) and category names (Technical, Tactical, Physical, Mental) **stay in original** per `11-localization-rules.md`.

## Design rationale

**Why blockers are listed before the radar.** Coaches plan their next session by reading the blockers, not by looking at the radar. The radar is a supporting visual — useful for "feel" but not actionable on its own. Putting blockers first matches the actual coaching workflow.

**Why the dual-color bar in blockers.** A single accent-filled progress bar would imply "you're at this level". The dual-color treatment (gray current cells + semi-transparent accent target cell + empty future cells) communicates "you're here, you need to be one cell further" — the gap is what's interesting.

**Why max 5 blocker rows.** More than 5 is overwhelming and the coach can't action them all in one session. If 8+ skills are blocking, show top 5 with "Show all 8" link.

**Why the radar fill is a polygon, not separate bars.** The polygon shape lets the coach see balance at a glance — a kite-shaped data polygon means strong technical, weak elsewhere. Bars don't communicate that as well.

**Why the action bar is in-flow at the bottom of scrollable content, not pinned.** iOS doesn't pin floating action buttons — that's a Material pattern. When the coach is on this screen, scrolling to the bottom is the natural moment to act.

**Why session cards include the summary text inline.** This is the "narrative continuity" payoff for the in-app session summary field. Without it, the session feed is just metadata. With it, it reads as a coaching story.

**Why category averages are 1-decimal precision.** Whole numbers (e.g., "Technical: 2") feel falsely confident. Decimals (e.g., "2.4") communicate it's an aggregation across many skills. Same reason GPA uses decimals.

## Out of MVP scope

- History line chart (avg score over time) — V1.5
- Hours-per-week bar chart — V2
- Skill detail screen (tap skill → see assessment history per skill) — V1.5
- Parent share button (generates parent-readable URL) — V1.5
- Comparison to other trainees in the club — V2 and ethically debated
- Drill recommendations per blocker — V2 (depends on drill library)

## Open questions

1. When a trainee is at the current MVP ceiling (Bronze), what does the "Tier progress" section show? **Recommendation:** "Top tier for current curriculum — keep refining" with no progress bar; once Silver+ ships, swap to a Diamond-ceiling treatment ("You've reached Diamond — keep refining").
2. How do we handle reactivated trainees (paused account, returned)? Show a "Returned after 6 months" badge? **Recommendation:** yes, subtle indicator above the hero.
3. If a coach has multiple trainees with the same first name, how do we disambiguate in the back-button title? **Recommendation:** use last initial in the previous-screen title — "Trainees" handles it; that screen shows full names anyway.

## Related screens

- `02-coach-today.md` — typically the entry point
- `04-coach-assessment.md` — destination of "New assessment"
- `05-trainee-home.md` — what the trainee sees from their side, same data
- `08-pdf-report.md` — what gets exported monthly
- `09-empty-states.md` — empty (no assessments) variant
