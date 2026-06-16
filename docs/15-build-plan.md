# racademy — Sequential FE↔BE Implementation Plan (Integrated)

> One prompt per step. Test, then advance. This plan integrates the original 20-step build sequence with pilot-readiness gaps surfaced during planning (multi-coach invite, session scheduling, trainee→coach assignment, demo seed, sample PDF, founder admin tool, in-app feedback widget, trial expiration UX) and re-sequences the work to reach a **demo-able state after Step 14** so club / coach outreach can begin before the full MVP is shipped.

---

## How to use this document with Cursor

Feed **one step at a time** to Cursor Composer (`Cmd+I` → switch to Agent mode). After each step:

1. Run the **Verify** block in the integrated terminal.
2. Confirm the **Done when** checklist is green.
3. Commit with the suggested conventional-commit message in the step.
4. Move to the next step in a *fresh* Composer session — context bloat across steps wastes tokens and degrades output.

### Cursor-specific prompt template

For any step, paste this into Composer:

> Read `@docs/CLAUDE.md` and the docs listed under **Reads** for this step (use `@docs/0X-...md` syntax to attach them). Then implement step `<N>` from `@docs/15-build-plan.md` exactly as written. Honor every convention in `CLAUDE.md`. Stop after the **Done when** checklist is green and the **Verify** block passes; do not advance to the next step. Suggest a conventional-commit message at the end.

### Cursor settings (one-time)

- Enable **Agent mode** in Composer settings — required for multi-file edits.
- Add `docs/CLAUDE.md` to **Cursor Rules → Project Rules** so it auto-attaches on every Composer session.
- Set `apps/web/node_modules` and `apps/api/.venv` to `.cursorignore` to keep indexing fast.
- Enable **YOLO mode** only for `pnpm install`, `pytest`, `alembic`, `docker compose` commands — never for `rm`, `mv`, `git push`.

If a step fails verification, paste the failure back into the *same* Composer session and ask it to fix — don't advance until the verify block passes. Skipping ahead compounds breakage.

**Order is non-negotiable within each pair.** FE steps assume their paired BE step lands next; BE steps assume the prior FE step has defined the contract. Across pairs you have some flexibility, but the dependency graph at the top of each pair tells you what must already exist.

---

## Conventions every step inherits

These are baked into `CLAUDE.md` and `docs/01-design-principles.md` — every step honors them silently, no need to repeat:

- TypeScript strict on FE, mypy strict on BE; no `any`, no untyped public functions.
- Tailwind tokens drive all visual chrome — never hardcode hex; read `--accent` from CSS vars.
- Sentence case everywhere. Two font weights only (400, 500). 0.5px hairlines, no shadows.
- 44pt minimum tap targets. Tabler / lucide-react outline icons only.
- All BE tables that are workspace-scoped get RLS with `current_workspace_id()`.
- Every API request scopes to a workspace via JWT-derived `app.current_workspace_id` GUC.
- Multi-sport from day 1 — no string `'padel'` in code, only `sport_id` lookups.
- EN + ID translations live in `apps/web/src/i18n/{en,id}.json`. Skill names stay English/Spanish.
- Conventional commits scoped per package: `feat(web): ...`, `feat(api): ...`, `chore(infra): ...`.

If a step would need to violate one of these, stop and ask before proceeding.

---

## Phase map

| Phase | Steps | What you can do at the end |
|---|---|---|
| 0 — Foundation | 0.1 → 0.3 | Repo boots; DB migrated + seeded; everything Docker-up healthy |
| 1 — Demo-able core | 1 → 14 | Coach signs in → creates workspace → invites coaches → adds trainees → assigns coach → schedules sessions → assesses skills → sees radar profile → generates PDF report. **Ready to demo to first 2-3 trusted coaches.** |
| 2 — Pilot enablers | 15 → 19 | Demo workspace pre-seeded; in-app tour; founder admin tool; in-app feedback; trial UX. **Ready for formal pilot outreach.** |
| 3 — Trainee side + settings | 20 → 25 | Trainees see their own home + tier progress; clubs can self-serve workspace settings; full i18n + offline + PWA polish. |
| 4 — Hardening | 26 | Audit log, Sentry, healthchecks, deploy script. **Production-ready.** |

Demo-ready checkpoint sits after **Step 14**. Pilot-launch checkpoint sits after **Step 19**. Production-launch checkpoint sits after **Step 26**.

---

# Phase 0 — Foundation (do once, in order)

Three setup steps before any FE↔BE work begins. These are not feature work; they exist so feature steps can assume the rails.

---

## Step 0.1 — Monorepo scaffold

**Goal.** Create the empty pnpm + Python monorepo structure exactly as specified in `CLAUDE.md`, with package.json files, tsconfigs, lint configs, and empty entry points.

**Reads.** `CLAUDE.md` (the "Repo structure" section).

**Files to create.**

```
/package.json                       (workspaces: apps/*, packages/*)
/pnpm-workspace.yaml
/tsconfig.base.json                 (strict)
/.editorconfig
/.gitignore
/.nvmrc                             (node 20)
/apps/web/package.json              (vite + react 18 + ts strict)
/apps/web/vite.config.ts            (PWA plugin scaffolded, off until Step 24)
/apps/web/tsconfig.json
/apps/web/index.html
/apps/web/src/main.tsx              (mounts <App />)
/apps/web/src/App.tsx               (returns <h1>racademy</h1> placeholder)
/apps/web/tailwind.config.ts        (CSS-var-driven theme; tokens from §"Color tokens" of 01-design-principles.md)
/apps/web/postcss.config.cjs
/apps/web/src/styles/tokens.css     (all the CSS vars from 01-design-principles.md)
/apps/web/src/styles/global.css     (imports tokens, Tailwind base/components/utilities)
/apps/api/pyproject.toml            (FastAPI 0.110, SQLAlchemy 2 async, Pydantic v2, alembic, structlog, ruff, mypy strict)
/apps/api/src/main.py               (FastAPI app, /healthz returning {"status":"ok"})
/apps/api/alembic.ini
/apps/api/alembic/env.py
/apps/api/scripts/__init__.py
/packages/types/package.json
/packages/types/src/index.ts        (empty re-export)
```

**Implementation notes.**

- `tsconfig.base.json` extends to apps; `strict: true`, `noUncheckedIndexedAccess: true`, `exactOptionalPropertyTypes: true`.
- ESLint with `@typescript-eslint`, `react-hooks`, `tailwindcss` plugins. Prettier + import-sort.
- Python: ruff for lint+format, mypy strict, pytest async.
- Don't install runtime deps yet beyond what's needed to boot — `pnpm install` should succeed but the apps don't have to do anything yet.

**Done when.**

- [ ] `pnpm install` succeeds at the repo root.
- [ ] `pnpm --filter @racademy/web build` produces a `dist/` with the placeholder `<h1>`.
- [ ] `cd apps/api && uv sync && uv run uvicorn src.main:app` boots; `curl localhost:8000/healthz` returns `{"status":"ok"}`.
- [ ] `pnpm typecheck` and `pnpm lint` both green.

**Verify.**

```bash
pnpm install && pnpm typecheck && pnpm lint
pnpm --filter @racademy/web build
(cd apps/api && uv run pytest -q)   # zero tests; should exit 0
```

**Commit.** `chore(repo): scaffold pnpm + python monorepo`

---

## Step 0.2 — Docker compose (postgres, redis, mailpit, minio)

**Goal.** Bring up all dev infrastructure in containers so api+web run identically on every machine. Dockerize api/web too, mounted with hot reload.

**Reads.** `docs/13-docker-setup.md`.

**Files to create / overwrite.**

```
/infra/docker-compose.yml            (postgres, redis, minio, mailpit, api, worker, web)
/infra/postgres/init/01-extensions.sql   (CREATE EXTENSION pgcrypto, citext, pg_trgm; pg_uuidv7 if available)
/infra/api/Dockerfile                (python 3.12 slim, uv, runs uvicorn with --reload)
/infra/web/Dockerfile                (node 20 alpine, runs vite dev --host 0.0.0.0)
/infra/nginx/default.conf            (reverse proxy /api → api:8000, / → web:5173 — scaffolded for prod use)
/.env.example                        (every var in api-env block, with safe dev defaults; no secrets)
/.env                                (gitignored; copy of .env.example to start)
```

**Implementation notes.**

- Postgres healthcheck must pass before api waits-on it (`depends_on.condition: service_healthy`).
- Mailpit on `:8025` (UI) + `:1025` (smtp).
- Minio on `:9000` (s3 API) + `:9001` (console). Pre-create bucket `racademy-dev` via init script.
- Bind mount `apps/api` and `apps/web` into containers for hot reload. Use named volumes for `node_modules` and `__pycache__` to avoid host/container clashes.
- Add `--profile tools` for adminer (DB GUI on `:8080`) — optional, off by default.

**Done when.**

- [ ] `docker compose -f infra/docker-compose.yml up -d` brings up 6+ services, all healthy within 30s.
- [ ] `docker compose ps` shows postgres, redis, minio, mailpit, api, web, worker all `healthy` or `running`.
- [ ] `curl localhost:8000/healthz` returns `{"status":"ok"}` from inside the container.
- [ ] `open http://localhost:8025` shows Mailpit UI.
- [ ] `open http://localhost:9001` shows MinIO console; bucket `racademy-dev` exists.

**Verify.**

```bash
docker compose -f infra/docker-compose.yml up -d
sleep 10
docker compose -f infra/docker-compose.yml ps
curl -fsS localhost:8000/healthz | jq .
docker compose -f infra/docker-compose.yml exec postgres psql -U racademy -d racademy -c "SELECT extname FROM pg_extension;"
```

**Commit.** `chore(infra): docker-compose with postgres, redis, minio, mailpit`

---

## Step 0.3 — Database schema, RLS, seed

**Goal.** Stand up the full schema from `docs/12-data-model.md`, enable RLS on every tenant-scoped table, and seed sports + curricula + 27 padel skills + 5 level descriptors per skill + 7 tiers + tier requirements.

**Reads.** `docs/12-data-model.md` (entire), `docs/padel-skill-framework-v0.md`, `docs/11-localization-rules.md` (for EN/ID descriptor copy).

**Files to create.**

