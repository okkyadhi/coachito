# Brand Identity

> The brand layer that sits on top of the platform-locked design system. Read `01-design-principles.md` first for the structural rules; this doc covers the visual identity that gives those rules a name and a voice.

## What changed from the original spec

The product was renamed from **PadelCoach** to **racademy** during brand exploration, on the strategic case that:

- Stripping vowels from "padel" reads as a sport-specific abbreviation; "academy" generalizes to padel + tennis + squash + pickleball as the product expands
- "Academy" carries institutional weight that "coach" alone doesn't — it sets up the premium positioning before any UI is seen
- The shorter wordmark is easier to set as a refined, classy lockup

All references to "PadelCoach" in older docs should be read as racademy going forward. The architectural notes (workspace types, role-based screens, MVP scope) carry over unchanged.

## Brand essence

> "Coaching, in the oldest sense of the word."

racademy positions itself as a small, serious academy of coaches — closer in feel to a private members' club than to a SaaS app. The visual reference set is **Aesop, Hermès, The Row, old European fencing academies, vintage racket club crests** — not Strava, not Nike, not any tech-startup adjacent.

The brand is built around three tensions:
- **Heritage signaling** + modern digital product
- **Editorial restraint** + functional UI density
- **Earned membership feel** + friendly trainee-facing tone

## Logo system

### Primary lockup

Crest (double circle + crossed rackets + R monogram) above a tracked-out wordmark, with a hairline divider and a serif tagline below. Used for:
- Marketing site hero and footer
- PDF report letterhead (cover page only)
- Welcome screen on first install
- Email signatures

### Monogram (R inside double circle)

The crest alone, no wordmark. The default form for any small or constrained surface:
- App icon (iOS, Android, web app)
- Favicon
- Loading splash
- In-product top-left brand mark

### Wordmark only

`racademy` set in italic serif, no crest. Used inline in body copy, social bio, where the crest would be redundant or too ornamental.

### Construction

```
Outer circle:    stroke 1.6px (large), 1px (medium), thicker as size shrinks
Inner circle:    stroke 0.5px — disappears below ~28px
Crossed lines:   stroke 0.8px terracotta, behind the R — disappear below ~28px
R monogram:      Georgia (or Fraunces) italic, fills ~64% of inner circle height
Wordmark:        Georgia italic, letter-spacing 0.04em
Tracked wordmark (in lockup): Georgia regular, letter-spacing 0.32em, all caps
Tagline:         Georgia italic, letter-spacing 0.22em, terracotta
```

### Scale rules

| Size | What renders |
|------|--------------|
| 96px+ | Full crest: outer circle + inner circle + crossed rackets + R |
| 40–60px | Outer circle + crossed rackets + R (inner circle dropped, strokes thicken) |
| 28–40px | Outer circle + R only (crossed rackets dropped) |
| 16–28px | R only (no circle) |

The rule is **simplify, don't shrink**. A favicon should not be a tiny version of the full crest — it should be a redrawn version that survives the size.

## The X — design rationale

The crossed lines behind the R are not decorative. They have three layered readings:

1. **Heraldic device.** Crossed swords (cavalry), crossed keys (Vatican), crossed oars (rowing clubs), crossed rackets (tennis clubs since the 1880s). The X says "club, academy, institution" in a visual language 800 years deep.
2. **The rally.** Racket sports require an opponent. The X is two opposing diagonals meeting at a center point — the literal moment a rally happens.
3. **The meeting point.** An academy is, etymologically, where paths cross. Coach and student arrive from different lives and meet at a court for an hour. The X is that intersection.

**Why drawn subtle (0.8px stroke, terracotta against forest, behind the R).** Heraldry whispers, it doesn't shout. The kind of detail that rewards a second look. At 16px favicon size the X disappears entirely — its meaning is layered, not advertised.

## Color system

The platform-locked neutral and semantic tokens from `01-design-principles.md` remain unchanged. Brand colors override `--accent` and add one new role (`--surface-deep` for the dark forest used on hero cards and PDF cover pages).

### Brand palette

```
--brand-forest        #1F3A2E   primary brand surface, hero cards, PDF letterhead
--brand-forest-deep   #14271E   body text on light, app icon background depth
--brand-terracotta    #B5613A   accent — links, primary CTA, badges, achievement medals
--brand-cream         #EDE6D6   secondary surface, quote-card background, monogram inverse
--brand-bone          #F7F2E6   page background (replaces white in racademy workspace)
--brand-stone         #8B8478   muted text, dividers, dot-indicator inactive state
```

