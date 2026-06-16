---
name: Coach Today screen + bottom nav shell (FE step 5)
description: /today screen, 5-tab bottom nav, shared CoachShell layout, mock data contract
type: project
---

**Pair 3 step 5 done.** Coach home screen renders with greeting, Up Next card, and Trainees Today grouped table; bottom nav switches across 5 tabs.

**Layout architecture**
- [`CoachShell`](apps/web/src/layouts/CoachShell.tsx) is a layout route that renders `<Outlet />` between a top brand strip and the bottom tab bar. Authenticated coach screens nest inside it: `/today`, `/trainees`, `/sessions`, `/reports`, `/settings`.
- Router gate `CoachShellGate` in [router.tsx](apps/web/src/app/router.tsx) enforces auth + workspace before the shell renders. Unauthenticated → `/signin`; authenticated but no workspace → `/onboarding/create-workspace`.
- Bottom nav uses `<NavLink>` from react-router for `isActive` styling, lucide icons (Home, Users, ClipboardList, BarChart2, Settings).

**Today screen data contract** ([today-api.ts](apps/web/src/features/today/today-api.ts))
The TS interface `TodaySession` is the wire shape that step 6 (BE) must produce:
```ts
{ id, scheduledAt: Date, durationMin, court, focus, trainee: { id, displayName, tier, lastAssessedAt } }
```
Mock toggle: flip `MOCK_EMPTY = true` to exercise the empty-state path. Currently 5 sessions at 08:00 / 09:30 / 11:00 / 15:00 / 17:30 with realistic Indonesian names.

**Reusable primitives** (will be shared across coach screens)
- [`Avatar`](apps/web/src/components/Avatar.tsx) — initials circle, accent-bg, hairline border. `name` → smart initials (first + last word).
- [`TierPill`](apps/web/src/components/TierPill.tsx) — accent-bg + accent text. Tier code → translated label via `tiers.{CODE}`. All seven tiers covered (post-MVP ones use same color until tier-styling lands).
- [`GroupedTable`](apps/web/src/components/GroupedTable.tsx) — iOS Settings pattern: section header outside, white card with rounded corners, 0.5px hairline rows. Uses arbitrary Tailwind selector `[&>*+*]:border-t` to insert dividers between children.
- [`BottomTabBar`](apps/web/src/components/BottomTabBar.tsx) — 5 tabs, 52px tap targets, accent vs tertiary for active/inactive.
- [`ComingSoon`](apps/web/src/components/ComingSoon.tsx) — shared placeholder used by Trainees/Sessions/Reports/Settings screens.

**Locale-aware dates** ([lib/dates.ts](apps/web/src/lib/dates.ts))
Wraps date-fns. `formatFullDate("Sunday, 10 May 2026" / "Minggu, 10 Mei 2026")`, `formatTime` (HH:mm in en, HH.mm in id per Indonesian convention), `formatRelative` (uses date-fns `formatDistanceToNow` with addSuffix per locale). User locale comes from `user.preferredLocale` in the auth store; falls back to `i18n.language`.

**i18n upgrade**: switched to `compatibilityJSON: 'v4'` so `today.sessionCount_one` / `_other` plural suffixes work cleanly. Same for `today.minutes`.

**Open question / followups for step 6 (BE)**
- The workspace name in CoachShell's top strip is currently hardcoded as "RACADEMY". Needs a workspace fetch (or to stash the name in the auth store on sign-in / switch) before the multi-club UI is real.
- The mock has session count 5 — but with i18next 23.x plural-key matching, ensure step 6 returns an array (not paginated object) so `t('today.sessionCount', { count: sessions.length })` keeps working.
- `Avatar` initials are a quick heuristic (first + last name word). Indonesian names with single-word display names get one letter — acceptable, revisit if any pilot user complains.
