# Docker Setup — Local Development

> Everything in Docker. Zero native installs except Node (for editor tooling) and Docker itself.

## Prerequisites

- **Docker Desktop** (Mac/Win) or **Docker Engine + Compose** (Linux), v24+
- **Node 20+** with pnpm — only for editor IntelliSense; not strictly required to run
- **8 GB RAM** allocated to Docker (Settings → Resources → 8 GB+)
- **Cursor / VSCode** with extensions for TypeScript, Python, Tailwind

That's it. No Postgres, Redis, Python, or anything else on host.

## First-time setup

```bash
# 1. Clone repo
git clone https://github.com/yourorg/padelcoach.git
cd padelcoach

# 2. Copy env file and customize if needed
cp .env.example .env
# Edit .env — at minimum set GOOGLE_CLIENT_ID if testing Google Sign-In

# 3. Install Node deps (for editor tooling, not runtime)
pnpm install

# 4. Build and start everything
docker compose -f infra/docker-compose.yml up -d

# 5. Run migrations
docker compose -f infra/docker-compose.yml exec api alembic upgrade head

# 6. Seed default data (sports, skills, tiers, descriptors)
docker compose -f infra/docker-compose.yml exec api python -m scripts.seed

# 7. Verify everything is up
open http://localhost:5173    # Web app
open http://localhost:8000/docs    # API Swagger
open http://localhost:8025    # Mailpit (catch dev emails)
open http://localhost:9001    # MinIO console (S3 dev)
```

## Service map

| Service | URL | Purpose |
|---------|-----|---------|
| **web** | http://localhost:5173 | Vite dev server (hot reload) |
| **api** | http://localhost:8000 | FastAPI + auto-reload |
| **api docs** | http://localhost:8000/docs | Swagger UI |
| **postgres** | localhost:5432 | DB (user: padelcoach, pass: padelcoach, db: padelcoach) |
| **redis** | localhost:6379 | Cache + RQ queue |
| **mailpit** | http://localhost:8025 | Captures all dev SMTP — open this to read magic links |
| **minio** | http://localhost:9000 (API), http://localhost:9001 (console) | S3-compatible local storage |
| **adminer** (optional) | http://localhost:8080 | DB GUI — start with `--profile tools` |

## Common operations

### Watching logs

```bash
# All services
docker compose -f infra/docker-compose.yml logs -f

# Specific service
docker compose -f infra/docker-compose.yml logs -f api
docker compose -f infra/docker-compose.yml logs -f web
docker compose -f infra/docker-compose.yml logs -f worker
```

### Running API commands

```bash
# Migrations
docker compose -f infra/docker-compose.yml exec api alembic upgrade head
docker compose -f infra/docker-compose.yml exec api alembic revision --autogenerate -m "add_x_table"
docker compose -f infra/docker-compose.yml exec api alembic downgrade -1

# Tests
docker compose -f infra/docker-compose.yml exec api pytest
docker compose -f infra/docker-compose.yml exec api pytest tests/test_auth.py -v
docker compose -f infra/docker-compose.yml exec api pytest --cov=src --cov-report=term-missing

# Lint
docker compose -f infra/docker-compose.yml exec api ruff check src
docker compose -f infra/docker-compose.yml exec api mypy src

# Python REPL with app context
docker compose -f infra/docker-compose.yml exec api python -m IPython

# Seed
docker compose -f infra/docker-compose.yml exec api python -m scripts.seed

# Shell
docker compose -f infra/docker-compose.yml exec api bash
```

### Running web commands

```bash
# Dev server is already running in container with hot reload
# For one-off commands:

docker compose -f infra/docker-compose.yml exec web pnpm typecheck
docker compose -f infra/docker-compose.yml exec web pnpm lint
docker compose -f infra/docker-compose.yml exec web pnpm test
docker compose -f infra/docker-compose.yml exec web pnpm build

# Add a dependency
docker compose -f infra/docker-compose.yml exec web pnpm add <package>
docker compose -f infra/docker-compose.yml exec web pnpm add -D <package>
```

### Database access

```bash
# psql shell
docker compose -f infra/docker-compose.yml exec postgres psql -U padelcoach

# Run a query
docker compose -f infra/docker-compose.yml exec postgres psql -U padelcoach -c "SELECT * FROM workspaces"

# Backup
docker compose -f infra/docker-compose.yml exec postgres pg_dump -U padelcoach padelcoach > backup.sql

# Restore
docker compose -f infra/docker-compose.yml exec -T postgres psql -U padelcoach < backup.sql

# Reset (destructive!)
docker compose -f infra/docker-compose.yml down -v
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml exec api alembic upgrade head
docker compose -f infra/docker-compose.yml exec api python -m scripts.seed
```

### Working with MinIO (local S3)

```bash
# Bucket auto-created by minio_init container on first start: padelcoach-dev
# Console login: minioadmin / minioadmin
open http://localhost:9001

# CLI
docker compose -f infra/docker-compose.yml exec minio mc ls local/padelcoach-dev/
```

