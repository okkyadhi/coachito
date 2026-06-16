# PadelCoach — Claude Code Context

> Read automatically by Claude Code at session start. Encodes stack, conventions, design language, and decisions so we don't re-derive every session.

## What we're building

**PadelCoach** — multi-tenant SaaS for padel coaching: skill assessment, progression tracking, session logging, monthly PDF reports. Architected to extend to **tennis** in V2 (skill ontology is sport-scoped from day one).

Two workspace types:
- **Club workspace** — multi-coach institution, paid (Club Starter Rp 500k/mo, Club Pro Rp 1.5jt/mo)
- **Personal workspace** — solo freelance coach, simpler UI, lower price (Solo Coach Rp 100k/mo)

Trainees and parents always free. Pricing is per-workspace based on coach count + active trainee quota.

Target market: Indonesia first (Jakarta, Bali, Surabaya). International later.

**MVP delivery: web app, mobile-first responsive, installable as PWA.** No app store at MVP — coach adds web URL to home screen, gets app-like experience. Native mobile is V2+ if needed.

## Stack

### Frontend (apps/web)
- **Vite 5** + **React 18** + **TypeScript strict**
- **Tailwind CSS 3** with custom iOS theme tokens
- **shadcn/ui** as component primitives (Radix-based, copy-paste, customizable)
- **React Router 6** for routing
- **TanStack Query v5** for server state + offline persistence
- **Zustand** for client state
- **react-hook-form + Zod** for forms and validation
- **i18next + react-i18next** for ID/EN
- **Dexie.js** for IndexedDB (offline mutation queue)
- **date-fns** for date/time formatting
- **lucide-react** for icons (outline only — never filled)
- **Framer Motion** for animations
- **Sentry** for error tracking
- **PWA** via `vite-plugin-pwa` (manifest + service worker)

### Backend (apps/api)
- **FastAPI 0.110+** on **Python 3.12**
- **SQLAlchemy 2.0** async + **Alembic** migrations
- **Pydantic v2** for schemas
- **Postgres 16** with Row Level Security
- **Redis 7** for cache + RQ queue
- **RQ** for background jobs
- **WeasyPrint** for PDF reports
- **httpx** for outbound HTTP
- **structlog** for logging
- **pytest + pytest-asyncio** for tests

### Infrastructure (infra/)
- **Docker Compose** for everything (postgres, redis, api, worker, web, mailpit, minio)
- **Cloudflare R2** for production storage (logos, photos, future video)
- **MinIO** for local dev storage (S3-compatible, runs in Docker)
- **Resend** for production email
- **Mailpit** for local dev email (catches magic links)
- **Sentry** for monitoring

### Auth
- **Google Sign-In** (gsi/client) + **email magic link** (free tier MVP)
- **JWT** with workspace context: `{user_id, active_workspace_id, role, exp}`
- No phone OTP at MVP (saves cost)

### Development
- **pnpm** as package manager
- **Turborepo** for monorepo orchestration
- **GitHub Actions** for CI
- **Docker** for everything dev → production
- **Cursor + Claude Code** for development

## Repo structure

