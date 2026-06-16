---
name: PadelCoach monorepo stack
description: Stack, tooling, and scaffold state for the racademy/PadelCoach project
type: project
---

pnpm workspace monorepo (apps/web, apps/api, packages/types).

**Why:** Multi-tenant padel coaching SaaS, MVP web-first PWA, Indonesia market.

**Frontend (apps/web):** Vite 5 + React 18 + TypeScript strict, Tailwind CSS 3 with CSS-variable theming (--accent #378ADD), vite-plugin-pwa scaffolded but disabled until step 19.

**Backend (apps/api):** FastAPI + SQLAlchemy 2 async + Alembic, Python 3.12, managed with uv.

**Tooling:** Turborepo for orchestration, ESLint 8 (@typescript-eslint + react-hooks + tailwindcss), Prettier + @trivago/prettier-plugin-sort-imports, mypy strict + ruff.

**Key quirk (eslint-plugin-tailwindcss):** tailwindcss must be declared in ROOT devDependencies (package.json) even though it's also in apps/web devDeps. The ESLint plugin's tailwind-api-utils resolves tailwindcss at runtime via mlly; if not at root, it fails. Also: do NOT set `settings.tailwindcss.config` to a relative path string — let the plugin auto-discover via resolveDefaultConfigPath() which returns an absolute path.

**Step 0.1 complete.** All checks pass: pnpm install, web build produces dist/, typecheck green, lint green, uv sync + uvicorn src.main:app → GET /healthz → {"status":"ok"}.

**Step 0.2 complete.** Docker Compose at infra/docker-compose.yml. All services healthy.

**Port map (host-side — internal Docker network always uses standard ports):**
- API: 8002 → 8000 (8000/8001 taken by other projects)
- Web: 5174 → 5173 (5173 taken by mocfin-frontend-1)
- Postgres: 5433 → 5432 (5432 taken by mocfin-db-1)
- Redis: 6380 → 6379 (6379 taken by tanarasa-redis)
- MinIO API: 9000, Console: 9001 (free)
- Mailpit UI: 8025, SMTP: 1025 (free)
- Adminer (--profile tools): 8082 → 8080

**Key quirk (Docker volumes):** API .venv lives inside the image at /app/apps/api/.venv; only src/, alembic/, tests/, scripts/, data/ are bind-mounted. This avoids cross-platform Python wheel conflicts. Web node_modules also stay in the image; only src/ and index.html are bind-mounted for hot reload.

**Step 0.3 complete.** Migrations 0001–0008 + RLS + seed. 27 padel skills, 135 descriptors, 7 tiers, 115 requirements, 13 pg_policies. Idempotent.

**Two-role DB setup (critical for RLS):**
- `racademy` is the POSTGRES_USER and a Postgres superuser — used for migrations via ALEMBIC_DATABASE_URL. Superusers bypass RLS even with FORCE ROW LEVEL SECURITY.
- `racademy_api` is a non-superuser role (created in `infra/postgres/init/02-app-user.sql`) — used by the API runtime via DATABASE_URL. RLS policies apply.
- Verified: as racademy_api with no `app.current_workspace_id` → 0 rows; with wrong workspace → 0; with correct → 1.

**Schema quirks:**
- `audit_log` column is named `metadata` in SQL but mapped as `meta` in SQLAlchemy (the attribute name `metadata` is reserved on DeclarativeBase).
- UUID PK default uses a `uuid_generate_v7()` SQL function that shims to `gen_random_uuid()` since postgres:16-alpine lacks pg_uuidv7. Swap to real pg_uuidv7 on managed Postgres if available.
- Standard `UNIQUE (col, workspace_id, code)` treats NULLs as distinct, breaking idempotent seeds. Migration 0008 adds `uq_*_platform_*` partial unique indexes `WHERE workspace_id IS NULL`. Seed uses these as conflict targets.
- GIN indexes cannot include UUID columns without an operator class — use separate B-tree index for workspace_id, GIN trgm index only for the text column (athletes.display_name).

**Set workspace context** via `src.db.rls.set_workspace_context(session, workspace_id)` which executes `SELECT set_config('app.current_workspace_id', :wid, TRUE)`. The TRUE flag makes it LOCAL to the transaction — every request handler needs a fresh transaction.

**How to apply:** Reference when adding new packages, lint rules, API routes, or migrations. When port conflicts arise, check the port map above first.
