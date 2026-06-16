# Railway deploy walkthrough

Step-by-step to get Coachito running on Railway with a `*.up.railway.app`
subdomain. Comes in three Railway "services" inside one project:

| Service | Image                       | Notes                              |
|---------|-----------------------------|------------------------------------|
| `api`   | `infra/api/Dockerfile.prod` | FastAPI + alembic                  |
| `worker`| `infra/api/Dockerfile.prod` | RQ — same image, different command |
| `web`   | `infra/web/Dockerfile.prod` | Vite build served by nginx-alpine  |

Plus two Railway **plugins** (managed services in the same project):
- **Postgres** — exposes `DATABASE_URL`
- **Redis** — exposes `REDIS_URL`

---

## 1. One-time prerequisites

You'll need accounts on:
- **Railway** — https://railway.app (free dev tier, hobby plan $5/mo for prod)
- **Cloudflare R2** — https://dash.cloudflare.com (free 10 GB)
- **Resend** — https://resend.com (free 100 emails/day)
- **Google AI Studio** — https://aistudio.google.com/apikey (free Gemini key)
- *(optional)* **Sentry** — https://sentry.io (free 5k errors/mo)

Tooling:
- `railway` CLI: `brew install railway` (or `npm i -g @railway/cli`)
- `railway login` → opens browser

---

## 2. Create the Railway project

```bash
railway init                     # in repo root
# Pick: "Empty project" → name it "coachito"
railway link                     # if you already created via dashboard
```

From the dashboard, **add the plugins**:
- "+ New" → Database → Postgres
- "+ New" → Database → Redis

Postgres + Redis spin up with their own `DATABASE_URL` / `REDIS_URL`
variables. We'll wire them into the api + worker services next.

---

## 3. Create the three services

For each of `api`, `worker`, `web` — in the Railway dashboard:

1. **+ New** → **GitHub Repo** → pick `okkyadhi/coachito` → branch `main`.
2. Open the service settings → **Root Directory** = repo root (`/`).
3. **Build** → set "Config Path" to `infra/railway/<service>.json`:
   - api    → `infra/railway/api.json`
   - worker → `infra/railway/worker.json`
   - web    → `infra/railway/web.json`
4. **Networking** → for `api` and `web`, click "Generate Domain". You'll get:
   - `coachito-api.up.railway.app`
   - `coachito-web.up.railway.app`
   The `worker` doesn't need a public domain.

---

## 4. Set environment variables

Copy [`.env.prod.example`](../.env.prod.example) and fill in the values.
Then in each service's "Variables" tab on Railway:

### `api` service
| Var | Value |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (reference syntax — Railway substitutes) |
| `REDIS_URL`    | `${{Redis.REDIS_URL}}` |
| `JWT_SECRET`   | random 64+ char string (`openssl rand -hex 48`) |
| `WEB_URL`      | `https://coachito-web.up.railway.app` |
| `ALLOWED_ORIGINS` | `https://coachito-web.up.railway.app` |
| `S3_ENDPOINT` / `S3_BUCKET` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_PUBLIC_HOST` | from Cloudflare R2 |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` | from Resend |
| `GEMINI_API_KEY` | from Google AI Studio |
| `SENTRY_DSN`     | optional, from Sentry project setup |
| `ENVIRONMENT`    | `production` |

### `worker` service
Same as `api` (it shares the image and most env). The `${{Postgres.*}}`
and `${{Redis.*}}` references mean both services see the live URLs.

### `web` service (build-time vars)
Web reads Vite vars at **build time**, so they have to be set BEFORE the
first deploy. Use Railway "Variables" with the `VITE_` prefix:

| Var | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://coachito-api.up.railway.app` |
| `VITE_SENTRY_DSN`   | optional |
| `VITE_GOOGLE_CLIENT_ID` | optional |

> ⚠ If you change a `VITE_` var later, you must **redeploy** `web` for the
> new value to bake into the bundle.

---

## 5. First deploy

Each service auto-deploys on push to `main`. To trigger the first build:

```bash
git push origin main
```

Watch the build logs in the Railway dashboard. Expected sequence:

1. **postgres** plugin: provisions DB.
2. **api**: builds image → runs `alembic upgrade head` → starts uvicorn.
3. **worker**: builds image → starts `rq worker`.
4. **web**: builds Vite bundle → nginx serves on `$PORT`.

Smoke test once green:

```bash
curl -fsS https://coachito-api.up.railway.app/healthz
curl -fsS https://coachito-web.up.railway.app/
```

---

## 6. Seed default data

The first deploy creates an empty DB — run the seed once to load sports,
curricula, descriptors, tiers:

```bash
railway run --service api python -m scripts.seed
```

---

## 7. Promote yourself to platform admin

Once you've signed up at `https://coachito-web.up.railway.app/signup/club`
(or `/signup/coach`), promote your user so you can hit the `/admin/*`
endpoints:

```bash
railway connect Postgres
# inside psql:
UPDATE users SET is_platform_admin = TRUE WHERE email = 'you@example.com';
\q
```

---

## 8. Known gaps (post-MVP)

- **RLS bypass on Railway**: Railway's default Postgres user has
  `BYPASSRLS = true`, so RLS policies are NOT enforced. Defense-in-depth
  drops to "application-layer scoping only". To restore RLS, create a
  dedicated `coachito_api` role *without* BYPASSRLS and point
  `DATABASE_URL` at it (keep `ALEMBIC_DATABASE_URL` on the superuser for
  migrations). Track this in [Decision log](../CLAUDE.md) — not blocking
  MVP launch but worth fixing before any real customer data lands.
- **Custom domain**: when you're ready, point a CNAME to
  `coachito-web.up.railway.app` and add it under Web → Settings → Domains.
  Update `WEB_URL` + `ALLOWED_ORIGINS` + `VITE_API_BASE_URL` accordingly.
- **No CI**: Railway builds straight from `main`. Once tests + lint are
  stable, add a GitHub Action that gates merges; Railway only deploys
  what's on `main`.