```
padelcoach/
├── CLAUDE.md                         ← this file
├── README.md
├── package.json                      ← pnpm workspace root
├── pnpm-workspace.yaml
├── turbo.json
├── .env.example
├── .gitignore
├── apps/
│   ├── web/                          ← Vite + React + TS
│   │   ├── src/
│   │   │   ├── main.tsx
│   │   │   ├── App.tsx
│   │   │   ├── router.tsx
│   │   │   ├── pages/                ← route-level components
│   │   │   ├── components/
│   │   │   │   └── ui/               ← shadcn/ui components
│   │   │   ├── hooks/
│   │   │   ├── lib/                  ← utilities, api client, dexie
│   │   │   ├── stores/               ← Zustand stores
│   │   │   ├── locales/
│   │   │   │   ├── en.json
│   │   │   │   └── id.json
│   │   │   ├── skills/               ← skill ontology constants (NOT in locale)
│   │   │   ├── theme/                ← Tailwind tokens, iOS HIG mapping
│   │   │   └── styles/
│   │   ├── public/
│   │   ├── index.html
│   │   ├── vite.config.ts
│   │   ├── tailwind.config.ts
│   │   ├── tsconfig.json
│   │   └── package.json
│   └── api/                          ← FastAPI
│       ├── src/
│       │   ├── main.py
│       │   ├── config.py
│       │   ├── auth/
│       │   ├── workspaces/
│       │   ├── skills/
│       │   ├── assessments/
│       │   ├── sessions/
│       │   ├── reports/
│       │   ├── invites/
│       │   ├── jobs/                 ← RQ workers
│       │   └── db/
│       ├── alembic/
│       ├── tests/
│       ├── pyproject.toml
│       └── scripts/
│           └── seed.py
├── packages/
│   └── types/                        ← shared TS types from API schemas
├── infra/
│   ├── docker-compose.yml            ← dev: postgres + redis + api + worker + web + mailpit + minio
│   ├── docker-compose.prod.yml       ← production override
│   ├── api/
│   │   └── Dockerfile
│   ├── web/
│   │   └── Dockerfile
│   └── nginx/
│       └── default.conf
└── docs/
    ├── README.md
    ├── 01-design-principles.md       ← already written, copy from project knowledge
    ├── 02-coach-today.md
    ├── 03-coach-trainee-profile.md
    ├── 04-coach-assessment.md
    ├── 05-trainee-home.md
    ├── 06-workspace-settings.md
    ├── 07-invite-and-onboarding.md
    ├── 08-pdf-report.md
    ├── 09-empty-states.md
    ├── 10-error-offline-states.md
    ├── 11-localization-rules.md
    ├── 12-data-model.md              ← Postgres schema + RLS (in repo, generated by Claude)
    ├── 13-docker-setup.md            ← local dev guide
    └── padel-skill-framework-v0.md   ← canonical 27-skill framework
```

## Multi-sport architecture (CRITICAL — workspaces are multi-sport)

A workspace offers 1+ sports (real clubs run padel **and** tennis under one
roof + one billing relationship). Tennis is active platform-wide; enabling it
on a workspace is an explicit admin action.

- `sports` table: `id`, `code` (`'padel'`, `'tennis'`), `name_en`, `name_id`, `is_active`
- `skills.sport_id` FK, `tiers.sport_id` FK — skill codes are sport-prefixed
  (`PADEL_TECH_BANDEJA`, `TENNIS_TECH_FH_DRIVE`)
- **Join tables** carry the per-workspace/athlete/coach sport relationships
  (migrations 0030–0033, doc `tennis-skill-framework-v0.1.md` §3):
  - `workspace_sports` (workspace_id, sport_id, curriculum_id, is_active) — which
    sports a workspace offers + the curriculum per sport
  - `athlete_sports` — which sports a trainee trains in
  - `membership_sports` — which sports a coach is qualified to assess
  - `athlete_sport_tiers` — denormalized current tier per (athlete, sport)
  - `sessions.sport_id` + `assessments.sport_id` (NOT NULL)
- **Legacy `workspaces.sport_id` / `workspaces.curriculum_id` still exist** and
  are dual-written; resolution falls back to them. Dropping them (doc M4) is
  deferred behind the doc's rollback window.
- **Sport resolution** is app-layer (`src/sports/service.py` `resolve_sport_id`):
  explicit `sport_id` → workspace's single active sport → legacy column. RLS
  stays sport-agnostic (scopes by `workspace_id`). Endpoints take an optional
  `?sport_id`; omitting it defaults to the single active sport, so single-sport
  workspaces need no client change.
- Coach sport-authz enforced on assessment create (lenient when a coach has no
  explicit `membership_sports` rows — keeps the invite flow working).
- FE: `features/sports/` (sport store keyed by workspace, `useCurrentSport`,
  `SportSwitcher` in the coach header — hidden when 1 sport), Settings → Sports
  panel to enable/archive. Plan gate: solo/starter/trial = 1 sport, club_pro = unlimited.

**No hardcoded "padel" anywhere.** It's a row in `sports`, queries always filter by sport.

## Substitutions from prior native plan

Many design docs and discussions referenced React Native primitives. Translate when implementing:

