# Deploy

The site runs on **Vercel**, deployed by its Git integration: a push to `main` builds and
promotes a production deployment, and a push to any other branch gets a preview URL. There
is nothing to run by hand — no build, no image, no server.

DNS is on **Cloudflare** and resolves `trackproduce.com` to Vercel.

## How the app maps onto Vercel

| Piece | Where it comes from |
|-------|--------------------|
| Entrypoint | `wsgi.py` — the Python runtime looks for a top-level `app` in a handful of file names, and this is one of them |
| Python | `.python-version` (3.12) |
| Dependencies | `requirements.txt` (runtime only; tests live in `requirements-dev.txt`) |
| Static files | `app/static/**`, served by Flask and cached at the edge (`x-vercel-cache: HIT` after the first request) |
| Everything else | one Vercel Function running the Flask app |
| Function config | `vercel.json` — the `excludeFiles` glob keeps tests and docs out of the bundle |

Three consequences of running on Vercel are wired into the app on purpose:

- **The filesystem is read-only.** Uploads from the content editor go to Vercel Blob
  (`app/media_store.py`) whenever `BLOB_READ_WRITE_TOKEN` is set, and to the local
  `UPLOAD_FOLDER` otherwise. Nothing else writes to disk.
- **Boot happens constantly.** `create_app()` skips `db.create_all()` / `ensure_schema()`
  on Vercel (`auto_schema()` in `app/factory.py`) so no cold start spends round trips on
  DDL. `scripts/init_db.py` does it once instead — see below.
- **Static files stay in `app/static`, not in `public/`.** Vercel's advice is to serve
  static assets from `public/`, but it strips that directory out of the function bundle,
  and `app/content.py` reads those same files to stamp each URL and to know which
  responsive variants exist — so a `public/`-only copy breaks the gallery. Keeping them in
  the package costs nothing real: Flask answers `/static/…` once and the edge caches the
  response for a year. (`includeFiles` does not bring `public/` back into the bundle, and
  a build step that copies into `public/` is not picked up by the Flask preset — both were
  tried.)

## Environment variables

Set in the Vercel project (Settings → Environment Variables), Production and Preview:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | added by the Neon integration when the store is attached |
| `BLOB_READ_WRITE_TOKEN` | added by the Blob store when it is attached |
| `SECRET_KEY` | 32 random bytes — `python -c "import secrets; print(secrets.token_hex(32))"`. Signs the editor's session; must be stable or the login stops sticking |
| `SITECOPY_PASSWORD` | the content editor's shared password. Unset, the panel refuses every password |
| `SITE_URL` | `https://trackproduce.com` — canonical origin for `og:url` and the editor's preview cards |
| `UMAMI_WEBSITE_ID` | analytics id; leave it out of Preview so staging traffic is not counted |

`DB_AUTO_SCHEMA` is not set: it defaults to off on Vercel and on everywhere else.

## First-time setup (already done — here for the next environment)

1. **Neon** — project → Storage → Create Database → Neon. Attach it to the project; it
   sets `DATABASE_URL`.
2. **Blob** — Storage → Create → Blob, access **public**. Attach it; it sets
   `BLOB_READ_WRITE_TOKEN`.
3. **Create the tables**, once, from a laptop:
   ```bash
   vercel env pull .env.production        # brings DATABASE_URL down
   DATABASE_URL="…" python scripts/init_db.py
   ```
   Re-run it after a `flask-sitecopy` upgrade, which is when its tables can gain a column.

## Domain and DNS

`trackproduce.com` is registered at **DonWeb**, resolved by **Cloudflare**, served by
**Vercel**.

- At DonWeb: nameservers point at the pair Cloudflare assigned to the zone.
- In Cloudflare, both records **DNS only (grey cloud)** — Vercel issues the certificate and
  serves the traffic, and proxying would put a second CDN in front of it:

  | Type | Name | Value |
  |------|------|-------|
  | A | `@` | `76.76.21.21` |
  | CNAME | `www` | `cname.vercel-dns.com` |

- In Vercel: add `trackproduce.com` and `www.trackproduce.com` to the project, with `www`
  redirecting to the apex.

## Local development

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cp .env.example .env          # fill SECRET_KEY and SITECOPY_PASSWORD to use the editor
.venv/bin/python run.py       # http://localhost:7015
```

`docker compose up --build` runs the same app against a Postgres that matches the deployed
engine, which is the closest thing to production available offline. Neither path touches
Vercel Blob: without a token, uploads land in `UPLOAD_FOLDER`.

Tests — including the performance suite — need browsers once:
`.venv/bin/python -m playwright install chromium`, then `.venv/bin/python -m pytest tests/`.

## Worth knowing

- **The cache stamp is the commit, not the mtime.** Vercel freezes every bundled file's
  mtime at the same value, so the `?v=` stamp the site relies on would never change and a
  replaced picture would serve stale bytes for a year. `deploy_version()` in
  `app/content.py` uses `VERCEL_GIT_COMMIT_SHA` instead wherever the platform sets it.
  The trade-off is that all assets re-download after a deploy, identical bytes included.
- **The Blob API version is pinned** in `app/media_store.py` (`x-api-version`). If uploads
  start failing with a 4xx after a Blob release, that constant is the first place to look.
- **Preview deployments share the production database** unless a separate Neon branch is
  attached to the Preview environment. Editing copy from a preview URL edits the live site.