When deploying to production, point S3_* env vars to Cloudflare R2 instead. Same code path.

### Working with Mailpit (catch dev emails)

Magic link emails, invites, report notifications all go to Mailpit at localhost:8025. Click the email, click the link, you're in. No real SMTP sending in dev.

## Optional: Adminer (DB GUI)

```bash
# Start with tools profile
docker compose -f infra/docker-compose.yml --profile tools up -d

open http://localhost:8080
# System: PostgreSQL
# Server: postgres
# Username: padelcoach
# Password: padelcoach
# Database: padelcoach
```

## Troubleshooting

### "port already in use"

Some service on host is using a port. Find and kill, or change port in docker-compose.yml.

```bash
# Mac/Linux
lsof -i :5432    # find what's using port
kill -9 <PID>

# Win
netstat -ano | findstr :5432
taskkill /PID <pid> /F
```

### Web dev server slow / hot reload broken

Volume mounts on Mac/Win can be slow. Try:

```bash
# Restart web container only
docker compose -f infra/docker-compose.yml restart web

# Or force re-install deps in container
docker compose -f infra/docker-compose.yml exec web pnpm install
```

If still slow on Mac, enable VirtioFS in Docker Desktop (Settings → General → Use Virtualization framework + VirtioFS).

### "alembic command not found"

The api container takes a few seconds to start. Wait for healthcheck:

```bash
docker compose -f infra/docker-compose.yml ps    # check status
docker compose -f infra/docker-compose.yml logs api    # check for errors
```

### Migrations conflict

Check the migration files in `apps/api/alembic/versions/`. If you have local-only revisions that conflict with merged ones, `git rebase` and re-run.

### "container is unhealthy"

```bash
# Inspect
docker compose -f infra/docker-compose.yml ps
docker inspect padelcoach_api --format='{{.State.Health.Status}}'
docker inspect padelcoach_api --format='{{json .State.Health}}' | jq

# Logs
docker compose -f infra/docker-compose.yml logs <service>
```

### Out of disk space

```bash
# Prune unused images/volumes
docker system prune -a --volumes

# Or just our project
docker compose -f infra/docker-compose.yml down -v
```

### Postgres data lost after `down -v`

That's `-v` (volumes) doing what it says. **Use `down` without `-v`** to preserve data:

```bash
docker compose -f infra/docker-compose.yml down       # safe — volumes preserved
docker compose -f infra/docker-compose.yml down -v    # destructive — wipes data
```

## Editor setup tips

### Cursor / VSCode

Open the **repo root** (not subdirectories) for proper monorepo language servers.

Recommended extensions:
- ESLint
- Prettier
- Tailwind CSS IntelliSense
- Python (Pylance)
- Even Better TOML
- Ruff

`.vscode/settings.json` recommended:

```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "tailwindCSS.experimental.classRegex": [
    ["cva\\(([^)]*)\\)", "[\"'`]([^\"'`]*).*?[\"'`]"],
    ["cn\\(([^)]*)\\)", "(?:'|\"|`)([^']*)(?:'|\"|`)"]
  ]
}
```

### Cursor + Claude Code

Open Cursor at repo root. Run Claude Code from terminal:

```bash
cd ~/projects/padelcoach
claude
```

Claude Code reads `CLAUDE.md` automatically.

## Deploying to production

Same docker-compose, with overrides for production:

```bash
docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml up -d
```

Or push individual services to managed platforms:

- **api** + **worker** → Railway / Fly.io / Render (point to `infra/api/Dockerfile` target=production)
- **web** → Cloudflare Pages, Netlify, Vercel (or Docker container with nginx)
- **postgres** → Neon, Supabase, RDS
- **redis** → Upstash, Redis Cloud
- **storage** → Cloudflare R2 (production env vars)
- **email** → Resend (production env vars)

The Docker setup is portable — same containers run dev → staging → prod, just different env files.

## Performance notes

- **Mac:** Docker on Mac is slower than native due to VM. VirtioFS (Settings → Virtualization framework) helps a lot.
- **Build cache:** First build takes 5–10 min. Subsequent builds are fast (under 1 min) due to layer caching.
- **Volume mounts:** dev mounts source as volume so hot reload works. This is slower than baked images but enables fast iteration.

## Production hardening (later)

When prepping for first paying customers:

- [ ] Generate strong JWT_SECRET (32+ random bytes)
- [ ] Configure CORS to only allow production web origin
- [ ] Set Postgres `ssl_mode=require` for managed DB
- [ ] Add Cloudflare in front of api (DDoS, rate limiting)
- [ ] Enable Sentry release tracking + source maps
- [ ] Add backup automation (`pg_dump` on schedule → R2)
- [ ] Set up status page (BetterUptime free tier)
- [ ] Add health checks to deploy platform
- [ ] Configure log retention
- [ ] Run security scan (`docker scout`, `trivy`)
