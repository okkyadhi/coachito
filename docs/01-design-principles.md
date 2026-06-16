# Design Principles

> Cross-cutting rules. Read this before building any screen.

## Visual philosophy: iOS, not Material

PadelCoach feels like a native iOS app — calm, restrained, premium. Reference apps: Apple Fitness, Things 3, Linear iOS, Cron / Notion Calendar, Whoop, Strava, Headspace.

**Skip Material Design libraries** (React Native Paper, etc.) — they pull in Google's design philosophy and clash with the Apple aesthetic. Use NativeWind (Tailwind for RN) with custom token mapping instead.

### Core rules

| Rule | Why |
|------|-----|
| **No shadows.** Use 0.5px hairline borders | iOS dropped shadows after iOS 7. Hairlines look cleaner and perform better on mobile. |
| **Sentence case only.** "View 20 more skills" not "View 20 More Skills" | Apple modernized to sentence case post-iOS 13. Title case feels dated. |
| **Single accent color** + grayscale + 1–2 semantic | More color = more Material. Restraint is the differentiator. |
| **Two font weights:** 400 regular, 500 medium | Never 600 or 700 — they look heavy against the iOS UI host. |
| **Body text stays regular.** Bold only for titles and small labels | Bold everywhere = noisy. |
| **Tap targets ≥ 44pt** (ideally 50–56pt for rows) | iOS Human Interface Guidelines minimum. |
| **No emoji.** Use Tabler icons (outline only) | Emoji age badly and don't theme. |

### Animation expectations

Apple feel comes partly from motion. Use `react-native-reanimated` with spring presets:
- Sheet slide-up: spring with overshoot
- Push transitions: subtle bounce
- Tap feedback: 0.96 scale + spring back
- List item insert/delete: layout animation

## Type scale

| Use | Size | Weight | Notes |
|-----|------|--------|-------|
| Large title (screen hero) | 22–28px | 500 | iOS large title style. Letter-spacing −0.3 to −0.5px |
| h2 / section title | 18px | 500 | |
| h3 / sub-section | 16px | 500 | |
| Body | 14–15px | 400 | Line-height 1.5–1.6 |
| Caption / meta | 12–13px | 400 | Color: secondary |
| Section header (small caps style) | 12px | 400 | Color: secondary, sentence case |
| Pill / badge | 10–11px | 500 | Tight padding |
| Footnote | 10–11px | 400 | Color: tertiary |

Default font: system / SF Pro on iOS, Roboto on Android (use `--font-sans`).

## Color tokens

The app uses CSS variables (or NativeWind theme keys) so the entire UI re-themes from one accent change.

### Brand & accent

```
--accent              #378ADD (iOS blue, default)
--accent-bg           rgba(accent, 0.12)
```

Per-club override: admin sets `--accent` to brand hex; `--accent-bg` derives automatically as 12% alpha. Never hardcode hex values inside components.

### Neutrals

```
--color-background-primary    #FFFFFF (white surface)
--color-background-secondary  #F5F5F0 (grouped table bg)
--color-background-tertiary   #ECECE5 (page background, segmented control track)
--color-text-primary          rgba(0,0,0,0.87)
--color-text-secondary        rgba(0,0,0,0.60)
--color-text-tertiary         rgba(0,0,0,0.30)
--color-border-tertiary       rgba(0,0,0,0.10)  ← default 0.5px hairlines
--color-border-secondary      rgba(0,0,0,0.20)  ← hover state
```

### Semantic

```
--color-text-success / --color-background-success    success states (gain icons, sync done)
--color-text-warning / --color-background-warning    offline banner, attention prompts
--color-text-danger / --color-background-danger      destructive actions, server errors only
--color-text-info / --color-background-info          informational, often = accent
```

### Color usage rules

- **Accent** drives: primary buttons, active tab, segmented selection, tier badges, info icons, link text, progress bars, radar fill.
- **Success green** drives: level-up icons, "Synced" pills.
- **Warning amber** drives: offline banner, stale data warning.
- **Danger red** is reserved: destructive confirmations ("Delete workspace"), server-side error icons (tinted, not full red bg).

When placing text on a colored background, use the same color family's darker stop (e.g., text on `--color-background-info` uses `--color-text-info`). Never plain black on tinted bg.

## Spacing & layout

