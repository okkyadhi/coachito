# Railway deploy (1-service, all-in-one)

The whole app — FastAPI, the Vite FE bundle, and the RQ worker — ships
as a single container ([infra/Dockerfile.allinone](../infra/Dockerfile.allinone)).
FastAPI serves the FE static files itself; the worker runs as a daemon
thread inside the same process.

Two Railway plugins back the container:
- **Postgres** — exposes `DATABASE_URL`
- **Redis** — exposes `REDIS_URL`

Per Railway billing this means **3 boxes total** (Postgres + Redis + app),
not 5. Plenty for MVP scale; split into separate services later if
worker pressure or web traffic actually demand it.

---

## 1. Prerequisites

Accounts:
- **Railway** — https://railway.app  *(login pakai GitHub)*
- *(optional, when needed)* Cloudflare R2, Resend, Google AI Studio, Sentry

CLI:
- `brew install railway`
- `railway login`

---

## 2. Bikin Railway project + plugin

1. Buka dashboard → **New Project** → **Empty Project** → kasih nama `coachito`.
2. Di project: **+ Create** → **Database** → **Add PostgreSQL**.
3. **+ Create** → **Database** → **Add Redis**.

---

## 3. Tambah satu service `app` dari repo

1. **+ Create** → **GitHub Repo** → pilih `okkyadhi/coachito` → branch `main`.
2. Service muncul dengan nama random — klik nama-nya di atas panel kanan,
   ganti jadi `app`.
3. Tab **Settings**:
   - Section **Build** → ganti Builder ke **Dockerfile** → field
     **Dockerfile Path** = `infra/Dockerfile.allinone`
   - Section **Deploy** → field **Healthcheck Path** = `/healthz`
   - Section **Networking** → klik **Generate Domain** → catat URL-nya
     (tipe `app-production-xxxx.up.railway.app`).

Start command tidak perlu di-isi — Dockerfile sudah punya `CMD` yang
menjalankan `alembic upgrade head` lalu uvicorn.

---

## 4. Isi environment variables

Tab **Variables** di service `app`, tambahkan baris-baris ini.
`${{Postgres.X}}` adalah syntax referensi Railway — dia substitusi
nilainya otomatis dari plugin Postgres.

| Variable | Value |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` |
| `JWT_SECRET` | jalankan `openssl rand -hex 48` di terminal lokal, paste hasilnya |
| `WEB_URL` | `https://<domain-app-Anda>.up.railway.app` |
| `ENVIRONMENT` | `production` |

> `ALLOWED_ORIGINS` **tidak perlu** diisi — FE & API satu origin.
>
> `VITE_API_BASE_URL` **tidak perlu** diisi — Dockerfile default-nya
> sudah string kosong, jadi FE pakai relative path ke origin yang sama.

Service-nya pernah-pernah dibutuhkan (boleh skip dulu sampai fitur dipakai):

| Variable | Untuk |
|---|---|
| `S3_ENDPOINT` / `S3_BUCKET` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_PUBLIC_HOST` | Upload logo, foto trainee → Cloudflare R2 |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` | Magic-link, welcome email → Resend |
| `GEMINI_API_KEY` | AI draft summary → Google AI Studio |
| `SENTRY_DSN` | Error tracking |

---

## 5. Deploy

Begitu env terisi, Railway auto-trigger build dari `main`. Pantau log
di tab **Deployments**. Sequence yang diharapkan:

1. `[stage web-build]` Vite build → `dist/`
2. `[stage final]` `uv sync` install Python deps
3. Container start → `alembic upgrade 0033 -> 0034`
4. `uvicorn` listen di `$PORT`
5. Healthcheck `/healthz` → 200

Smoke test:

```bash
curl -fsS https://<domain-app-Anda>.up.railway.app/healthz
open https://<domain-app-Anda>.up.railway.app
```

---

## 6. Seed data default

DB pertama kali masih kosong — load skills/curricula/descriptors/tiers:

```bash
railway link        # link folder lokal ke project Railway
railway run --service app python -m scripts.seed
```

---

## 7. Promote akun jadi platform admin

Setelah signup via `/signup/club` (atau `/signup/coach`) di URL deploy-nya,
promote akun Anda biar bisa akses `/admin/*`:

```bash
railway connect Postgres
# Di psql:
UPDATE users SET is_platform_admin = TRUE WHERE email = 'you@example.com';
\q
```

---

## 8. Known gaps untuk MVP

- **RLS bypass**: Railway's default Postgres user punya `BYPASSRLS = true`,
  jadi policies RLS **tidak ter-enforce**. Defense-in-depth turun ke
  "application-layer scoping only". Untuk restore RLS, bikin role
  `coachito_api` tanpa BYPASSRLS dan point `DATABASE_URL` ke role itu
  (simpan `ALEMBIC_DATABASE_URL` di superuser supaya migrations tetap
  jalan). Tidak blocking untuk MVP launch tapi wajib di-fix sebelum
  ada customer beneran.
- **Worker pressure**: PDF generation jalan di thread yang sama dengan
  uvicorn. Kalau >50 PDF di-generate bareng-bareng, request API
  bisa lambat. Pecah jadi worker service terpisah saat itu mulai
  jadi masalah.
- **Custom domain**: kalau sudah ready, CNAME ke `<app>.up.railway.app`
  dan tambah domain di service Settings → Networking → Custom Domain.
  Update `WEB_URL` setelah itu.
- **No CI**: Railway build straight dari `main`. Setelah test+lint
  stable, tambah GitHub Action sebagai gate sebelum merge ke main.
