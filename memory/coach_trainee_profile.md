---
name: Coach trainee profile screen (FE step 9)
description: /trainees/:id — hero, stats, tier progress, blockers, SVG radar, gains, accordion, sessions
type: project
---

**Pair 5 step 9 done.** `/trainees/:id` renders every section in docs/03 against mock data.

**Routing**
- `/trainees/:id` lives inside `CoachShellGate` (bottom tab bar visible, Trainees tab active because NavLink prefix-matches `/trainees`).
- `/trainees/:id/assess` is a placeholder using the existing `ComingSoon` component; real screen lands in step 11.
- `/trainees/new` (modal, full-screen) is *outside* the shell. React Router 6 path ranking prefers the static `new` segment over `:id`, so navigation order doesn't matter.

**Data contract** ([profile-types.ts](apps/web/src/features/trainee-profile/profile-types.ts))
The TS shape future BE has to return:
```
{ trainee, stats, tierProgress{currentTier, nextTier, metCount, totalRequirements, blockingSkills},
  categoryAverages[], recentGains[], allSkills[], recentSessions[] }
```
Mock toggle: `MOCK_EMPTY` in [profile-api.ts](apps/web/src/features/trainee-profile/profile-api.ts) → empty-state path.

**The radar SVG** ([SkillRadar.tsx](apps/web/src/features/trainee-profile/SkillRadar.tsx))
Hand-rolled — no chart lib. Four axes at cardinal points (top=Technical, right=Tactical, bottom=Physical, left=Mental). Concentric "rings" are diamond polygons (squares rotated 45° by virtue of using only the four axis points). Data polygon: `fill: var(--accent); fill-opacity: 0.18; stroke: var(--accent)` per docs/01. Axis labels rendered with `<text>` elements; `text-anchor` picked per axis position so the labels don't overlap the polygon. Legend below shows 1-decimal averages per category (whole numbers feel falsely confident — docs/03 rationale).

**Section composition pattern**
Each section is its own component returning a `<section>` with a small-caps `<h2>` outside a white card (the iOS grouped-table look). The card uses the same `[&>*+*]:border-t [&>*+*]:border-[0.5px] [&>*+*]:border-border-hairline` arbitrary-selector trick from `GroupedTable` to draw 0.5px dividers between children. `GroupedTable` itself is reusable but sections like the radar / sessions need different inner layouts so they roll their own card.

**Mini-bar primitives**
- `BlockingSkillsList.GapBar` — 5 cells: current = solid gray (`bg-text-color-tertiary`), required = `bg-accent-bg`, rest empty. The "gap" reading is the takeaway (docs/03 rationale on dual-color bar).
- `AllSkillsAccordion.MiniBar` — 5 cells: filled to current level with `bg-accent`, rest empty. "Not rated" → all empty.

**Action bar is in-flow, not pinned**
docs/03: "iOS doesn't pin floating action buttons — that's a Material pattern." Two stacked buttons at the bottom of the scrolling content. "New assessment" navigates to `/trainees/:id/assess` (placeholder). "Schedule" navigates to `/sessions` for now (V2 will open a real sheet).

**Empty state**
Hero + stats (with `0` / `0.0` / `—`) + the empty-state pattern from docs/09 replaces sections 4–9. Single primary CTA "Start first assessment". Same icon (radar) as docs/09 § "Trainee profile". Action bar still rendered below.

**Reused locales pattern** — i18next `_one`/`_other` for `tierProgress.met`, `tierProgress.blocking`, `sessions.skillsUpdated`. Category names (Technical, Tactical, Physical, Mental) stay English in both locales per docs/03 § Localization.

**Known sharp edges**
- Linter auto-formatted Tailwind class order in three files; nothing semantic changed but worth knowing if a diff looks busier than expected.
- The radar fills are visually noisy at small averages (< 1.0) — added a 0.05 minimum so the polygon is never collapsed to a point. Real BE values shouldn't hit this but worth noting if a "no data" case slips through with averages set to 0.
- `daysSinceLastSession` formatting: < 7 = "Nd", < 30 = "Nw", else "Nmo". Approximate but matches docs/03 examples ("3d", "2w"). Real localization can come later.

**Open followups**
- Step 11 (BE) needs `GET /trainees/:id` returning the `TraineeProfile` shape. Tier calculation server-side (data-model.md § Performance notes); recent-gains query uses `LAG()` per docs/12.
- "Schedule" button currently lands on `/sessions` (an empty placeholder). When the scheduling sheet ships, replace with the actual open-sheet handler.
- The trainee profile is meant to be the most-visited screen (docs/03 line 9). Worth considering a `useInfiniteQuery` for the All Skills accordion when we go past 27 skills (e.g., custom skills per workspace) — but not before.
