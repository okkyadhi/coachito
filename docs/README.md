# PadelCoach — Design System & Page Specs

Comprehensive UX/UI documentation for the PadelCoach MVP. This folder is the canonical handover from design to engineering.

## What's in here

| File | Covers |
|------|--------|
| `01-design-principles.md` | Cross-cutting rules: iOS philosophy, theming, type, color, spacing, tap targets |
| `02-coach-today.md` | Coach home screen — today's sessions and trainee list |
| `03-coach-trainee-profile.md` | Coach view of a single trainee with tier progress, radar, blockers, sessions |
| `04-coach-assessment.md` | Skill assessment screen with rubric, descriptors, session summary |
| `05-trainee-home.md` | Trainee-facing home with achievements, tier, upcoming session, coach note |
| `06-workspace-settings.md` | Workspace settings (club + personal variants), branding, plan |
| `07-invite-and-onboarding.md` | Add trainee → WhatsApp → welcome → first-run home + web landing page |
| `08-pdf-report.md` | Monthly PDF report layout and content |
| `09-empty-states.md` | Empty state patterns for all main screens |
| `10-error-offline-states.md` | Offline, sync, error, and loading state patterns |
| `11-localization-rules.md` | EN/ID localization layer specifics |

## How to use

**Engineers:** start with `01-design-principles.md` to absorb the visual language, then read the page spec for the screen you're building. Each page doc lists data requirements, components, interactions, states, and design rationale. The "Design rationale" sections explain *why* — read them before deviating.

**Designers iterating later:** the page docs are the source of truth for what's specified. Update the relevant doc in the same PR as a design change. Don't let docs drift.

**Product/founders:** the page docs are also a comprehensive PRD — every screen's purpose, audience, and rationale is explicit. Use them when scoping work, briefing new contributors, or validating with advisors.

## Design system at a glance

- **Visual language:** iOS / Apple Human Interface Guidelines — flat surfaces, 0.5px hairlines, no shadows, sentence case, single accent color
- **Two font weights only:** 400 regular for body, 500 medium for emphasis. Never 600 or 700.
- **Single accent variable** (`--accent`) drives all per-club brand theming. Default iOS blue `#378ADD`.
- **Tap targets ≥ 44pt minimum**, ideally 50–56pt for list rows.
- **Two languages** at MVP: English (default design canvas) and Indonesian (localization layer).
- **Two workspace types:** `club` (multi-coach institution) and `personal` (solo coach).

## Related references

- `padel-skill-framework-v0.md` (parent folder) — canonical skill ontology, tier thresholds, level descriptors
- Memory files at `/Users/noviairenda/.../spaces/.../memory/` — durable design decisions saved across conversations

## Out of MVP scope (deferred)

Features explicitly *not* designed at MVP, listed here so they don't get scoped in by mistake:

- Video analysis
- Drill library
- In-app payments (subscriptions handled externally for now)
- Multi-club switcher polish
- Coach-to-trainee chat
- Parent-specific app (parents read PDF reports for now)
- Tier celebration animations (worth a polish week before launch, not blocking)
- Custom curriculum builder beyond enable/disable platform skills

## Status

These docs reflect the design state as of conversation completion. Live mockups for each page are stored as Cowork artifacts and can be re-opened from chat history.
