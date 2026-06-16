# Trainee · Home

> Trainee-facing home screen. Same data as the coach profile, completely different psychology — encouraging, forward-looking, narrative-led.

## Purpose

The trainee's default landing screen. Optimized for emotional engagement: celebrate wins, surface what's next, make the trainee feel their progress is being seen. Retention loops live here.

## Audience

- **Role:** Trainee
- **Workspace types:** Both
- **Context:** Day after a session ("what did coach say?"), week after sign-up ("am I improving?"), morning of next session ("what's coming?")

## Layout (top to bottom)

1. **Status bar** — system, with workspace name on the right
2. **Greeting block**
   - Large title: "Hi, Andi" (28px, weight 500)
   - Subtitle: short date "Sunday, 10 May"
   - Right: bell icon button with notification dot
3. **Achievement card (hero)** — the celebration moment
   - Tag (small caps): "NEW BADGE"
   - Title: "Functional forehand" (22px, weight 500)
   - Description: 2-line copy explaining what the level means and what's next
   - Primary button: "View skill"
   - Secondary button: "Share"
   - Medal icon (`ti-award`) in white circle, top-right of card, accent-bg surrounding
4. **Tier progress card**
   - "Lower Bronze" (current) ──── "Bronze · 8 skills to go"
   - Progress bar
   - Encouragement line below: "Closer than ever — keep this pace and you're Bronze by July."
   - MVP ceiling note: a trainee already at Bronze sees a "Top tier — keep refining" treatment instead of a next-tier bar (Silver+ ship post-MVP)
5. **"Up next" section** — upcoming session card
   - Day badge (e.g., "11 MAY") in accent-bg square
   - "Tomorrow, 8:00 am" + "Court 2 · 60 min · Drilling"
   - Coach avatar (small) + "Coach Novia"
   - Right chevron
6. **"Latest from Coach Novia" section** — most recent session summary
   - Coach mini-avatar + "Coach Novia" + "After your session 3 May"
   - Quote text: the actual session summary the coach wrote
7. **"How you're tracking" section**
   - 4-axis radar SVG
   - Legend with category averages
8. **"Wins this month" section**
   - 2–4 rows of skill level-ups: green up-arrow icon + "{skill}" + "{from} → {to}" + "When"
9. **"Your rhythm" section**
   - Flame icon + "4 sessions in 14 days" + "Your most consistent stretch yet."
   - 14 dots representing past 14 days, 4 active in accent
   - Footer: "Tomorrow keeps the streak going."
10. **Bottom tab bar** — Home / Progress / Sessions / Coach / Profile

## Components used

- Greeting block with notification bell + dot
- Achievement card (accent-bg fill, medal icon, two action buttons)
- Tier progress card with motivational footer
- Upcoming session card with day badge and coach avatar
- Coach note card (quote-style)
- Radar (same as profile)
- Win row (success-bg green icon + 2-line text + when)
- Rhythm card (flame icon + dots row)
- Bottom tab bar (5 tabs, different from coach: Home, Progress, Sessions, Coach, Profile)
- Tabler icons: `ti-bell`, `ti-award`, `ti-arrow-up`, `ti-flame`, `ti-calendar-event`, `ti-chevron-right`, `ti-message-circle`, `ti-user`

## Data requirements

| Field | Source | Notes |
|-------|--------|-------|
| Trainee name | `users.display_name` | First name only for the greeting |
| Today's date (short) | Client clock | "Sunday, 10 May" — no year |
| Most recent badge | Latest level-up that crossed a threshold (e.g., 2→3 = "Functional X") | Compute from `assessments` history |
| Tier progress | Same as coach profile | tier, next, %, blockers count |
| Tier-by-date prediction | Linear projection from session pace + remaining blockers | "Bronze by July" copy |
| Upcoming session | `sessions` where `trainee_id = current_user` AND `scheduled_at > NOW()` ORDER ASC LIMIT 1 | |
| Coach name + avatar for that session | Joined to `users` | |
| Most recent session summary text | `sessions.summary` from latest past session | |
| Category averages | Same as profile | |
| Recent gains | Same as profile | Show 2–4 most recent |
| Sessions in last 14 days | Boolean array length 14 | For dot rendering |
| Pending notifications | `notifications` where `read_at IS NULL` | Just for the bell dot |

## Interactions

| Action | Result |
|--------|--------|
| Tap bell | Open notifications screen |
| Tap "View skill" on badge | Navigate to skill detail (V2; for MVP, navigates to Progress tab) |
| Tap "Share" | Open native iOS/Android share sheet with rendered badge image |
| Tap upcoming session card | Open session detail screen |
| Tap coach note quote | Navigate to that session's detail (full summary, all scores updated) |
| Tap any "Wins this month" row | Navigate to Progress tab, scrolled to that skill |
| Tap rhythm card | Navigate to Sessions tab, calendar view |
| Tap bottom tab | Switch tab |
| Pull to refresh | Refetch data |

## States

### Default
Has an achievement, tier progress, scheduled session, recent summary. As described.

### First-run (no assessments yet)
See `09-empty-states.md` and `07-invite-and-onboarding.md` — replaced layout: greeting + "Your first session" card + empty radar message + "What happens next" 3-step list. No achievement card, no wins, no rhythm.

### Mid-state (has 1–2 assessments, no achievement yet)
Skip the achievement card. Show tier progress, upcoming session, coach note, radar, wins (if any), rhythm.

### No upcoming session scheduled
"Up next" section becomes "No session scheduled" with "Ask your coach to schedule one" link (V1.5: in-app message; for MVP: opens WhatsApp to coach).