Use rem for vertical rhythm, px for component-internal gaps.

```
Vertical between sections   16–24px
Card internal padding        14–18px
Row internal padding         12–14px vertical, 14px horizontal
Section header to first row  6–8px
Form input min-height        36–44px
Button min-height            44px
Border radius (small)        8px (input, segmented control segments)
Border radius (medium)       10px (cards, banners)
Border radius (large)        12–16px (grouped tables, page-level cards)
```

## Components

### Grouped tables (iOS Settings style)

White surface, 12px radius, no border on the group itself, hairlines between rows. Section header is small gray text *outside* the group, sentence case.

```
┌─[Section header in gray]──┐
│ Group (white, 12px radius) │
│  Row                       │
│  ─────────── (hairline)   │
│  Row                       │
└────────────────────────────┘
```

Used everywhere: trainee lists, settings, skill rows, sessions.

### Segmented control (1–5 rubric input)

Rounded-pill container with gray track, 5 segments, selected segment lifts to white-on-tinted with hairline border. Replaces sliders for discrete choices.

### Tier pill / score pill

Small rounded-999 pill, accent-bg background + accent text. 10–11px font, tight padding. Used for tier badges, current scores, focus tags.

### Avatar circle

40–44px diameter, accent-bg background + accent text initials, 13–15px medium weight. Used for trainees, coach mentions, club marks.

### Bottom tab bar

5 tabs across, 22px outline icon + 10px label below, hairline top border. Active tab uses accent color.

### Top nav bar

44px min height, left action (back chevron + previous title) + center title (or empty for large-title style) + right action (Save, More, etc.). Actions use accent color.

### Buttons

- **Primary:** accent fill, white text, 10px radius, 13–14px medium weight, 44px min height
- **Secondary:** white fill, primary text, 0.5px hairline border, otherwise same dimensions
- **Link:** accent text, no background, no border, used inline

## Theming model (per workspace)

Each workspace can override **one** CSS variable: `--accent`. Everything else (typography, spacing, borders, neutrals) is platform-locked.

Implementation:

```js
// Per workspace context
const theme = {
  accent: workspace.brandColor || '#378ADD',  // hex from settings
};
// All components read from --accent CSS var or theme.accent prop.
```

Logo is a separate concern — uploaded image, displayed as 32–50px rounded square (or circle for solo coach profile photo). Falls back to first-letter initials of workspace name.

## Workspace types

Two types: `club` and `personal`. Same screens, conditional rendering on:
- Settings page (simpler for personal — no Members section, "Display name" not "Club name", "Profile photo" not required logo, Solo Coach plan not Club plans)
- Trainee app status bar text and welcome screen branding (coach name vs club name)
- PDF letterhead

See `06-workspace-settings.md` and the per-page docs for specifics.

## Accessibility minimums

- Tap targets ≥ 44×44pt
- Text contrast: ≥ 4.5:1 for body, ≥ 3:1 for large text
- Screen reader labels (`aria-label`) on icon-only buttons
- Focus rings visible on web (where applicable)
- Localization-aware (no hardcoded English in user-facing strings)
- Respect `prefers-reduced-motion` for animations

## Voice & tone

- **Coach-facing copy:** direct, clinical-but-warm, no marketing fluff. "8 skills below threshold for Bronze." Coaches want signal.
- **Trainee-facing copy:** encouraging, forward-looking, never shaming. "8 skills to Bronze — closer than ever." Same data, kinder framing.
- **Parent-facing copy** (PDF report): narrative-first, evidence-second. Lead with the coach's voice, support with metrics.
- **Error & offline copy:** calm, non-blaming, action-oriented. Never "Oops!" — adults don't appreciate it.

## What to avoid

- Drop shadows, gradients, blur backgrounds, neon glows
- Multiple accent colors in one screen
- Title case anywhere
- Bold body text or 600+ font weight
- Sub-44pt tap targets
- Emoji in app UI
- Material Design libraries
- "Helpful" assistant copy ("Oops!", "Great job!", excessive exclamation marks)
- Modal overlays for things that fit inline
- Auto-advancing carousels
- Notification spam

## What to keep doing

- Accent variable theming
- Sentence case
- Hairline dividers
- Single primary CTA per screen
- Empty states with clear next actions
- Transparent state surfacing (offline, syncing, stale)
- Coach narrative as the trust-builder
