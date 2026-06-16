# Empty States

> Pattern library for what every main screen looks like when there's no data yet.

## Purpose

Empty states are where most apps lose users. A new user opens the app, sees blank charts and unfilled lists, and bounces. Good empty states do three things:
1. **Explain what's missing and why** (set expectations)
2. **Guide the next action** when one exists (avoid dead ends)
3. **Match brand and tone** — they're as important as filled states

This doc defines the pattern and applies it to the 5 main screens that need empty states at MVP.

## The pattern

```
┌──────────────────────────────────────┐
│                                      │
│           [Icon, 60×60]              │
│                                      │
│         Title (16–17px, 500)         │
│                                      │
│   Description (13px, secondary,      │
│   max 2 sentences, max 260px wide)   │
│                                      │
│       [Primary CTA button]           │
│       [Secondary link or button]     │
│                                      │
└──────────────────────────────────────┘
```

### Icon

- 60×60 circle, secondary background, hairline border
- Tabler icon at 26px, tertiary color
- Never emoji
- Pick an icon that represents the *missing thing*, not the *action* (e.g., `ti-calendar-off` for "no sessions", not `ti-plus`)

### Title

- 16–17px, weight 500, primary text color
- States what's missing, NOT what to do
- "No sessions today" ✓
- "Schedule a session" ✗ (that's the CTA, not the title)
- Sentence case

### Description

- 13px, secondary color
- Max 2 sentences
- Max-width 260px (centered) for readability
- Explains the why or sets expectations for what'll appear here later
- Conversational tone, no marketing-speak

### CTAs

- One **primary** CTA max (accent fill)
- Optionally one **secondary** (white fill, hairline border) or **link** (no border, accent text)
- 44px min height for tap target
- 160px min width for visual weight
- Some empty states have **no CTA** — when the user can't action anything (e.g., trainee waiting for coach assessment)

## Per-screen empty states

### Coach · Today (no sessions today)

| Field | Value |
|-------|-------|
| Icon | `ti-calendar-off` |
| Title | "No sessions today" |
| Description | "When you schedule sessions with your trainees, they'll show up here." |
| Primary CTA | "Schedule session" |
| Secondary | "Add a trainee first" (link, only shown if no trainees exist) |

**Why:** Common state — coaches don't have sessions every day. Encouraging next-step toward scheduling. Conditional secondary link surfaces the prerequisite (need trainees before sessions).

### Coach · Trainees (first-run, no trainees)

| Field | Value |
|-------|-------|
| Icon | `ti-user-plus` |
| Title | "Add your first trainee" |
| Description | "Send a WhatsApp invite or save a trainee for later. Takes about 30 seconds." |
| Primary CTA | "Add and invite" (with `ti-brand-whatsapp` icon) |
| Secondary | "Add without invite" |

**Why:** Day-zero state for a brand-new club. Two paths because some coaches are sitting in front of a trainee (no need for invite); others are setting up at home. Time estimate ("30 seconds") reduces perceived friction.

### Coach · Trainee profile (added but not assessed)

| Field | Value |
|-------|-------|
| Icon | `ti-chart-radar` |
| Title | "No assessments yet" |
| Description | "Skills, tier progress, and the radar chart appear after the first session you assess." |
| Primary CTA | "Start first assessment" (with `ti-clipboard-check` icon) |

**Why:** Tells the coach what they'll see *later* (sets expectations) and offers the next action. Hero stats grid still renders above this empty state with 0 values; the empty state replaces only the body sections (tier progress, blockers, radar, etc.).

### Coach · Reports (no reports generated)

| Field | Value |
|-------|-------|
| Icon | `ti-file-text` |
| Title | "No reports yet" |
| Description | "Monthly reports generate automatically on the 1st. You can also create one anytime." |
| Primary | (none) |
| Secondary | "Create report manually" |

**Why:** No primary CTA because the default behavior is automatic — manual creation is rare. The description does the heavy lifting (sets up the auto-generation mental model). Secondary CTA is the escape hatch.

### Trainee · Progress / Home (signup complete, no first session yet)

| Field | Value |
|-------|-------|
| Icon | `ti-chart-bar` |
| Title | "Your progress will live here" |
| Description | "After your first session, Coach Novia will rate your skills and you'll see your tier, radar, and wins build up here." |
| Primary | (none) |
| Secondary | "See next session" (with `ti-calendar` icon) |

**Why:** Trainee can't fix this — only the coach can, by assessing them. Forcing the trainee to act here would be frustrating ("nag your coach"). Description names the coach (humanizes the wait) and lists what'll appear (sets expectations). Secondary CTA pivots to a useful adjacent action.

## Pattern rules (do / don't)

- **Always have an icon.** Never plain text-only empty states.
- **Title states the missing thing.** Not the action ("No sessions today" not "Schedule a session").
- **Description ≤ 2 sentences.** More feels like a marketing pitch.
- **Description max-width 260px.** Long lines lose readability when centered.
- **One primary CTA max.** Two equal-weight buttons fragment attention.
- **Skip the CTA when the user can't actually act.** Don't manufacture fake forward motion.
- **Voice matches the screen.** Coach screens are direct; trainee screens are encouraging.
- **No emoji, no exclamation marks, no "Oops!"** Adults don't appreciate that.

## Empty state vs error vs loading

| State | What it means | Visual treatment |
|-------|---------------|------------------|
| Empty | Data successfully fetched, but there's nothing to show | This pattern (calm, neutral) |
| Loading | Fetching data | Skeleton (`10-error-offline-states.md`) |
| Error | Fetch failed | Full-screen error pattern (`10-error-offline-states.md`) |
| Offline | Network unavailable | Banner + cached data (`10-error-offline-states.md`) |

**Do not conflate them.** Showing the empty pattern when actually offline is dishonest — it implies "you have no data" when actually "we couldn't fetch your data."

## Localization

| EN | ID |
|----|----|
| No sessions today | Tidak ada sesi hari ini |
| When you schedule sessions with your trainees, they'll show up here. | Saat kamu menjadwalkan sesi dengan trainee, mereka akan muncul di sini. |
| Schedule session | Jadwalkan sesi |
| Add a trainee first | Tambah trainee dulu |
| Add your first trainee | Tambah trainee pertamamu |
| Send a WhatsApp invite or save a trainee for later. Takes about 30 seconds. | Kirim undangan WhatsApp atau simpan trainee dulu. Sekitar 30 detik. |
| Add and invite | Tambah dan undang |
| Add without invite | Tambah tanpa undang |
| No assessments yet | Belum ada penilaian |
| Skills, tier progress, and the radar chart appear after the first session you assess. | Skill, progres tier, dan radar muncul setelah sesi pertama yang kamu nilai. |
| Start first assessment | Mulai penilaian pertama |
| No reports yet | Belum ada laporan |
| Monthly reports generate automatically on the 1st. You can also create one anytime. | Laporan bulanan dibuat otomatis tiap tanggal 1. Kamu juga bisa buat manual kapan saja. |
| Create report manually | Buat laporan manual |
| Your progress will live here | Progresmu akan muncul di sini |
| After your first session, Coach Novia will rate your skills and you'll see your tier, radar, and wins build up here. | Setelah sesi pertamamu, Coach Novia akan menilai skill dan kamu akan lihat tier, radar, dan pencapaian terbangun di sini. |
| See next session | Lihat sesi berikutnya |

## Related

- `10-error-offline-states.md` — distinct patterns for connection / server failures
- Each per-page doc lists its own empty state in the "States" section