### Mapping to existing tokens

| Existing token | racademy override | Notes |
|---|---|---|
| `--accent` | `#B5613A` (terracotta) | Drives all the same affordances — primary buttons, active tab, links, progress bars |
| `--accent-bg` | `rgba(181, 97, 58, 0.12)` | Auto-derived 12% alpha, same as system rule |
| `--color-background-tertiary` | `#F7F2E6` (bone) | Page background gets warmer in racademy |
| `--surface-deep` *(new)* | `#1F3A2E` (forest) | Reserved for hero cards (achievement, PDF cover, marketing site) — never for tab bar, status bar, or chrome |

**Why the tab bar stays white, not forest.** Color the chrome and the brand becomes a costume; color the moments and the brand becomes a personality. Forest is reserved for *occasions* (achievement card, PDF cover, marketing hero). Terracotta is the accent for *actions* (CTAs, links, badges). Both restraint rules from the original spec ("single accent color", "no Material") still apply.

### Semantic colors stay platform-locked

`--color-text-success`, `--color-text-warning`, `--color-text-danger` keep their existing values. Achievement gains in the trainee profile still use success green for the up-arrow icon, not terracotta. Brand color is for branded surfaces; semantic color is for state.

## Typography

The platform spec establishes system sans (SF Pro / Roboto) as the body and UI font. racademy adds a **serif display role** for moments where the brand voice needs to surface, without changing the sans-serif foundation.

### Type roles

| Role | Family | Weight | Used for |
|------|--------|--------|----------|
| Display serif | Fraunces (free) or Canela (paid) | 400 | Marketing hero headlines, achievement card titles, PDF cover, screen large titles in branded moments |
| Display serif italic | Same family, italic | 400 | Pull-quotes from coach summaries, taglines, brand wordmark |
| UI sans | System (SF Pro / Roboto) | 400 / 500 | Everything else — body, labels, buttons, navigation, forms |
| Mono | System mono | 400 | Hex codes in design specs only — not used in product UI |

**Free vs paid families.** Fraunces (Google Fonts) is the v1 display serif. It captures ~85% of Canela's character at zero licensing cost. Upgrade to Canela (Commercial Type) or Editorial New (Pangram Pangram) when revenue justifies the ~$300–600 web license. Most users won't notice the upgrade. The team will.

### When to use display serif

The serif is precious. Overuse and it loses its effect. Use it for:

- Achievement card titles (`Functional forehand`)
- Tier names in tier-progress card (`Bronze`, `Silver`)
- Marketing site headlines and pull-quotes
- Coach session summaries presented as quotes (with the oversized opening quote mark)
- PDF report cover and section dividers
- Greeting on trainee home (`Hi, Andi`)

Don't use serif for:

- Body text in lists or rows
- Buttons, form labels, or tab labels
- Numerics in stat cards (those use sans for tabular alignment)
- Any high-density data surface (skill grid, session feed, settings)

### The tracked-caps label pattern

A signature racademy detail: small caps labels with heavy letter-spacing (0.14–0.32em), sans-serif, used as section headers. Replaces the bold/heavy section header pattern common in modern apps. Examples:

```
SECTION  →  UP NEXT
SECTION  →  YOUR RHYTHM
SECTION  →  EST · MMXXVI · BY REFERRAL
```

This is borrowed directly from old hotel signage and editorial magazines. It reads as "considered" without reading as "loud."

## App icon system

Three official variants are exported from the `1024×1024` master:

| Variant | Background | Use |
|---------|-----------|-----|
| **Default** | Forest `#1F3A2E` | iOS / Android home screen, marketing |
| **Light** | Cream `#EDE6D6` | iOS Tinted mode (light), branded contexts on light backgrounds |
| **Seasonal** | Terracotta `#B5613A` | Limited use — App Store featured campaigns, end-of-year, optional toggle |

All three keep the same construction: outer circle stroke + crossed rackets + R monogram, contrast-inverted as needed.

Notification badge sits at the standard iOS position (top-right, ~12% inset) and uses the iOS system red, not brand terracotta — system red is unambiguous; terracotta would read as part of the icon.

## Voice & tone (extends `01-design-principles.md`)

The original voice rules carry over. racademy adds one layer:

