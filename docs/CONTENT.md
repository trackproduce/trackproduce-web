# Editable site copy

Every user-facing string on this site is editable from an admin panel, in place on the
real page, without a deploy. It runs on
[flask-sitecopy](https://github.com/CROCDC/flask-sitecopy).

- **Panel:** `/admin/content` — the site in a frame; click any text and type over it.
- **List view:** `/admin/content/list` — the same copy as forms, and the path that works
  with JavaScript off. It is also where copy with no visible text lives (the `<title>`,
  the meta description, aria-labels).
- **Password:** `SITECOPY_PASSWORD`. Left unset, the panel refuses every password.

## Where things live

| file | role |
|------|------|
| `app/registry.py` | the catalogue: every editable string, with a label and the default the code ships |
| `app/templates/index.html` | renders them through `t('<key>')` |
| `app/factory.py` | `sitecopy.init_app(...)` — one call, wired after `Compress(app)` |
| `site_texts` (DB) | **overrides only** — a key with no row renders its code default |

Because the table stores overrides only, a fresh database renders exactly what the code
says. There is no seeding step, "restore the original" is a row delete, and adding new
copy never needs a data migration.

## Adding a new text

1. Declare it in `app/registry.py` — a `TextField(key, label, default)` in the right
   `Section`.
2. Render it: `{{ t('the.key') }}`.

That is all; it shows up in the panel on the next request. `tests/test_content_registry.py`
fails if you do one without the other, in either direction.

**Keys are an API.** A key is the primary key of the override row, so renaming one drops
whatever the editor had written there. Migrate the row if you must rename.

## Draft → preview → publish

Nothing an editor types is live until they publish. **Guardar borrador** writes a draft;
**Previsualizar** opens the real page with `?preview=1` (drafts applied, admins only, and
the response carries `noindex` / `no-store`); **Publicar cambios** promotes drafts to the
public site. Publishing records the wording it replaced, so a published mistake has a way
back.

## What is *not* in the registry

The gallery pieces in `app/content.py` — their category names and the alt text of each
image and video. Those are tied one-to-one to a media file that only changes with a
deploy, so they ride with the files. The editor knows: clicking a gallery card says so,
via the `external_content` option in the factory.

## Things to know when changing this wiring

- **`sitecopy.init_app` must stay after `Compress(app)`.** Flask runs `after_request`
  hooks in reverse registration order, and the editor rewrites the HTML of an `?edit=1`
  response — wire it the other way round and the rewrite reads a gzipped body, shipping
  the editor's markers to the browser as empty boxes.
  `test_the_editor_rewrite_still_sees_the_html` guards this.
- **`SECRET_KEY` must be set in every deployed environment.** It signs the admin session.
  Unset, the factory generates one per process, so with more than one gunicorn worker the
  login stops sticking.
- **Uploads** land in `UPLOAD_FOLDER` (a mounted volume, so a rebuild does not wipe them)
  and are served back by the `serve_upload` route. Their names are content hashes. Only
  `png/jpg/webp/gif` and `mp4/webm` are accepted, sniffed from the bytes rather than the
  filename.
- **Text sizes are off.** Turning them on (`text_sizes=True`) lets editors resize a text
  from the panel, at the cost of a wrapper `<span>` around any sized value — which this
  site's CSS, built on tight selectors, would need checking against first.