| Prior (RN) | Current (web) |
|------------|---------------|
| React Native + Expo | React + Vite |
| NativeWind | Tailwind CSS |
| Expo Router | React Router 6 |
| MMKV | IndexedDB via Dexie.js |
| react-native-reanimated | Framer Motion or CSS transitions |
| Tabler RN webfont | lucide-react |
| Native bottom sheet | Radix Dialog (or Vaul) |
| Native segmented control | Custom Tailwind component (mirror iOS look) |
| Native haptic feedback | Skip (web vibrate API unreliable) |
| Native push | Web Push (V1.5 only if needed) |
| EAS Build | Docker container deploy |

The **design language is identical** — iOS HIG aesthetic, sentence case, hairlines, no shadows, single accent. Just rendered in browser via Tailwind.

## Conventions — DO

### General
- **TypeScript strict** in `apps/web` and `packages/types`. No `any`. Use Zod at API boundary.
- **Python typed** with mypy strict in `apps/api`. Pydantic v2 for everything that crosses a boundary.
- **All UI strings** in `apps/web/src/locales/*.json`. Never hardcode user-facing text.
- **Skill names** stay in `apps/web/src/skills/skills.ts` constants, NOT locale files.
- **Workspace_id** on every tenant-scoped table + RLS policy enforcing isolation.
- **UUIDs** for primary keys (UUIDv7 if available, UUIDv4 fallback).
- **Snake_case** in DB and Python; **camelCase** in TypeScript over the wire.
- **Sentence case** in all user-facing copy.
- **0.5px hairlines** (`border-[0.5px]` or `border` with `border-color: rgba(0,0,0,0.1)`).
- **Two font weights:** 400 regular, 500 medium. Never 600+.
- **Tap targets ≥ 44pt** (44px in CSS for mobile viewport).
- **Single accent color** per workspace via CSS variable `--accent`. Default `#378ADD`.

### Mobile-first responsive
- Default styles target **375px viewport** (iPhone SE width) — works up to standard desktop
- Breakpoints: `sm: 640px` (large phone landscape), `md: 768px` (tablet), `lg: 1024px` (desktop)
- Mobile: bottom tab nav. Desktop: sidebar nav.
- Coach courtside on phone is the primary use case at MVP — don't sacrifice mobile for desktop polish

### PWA
- `manifest.json` configured with app name, icon, theme color, `display: standalone`
- Service worker via `vite-plugin-pwa` (Workbox-based)
- "Install to home screen" prompt after second visit
- Cache strategy: stale-while-revalidate for API, cache-first for static assets

### Git & PRs
- **Conventional commits**: `feat(scope): subject`, `fix(scope): subject`. Scope = `web`, `api`, `db`, `infra`, etc.
- **PR description**: what + why + screenshot/clip + test plan
- **Branches**: `feat/short-name`, `fix/short-name`, `chore/short-name`
- **Always rebase**, no merge commits in feature branches

### Code style
- ESLint + Prettier at root, all packages inherit
- Ruff + Black for Python in `apps/api`
- `pnpm typecheck` and `pnpm lint` must pass before PR
- Components <200 LOC; extract sub-components or hooks when bigger
- Prefer composition over props explosion

### Offline-first patterns
- Writes (assessments, summaries, settings) → Dexie (IndexedDB) first → TanStack Query mutation queue → server
- Show sync status visibly: `Saved offline ⏳` / `Synced ✓` / `Sync failed ⚠️`
- Never block coach workflow on network — courtside signal is unreliable

### Auth
- JWT with workspace context: `{user_id, active_workspace_id, role, exp}`
- FastAPI middleware extracts `workspace_id` from JWT, executes `SET LOCAL app.current_workspace_id` per request
- RLS policies filter on `current_setting('app.current_workspace_id')::uuid`
- JWT in httpOnly secure cookie (not localStorage — XSS risk)
- Refresh token pattern, 15-min access + 30-day refresh

## Conventions — DON'T

