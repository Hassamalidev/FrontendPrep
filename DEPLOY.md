# Deploying Frontline Prep

Three free services: **Neon** (Postgres), **Render** (the API), **Vercel** (the
app). Total cost is zero; the trade-offs are noted where they bite.

Deploy in this order — each step needs a value from the one before.

---

## 1. Neon — the database

1. Create a project at [neon.tech](https://neon.tech). Pick the region nearest
   your users (`ap-southeast-1` Singapore for Pakistan).
2. On the dashboard, open **Connection Details** and copy the
   **Pooled connection** string. It has `-pooler` in the host:

   ```
   postgresql://user:pw@ep-name-12345-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
   ```

**Use the pooled string, not the direct one.** Render's free instance sleeps and
wakes constantly; without pgbouncer in front you exhaust Neon's connection limit.

You do not need to strip the query string. The app normalises the URL itself —
rewrites `postgresql://` to `postgresql+asyncpg://` and drops `sslmode` and
`channel_binding`, which are libpq options asyncpg rejects.

**Free tier:** 0.5 GB storage, and the compute auto-suspends after 5 minutes
idle. First request after a suspend takes a few seconds.

---

## 2. Render — the API

### Option A: the blueprint (recommended)

`render.yaml` is committed **at the repository root** — that is where Render
looks, and a blueprint inside `backend/` is invisible to it. The file itself
sets `rootDir: backend`.

In Render: **New → Blueprint**, point it at the repo, apply. It creates the
service with the right runtime, build command, health check and all six
environment variables.

### Option B: by hand

**New → Web Service**, connect the repo, then:

| Setting | Value |
|---|---|
| Root directory | `backend` |
| Language / Runtime | **Python 3** — not Docker |
| Build command | `pip install -r requirements.txt && alembic upgrade head && python -m app.seed` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1` |
| Health check path | `/health` |
| Instance type | Free |

The build runs migrations **and** the seed. The seed is idempotent (rows match
on their natural key), so it creates the catalog, the ISSB content and your
admin account on the first deploy and does nothing on later ones. Without it you
get a schema with no way to sign in.

`--workers 1` is deliberate: each worker holds its own connection pool, and a
512 MB instance with a free Neon project cannot afford more.

### Render environment variables

Only **two** need you to type anything. Everything else the application already
defaults correctly in production, and restating a default in the blueprint just
creates somewhere for the two to drift apart.

| Key | Value | Why it is here |
|---|---|---|
| `DATABASE_URL` | *your Neon **pooled** string* | Paste exactly as Neon gives it; the app rewrites the driver and strips libpq args |
| `CORS_ORIGINS` | `https://your-app.vercel.app` | Scheme included, no trailing slash |

Two more are filled in by Render itself when you deploy the blueprint:

| Key | How |
|---|---|
| `JWT_SECRET` | `generateValue` — Render creates and stores it |
| `BOOTSTRAP_ADMIN_PASSWORD` | `generateValue` — read it from the service's **Environment** tab to sign in the first time, then change it |

And two are fixed in `render.yaml`:

| Key | Value |
|---|---|
| `ENV` | `production` |
| `PYTHON_VERSION` | `3.12.8` |

**Not set, on purpose.** `DEBUG`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`,
`DB_STATEMENT_CACHE_SIZE`, `ARGON2_MEMORY_COST`, `ARGON2_TIME_COST` and
`NEWS_CACHE_MINUTES` already default to their correct production values.
`DEMO_MODE` is omitted too: it defaults to on, but demo access additionally
requires `ENV` not to be `production`, so setting `ENV` already closes it.

`BOOTSTRAP_ADMIN_EMAIL` defaults to `admin@frontlineprep.pk` — add it if you
want a different address. It is not a secret, and the seed never re-passwords an
account that already exists.

Optional: `CORS_ORIGIN_REGEX=https://.*\.vercel\.app` also allows Vercel
preview deployments.

**Demo accounts on a portfolio site.** `DEMO_MODE` alone is not enough: demo
access requires `DEMO_MODE=true` **and** `ENV` not being `production`. That is
deliberate — a forgotten flag must not publish working credentials. If you *want*
visitors to try the app without registering, set `ENV=staging` and
`DEMO_MODE=true`. Be aware this also re-exposes `/docs`.

**Free tier:** the service sleeps after 15 minutes idle and cold-starts in about
30 seconds. The health check points at `/health`, which deliberately does not
touch the database — waking Neon on every platform ping would burn its compute
allowance for nothing. `/health/db` is the readiness check that does.

---

## 3. Vercel — the app

**Add New → Project**, import the repo, then:

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Framework preset | Vite |
| Build command | `npm run build` |
| Output directory | `dist` |

`frontend/vercel.json` is committed and supplies the SPA rewrite. Without it,
loading `/dashboard` directly returns 404 — the router is client-side, so every
path has to serve `index.html`.

### Vercel environment variables

| Key | Value |
|---|---|
| `VITE_API_URL` | `https://your-api.onrender.com/api/v1` |

That is the only one. Two things about it:

- **Include the `/api/v1` suffix.** The client appends paths directly to it.
- **Vite inlines `VITE_*` at build time, not run time.** Changing it in the
  dashboard does nothing until you redeploy.

---

## 4. Close the loop

Once Vercel gives you a URL, go back to Render and set `CORS_ORIGINS` to it,
then redeploy. This is the step everyone forgets; the symptom is every request
failing in the browser while `curl` works fine.

### Check it

```bash
curl https://your-api.onrender.com/health          # {"status":"ok"}
curl https://your-api.onrender.com/health/db       # {"database":"reachable"}
```

Then open the Vercel URL, sign in with your bootstrap admin, and **change the
password**.

---

## Keeping inside the free tiers

The platform is built for this, but two habits matter:

- **Current affairs are never stored** — read live from RSS and cached in
  memory. Do not "fix" this by persisting them; a dozen stories a day is roughly
  11 MB a year of text nobody re-reads.
- **Generating from news keeps the questions, not the stories.** Run
  `POST /admin/news/generate` as often as you like; it adds questions and zero
  articles.

Watch usage at **Admin → Maintenance**, which shows row counts per table and
runs the retention job (drops old agent traces, article bodies and attempt
detail; scores are kept forever).

A fresh deploy is about 49 questions and 0 articles.

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| `failed to read dockerfile: open Dockerfile: no such file` | A Docker service whose Root Directory is the repo root. There is now a `Dockerfile` at the root that builds the backend, so a redeploy fixes it. Note that **an existing service never reads `render.yaml`** — that file only configures services created *from* a Blueprint |
| `rejected SSL upgrade` on connect | The database does not offer TLS (Render's internal Postgres, a Docker network, a VPC). Set `DB_SSL=disable`. Neon needs the default `auto` |
| Blueprint not detected | `render.yaml` must be at the **repository root**, not in `backend/` |
| Browser requests all fail, `curl` works | `CORS_ORIGINS` does not exactly match the Vercel origin (scheme, no trailing slash) |
| 404 on refresh at `/dashboard` | `vercel.json` missing or root directory not `frontend` |
| `prepared statement ... already exists` | `DB_STATEMENT_CACHE_SIZE` is not `0`, or you used the direct rather than pooled Neon string |
| Cannot sign in after first deploy | The seed did not run — check the build log for `python -m app.seed` |
| First request takes ~30s | Render free tier waking. Expected |
| `starter questions: 0` in the deploy log | Not a failure. The seed is idempotent, and 0 means every question was already present. The line now also reports how many are in the bank |
| `No open ports detected, continuing to scan` | Harmless; the service still comes up. `/` and `/health` now answer HEAD, which is what the scanner probes with |
| API calls go to the Vercel domain | `VITE_API_URL` unset at build time, so it fell back to the dev default `/api/v1` |