### Loading
Skeleton: greeting + skeleton achievement card + skeleton tier card + skeleton sessions list.

### Offline
Top banner. Cached data shown. Pull-to-refresh disabled with toast.

## Workspace type adaptations

- **Club workspace:** status bar shows "Senayan padel club", coach attribution shows "Coach Novia · Senayan Padel Club"
- **Personal workspace:** status bar shows "PadelCoach" or coach name, coach attribution shows just "Coach Novia"

Otherwise identical.

## Localization

| EN | ID |
|----|----|
| Hi, Andi | Halo, Andi |
| Sunday, 10 May | Minggu, 10 Mei |
| New badge | Pencapaian baru |
| Functional forehand | Forehand · Fungsional (skill name English, level Indonesian) |
| Your crosscourt rally is now reliable. Time to start attacking the short balls. | Rally crosscourt-mu sekarang konsisten. Saatnya mulai serang bola pendek. |
| View skill | Lihat skill |
| Share | Bagikan |
| Bronze · 8 skills to go | Perunggu · 8 skill lagi |
| Closer than ever — keep this pace and you're Bronze by July. | Lebih dekat dari sebelumnya — pertahankan tempo ini dan kamu jadi Perunggu di Juli. |
| Up next | Sesi berikutnya |
| Tomorrow, 8:00 am | Besok, 08.00 |
| Court 2 · 60 min · Drilling | Lapangan 2 · 60 menit · Drill |
| Coach Novia | Coach Novia |
| Latest from Coach Novia | Dari Coach Novia |
| After your session 3 May | Setelah sesi 3 Mei |
| How you're tracking | Perkembanganmu |
| Wins this month | Pencapaian bulan ini |
| Last week | Minggu lalu |
| 2 weeks ago | 2 minggu lalu |
| 3 weeks ago | 3 minggu lalu |
| Developing → Functional | Berkembang → Fungsional |
| Your rhythm | Ritmemu |
| 4 sessions in 14 days | 4 sesi dalam 14 hari |
| Your most consistent stretch yet. | Periode paling konsisten sejauh ini. |
| Tomorrow keeps the streak going. | Besok lanjutkan ritme ini. |
| Home / Progress / Sessions / Coach / Profile | Beranda / Progres / Sesi / Coach / Profil |

## Design rationale

**Why the achievement card sits at the top, not the tier progress.** Apple Fitness, Strava, Duolingo all open with celebration before utility. Trainees who feel seen retain. Tier progress is informational; achievement is emotional.

**Why "View skill" + "Share" together on the achievement.** The Share button is the viral/social loop — trainees screenshot achievements and send to family. Building the share affordance in costs nothing and creates organic word-of-mouth.

**Why the tier copy is forward-looking ("Bronze by July") not just status ("56% to Bronze").** The percentage feels passive; the prediction implies agency and momentum. Same data, kinder framing.

**Why "Latest from Coach Novia" surfaces the actual session summary, not a metric.** This is the *single highest-value* piece of content for trainee retention. Coaches who write thoughtful summaries create trainees who open the app daily to check for new ones. Without this surface, the session summary field on the assessment screen has no payoff.

**Why no "blocking skills" / "what to improve" section.** Coach view leads with blockers because coaches plan sessions. Trainee view doesn't because trainees aren't planning sessions — they're showing up to them. Showing them what they're "failing at" creates anxiety, not motivation. The improvement nudge is implicit in the achievement card and the upcoming session prompt.

**Why "Your rhythm" not "Your streak".** Streaks shame breakage; rhythm is forgiving. A trainee who misses a week shouldn't feel like they "lost" something. Borrowed from Apple Activity rings tone, not Duolingo's harder edge.

**Why the radar uses fill-opacity 0.18 (vs 0.15 in coach view).** Subtly more saturated for trainee — psychologically reads as "filled in" / proud. Coach view stays slightly more analytical.

**Why the 14-dot rhythm row instead of a streak counter.** Visual rhythm communicates pattern at a glance. A coach who looks at the trainee's profile sees the dots and knows immediately if they're consistent. A counter ("5 sessions this month") loses that texture.

**Why the bell has a notification dot built into the design.** This is the loop: coach writes summary → notification fires → trainee opens app → sees coach's words → opens app tomorrow looking for the next one. Without the dot, the loop dies.

## Out of MVP scope

- Streak gamification (intentionally avoided)
- Leaderboards or ranking vs other trainees (corrosive in coaching context)
- Skill detail screen (V1.5)
- In-app messaging with coach (V2 — for MVP, the Coach tab links to WhatsApp)
- Trainee self-assessment ("how do you think you did?") — V2
- Goal-setting interface ("I want to reach Bronze by ____") — V1.5
- Photo/video upload from session — V2

## Open questions

1. When a trainee has no recent badge, what fills the achievement-card slot? **Recommendation:** swap to a "Keep going" prompt referencing their nearest tier blocker — but framed encouragingly: "Bandeja is your nearest milestone — 1 to 2 next!"
2. How long does an achievement remain on the home screen before auto-dismissing? **Recommendation:** until the next achievement replaces it, OR 14 days, whichever first.
3. If a trainee disagrees with a coach's score, where do they raise it? **Recommendation:** V1.5 — for MVP, no in-app dispute mechanism; trainee talks to coach directly.
4. Multi-coach trainees (rare in MVP, but possible in clubs): which coach's "Latest" note shows? **Recommendation:** most recent session's coach.

## Related screens

- `03-coach-trainee-profile.md` — same data, coach perspective
- `04-coach-assessment.md` — where the summary trainee reads gets written
- `07-invite-and-onboarding.md` — first-run state of this screen
- `08-pdf-report.md` — monthly export of similar content