- ❌ Don't use Material UI, Ant Design, Chakra. Use Radix + Tailwind + shadcn/ui.
- ❌ Don't use localStorage for sensitive data — IndexedDB for app data, httpOnly cookies for auth.
- ❌ Don't use phone OTP at MVP. Google + email magic link only.
- ❌ Don't hardcode "padel" anywhere. Reference via `sports` table.
- ❌ Don't skip RLS for "convenience". Multi-tenant data leak risk.
- ❌ Don't translate skill names. Bandeja, Víbora, Chiquita stay Spanish in EN and ID.
- ❌ Don't use emoji in UI. Use lucide-react icons (outline).
- ❌ Don't use shadows. 0.5px hairline borders only.
- ❌ Don't use Title Case or ALL CAPS in UI.
- ❌ Don't use bold body text. Bold for titles + small labels only.
- ❌ Don't use 600/700 font weights.
- ❌ Don't make tap targets <44px. Coach uses courtside with sweaty hands.
- ❌ Don't auto-translate coach narrative (session summaries, monthly notes). Store as-typed.
- ❌ Don't add features outside MVP scope without explicit decision.
- ❌ Don't put video features in MVP. V2+.
- ❌ Don't use server-side rendering features (no Next.js, no Remix). Vite SPA only.
- ❌ Don't put credentials in code. Always `.env`.

## MVP scope (locked)

### In scope (12 weeks)
- Auth: Google Sign-In + email magic link
- Workspace creation (club + personal variants)
- Workspace settings (branding, tier naming Game/Skill/Custom, plan)
- Add trainee + WhatsApp invite (manual via wa.me, no Business API)
- Junior trainee + parent flow
- 27-skill assessment with 1–5 rubric, descriptors, session summary
- Coach trainee profile (radar, blockers, history, sessions)
- Trainee home (tier progress, recent gains, upcoming session, coach note)
- Tier auto-calculation (server-side)
- Monthly PDF report (auto on 1st, manual anytime)
- Coach Today (sessions today, trainee list)
- Mobile bottom nav (Today / Trainees / Sessions / Reports / Settings)
- EN + ID localization
- Offline-first assessment + session summary
- Sentry error tracking
- PWA installable
- Sports = padel (tennis row exists but inactive)

### Out of MVP (deferred)
- Video upload + analysis
- Drill library
- Custom skills per club (only enable/disable platform skills)
- Match maker (Americano, Mexicano, KOTH)
- Phone OTP auth
- WhatsApp Business API auto-send
- In-app payments (manual invoicing for first ~10 clubs)
- AI insights / recommendations
- Tier celebration animations
- Cross-club rankings
- Tournament management
- Custom rubric per club
- Native mobile (RN) — possible V2 if PWA insufficient
- Tennis activation (architecture ready, not surfaced)
- Coach-to-trainee chat
- Web Push notifications

## Reference docs (in this repo)

| Task | Read |
|------|------|
| Any new screen | `docs/01-design-principles.md` |
| Coach Today | `docs/02-coach-today.md` |
| Coach trainee profile | `docs/03-coach-trainee-profile.md` |
| Skill assessment | `docs/04-coach-assessment.md` |
| Trainee home | `docs/05-trainee-home.md` |
| Settings | `docs/06-workspace-settings.md` |
| Invite / onboarding | `docs/07-invite-and-onboarding.md` |
| PDF reports | `docs/08-pdf-report.md` |
| Empty states | `docs/09-empty-states.md` |
| Error / offline | `docs/10-error-offline-states.md` |
| Translations | `docs/11-localization-rules.md` |
| Database schema | `docs/12-data-model.md` |
| Docker / dev | `docs/13-docker-setup.md` |
| Skill ontology | `docs/padel-skill-framework-v0.md` |

## Common commands

