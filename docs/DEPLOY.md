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
| Static files | `app/static/**`, copied to `public/static` by the Build Command so the CDN answers `/static/…` |
| Everything else | one Vercel Function running the Flask app |
| Build Command | `python scripts/collect_static.py` (`vercel.json`) |
| Function config | `vercel.json` — the `excludeFiles` glob keeps tests and docs out of the bundle |

Two consequences of running serverless are wired into the app on purpose:

- **The filesystem is read-only.** Uploads from the content editor go to Vercel Blob
  (`app/media_store.py`) whenever `BLOB_READ_WRITE_TOKEN` is set, and to the local
  `UPLOAD_FOLDER` otherwise. Nothing else writes to disk.
- **Boot happens constantly.** `create_app()` skips `db.create_all()` / `ensure_schema()`
  on Vercel (`auto_schema()` in `app/factory.py`) so no cold start spends round trips on
  DDL. `scripts/init_db.py` does it once instead — see below.
- **`public/` is generated, and the function cannot read it.** Vercel serves `public/`
  from the CDN *and* strips it from the function bundle, but `app/content.py` reads those
  same files to stamp URLs and to know which responsive variants exist. So the files live
  in `app/static` (bundled with the code) and the build copies them out —
  `scripts/collect_static.py`. `public/` is gitignored: never edit it, never commit it.
  `includeFiles` in `vercel.json` does not work around this; the Python builder ignores it
  for `public/`.

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

- **Every deploy re-stamps the static URLs.** `media_src()` busts the year-long cache with
  `?v=<mtime>`, and a fresh checkout gives every file a new mtime, so returning visitors
  re-download assets after a deploy even when the bytes are identical. Harmless, but it is
  why the numbers move on their own.
- **The Blob API version is pinned** in `app/media_store.py` (`x-api-version`). If uploads
  start failing with a 4xx after a Blob release, that constant is the first place to look.
- **Preview deployments share the production database** unless a separate Neon branch is
  attached to the Preview environment. Editing copy from a preview URL edits the live site.