```
/apps/api/alembic/versions/0001_extensions_and_sports.py
/apps/api/alembic/versions/0002_users_and_workspaces.py
/apps/api/alembic/versions/0003_athletes_skills_tiers.py
/apps/api/alembic/versions/0004_sessions_assessments_reports.py
/apps/api/alembic/versions/0005_invites_subscriptions_audit.py
/apps/api/alembic/versions/0006_rls_policies.py
/apps/api/alembic/versions/0007_helper_functions.py     (current_workspace_id() etc.)
/apps/api/src/db/models/                                (SQLAlchemy models — one per table)
/apps/api/src/db/session.py                             (async engine + sessionmaker)
/apps/api/src/db/rls.py                                 (set_workspace_context() helper)
/apps/api/scripts/seed.py                               (idempotent INSERT ... ON CONFLICT DO NOTHING)
/apps/api/data/skills_padel.json                        (27 skills with category, code, EN+ID names)
/apps/api/data/descriptors_padel.json                   (135 entries: 27 skills × 5 levels, EN+ID)
/apps/api/data/tiers.json                               (7 tiers, Game + Skill + Custom labels)
/apps/api/data/tier_requirements.json                   (per padel-skill-framework-v0.md §6)
```

**Implementation notes.**

- Migrations run in numbered order, each one atomic.
- `0006_rls_policies.py` enables RLS and writes every policy from `docs/12-data-model.md` § "Per-table policies".
- `set_workspace_context(session, workspace_id)` runs `SET LOCAL app.current_workspace_id = '...'` per request — wire this into a FastAPI dependency in Step 2.
- Seed is idempotent: re-running it must not duplicate rows. Use natural keys (`code`, `slug`) on conflict targets.
- The `tennis` sport row exists with `is_active = false`. No tennis skills seeded.

**Done when.**

- [ ] `docker compose exec api alembic upgrade head` runs cleanly.
- [ ] `docker compose exec api python -m scripts.seed` runs and is idempotent (run twice, same row counts).
- [ ] `psql` query `SELECT count(*) FROM skills WHERE sport_id = (SELECT id FROM sports WHERE code = 'padel')` returns 27.
- [ ] `SELECT count(*) FROM skill_level_descriptors` returns 135.
- [ ] `SELECT count(*) FROM tiers` returns 7.
- [ ] All RLS policies exist: `SELECT count(*) FROM pg_policies` ≥ 12.
- [ ] Without `app.current_workspace_id` set, queries against `athletes` return 0 rows even after inserting test data — proves RLS works.

**Verify.**

```bash
docker compose -f infra/docker-compose.yml exec api alembic upgrade head
docker compose -f infra/docker-compose.yml exec api python -m scripts.seed
docker compose -f infra/docker-compose.yml exec api python -m scripts.seed   # idempotency check
docker compose -f infra/docker-compose.yml exec postgres psql -U racademy -d racademy -c \
  "SELECT 'skills' tbl, count(*) FROM skills UNION ALL
   SELECT 'descriptors', count(*) FROM skill_level_descriptors UNION ALL
   SELECT 'tiers', count(*) FROM tiers UNION ALL
   SELECT 'sports', count(*) FROM sports;"
```

**Commit.** `feat(api): schema, RLS policies, padel curriculum seed`

---

# Phase 1 — Demo-able core (Steps 1–14)

7 pairs, 14 steps. At the end of Step 14 you can sign in as a coach, build out a workspace with trainees, assess them, and produce a polished PDF — the full demo loop you need to put in front of a club.

---

## Pair 1 — Auth shell

### Step 1 [FE] — Sign-in / sign-up screens with mocked auth

**Goal.** The full unauthenticated experience: `/signin`, `/signup`, `/auth/callback` (Google), `/auth/magic` (magic link landing). Routes work, design tokens applied, mocked sign-in just sets a fake JWT in memory.

**Reads.** `docs/01-design-principles.md`, `docs/07-invite-and-onboarding.md` (welcome screen layout).

**Files to create.**

```
/apps/web/src/app/router.tsx                  (React Router 6 with public + protected route groups)
/apps/web/src/app/providers.tsx               (TanStack Query, i18n stub, auth context)
/apps/web/src/features/auth/SignInScreen.tsx
/apps/web/src/features/auth/SignUpScreen.tsx
/apps/web/src/features/auth/MagicLinkLanding.tsx
/apps/web/src/features/auth/GoogleCallback.tsx
/apps/web/src/features/auth/auth-store.ts     (Zustand: { token, user, signIn(), signOut() })
/apps/web/src/features/auth/auth-api.ts       (mock: returns fake { token, user } after 600ms)
/apps/web/src/components/PrimaryButton.tsx
/apps/web/src/components/SecondaryButton.tsx
/apps/web/src/components/TextInput.tsx
/apps/web/src/components/Logo.tsx             (R-monogram from docs/14-brand-identity.md)
```

**Implementation notes.**

- Welcome / sign-in layout matches `docs/07-invite-and-onboarding.md` Step 4a — large logo, "Continue with Google" primary, "Continue with email" secondary, terms/privacy footer.
- Magic link landing accepts a `?token=...` query param and shows "Signing you in…" then redirects.
- Auth context exposes `user`, `currentWorkspaceId`, `signIn`, `signOut`. Persist nothing yet — refresh logs you out (BE step adds real persistence).
- Tailwind: `bg-[var(--color-background-tertiary)]`, primary CTA `bg-[var(--accent)] text-white`, hairline borders `border-[0.5px] border-[color:var(--color-border-tertiary)]`.

**Done when.**

- [ ] `/signin` renders the welcome layout with both buttons; tap "Continue with email" → email input + "Send magic link" button → "Check your email" confirmation card.
- [ ] Tap "Continue with Google" → 600ms shimmer → redirects to `/today` (placeholder for now).
- [ ] Tap "Sign out" from the placeholder `/today` → returns to `/signin`.
- [ ] No real network calls — open DevTools Network tab and confirm.

**Verify.**

```bash
pnpm --filter @racademy/web dev
# Manual click-path:
# /signin → Continue with Google → /today (placeholder) → Sign out → /signin
# /signin → Continue with email → enter foo@bar.com → Send magic link → confirmation card
```

**Commit.** `feat(web): sign-in / sign-up screens with mocked auth`

---

### Step 2 [BE] — Real auth: Google verify, magic link, JWT issue/refresh

**Goal.** Replace the FE mocks with real endpoints. `POST /auth/google` verifies Google id_token; `POST /auth/magic/request` emails a magic link via Mailpit; `GET /auth/magic/consume?token=...` mints a JWT; `POST /auth/refresh` rotates it.

**Reads.** `CLAUDE.md` § "Auth" and § "Decision log #7".

**Files to create.**

```
/apps/api/src/auth/__init__.py
/apps/api/src/auth/router.py             (4 endpoints above)
/apps/api/src/auth/schemas.py            (Pydantic v2: GoogleSignInIn, MagicLinkRequestIn, TokenPair, ...)
/apps/api/src/auth/service.py            (find-or-create user, issue tokens, send magic link)
/apps/api/src/auth/jwt.py                (encode/decode access + refresh; HS256, 15min/30day)
/apps/api/src/auth/google.py             (verify id_token via google-auth lib)
/apps/api/src/auth/magic.py              (token = secrets.token_urlsafe(32); store hashed in redis with 15min TTL)
/apps/api/src/auth/email.py              (SMTP via aiosmtplib → mailpit at smtp:1025)
/apps/api/src/deps.py                    (get_current_user, get_current_workspace_id; sets RLS GUC)
/apps/api/tests/test_auth.py             (pytest async: full magic-link flow, expired token rejection, JWT roundtrip)
```

**FE changes (in same step).**

- Replace `auth-api.ts` mock with real `fetch('/api/auth/...')` calls.
- Add a tiny `apiClient.ts` that prepends `/api` and attaches `Authorization: Bearer ${token}` from the auth store.
- Vite dev server proxies `/api/*` to `http://localhost:8000` (`vite.config.ts` `server.proxy`).

**Implementation notes.**

- Magic link URL format: `${WEB_URL}/auth/magic?token=...`. The token is the raw URL-safe value; redis stores `sha256(token) → user_email` so a leak doesn't replay.
- Google verification: `google.oauth2.id_token.verify_oauth2_token(id_token, requests.Request(), GOOGLE_CLIENT_ID)` returns the payload; `sub` becomes `users.google_sub`, email + name come from claims.
- JWT claims: `{ sub: user_id, wsid: current_workspace_id_or_null, exp, iat, jti }`. Refresh tokens stored in redis (rotation on use).
- A user with **no workspace memberships** signs in successfully but `wsid` is null; the FE's protected routes redirect them to `/onboarding/create-workspace` (built in Step 3).

**Done when.**

- [ ] `curl -X POST localhost:8000/auth/magic/request -d '{"email":"foo@bar.com"}'` returns 202; Mailpit shows the email.
- [ ] Clicking the magic link in Mailpit lands on `/auth/magic?token=...`; FE consumes it, gets a JWT, lands on `/today` (or `/onboarding/create-workspace` if no membership).
- [ ] `curl -X POST localhost:8000/auth/refresh -H 'Authorization: Bearer <refresh>'` returns a new pair.
- [ ] Expired or already-consumed magic tokens return 410 with a clear message.
- [ ] `pytest apps/api/tests/test_auth.py` is green.

**Verify.**

```bash
docker compose -f infra/docker-compose.yml exec api pytest tests/test_auth.py -v
# End-to-end click path in browser:
# /signin → "Continue with email" → foo@bar.com → check Mailpit → click link → /onboarding/create-workspace
```

**Commit.** `feat(api): google + magic-link auth with JWT issue/refresh`

---

## Pair 2 — Workspace bootstrap + multi-coach invite

> **New in this plan:** the Members screen and invite-coach endpoint are folded into Pair 2 so Club workspaces are usable from day one. Without this, club owners log in and can't actually add their coaching staff — a pilot blocker.

### Step 3 [FE] — Workspace creation wizard, switcher, and Members screen

**Goal.** A 3-step wizard at `/onboarding/create-workspace` so a freshly authenticated user picks club vs personal, names it, picks an accent color, and lands on `/today`. Plus a workspace switcher in the top-right for users with multiple memberships. Plus a Members screen (Club workspaces only) to invite coaches.

**Reads.** `docs/06-workspace-settings.md`, `docs/01-design-principles.md`, `docs/07-invite-and-onboarding.md`.