- **Brand surfaces** (marketing site, PDF cover, achievement copy, welcome screen) lean **editorial-confident**. Short serif headlines. Latin numerals. Em-dashes. The voice of a curator, not a coach.
- **Product surfaces** (every screen inside the app) keep the voice rules from the original spec — direct/clinical for coach, encouraging/forward for trainee, narrative for parent.

The split protects against the common failure mode where a brand voice bleeds into UI copy and creates phrases like *"Refine your craft"* on a save button. The save button still says **Save**.

## Application notes (per screen)

| Screen | Brand-specific notes |
|--------|---------------------|
| `02-coach-today.md` | Top status bar shows workspace name in tracked-caps serif italic. Otherwise platform-locked. |
| `03-coach-trainee-profile.md` | Tier pill uses brand-tinted accent-bg per usual. Hero block name in serif large title. |
| `04-coach-assessment.md` | Stays sans-serif throughout — high-density input surface, no place for display serif. |
| `05-trainee-home.md` | Achievement card uses forest surface + serif title + terracotta medal. Coach summary card uses cream bg + oversized opening quote mark. Greeting in serif. Rhythm dots use cream + terracotta (no green). |
| `08-pdf-report.md` | Cover page uses full forest treatment with crest centered + tagline. Interior pages use bone background + serif section dividers. |
| Marketing site (`racademy.com`) | Editorial layout, serif-led, hero with side-by-side copy + framed crest panel. Marquee strip in deep forest. |

## Out of MVP scope

- Custom typeface licensing (Canela / Editorial New / Söhne) — ship on Fraunces, upgrade later
- Custom illustration style for empty states — use Tabler icons through MVP
- Branded loading animations — use platform default
- Branded share-to-Instagram template for achievement cards — V1.5
- Localized brand voice variants (the brand voice currently assumes English; Bahasa Indonesia copy adapts but doesn't get a parallel voice doc) — V1.5
- Print collateral (business cards, court signage, gym-bag patches) — post-launch when there's a reason
- Animated logo for video / opening title — post-launch

## Open questions

1. **Is "racademy" trademark-clear in NICE class 41 (education/training services) and 28 (sports equipment)?** Recommendation: file a clearance search before public launch. The name is short and ucapable enough that collisions are likely in adjacent industries.
2. **Should the workspace-override system be loosened to allow club-specific accent + cream overrides, or stay locked to the racademy palette as the platform default?** Recommendation: lock for v1 (one consistent brand surface across all workspaces); revisit when a club partner specifically asks.
3. **At what revenue threshold do we upgrade Fraunces → Canela?** Recommendation: tie it to a specific milestone (first club partnership, first 1,000 paying trainees) rather than a calendar date.
4. **Does the X read as crossed rackets to a non-padel audience, or does it read generically as a "no" mark?** Recommendation: user-test the icon in a blind read with 5–10 non-racket-sport users post-launch. If it reads as "X = no", iterate to a more obvious crossed-racket abstraction.
5. **Tagline lock — "Coaching, in the oldest sense of the word." vs "The racket academy." vs something shorter?** Recommendation: hold both. Long tagline for marketing site hero; short tagline (`the racket academy`) for compact lockups.

## Related docs

- `01-design-principles.md` — the platform-locked design system this brand layer sits on
- `06-workspace-settings.md` — workspace-level theming overrides (per-club accent)
- `08-pdf-report.md` — the highest-leverage brand surface (parents see this monthly)
- `11-localization-rules.md` — how brand voice translates to Bahasa Indonesia

## Asset checklist

Before public launch the following assets need to be exported and stored in `/brand/`:

- [ ] Primary lockup — SVG, PNG (1×, 2×, 3×) on transparent + on each brand color
- [ ] Monogram (crest only) — SVG, PNG (1×, 2×, 3×) on each brand color
- [ ] Wordmark only — SVG, PNG, on each brand color
- [ ] App icon — 1024×1024 master + iOS/Android export sizes, all three variants
- [ ] Favicon — 16, 32, 48, 180 (apple-touch-icon)
- [ ] Open Graph image — 1200×630 with crest + tagline on forest
- [ ] Twitter / X header — 1500×500
- [ ] PDF letterhead template — A4, with crest top-center + tracked wordmark
- [ ] Email signature template — HTML with inline-SVG crest + wordmark
- [ ] Color tokens exported as CSS, Tailwind config, and Figma library
- [ ] Type tokens documented for engineering (Fraunces fallback chain, Inter for sans)