```bash
# Install everything
pnpm install

# Start full stack (everything in Docker)
docker compose -f infra/docker-compose.yml up -d

# Watch logs
docker compose -f infra/docker-compose.yml logs -f

# Run migrations
docker compose -f infra/docker-compose.yml exec api alembic upgrade head

# Seed default data (sports, skills, tiers, descriptors)
docker compose -f infra/docker-compose.yml exec api python -m scripts.seed

# Create new migration
docker compose -f infra/docker-compose.yml exec api alembic revision --autogenerate -m "add_x_table"

# Web dev (also in Docker but with volume mount for hot reload)
docker compose -f infra/docker-compose.yml up web

# Run tests
pnpm test                    # all
docker compose -f infra/docker-compose.yml exec api pytest

# Type check (must pass before PR)
pnpm typecheck

# Lint
pnpm lint
pnpm lint:fix

# DB shell
docker compose -f infra/docker-compose.yml exec postgres psql -U padelcoach

# Mailpit UI (catch dev emails)
open http://localhost:8025

# MinIO console (S3 dev)
open http://localhost:9001

# Reset everything (destructive — local only)
docker compose -f infra/docker-compose.yml down -v
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml exec api alembic upgrade head
docker compose -f infra/docker-compose.yml exec api python -m scripts.seed
```

## Decision log (anchored — don't re-litigate without strong reason)

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Workspace = tenant (not club) | Lets solo coaches use the platform without forcing club affiliation |
| 2 | Multi-sport via join tables (`workspace_sports` / `athlete_sports` / `membership_sports`); a workspace offers 1+ sports | Real clubs run padel + tennis under one roof + one billing relationship. Sport is an app-layer filter (`resolve_sport_id`, default = single active sport); RLS stays workspace-scoped. Legacy `workspaces.sport_id` kept + dual-written until the M4 drop |
| 3 | iOS HIG aesthetic, no Material | Premium feel, single accent for branded SaaS |
| 4 | Web first, no app stores | Faster MVP iteration, no review delays, lower cost |
| 5 | Vite SPA, not Next.js | Simpler, smaller, all-auth so no SSR benefit |
| 6 | PWA installable | Mobile users get app-like experience, no app store overhead |
| 7 | Google + email magic link only at MVP | Phone OTP costs money; pilots have email |
| 8 | RLS for multi-tenancy | Defense in depth — code bug doesn't leak data |
| 9 | IndexedDB via Dexie | Robust offline storage, complex queries possible |
| 10 | Manual WhatsApp share via wa.me | WA Business API costs money; manual works at MVP scale |
| 11 | Sentence case + 0.5px hairlines | Modern iOS aesthetic, no shadows |
| 12 | EN + ID with selective translation | Skills stay Spanish/English (international vocab); UI translates |
| 13 | Trainees free, paid per workspace | Standard B2B SaaS pattern |
| 14 | Default curriculum APPA-aligned | Asia-Pacific focus; clubs can override at Club Pro tier |
| 15 | Tier naming: Game/Skill/Custom | Clubs choose Bronze/Silver style or Beginner/Intermediate/Advanced or fully custom |
| 16 | PDF reports = monthly auto + manual | Parent-facing artifact; concrete value |
| 17 | Everything Docker (dev + prod) | Consistency, easy deploy to VPS or Railway |
| 18 | Skip in-app payment at MVP | Manual invoicing first 10 clubs; Stripe/Xendit later |

## When user asks for a feature

1. Check MVP scope above
2. If in scope → build
3. If out of scope → flag and ask: skip, V1.5 ticket, or rescope MVP?
4. Don't silently add scope

## Working with this codebase

When implementing a feature:

1. Read the relevant doc in `docs/` first
2. Check existing patterns — does similar code exist? Mirror it.
3. Plan in commits — small, atomic, reviewable
4. Write tests for backend logic + critical UI flows (Playwright for E2E, Vitest for unit)
5. Run typecheck + lint before claiming done
6. Update docs if behavior diverges from spec

When stuck on a design decision, the design rationale sections in `docs/0X-*.md` usually have the answer. If not, ask the human — don't improvise on aesthetics.

## Brand & identity

- Product name: **PadelCoach** (working name)
- Default accent: `#378ADD` (iOS blue)
- Logo: square with workspace initials (white on accent), or uploaded image
- Default font: System (`-apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, "Segoe UI", Roboto, "Helvetica Neue", sans-serif`)
- Domain: TBD

## Out of scope for Claude Code (need human)

- Design new screens (use design tool first, then write spec doc)
- Update copy tone (review with native ID speaker)
- Pricing decisions
- Pilot club outreach
- Privacy policy / Terms of Service legal text
- Marketing site / landing page

## When in doubt

Default to: simpler, more iOS, more conservative on color, more space, fewer words.