**Files to create.**

```
/apps/web/src/features/workspace/CreateWorkspaceWizard.tsx
/apps/web/src/features/workspace/steps/StepType.tsx          (segmented: Club vs Personal)
/apps/web/src/features/workspace/steps/StepBranding.tsx      (name, city, accent color picker, optional logo)
/apps/web/src/features/workspace/steps/StepConfirm.tsx       (live preview card matching 06-workspace-settings.md)
/apps/web/src/features/workspace/workspace-api.ts            (createWorkspace, listMine, switchTo, listMembers, inviteMember)
/apps/web/src/features/workspace/WorkspaceSwitcher.tsx
/apps/web/src/features/workspace/use-current-workspace.ts
/apps/web/src/features/members/MembersScreen.tsx             (Club only — list + invite)
/apps/web/src/features/members/InviteMemberSheet.tsx         (email + role: coach / club_admin)
/apps/web/src/features/members/MemberRow.tsx                 (avatar, name, role pill, "Pending" badge if not yet claimed)
/apps/web/src/components/SegmentedControl.tsx
/apps/web/src/components/ColorSwatch.tsx                    (5 preset swatches + custom hex input)
/apps/web/src/components/RolePill.tsx
```

**Implementation notes.**

- Wizard state in Zustand; submit on confirm step.
- Live preview re-renders the workspace card from `06-workspace-settings.md` as the user types. Accent change is instant (sets CSS var inline on the preview container only — global accent doesn't change until creation).
- Workspace switcher is a small dropdown in the top nav. Switching calls `POST /workspaces/{id}/switch` (added in Step 4) which mints a new JWT scoped to that workspace.
- Members screen lives at `/settings/members`; Personal workspaces redirect away from it with "Members aren't used in personal workspaces".
- Invite flow: enter email → pick role (Coach default, Club admin secondary) → submit → row appears in list with "Pending" pill → "Resend invite" available on right-side menu.
- After successful workspace creation, navigate to `/today` for Personal, or `/settings/members` for Club (so the owner is nudged to invite coaches immediately).

**Done when.**

- [ ] User without a workspace is redirected to the wizard on every protected route.
- [ ] Wizard validates name (required, ≤ 120 chars), accent color (valid hex), progresses through all 3 steps.
- [ ] Live preview reflects current input.
- [ ] On submit, calls `POST /workspaces` (still mocked — returns a fake workspace object after 400ms).
- [ ] After landing on `/today` (personal) or `/settings/members` (club), the top-right shows `WorkspaceSwitcher` with the new workspace selected.
- [ ] Club workspace: tap "Invite member" → sheet opens → submit email + role → row appears with "Pending" pill.

**Verify.** Click-path: sign in fresh → wizard → create *Club* → land on `/settings/members` → invite `coach2@example.com` as Coach → see pending row in list. Switch to a Personal workspace → confirm `/settings/members` redirects away.

**Commit.** `feat(web): workspace wizard, switcher, members screen`

---

### Step 4 [BE] — Workspaces + memberships + invite-member + RLS context

**Goal.** Real `POST /workspaces`, `GET /workspaces/mine`, `POST /workspaces/{id}/switch`, `GET /workspaces/{id}/members`, `POST /workspaces/{id}/members/invite`, `POST /memberships/{token}/accept`. RLS context middleware sets `app.current_workspace_id` on every request from the JWT's `wsid` claim.

**Reads.** `docs/12-data-model.md` § "Workspaces", § "Workspace memberships", § "Invites", § "Row Level Security".

**Files to create.**

```
/apps/api/src/workspaces/router.py
/apps/api/src/workspaces/schemas.py
/apps/api/src/workspaces/service.py        (create_workspace + create_owner_membership in one txn)
/apps/api/src/workspaces/members.py        (list, invite, accept)
/apps/api/src/middleware/rls.py            (FastAPI dependency: SET LOCAL app.current_workspace_id = ...)
/apps/api/tests/test_workspaces.py
/apps/api/tests/test_member_invites.py
```

**FE changes (same step).** Delete the mocks in `workspace-api.ts`; point at real endpoints.

**Implementation notes.**

- `POST /workspaces` body: `{ type, name, city?, brand_color?, primary_locale }`. Server sets `sport_id` to padel by default, `plan = 'free_trial'`, `trial_ends_at = now + 30 days`, `owner_user_id = current_user`. Creates a membership row with role `club_admin` (if club) or `coach` (if personal).
- After creation, server returns a *new* JWT with `wsid` set to the new workspace. FE replaces its stored token.
- `POST /workspaces/{id}/switch` validates the current user has an active membership, then mints a new JWT with `wsid = id`.
- `POST /workspaces/{id}/members/invite` body: `{ email, role }`. Creates a `workspace_member_invites` row with `token = secrets.token_urlsafe(20)` and 7-day expiry. Sends an email via Mailpit with the magic link `${WEB_URL}/invite/member?token=...`.
- `POST /memberships/{token}/accept` (called from the link landing): requires authenticated user. Creates membership row, marks invite consumed, mints new JWT with `wsid` set.
- RLS dependency: every authenticated route runs `SET LOCAL app.current_workspace_id = '<wsid>'` before handler executes. If `wsid` is null, set the GUC to empty (and `current_workspace_id()` returns null → policies that allow `IS NULL` see platform data only).
- Authorization: only `club_admin` of a Club workspace can invite members. Personal workspace owners can't (no members).

**Done when.**

- [ ] FE wizard creates a real workspace; row appears in `psql`.
- [ ] After switch, queries from a different workspace's coach return zero rows for the first workspace's data — RLS proven by integration test.
- [ ] Club admin can invite a coach by email; Mailpit shows the email; clicking the link → sign in → membership created.
- [ ] A coach (role `coach`) gets 403 when calling `POST /members/invite`.
- [ ] `pytest test_workspaces.py test_member_invites.py` green.

**Verify.**

```bash
TOKEN=$(curl -s ...)   # from Step 2 magic-link flow
curl -X POST localhost:8000/workspaces -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type":"club","name":"Senayan Padel Club","brand_color":"#378ADD","primary_locale":"id"}'
# Then in psql:
docker compose exec postgres psql -U racademy -d racademy -c "SELECT id, type, name, plan FROM workspaces;"
# Invite flow:
WSID=...
curl -X POST localhost:8000/workspaces/$WSID/members/invite -H "Authorization: Bearer $TOKEN" \
  -d '{"email":"coach2@example.com","role":"coach"}'
# Check Mailpit at localhost:8025
```

**Commit.** `feat(api): workspaces, memberships, member invites, RLS context`

---

## Pair 3 — Trainees + WhatsApp invite + coach assignment

> **New in this plan:** `athletes.primary_coach_id` is added now (not deferred) so Club workspaces with multiple coaches have a clear "owner" per trainee from day one. Avoids the "all coaches see all trainees" confusion in pilots.

### Step 5 [FE] — Trainees list + Add trainee + WhatsApp + coach assignment

**Goal.** Build the Trainees tab list, the Add Trainee form per `docs/07-invite-and-onboarding.md` Step 1, the WhatsApp hand-off via `wa.me` deep link with the templated message, and (Club only) a coach picker on the trainee form + edit menu.

**Reads.** `docs/07-invite-and-onboarding.md` Steps 1–3, `docs/09-empty-states.md` § "Coach · Trainees".

**Files to create.**

```
/apps/web/src/features/trainees/TraineesScreen.tsx
/apps/web/src/features/trainees/AddTraineeScreen.tsx       (modal-route /trainees/new)
/apps/web/src/features/trainees/trainee-form.ts            (zod schema + react-hook-form)
/apps/web/src/features/trainees/whatsapp.ts                (buildWhatsAppUrl, EN/ID templates)
/apps/web/src/features/trainees/trainees-api.ts            (createTrainee, getInviteToken, assignCoach — mocked)
/apps/web/src/features/trainees/CoachPickerField.tsx       (Club only — list of workspace coaches as segmented or dropdown)
/apps/web/src/features/trainees/AssignCoachSheet.tsx       (reusable, opens from trainee row context menu)
/apps/web/src/components/PhoneInput.tsx                   (E.164 with +62 prefill for ID locale)
```

**Implementation notes.**

- Required fields only: name + WhatsApp phone (E.164). Optional: email, date of birth, notes.
- **Club workspaces** also show a "Coach" field defaulting to "Me" — solo coaches in Personal workspaces never see this field.
- "Send WhatsApp invite" calls `createTrainee` → receives `{trainee, invite}` → opens `https://wa.me/${e164}?text=${encodeURIComponent(message)}` in a new tab.
- Templated message uses i18n keys (EN+ID variants from `docs/07`).
- "Save without invite" creates the trainee row but no invite — user can send later from the trainee profile.
- Trainee list shows a small coach name under each trainee in Club workspaces (subtle, secondary text color).
- Reassign coach: row context menu → "Reassign coach" → sheet → save.
- Empty state per `docs/09-empty-states.md`: "Add your first trainee" → 2 CTAs.

**Done when.**

- [ ] `/trainees` shows the list (or empty state).
- [ ] Tap "+" → `/trainees/new` modal-style screen.
- [ ] Fill name + phone → "Send WhatsApp invite" → new tab opens `wa.me/...` with templated message.
- [ ] "Save without invite" creates the trainee, returns to list, no tab opens.
- [ ] Club workspace: Coach picker visible, defaults to current user, can switch to another invited coach.
- [ ] Personal workspace: Coach picker hidden.
- [ ] Reassign from list row works and updates the displayed coach name.

**Verify.** Add a real-looking trainee, confirm wa.me URL contains the templated message verbatim (URL-decode it). In a Club workspace with 2 coaches invited, reassign and confirm the secondary-line coach name updates.

**Commit.** `feat(web): trainees list, add form, whatsapp invite, coach assignment`

---

### Step 6 [BE] — Trainees + Invites + branded OG + primary_coach_id

**Goal.** `POST /trainees` creates an athlete + invite atomically. `GET /trainees`, `PATCH /trainees/:id`, `DELETE /trainees/:id` (soft-delete), `PATCH /trainees/:id/coach` for reassignment. `GET /i/{token}` is a public HTML page with workspace-branded OG meta tags so the WhatsApp link unfurls properly. New migration adds `athletes.primary_coach_id`.

**Reads.** `docs/12-data-model.md` § "Invites" and § "Athletes", `docs/07-invite-and-onboarding.md` § "Server-side requirement".

**Files to create.**

```
/apps/api/alembic/versions/0008_athletes_primary_coach.py    (ADD COLUMN primary_coach_id UUID REFERENCES users(id))
/apps/api/src/athletes/create.py            (creates athlete + invite in one txn; assigns primary coach)
/apps/api/src/athletes/reassign.py          (PATCH /trainees/:id/coach — validates target user is a member)
/apps/api/src/invites/router.py
/apps/api/src/invites/schemas.py
/apps/api/src/invites/service.py            (token = secrets.token_urlsafe(20); 7-day expiry)
/apps/api/src/invites/og_landing.py         (returns text/html with og:* meta from workspace)
/apps/api/templates/invite_landing.html     (jinja2 — minimal HTML, dynamic og:image, og:title, og:description)
/apps/api/tests/test_invites.py
/apps/api/tests/test_coach_assignment.py
```

**FE changes.** Wire `trainees-api.ts` to real endpoints. Drop the mock. Add `assignCoach` call.

**Implementation notes.**

- Invite token format: `{workspace_slug_short}-{trainee_handle}-{rand6}` — readable, debuggable.
- `GET /i/{token}` returns full HTML (this is the only non-API route on the API service). Includes `<meta property="og:title" content="{workspace.name}">`, `og:description` ("Track your padel progress with {workspace.name}"), `og:image` (workspace logo if set, else generated initials avatar). Cache `Cache-Control: public, max-age=86400` (CDNs unfurl).
- Page renders the Step 4b layout from `docs/07` with OS-detect → "Open the app" or "Continue in browser" link to `/login?invite_token={token}`.
- `primary_coach_id` defaults to the inviting user. Reassign requires the new coach be an active member of the workspace (else 422).
- Tests: invite creation, expiry rejection, idempotency (re-inviting same trainee creates new token, invalidates old), OG HTML smell-check, coach reassignment authorization (only `club_admin` can reassign anyone; coaches can only reassign trainees where they're current owner).

**Done when.**

- [ ] FE add-trainee flow really creates rows.
- [ ] `curl localhost:8000/i/SOMETOKEN` returns HTML with branded `og:*` tags.
- [ ] `psql` shows `primary_coach_id` set on every new athlete.
- [ ] `PATCH /trainees/:id/coach` reassigns; non-admin coach gets 403 when reassigning another coach's trainee.
- [ ] `pytest test_invites.py test_coach_assignment.py` green.
- [ ] Sharing the URL in WhatsApp Web (manual smoke test) shows the branded preview.

**Verify.**

```bash
TOKEN=$(curl -X POST localhost:8000/trainees -H "Authorization: Bearer $JWT" \
  -d '{"name":"Andi","phone_e164":"+628123456789"}' | jq -r .invite.token)
curl -s localhost:8000/i/$TOKEN | grep og:title
docker compose exec postgres psql -U racademy -d racademy -c \
  "SELECT display_name, primary_coach_id FROM athletes ORDER BY created_at DESC LIMIT 5;"
```

**Commit.** `feat(api): trainees, invites, OG landing, primary_coach_id`

---

## Pair 4 — Coach Today + session scheduling

> **New in this plan:** session creation flow added. The original plan only read sessions; without a create-session UI, `/today` is empty unless seeded by hand. Coaches need to schedule tomorrow's lesson from the app.

### Step 7 [FE] — Coach Today + bottom nav + Schedule Session sheet

**Goal.** The coach home (`/today`) per `docs/02-coach-today.md`: greeting block, "Up next" card, "Trainees today" grouped table. The 5-tab bottom nav (Today / Trainees / Sessions / Reports / Settings) shared across all authed coach screens. A "Schedule session" sheet reachable from the floating "+" on `/today` and `/sessions`.

**Reads.** `docs/02-coach-today.md`, `docs/01-design-principles.md` (grouped tables, bottom tab bar, avatar circle).

**Files to create.**

```
/apps/web/src/layouts/CoachShell.tsx                  (top status bar + content + bottom nav)
/apps/web/src/components/BottomTabBar.tsx
/apps/web/src/components/GroupedTable.tsx             (white surface, hairline rows, section header outside)
/apps/web/src/components/Avatar.tsx
/apps/web/src/components/TierPill.tsx
/apps/web/src/features/today/CoachTodayScreen.tsx
/apps/web/src/features/today/today-api.ts             (getTodaySessions — mocked for now)
/apps/web/src/features/today/UpNextCard.tsx
/apps/web/src/features/today/TraineeRow.tsx
/apps/web/src/features/sessions/SessionsScreen.tsx    (weekly view, simple list grouped by day)
/apps/web/src/features/sessions/ScheduleSessionSheet.tsx   (trainee picker + datetime + court + focus + duration)
/apps/web/src/features/sessions/sessions-api.ts       (createSession, listSessions — mocked)
/apps/web/src/components/DateTimePicker.tsx           (mobile-friendly native input + display)
```

**Implementation notes.**

- Mock data in `today-api.ts`: array of 5 sessions with realistic times, courts, trainees, last-assessed timestamps. The mock conforms to the contract that Step 8 will fulfill — define it as a TS type now in `packages/types`.
- Empty state: when mock returns `[]`, render the empty state from `docs/09-empty-states.md` § "Coach · Today" — but ensure the "Schedule session" CTA in the empty state opens the same `ScheduleSessionSheet`.
- Tier pill colors come from accent + accent-bg. Game-style labels by default ("Bronze", "Silver", "Gold").
- Locale-aware date formatting with `date-fns/format` and the user's preferred locale.
- `ScheduleSessionSheet` fields: trainee (combobox searchable), date+time, court (free text), focus (free text, optional), duration in minutes (default 60). On submit → optimistic insert into today/sessions list → API call → reconcile.

**Done when.**

- [ ] `/today` renders the greeting, up-next card, and 5 trainee rows.
- [ ] Toggle the mock to `[]` → empty state with "Schedule session" + "Add a trainee first" buttons appears.
- [ ] Tap "Schedule session" → sheet opens → submit → row appears optimistically.
- [ ] Bottom nav switches between tabs (other tabs render placeholder screens for now).
- [ ] `/trainees`, `/sessions`, `/reports`, `/settings` are all routable.

**Verify.** Visual click-through. Take a screenshot, compare to `docs/02-coach-today.md` mockup.

**Commit.** `feat(web): coach today screen, bottom nav, schedule session sheet`

---

### Step 8 [BE] — Sessions endpoints + Trainees list + dev seed

**Goal.** `POST /sessions` (create), `GET /sessions/today` (coach-scoped, sorted by `scheduled_at`, with last-assessed-at per trainee joined in), `GET /sessions?from=&to=` (range for the Sessions tab), `PATCH /sessions/:id` (reschedule), `DELETE /sessions/:id` (cancel). `GET /trainees` (paginated list filterable by name). A `dev_seed_demo.py` script that creates a fully-populated demo workspace.

**Reads.** `docs/12-data-model.md` § "Sessions" and § "Athletes".

**Files to create.**

```
/apps/api/src/sessions/router.py
/apps/api/src/sessions/schemas.py
/apps/api/src/sessions/service.py
/apps/api/src/athletes/router.py
/apps/api/src/athletes/schemas.py
/apps/api/src/athletes/service.py
/apps/api/tests/test_sessions.py
/apps/api/tests/test_athletes.py
/apps/api/scripts/dev_seed_demo.py    (creates a demo Club workspace, 2 coaches, 8 trainees with assignments, 5 sessions today, prior assessments)
```

**FE changes.** Replace `today-api.ts` and `sessions-api.ts` mocks with real fetch calls.

**Implementation notes.**

- `POST /sessions` body: `{ athlete_id, scheduled_at, duration_min, court?, focus? }`. Server sets `coach_id = current_user` and inherits `workspace_id` from RLS context.
- `GET /sessions/today` returns `[{id, scheduled_at, court, focus, duration_min, trainee: {id, name, last_assessed_at, current_tier}}]`. Tier is derived server-side per docs/12 § Performance notes; cache result on athlete row.
- `GET /trainees` supports `?q=` (pg_trgm fuzzy on display_name), `?limit=`, `?cursor=`, `?coach_id=` (filter to one coach in Club workspaces). Default order: most recently assessed first.
- `dev_seed_demo.py` is critical — without it the FE has nothing to render. Run after `seed.py` to populate a demo workspace named "Demo Club" with realistic data. Idempotent. Used in dev *and* as the basis for Step 15.

**Done when.**

- [ ] `curl -X POST localhost:8000/sessions -d '{"athlete_id":"...","scheduled_at":"...","duration_min":60}'` creates a row; FE shows it.
- [ ] `curl localhost:8000/sessions/today -H "Authorization: Bearer $TOKEN"` returns sessions for the demo workspace.
- [ ] FE `/today` shows real names from the dev seed.
- [ ] Switching to a workspace with no sessions shows the empty state.
- [ ] `pytest test_sessions.py test_athletes.py` green; tests prove RLS isolation between workspaces.

**Verify.**

```bash
docker compose exec api python -m scripts.dev_seed_demo
curl -s localhost:8000/sessions/today -H "Authorization: Bearer $TOKEN" | jq '. | length'   # 5
```

**Commit.** `feat(api): sessions CRUD, trainees list, dev seed demo`

---

## Pair 5 — Coach trainee profile

### Step 9 [FE] — Coach Trainee Profile screen

**Goal.** `/trainees/:id` showing every section from `docs/03-coach-trainee-profile.md`: hero, stats grid, tier progress, blocking skills, radar SVG, recent gains, all-skills grid, recent sessions, action bar.

**Reads.** `docs/03-coach-trainee-profile.md` end to end, `docs/01-design-principles.md` (radar style).

**Files to create.**

```
/apps/web/src/features/trainee-profile/TraineeProfileScreen.tsx
/apps/web/src/features/trainee-profile/HeroBlock.tsx
/apps/web/src/features/trainee-profile/StatsGrid.tsx
/apps/web/src/features/trainee-profile/TierProgressCard.tsx
/apps/web/src/features/trainee-profile/BlockingSkillsList.tsx
/apps/web/src/features/trainee-profile/SkillRadar.tsx          (SVG, 4 axes — Tech/Tac/Phys/Mental)
/apps/web/src/features/trainee-profile/RecentGains.tsx
/apps/web/src/features/trainee-profile/AllSkillsAccordion.tsx
/apps/web/src/features/trainee-profile/RecentSessions.tsx
/apps/web/src/features/trainee-profile/profile-api.ts          (mocked — returns full profile shape)
/apps/web/src/features/trainee-profile/profile-types.ts
```

**Implementation notes.**

- Radar is hand-rolled SVG (no chart lib). 4 axes 90° apart, polygon filled with `fill: var(--accent); fill-opacity: 0.18; stroke: var(--accent)`.
- Stats grid: 3 columns, hairline dividers, no shadows.
- "All skills" accordion uses the same pattern as the assessment screen — single-open by default. Each skill row shows a 5-cell mini-bar (filled cells = score), score pill, "Not rated" if no assessment.
- Empty profile state: trainee added but never assessed. Shows the empty state from `docs/09-empty-states.md` § "Trainee profile" — "No assessments yet, Start first assessment" CTA.

**Done when.**

- [ ] Tap any trainee row from `/today` or `/trainees` → opens `/trainees/:id`.
- [ ] All sections render with mock data.
- [ ] Mock-toggle to "no assessments" → empty state.
- [ ] "New assessment" button is wired but goes to a placeholder for now (real screen lands in Step 11).

**Verify.** Visual diff against the screenshot in `docs/03-coach-trainee-profile.md`.

**Commit.** `feat(web): coach trainee profile screen`

---

### Step 10 [BE] — Aggregated trainee profile endpoint

**Goal.** One endpoint `GET /trainees/:id/profile` that returns everything the FE screen needs: identity, stats, tier progress, blockers, radar averages, recent gains, all skill scores, recent sessions. Server does the math; FE renders.

**Reads.** `docs/12-data-model.md` § "Performance notes", `docs/padel-skill-framework-v0.md` § "Tier requirements".

**Files to create.**

```
/apps/api/src/athletes/profile.py        (the aggregate query)
/apps/api/src/athletes/tier_calc.py      (current tier from latest scores; gap-to-next-tier)
/apps/api/src/athletes/radar.py          (averages per category)
/apps/api/tests/test_profile.py
```

**FE changes.** Replace mock with real fetch. Delete `profile-api.ts` mock data.

**Implementation notes.**

- Use Postgres `DISTINCT ON (skill_id)` to fetch latest assessment per skill in one query.
- Tier calc: walk `tier_requirements` ascending, find the highest tier where ALL required skills meet threshold. Blocking skills for next tier = skills below threshold.
- "Recent gains" = assessments in last 30 days where new score > prior latest. Limit 4.
- All math runs server-side; FE shape is dumb. Keeps tier logic in one place and out of the client.
- One-shot endpoint avoids a chatty client (significant on slow 3G — Indonesia target).

**Done when.**

- [ ] `curl localhost:8000/trainees/<id>/profile` returns all sections in one JSON payload.
- [ ] Scores match what's in the DB (dev seed has known assessments — assert in tests).
- [ ] Tier calc matches the framework v0 thresholds.
- [ ] FE screen now shows real data from the demo seed.

**Verify.**

```bash
curl -s localhost:8000/trainees/$ID/profile -H "Authorization: Bearer $JWT" | jq '.tier_progress, .blockers[0:3]'
```

**Commit.** `feat(api): aggregated trainee profile endpoint with tier calc`

---

## Pair 6 — Assessment

### Step 11 [FE] — Assessment screen with offline queue

**Goal.** `/trainees/:id/assess` per `docs/04-coach-assessment.md`: trainee strip, level legend, 4 collapsible categories with 27 skills, segmented controls, expandable descriptors with notes, session summary, save. Writes to local IndexedDB queue first, then syncs when online.

**Reads.** `docs/04-coach-assessment.md`, `docs/10-error-offline-states.md` § "Local-first writes".

**Files to create.**

```
/apps/web/src/features/assessment/AssessmentScreen.tsx
/apps/web/src/features/assessment/SkillRow.tsx
/apps/web/src/features/assessment/SegmentedScore.tsx
/apps/web/src/features/assessment/DescriptorPanel.tsx
/apps/web/src/features/assessment/SessionSummary.tsx
/apps/web/src/features/assessment/CategoryGroup.tsx          (collapsible, single-open default)
/apps/web/src/features/assessment/use-assessment-draft.ts    (in-memory + IndexedDB persistence)
/apps/web/src/db/dexie.ts                                    (Dexie tables: assessments_pending, sessions_pending)
/apps/web/src/features/sync/sync-engine.ts                   (drains pending tables when online)
/apps/web/src/components/OfflineBanner.tsx
```

**Implementation notes.**

- Save flow: write to `assessments_pending` Dexie table → return immediately (optimistic) → sync engine POSTs in background. On success, remove from pending. On 5xx/network error, keep in pending and retry with exponential backoff.
- `Save` button always succeeds locally; toast says "Saved" or "Saved offline" based on connectivity.
- Confirmation dialog "Discard changes?" only if user backs out with unsaved local edits.
- Descriptors panel pulls from `/skills/:code/descriptors` endpoint (added in Step 12). Cache aggressively in TanStack Query (these don't change).
- Segmented control is fully tap-driven, 5 segments, 44pt+ tall.

**Done when.**

- [ ] Coach can score 27 skills, expand descriptors, write notes, write session summary, save.
- [ ] Save with network on → assessments appear in DB.
- [ ] Disable network in DevTools → save succeeds locally → "Saved offline" toast → re-enable network → assessments sync, banner clears.
- [ ] Refresh while offline + unsaved → draft is preserved (Dexie survives reload).

**Verify.** Manual click-through with DevTools throttle.

**Commit.** `feat(web): assessment screen with offline queue`

---

### Step 12 [BE] — Assessments POST + tier recalc + idempotency

**Goal.** `POST /assessments` (batch — accepts an array of skill scores plus optional summary) writes assessment rows, recalculates tier, returns updated profile snippet. Idempotent on `client_assessment_id` so retries from the offline queue don't duplicate.

**Reads.** `docs/12-data-model.md` § "Sessions" and § "Assessments".

**Files to create.**

```
/apps/api/src/assessments/router.py
/apps/api/src/assessments/schemas.py
/apps/api/src/assessments/service.py         (transactional batch insert + tier recalc)
/apps/api/src/skills/router.py               (GET /skills, GET /skills/:code/descriptors)
/apps/api/tests/test_assessments.py
/apps/api/tests/test_idempotency.py
```

**Implementation notes.**

- Body: `{ session_id?, athlete_id, summary?, scores: [{skill_id, level, note?, client_recorded_at, client_assessment_id}] }`. `client_assessment_id` is a UUID generated on FE — server upserts on conflict to handle retries.
- One transaction: insert/upsert all assessment rows, optionally insert/update session, recompute athlete's current tier (and write to `athletes.current_tier_id` cache column).
- Returns the recomputed profile slice (current tier, recent gains, updated radar) — FE invalidates its cache and rerenders.
- 27-skill batch must complete in <300ms p95 on dev hardware. Use `INSERT ... VALUES (...), (...), ... ON CONFLICT (client_assessment_id) DO UPDATE`.

**Done when.**

- [ ] FE save flow really persists; profile screen reflects new scores immediately on return.
- [ ] Posting the same payload twice (simulating retry) results in 1 set of rows, not 2 — idempotency proven by test.
- [ ] Tier recalc matches framework v0 — assertion test against fixture.
- [ ] `pytest test_assessments.py test_idempotency.py` green.

**Verify.**

```bash
docker compose exec api pytest tests/test_assessments.py tests/test_idempotency.py -v
# Then click-test: /assess → score 5 skills → save → back to profile → see updated radar
```

**Commit.** `feat(api): assessments batch POST with tier recalc and idempotency`

---

## Pair 7 — Reports (pulled forward — was originally Pair 9)

> **Re-sequenced in this plan:** PDF generation moved here because the PDF is the most important pitch artifact. Once Step 14 ships you have something physical to hand a club owner.

### Step 13 [FE] — Reports list + PDF preview + generate sheet

**Goal.** `/reports` lists all generated reports per `docs/08-pdf-report.md` UX. Tap a report → opens the PDF in a new tab (or inline iframe on desktop). "Generate report" button manually triggers a one-off for any trainee.

**Reads.** `docs/08-pdf-report.md`, `docs/09-empty-states.md` § "Coach · Reports".

**Files to create.**

```
/apps/web/src/features/reports/ReportsScreen.tsx
/apps/web/src/features/reports/ReportRow.tsx
/apps/web/src/features/reports/GenerateReportSheet.tsx        (trainee picker + period picker)
/apps/web/src/features/reports/reports-api.ts                 (list, generate, getStatus — mocked)
/apps/web/src/features/reports/use-report-polling.ts          (polls every 2s while status = 'pending')
```

**Implementation notes.**

- Empty state per `docs/09`: "No reports yet" + "Create report manually".
- Each row: trainee avatar + name + "Sep 2026" period + "Generated 1 Oct 2026" + view-count + chevron.
- Generation is async (BE step 14 enqueues a job). Show "Generating…" pill on the new row, optimistic insert, replace with "View PDF" when status flips to `completed`.
- Polling stops after 5 minutes with a soft error "Generation is taking longer than usual" + retry button.

**Done when.**

- [ ] List renders mocked reports.
- [ ] "Create report" sheet picks a trainee + month, calls API (still mocked — returns fake completed status after 1.5s).
- [ ] Tap row → opens a placeholder PDF (any test PDF works for now).

**Verify.** Visual click-through.

**Commit.** `feat(web): reports list, generate sheet, PDF preview`

---

### Step 14 [BE] — PDF generation (RQ + WeasyPrint) + sample PDF script

**Goal.** `POST /reports` enqueues an RQ job that generates a PDF via WeasyPrint, uploads to MinIO, persists `reports` row. `GET /reports` lists; `GET /reports/:id` returns status + signed URL when ready. A standalone CLI script `make_sample_pdf.py` produces a print-ready sample PDF you can take to in-person meetings.

> **New in this plan:** the monthly cron is *deferred* to Step 25 because at this point you don't have enough pilot data for monthly auto-generation to matter, and the cron adds complexity. The standalone sample PDF script is *added* because it's the actual demo artifact.

**Reads.** `docs/08-pdf-report.md` (full PDF layout), `docs/12-data-model.md` § "Reports".

**Files to create.**

```
/apps/api/src/reports/router.py
/apps/api/src/reports/jobs.py            (RQ-decorated generate_report_pdf function)
/apps/api/src/reports/template.py        (Jinja2 → HTML → WeasyPrint → PDF bytes)
/apps/api/templates/report.html          (the PDF layout from docs/08)
/apps/api/templates/report.css           (print stylesheet — A4, page margins, branded letterhead)
/apps/api/tests/test_reports.py
/apps/api/scripts/test_pdf_smoke.py      (generates a sample PDF locally for visual review)
/apps/api/scripts/make_sample_pdf.py     (the demo artifact — uses dev_seed_demo workspace, writes /tmp/racademy-sample-report.pdf)
```

**FE changes.** Drop mock; real list + real generate trigger. Poll for status via `use-report-polling`.

**Implementation notes.**

- Worker container (`apps/api` with `rq worker` instead of uvicorn) processes the queue.
- Template uses workspace branding (logo + accent), serif title for cover (per racademy brand guide), trainee radar SVG, recent gains, top blocking skills, full coach narrative.
- WeasyPrint reads the same CSS variables — set them inline on the root `<html>` element from workspace settings.
- `make_sample_pdf.py` is *not* an endpoint — it's a CLI for you. Runs `dev_seed_demo` if not already seeded, picks a representative trainee with rich assessment history, generates a beautiful PDF you can print at home or at a copy shop. **This is the artifact you bring to club meetings.**

**Done when.**

- [ ] `POST /reports {athlete_id, period_start, period_end}` returns 202 with job id.
- [ ] Within 5s, status flips to `completed`; PDF appears in MinIO; `reports` row populated.
- [ ] Opening the PDF shows correct branding, real radar, real coach narrative.
- [ ] `docker compose exec api python -m scripts.make_sample_pdf` writes `/tmp/racademy-sample-report.pdf` that prints cleanly on A4.

**Verify.**

```bash
docker compose exec api python -m scripts.make_sample_pdf
docker cp racademy_api:/tmp/racademy-sample-report.pdf ./sample.pdf
open sample.pdf
```

**Commit.** `feat(api): PDF report generation with WeasyPrint + sample CLI`

---

# 🚦 Demo-ready checkpoint

After Step 14 you can credibly show racademy to a coach or club owner. End-to-end loop works: sign in → workspace → invite coach → add trainee → schedule session → assess → see profile → generate PDF.

Before reaching out to *any* prospect, complete **Step 15** (demo seed) so they can poke around without seeing an empty app. Items 16–19 can land in any order and partially overlap with Phase 3 work.

---

# Phase 2 — Pilot enablers (Steps 15–19)

Five steps focused on making the pilot conversation work — not new product features, but founder/sales/onboarding scaffolding.

---

## Step 15 — Demo workspace seed (production-ready)

**Goal.** A pristine "Demo Club" workspace prospects can play with. Login via a magic invite link, no signup friction. Re-seeded nightly to a known state.

**Files to create.**

```
/apps/api/scripts/seed_demo_workspace.py     (production-grade — distinct from dev_seed_demo.py)
/apps/api/scripts/reset_demo_workspace.py    (truncates demo workspace + re-runs seed)
/apps/api/src/jobs/demo_reset.py             (RQ-scheduled: runs reset at 03:00 UTC daily)
/infra/scripts/grant_demo_access.sh          (CLI you run: takes an email, mints a 30-day membership in the demo workspace, prints the magic link)
```

**Implementation notes.**

- Demo workspace data: 1 club admin (`demo-admin@racademy.id`), 3 coaches, 12 trainees (mix of beginner / intermediate / advanced tiers), 60 days of assessment history, 8 sessions scheduled this week, 4 generated PDF reports in the Reports tab.
- Trainee names should be realistic Indonesian names — Andi, Sari, Budi, etc. (random sampling from a small fixed list — same names every reset for stability).
- All data tagged with `is_demo = TRUE` on each row's metadata JSON. Demo workspace `id` is hardcoded; `slug = 'demo-club'`.
- Nightly reset runs in worker via rq-scheduler. Truncates demo workspace's data + re-runs seed.
- `grant_demo_access.sh prospect@example.com` creates a membership row, mints a magic link valid for 30 days, prints to stdout. You paste into WhatsApp / email to the prospect.

**Done when.**

- [ ] `docker compose exec api python -m scripts.seed_demo_workspace` creates a workspace named "Demo Club" with the data above.
- [ ] After the seed, logging in as `demo-admin@racademy.id` shows a populated `/today`, `/trainees`, and `/reports`.
- [ ] `bash infra/scripts/grant_demo_access.sh test@example.com` prints a magic link that lands on `/today` for the demo workspace.
- [ ] Reset script run twice produces identical state (idempotent).

**Verify.**

```bash
docker compose exec api python -m scripts.seed_demo_workspace
bash infra/scripts/grant_demo_access.sh you+demo@example.com
# Open the printed link → land on /today as demo-admin
```

**Commit.** `feat(api): seedable demo workspace + grant-access CLI`

---

## Step 16 — In-app coach tour (first-time UX)

**Goal.** First-time coaches get a 5-step overlay walk-through: "Tap +", "Pick a trainee", "Score a skill", "Save", "See the profile". Dismissable, never auto-shown again.

**Files to create.**

```
/apps/web/package.json                                  (add shepherd.js or driver.js)
/apps/web/src/features/onboarding/CoachTour.tsx         (5-step tour, attached to actual DOM nodes)
/apps/web/src/features/onboarding/tour-steps.ts         (step definitions: target selector, title, body, action)
/apps/web/src/features/onboarding/use-tour-state.ts     (Dexie-backed: { dismissed_at, completed_at })
/apps/web/src/features/onboarding/TourReplayButton.tsx  (lives in Settings → "Replay welcome tour")
```

**Implementation notes.**

- Library: `shepherd.js` (smaller, more iOS-friendly than `driver.js`). Style overrides to match design system — hairline borders, no shadows, sentence case.
- Trigger: on first `/today` load *after* a fresh sign-up, if `tour_state.dismissed_at` and `tour_state.completed_at` are both null.
- Steps target real DOM selectors — `data-tour="add-trainee-fab"`, `data-tour="trainee-row-first"`, etc. Add these attributes back to the components built in earlier steps.
- "Skip tour" button on every step. Dismissal persists across reloads via Dexie.
- Settings → "Replay welcome tour" resets state so coach can run it again.

**Done when.**

- [ ] Fresh sign-up → land on `/today` (empty) → tour overlay appears on the FAB.
- [ ] Following the tour completes all 5 steps, ending on a populated trainee profile.
- [ ] Skip → tour never reappears.
- [ ] "Replay welcome tour" in Settings re-triggers it.

**Verify.** Manual: sign up fresh, walk through tour. Sign up another fresh user, skip tour, confirm it doesn't reappear after reload.

**Commit.** `feat(web): first-time coach tour with shepherd.js`

---

## Step 17 — Founder admin tool (`/_admin`)

**Goal.** A bare-bones internal page only you can access. Manually provision workspaces, extend trials, browse usage. Auth: hardcoded allow-list of emails in env var.

**Files to create.**

```
/apps/api/src/admin/router.py                  (mounted at /_admin/api/*)
/apps/api/src/admin/auth.py                    (ADMIN_EMAILS env var allow-list)
/apps/api/src/admin/queries.py                 (workspaces overview, recent signups, last-7-days activity)
/apps/web/src/features/admin/AdminShell.tsx    (separate from CoachShell — sidebar nav, denser tables)
/apps/web/src/features/admin/WorkspacesTable.tsx
/apps/web/src/features/admin/WorkspaceDetailDrawer.tsx   (extend trial, suspend, view audit log)
/apps/web/src/features/admin/SignupsTable.tsx
/apps/web/src/features/admin/UsageTable.tsx              (last_sign_in_at per workspace, assessment count, report count)
/apps/web/src/features/admin/admin-api.ts
```

**Implementation notes.**

- Route guard: protected by both standard auth *and* an additional admin check (`current_user.email IN ADMIN_EMAILS`). Otherwise 404 (not 403 — don't reveal it exists).
- Actions available: create workspace (skips wizard), extend trial by N days, suspend workspace, view audit log entries, view raw signup list.
- "Extend trial" sets `trial_ends_at = trial_ends_at + interval` and writes an audit row.
- No fancy charts — plain tables sorted by signup date / last-active date. SQL straight from the DB.
- Don't bother with E2E tests for admin — it's internal-only.

**Done when.**

- [ ] Logging in as `nirenda@alterra.id` → `/_admin` loads.
- [ ] Logging in as any other email → `/_admin` returns 404.
- [ ] WorkspacesTable shows all workspaces with type, plan, trial status, last_active.
- [ ] "Extend trial 30 days" button updates `trial_ends_at` and the new value appears immediately.
- [ ] UsageTable shows assessment count per workspace last 7 days.

**Verify.** Manual: log in, browse, extend a trial, confirm change in psql.

**Commit.** `feat(web,api): founder admin tool at /_admin`

---

## Step 18 — In-app feedback widget

**Goal.** Floating "💬 Beri masukan" button bottom-right on every authed coach screen. Tap → small form (category + text) → submits to `POST /feedback` → forwarded to Slack/email.

**Files to create.**

```
/apps/web/src/features/feedback/FeedbackWidget.tsx       (floating button + sheet)
/apps/web/src/features/feedback/feedback-api.ts
/apps/web/src/features/feedback/categories.ts            ('Bug', 'Saran fitur', 'Pertanyaan', 'Lainnya')
/apps/api/src/feedback/router.py                         (POST /feedback)
/apps/api/src/feedback/sink.py                           (forwards to Slack webhook or SMTP)
/apps/api/alembic/versions/0009_feedback_log.py          (table feedback_log)
```

**Implementation notes.**

- The "💬" emoji is the *one* explicit exception to the no-emoji rule, because it's universally understood as "talk to us." Document this exception in the component file header.
- Form fields: category (4-option segmented), free-text (200 char min, 2000 max), screenshot upload (optional, presigned to same MinIO bucket as logos).
- On submit: persist to `feedback_log` table + forward via `SLACK_WEBHOOK_URL` if set, else email to `FEEDBACK_EMAIL_TO`.
- Include workspace_id, user_id, current_route, user_agent in the payload.
- Show "Terima kasih, kami baca semua masukan" toast on success.

**Done when.**

- [ ] Floating button visible on `/today`, `/trainees`, `/assess`, every authed coach route.
- [ ] Tap → sheet → submit → `feedback_log` row created.
- [ ] Slack webhook receives the message (or email if no Slack configured).
- [ ] Screenshot upload works (optional field).

**Verify.**

```bash
# Set SLACK_WEBHOOK_URL in .env, restart api
# In app: open feedback, submit "Test from pilot", confirm Slack post + DB row
docker compose exec postgres psql -U racademy -d racademy -c "SELECT * FROM feedback_log ORDER BY created_at DESC LIMIT 5;"
```

**Commit.** `feat(web,api): in-app feedback widget`

---

## Step 19 — Trial expiration UX + extend flow

**Goal.** Coaches see a banner from day 23 onward ("Trial habis dalam 7 hari, hubungi kami"). On day 31, the workspace is suspended — coach can still log in and view, but write actions are blocked with a clear "Trial expired, contact us to continue" modal. WA deep link to your number for re-activation.

**Files to create.**

```
/apps/web/src/features/billing/TrialBanner.tsx                 (top banner, day 23+)
/apps/web/src/features/billing/TrialExpiredModal.tsx           (write-action gate)
/apps/web/src/features/billing/use-trial-status.ts             (derived from workspace.trial_ends_at)
/apps/web/src/features/billing/contact-us.ts                   (buildWhatsAppUrl with your sales number)
/apps/api/src/workspaces/trial.py                              (helper: is_active(), days_until_expiry())
/apps/api/src/middleware/trial_gate.py                         (rejects write requests with 402 when expired)
/apps/api/tests/test_trial_gate.py
```

**Implementation notes.**

- Banner copy in `id.json`: "Trial Anda berakhir dalam {n} hari. Hubungi kami untuk lanjut."
- Day 31 — workspace `plan` still `free_trial`, `trial_ends_at < NOW()`. Middleware allows GET, blocks POST/PATCH/DELETE with HTTP 402 + structured body.
- FE catches 402 globally → shows `TrialExpiredModal` with two buttons: "Hubungi sales (WhatsApp)" → opens `wa.me/${SALES_PHONE}?text=...` with a template, and "Tutup".
- Founder admin tool (Step 17) lets you extend trials. Activate paid: just bump `plan` to `club_starter` / `club_pro` / `solo_coach` and clear `trial_ends_at`.
- Tests: write request fails after expiry; read still works; admin-extended trial restores write access.

**Done when.**

- [ ] Set `trial_ends_at = NOW() - INTERVAL '1 day'` for a workspace → banner becomes red "expired" → any write attempt → modal.
- [ ] Set `trial_ends_at = NOW() + INTERVAL '5 days'` → banner shows "5 days remaining" amber color.
- [ ] Admin-extend → banner clears.
- [ ] `pytest test_trial_gate.py` green.

**Verify.**

```bash
docker compose exec postgres psql -U racademy -d racademy -c \
  "UPDATE workspaces SET trial_ends_at = NOW() - INTERVAL '1 day' WHERE slug = 'demo-club';"
# Log in to demo-club, try to add a trainee → modal appears
```

**Commit.** `feat(web,api): trial expiration banner and write-gate`

---

# 🎯 Pilot-launch checkpoint

After Step 19 you're ready for formal pilot outreach. You have:
- Polished sample PDF you can print and hand over
- Demo workspace prospects can poke without signing up
- In-app tour so coaches who do sign up don't get lost
- Admin tool to provision their workspace manually
- Feedback widget so they tell you what's broken
- Trial UX so conversations about "ok we want to keep going" have a clear next step

Phases 3 and 4 can land in parallel with active pilot conversations.

---

# Phase 3 — Trainee side + settings + polish (Steps 20–25)

The trainee experience, workspace settings, and i18n/PWA polish. None of these block pilot launch — coaches don't *need* their trainees on the app to assess them — but Phase 3 unlocks the parent-facing WOW factor and the self-serve settings flow.

---

## Pair 8 — Trainee experience

### Step 20 [FE] — Trainee home + welcome screen + public landing

**Goal.** Build the trainee's side of the app. Welcome / sign-in via invite token. First-run home (empty radar + 3-step explainer). Standard home (achievement card, tier progress, upcoming session, coach note) per `docs/05-trainee-home.md`. Public web landing for non-installed taps.

**Reads.** `docs/05-trainee-home.md`, `docs/07-invite-and-onboarding.md` Steps 4a, 4b, 5.

**Files to create.**

```
/apps/web/src/features/trainee-home/TraineeHomeScreen.tsx
/apps/web/src/features/trainee-home/AchievementCard.tsx          (forest/terracotta serif title — branded moment)
/apps/web/src/features/trainee-home/TierProgressCard.tsx          (trainee variant — encouraging tone)
/apps/web/src/features/trainee-home/UpcomingSession.tsx
/apps/web/src/features/trainee-home/CoachNoteCard.tsx             (oversized opening quote, serif italic)
/apps/web/src/features/trainee-home/FirstRunHome.tsx
/apps/web/src/features/onboarding/InviteWelcomeScreen.tsx         (in-app, post-tap, pre-signin)
/apps/web/src/features/onboarding/PublicLandingPage.tsx           (browser-rendered public route /i/:token)
/apps/web/src/features/onboarding/use-invite-token.ts
/apps/web/src/layouts/TraineeShell.tsx                            (5-tab nav: Home / Progress / Sessions / Coach / Profile)
```

**Implementation notes.**

- Role-based shell selection: after sign-in, server returns the user's roles. If primary role is `trainee`, mount `TraineeShell`; else `CoachShell`.
- Public landing is a *public* route — no auth required. Reads workspace branding from a public endpoint (added next step). OS detection via `navigator.userAgent` for the install CTA.
- First-run home shows the 3-step explainer; converts to standard home automatically once at least one assessment exists.
- Trainee-facing tone per `docs/01-design-principles.md` — encouraging, never shaming. "8 skills to Silver — closer than ever."

**Done when.**

- [ ] A trainee user (created via invite claim) lands on `/home` showing first-run layout.
- [ ] After a coach assesses them (in another window), refreshing shows the standard home with achievement card.
- [ ] Public landing at `/i/:token` renders with workspace branding and OS-aware CTA.

**Verify.** End-to-end click-through with two browser windows (coach + trainee).

**Commit.** `feat(web): trainee home, welcome, public landing`

---

### Step 21 [BE] — Invite claim + trainee-scoped reads + public branding

**Goal.** `POST /invites/:token/claim` (after auth) creates the membership and links the trainee user to the existing athlete row. `GET /trainees/me/home` returns the trainee's own home payload. `GET /workspaces/public/:slug` returns minimal branding for the public landing.

**Reads.** `docs/12-data-model.md` § "Invites" and § "Workspace memberships".

**Files to create.**

```
/apps/api/src/invites/claim.py
/apps/api/src/athletes/me.py                  (GET /trainees/me/home — self-scoped read)
/apps/api/src/workspaces/public.py            (GET /workspaces/public/:slug — name, brand_color, logo_url, sport)
/apps/api/tests/test_invite_claim.py
/apps/api/tests/test_trainee_scope.py
/apps/api/alembic/versions/0010_trainee_self_read_policy.py    (RLS policy: trainee role can read own row)
```

**Implementation notes.**

- Claim flow: validate token (not expired, not consumed) → require auth → if email mismatch with `users.email`, allow → mark consumed → create membership with role `trainee` → link `athletes.user_id` to the authenticated user → mint a new JWT with `wsid` set to the workspace.
- Trainee-scoped reads: a separate RLS policy lets a user with role `trainee` see only their own athlete row + their own assessments + their own sessions. Add this policy in the new migration.
- Public branding endpoint is *unauthenticated*; cache `Cache-Control: public, max-age=300`. Strict shape, no PII.

**Done when.**

- [ ] Trainee taps invite → signs in → claim succeeds → lands on first-run home.
- [ ] Re-tapping the same invite token returns 410 (consumed).
- [ ] A trainee querying `/trainees/me/home` sees their own data; another trainee gets 0 rows for the first one — RLS verified.
- [ ] `pytest test_invite_claim.py test_trainee_scope.py` green.

**Verify.**

```bash
docker compose exec api pytest tests/test_invite_claim.py tests/test_trainee_scope.py -v
# Browser: copy invite URL → paste in incognito → sign in fresh → trainee home appears
```

**Commit.** `feat(api): invite claim, trainee self-read, public branding`

---

## Pair 9 — Workspace settings

### Step 22 [FE] — Workspace settings screen

**Goal.** `/settings` matching the screenshots in `docs/06-workspace-settings.md`: live preview card, branding section (name, accent, logo), tiers & curriculum (tier naming Game/Skill/Custom, default curriculum, allow coach overrides), plan & billing card. Personal vs Club variants.

**Reads.** `docs/06-workspace-settings.md`, `docs/14-brand-identity.md` (for racademy variant).

**Files to create.**

```
/apps/web/src/features/settings/WorkspaceSettingsScreen.tsx
/apps/web/src/features/settings/LivePreviewCard.tsx
/apps/web/src/features/settings/BrandingSection.tsx
/apps/web/src/features/settings/TiersCurriculumSection.tsx
/apps/web/src/features/settings/PlanBillingCard.tsx
/apps/web/src/features/settings/LogoUploader.tsx
/apps/web/src/features/settings/settings-api.ts          (PATCH /workspaces/me, presigned uploads — mocked)
/apps/web/src/components/InlineSavedToast.tsx
```

**Implementation notes.**

- Auto-save on blur, with "Saved ✓" indicator that fades after 5s (per offline/sync rules).
- Live preview re-renders instantly on every change; debounce only the network PATCH.
- Logo upload flow: pick file → request presigned URL from `/uploads/logo/sign` → PUT to S3/MinIO directly → PATCH workspace with the returned URL.
- Personal variant hides the Members section (already gated since Step 3), uses "Display name" instead of "Club name", "Profile photo" instead of "Club logo".

**Done when.**

- [ ] Changing the name updates the live preview as you type.
- [ ] Changing accent color updates the preview's `--accent` CSS var inline.
- [ ] Logo upload UI (still mocked) shows progress and renders the new logo.
- [ ] Tier naming radio (Game / Skill / Custom) updates the preview's tier pills.

**Verify.** Visual click-through, screenshot diff against `docs/06`.

**Commit.** `feat(web): workspace settings screen`

---

### Step 23 [BE] — Settings PATCH + presigned logo upload

**Goal.** `PATCH /workspaces/me` for branding/curriculum/tier-style. `POST /uploads/logo/sign` returns a presigned PUT URL for direct S3/MinIO upload. Validate file types and sizes server-side. Audit-log every change.

**Reads.** `docs/12-data-model.md` § "Audit log", `docs/06-workspace-settings.md`.

**Files to create.**

```
/apps/api/src/workspaces/settings.py        (PATCH handler with field-level audit)
/apps/api/src/uploads/router.py             (presign for logo + report assets later)
/apps/api/src/uploads/s3.py                 (boto3 / aiobotocore wrapper)
/apps/api/src/audit/service.py              (write_audit_log helper)
/apps/api/tests/test_settings.py
/apps/api/tests/test_uploads.py
```

**FE changes.** Drop the mock; real PATCH + real presigned upload to MinIO.

**Implementation notes.**

- Presign returns `{url, fields, expires_at, public_url}`. Bucket policy makes uploaded objects public-read (logos and report PDFs are not sensitive — they're shared with parents anyway).
- Validate `Content-Type` (image/png, image/jpeg, image/webp), max 2MB. Server fetches the head after upload to confirm size + type before persisting `logo_url`.
- Every PATCH writes an audit row: `action = 'workspace.updated'`, `metadata = {changed_fields: ['name', 'brand_color']}`.
- Authorization: only `club_admin` (club workspaces) or owner (personal) can modify settings.

**Done when.**

- [ ] FE settings auto-save persists in DB.
- [ ] Logo upload to MinIO works; `public_url` is reachable in browser.
- [ ] Audit table grows on every change; query `SELECT * FROM audit_log WHERE action = 'workspace.updated'` shows entries.
- [ ] A coach (not admin) gets 403 on PATCH.

**Verify.**

```bash
docker compose exec api pytest tests/test_settings.py tests/test_uploads.py -v
# Browser: /settings → change name → reload → name persists
```

**Commit.** `feat(api): workspace settings PATCH + presigned uploads`

---

## Pair 10 — i18n, offline, PWA + monthly cron

### Step 24 [FE] — i18n EN/ID, offline banner, empty/error states polish, PWA

**Goal.** Every user-facing string runs through `i18next`. Locale switcher in profile. Offline banner always visible when offline. All error and empty states match `docs/09` and `docs/10`. PWA installable.

**Reads.** `docs/11-localization-rules.md`, `docs/09-empty-states.md`, `docs/10-error-offline-states.md`.

**Files to create.**

```
/apps/web/src/i18n/index.ts
/apps/web/src/i18n/en.json
/apps/web/src/i18n/id.json
/apps/web/src/features/profile/LocalePicker.tsx
/apps/web/src/components/EmptyState.tsx                (canonical pattern from docs/09)
/apps/web/src/components/ErrorBoundary.tsx
/apps/web/src/components/SyncIndicator.tsx             (auto-clears at 5s)
/apps/web/public/manifest.webmanifest                  (PWA manifest)
/apps/web/src/sw.ts                                    (service worker via vite-plugin-pwa)
```

**Implementation notes.**

- Audit every string: any literal `"..."` in JSX is a smell. Use `t('namespace.key')`.
- Skill names *don't* translate — they stay in the original (Spanish/English padel vocab) per `docs/11`.
- Tier names *do* translate — Bronze ↔ Perunggu, Silver ↔ Perak, Gold ↔ Emas, etc.
- PWA: register service worker, precache shell, add install prompt detection. Test by visiting on Android Chrome → "Add to home screen".

**Done when.**

- [ ] Locale switcher flips the entire UI.
- [ ] Disable network → banner appears within 1s; re-enable → banner clears within 1s.
- [ ] All empty states match the docs.
- [ ] Lighthouse PWA score ≥ 90.

**Verify.**

```bash
pnpm --filter @racademy/web build && pnpm --filter @racademy/web preview
# Open in Chrome, run Lighthouse PWA audit
```

**Commit.** `feat(web): i18n EN/ID, offline banner, PWA install`

---

### Step 25 [BE] — Monthly auto-PDF cron

**Goal.** A daily worker cron auto-generates monthly reports on the 1st for every trainee with assessments in the prior month. Was originally bundled with Step 14; deferred here because it only matters once pilot workspaces have a month of data.

**Reads.** `docs/08-pdf-report.md`, `docs/12-data-model.md` § "Reports".

**Files to create.**

```
/apps/api/src/reports/cron.py            (rq-scheduler cron: monthly auto-generation at 03:00 UTC on 1st)
/apps/api/scripts/run_monthly_cron.py    (manual trigger for testing — supports --dry)
/apps/api/tests/test_reports_cron.py
```

**Implementation notes.**

- Cron at 03:00 UTC on the 1st of each month: enumerates active trainees with assessments in the prior calendar month, enqueues one `generate_report_pdf` job per trainee.
- Skip trainees with zero assessments in the period (no point generating an empty report).
- Tag auto-generated reports with `source = 'monthly_auto'` in metadata so admin can filter.

**Done when.**

- [ ] `docker compose exec api python -m scripts.run_monthly_cron --dry` lists what *would* be generated for a given period.
- [ ] `--apply` actually enqueues jobs; reports appear in Reports tab within minutes.
- [ ] `pytest test_reports_cron.py` covers: skips empty trainees, processes active ones, idempotent if re-run for the same period.

**Verify.**

```bash
docker compose exec api python -m scripts.run_monthly_cron --period 2026-04 --dry
docker compose exec api python -m scripts.run_monthly_cron --period 2026-04 --apply
```

**Commit.** `feat(api): monthly auto-PDF cron`

---

# Phase 4 — Production hardening (Step 26)

## Step 26 — Audit log everywhere, Sentry, healthchecks, deploy script

**Goal.** Every state-changing API writes to `audit_log`. Sentry SDK initialized on api + worker. `/healthz` includes DB + Redis + S3 + SMTP pings. Deploy script (`infra/deploy.sh`) builds, pushes images, runs migrations, swaps containers.

**Reads.** `docs/12-data-model.md` § "Audit log", `CLAUDE.md` § "Conventions — DO".

**Files to create.**

```
/apps/api/src/audit/decorators.py       (@audit_action decorator for routes)
/apps/api/src/observability/sentry.py
/apps/api/src/observability/health.py    (DB, Redis, MinIO, SMTP probes)
/apps/api/src/middleware/request_id.py   (sets X-Request-Id; structlog binds)
/infra/deploy.sh                         (idempotent: build, push, migrate, restart)
/infra/docker-compose.prod.yml           (overrides: nginx, no bind mounts, real env)
/apps/api/tests/test_health.py
/apps/api/tests/test_audit.py
```

**Implementation notes.**

- Audit decorator wraps handlers, captures `(user_id, workspace_id, action, entity_type, entity_id, metadata)`. Falls back gracefully on read-only routes (no audit row).
- Sentry: separate DSNs for api + worker; tags include `workspace_id` and `user_id` (after auth).
- `/healthz`: returns `{db: ok, redis: ok, s3: ok, smtp: ok}` with HTTP 200; if any subsystem fails, return HTTP 503 with the failure detail.
- Deploy script: `set -euo pipefail`. Pre-flight: confirm `git status` clean, tag the release, push to registry, ssh to host, pull + `alembic upgrade head` + `docker compose up -d --no-deps --build api worker web`.

**Done when.**

- [ ] Every PATCH/POST route writes an audit row; verified by integration test.
- [ ] `curl /healthz` returns 200 normally, 503 when redis is stopped.
- [ ] Sentry receives a test event from a deliberately-failing endpoint.
- [ ] `bash infra/deploy.sh --dry` prints the planned actions without executing.

**Verify.**

```bash
docker compose exec api pytest tests/test_health.py tests/test_audit.py -v
docker compose stop redis
curl -s -o /dev/null -w "%{http_code}\n" localhost:8000/healthz   # 503
docker compose start redis
```

**Commit.** `feat(api,infra): audit log, sentry, healthchecks, deploy script`

---

# After step 26 — Pilot launch checklist

The MVP is functionally complete and deployable. Before the first formal pilot signup:

- [ ] Production deploy on Hetzner / Railway / Render — single VPS is fine for first 10 clubs.
- [ ] Domain configured (e.g. `app.racademy.id` for app, `racademy.id` for the 1-pager landing).
- [ ] Cloudflare R2 swapped in for MinIO (env vars; same S3 API).
- [ ] Resend swapped in for Mailpit (env vars; same SMTP).
- [ ] Sentry project created, DSNs wired in.
- [ ] Sample PDF printed glossy A4, in a folder you carry to meetings.
- [ ] Demo workspace seeded in production, magic-link generator script working.
- [ ] Privacy policy + Terms of Service published (legal/copywriter — out of scope here).
- [ ] First 5 prospect emails drafted, magic-link grants pre-prepared.

Backlog from `CLAUDE.md` § "Out of MVP" — only after 30 days of pilot data tells you which one matters most. Likely first additions: CSV import (if coaches keep asking), Stripe/Xendit payments (when invoice volume becomes painful), trainee-facing notifications (if engagement drops after week 2).

Tennis activation lives in a single migration: `UPDATE sports SET is_active = TRUE WHERE code = 'tennis'`. The architecture is ready; the skill ontology is the work.

---

## Quick reference — Cursor Composer prompt template

For any step, paste this into Composer (Cmd+I → Agent mode):

> Read `@docs/CLAUDE.md` and the docs listed under **Reads** for this step (attach them with `@docs/0X-...md`). Then implement step `<N>` from `@docs/15-build-plan.md` exactly as written. Honor every convention in `CLAUDE.md`. Stop after the **Done when** checklist is green and the **Verify** block passes; do not advance to the next step. Suggest a conventional-commit message at the end.

Replace `<N>` with the step number. Don't paste multiple steps into one session — fresh Composer per step keeps context clean.
