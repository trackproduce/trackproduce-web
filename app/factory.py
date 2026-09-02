"""Application factory for the Track Produce site."""
from __future__ import annotations

import os
import secrets

from dotenv import load_dotenv
from flask import Flask
from flask_compress import Compress
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from markupsafe import Markup
from sitecopy import FileStore, LocalFileStore, SiteCopy, is_edit_mode, t
from sitecopy.resolver import editable

from app.content import STATIC_PREFIX, deploy_version, media_src, responsive_image
from app.media_store import VercelBlobStore
from app.registry import REGISTRY

load_dotenv()

DEFAULT_SITE_URL = "https://trackproduce.com"

# Extensions are created at module level so models and repositories can import
# them (e.g. ``from app.factory import db``).
db: SQLAlchemy = SQLAlchemy()
migrate: Migrate = Migrate()
sitecopy: SiteCopy = SiteCopy()


def editable_media(*keys: str) -> Markup:
    """Attach media field `keys` to the ``<img>``/``<video>`` they are rendered on.

    The visual editor hangs its "cambiar imagen" control off the picture itself, and
    finds the picture by looking for a media key among the ones that element carries.
    A key reaches an element by appearing in one of its attributes, which normally
    happens for free — but this site renders media through a cache-stamped, responsive
    URL rather than the stored value, so nothing would carry the key.

    Hence a marker in a throwaway attribute, emitted **only in edit mode**: the response
    rewrite consumes it and records the key, and a visitor's HTML never grows an
    attribute that exists purely for the editor.
    """
    if not is_edit_mode():
        return Markup("")
    # Leading space, and every call site strips the whitespace before it: that way the
    # attribute is separated from its neighbour here, and a public render collapses to
    # nothing at all rather than leaving a ragged blank line behind.
    return Markup(
        "".join(f' data-ct-key-{index}="{editable(key)}"' for index, key in enumerate(keys))
    )


def editor_pages() -> list[dict[str, str]]:
    """The pages the visual editor may open in its canvas.

    Also the allow-list of pages it can START on, so the editor can never be loaded
    into its own frame. One entry, because the site is one page.
    """
    return [{"path": "/", "label": "Inicio"}]


def on_vercel() -> bool:
    """True when running as a Vercel Function (Vercel sets ``VERCEL`` in every runtime)."""
    return bool(os.environ.get("VERCEL"))


def file_store(upload_folder: str) -> FileStore:
    """Where the content editor's uploads go.

    Vercel Functions have a read-only filesystem, so writing next to the app is not an
    option there — with a Blob token present, uploads go to Vercel Blob and are served
    from its CDN. Development and Docker keep the local folder, which needs no account
    and survives a rebuild through its volume.
    """
    token = os.environ.get("BLOB_READ_WRITE_TOKEN")
    if token:
        return VercelBlobStore(token, prefix=os.environ.get("BLOB_PREFIX", "uploads"))
    return LocalFileStore(upload_folder, "/uploads")


def auto_schema() -> bool:
    """Whether to create the tables at boot.

    Off on Vercel: every cold start would spend two round trips re-checking a schema
    that only changes on deploy, and a serverless process is the wrong place to be
    running DDL from. ``scripts/init_db.py`` does it once against the deployed database
    instead. On everywhere else, where boot happens once and a fresh checkout should
    just run.
    """
    default = "0" if on_vercel() else "1"
    return os.environ.get("DB_AUTO_SCHEMA", default) not in ("0", "false", "False", "")


def create_app() -> Flask:
    """Create, configure and return the Flask application."""
    # Static files stay in the package, where ``app/content.py`` can read them: Vercel
    # keeps ``public/`` out of the function bundle, so serving from there would leave the
    # cache stamps and the responsive variants with nothing to look at. The build copies
    # this folder to ``public/static`` (``scripts/collect_static.py``) so the CDN answers
    # those requests in production and this route only ever runs in development.
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///local.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    if on_vercel():
        # A function instance serves many requests but can sit idle for a long time
        # between them, and the database is a managed Postgres several network hops
        # away. Keep a single connection to reuse, check it is still alive before
        # handing it out, and drop it well before either side times it out.
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_size": 1,
            "max_overflow": 2,
            "pool_pre_ping": True,
            "pool_recycle": 300,
        }
    # Absolute: uploaded media is served back out of this directory, and a relative
    # path would resolve against whatever the working directory happens to be.
    app.config["UPLOAD_FOLDER"] = os.path.abspath(
        os.environ.get("UPLOAD_FOLDER", "uploads")
    )
    app.config["UMAMI_WEBSITE_ID"] = os.environ.get("UMAMI_WEBSITE_ID")
    app.config["SITE_URL"] = os.environ.get("SITE_URL", DEFAULT_SITE_URL).rstrip("/")
    # Signs the content editor's admin session. A generated key is a dev convenience
    # only: it differs per process, so with more than one worker the login stops
    # sticking. Set SECRET_KEY in every deployed environment.
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    # The editor's shared password. Unset, the panel refuses every password — which is
    # the right default for an environment that was never meant to have one.
    app.config["SITECOPY_PASSWORD"] = os.environ.get("SITECOPY_PASSWORD", "")

    # Cache static assets for a year; a ``?v=<mtime>`` cache-buster (below) makes
    # this safe — the URL changes whenever a file is edited, so clients never see
    # a stale asset.
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 31_536_000  # 1 year, in seconds

    db.init_app(app)
    migrate.init_app(app, db)

    # gzip/br/deflate HTML, CSS and JS responses (Lighthouse "text compression").
    Compress(app)

    @app.url_defaults
    def _static_cache_buster(endpoint: str, values: dict[str, object]) -> None:
        """Append ``?v=…`` to ``static`` URLs so the long cache never stales."""
        if endpoint != "static" or "filename" not in values:
            return
        # Deployed, the commit is the stamp: the bundle's mtimes are all the same frozen
        # number, so they would never bust anything. See ``deploy_version()``.
        version = deploy_version()
        if version:
            values["v"] = version
            return
        filename = values["filename"]
        if not isinstance(filename, str) or app.static_folder is None:
            return
        try:
            mtime = int(os.stat(os.path.join(app.static_folder, filename)).st_mtime)
        except OSError:
            return
        values["v"] = mtime

    # Site copy: every user-facing string comes from ``app/registry.py`` and can be
    # edited at /admin/content without a deploy. The brand name and the year used to
    # be template globals; they are registry fields and the {brand}/{year} tokens now,
    # so there is only ever one source of truth for them.
    #
    # AFTER ``Compress(app)`` on purpose: Flask runs ``after_request`` hooks in reverse
    # registration order, so registering later means the editor's HTML rewrite sees the
    # response while it is still text rather than an already-gzipped body.
    sitecopy.init_app(
        app,
        registry=REGISTRY,
        db=db,
        pages=editor_pages,
        brand=lambda: str(t("global.brand")),
        site_url=app.config["SITE_URL"],
        # Vercel Blob once deployed; in development the mounted UPLOAD_FOLDER volume,
        # which is outside static/ so an image rebuild does not wipe it and which
        # ``serve_upload`` in routes.py serves back.
        files=file_store(app.config["UPLOAD_FOLDER"]),
        # Let the editor change how big a text renders. The wrapper this puts around a
        # sized value is a <span>, so the site's CSS must not style bare descendant
        # spans — `.brand__accent` and `.site-nav__num` carry classes for that reason.
        # Fields that only ever land in an attribute opt out in the registry instead:
        # there is no text on the page for a size to apply to.
        text_sizes=True,
    )

    # The gallery's registry defaults are literal "/static/…" strings built at import,
    # with no app to ask, and ``content.py`` reads the files themselves to decide which
    # responsive variants exist. A different prefix, or a folder that did not survive the
    # deploy, would 404 every piece at once — so fail at boot rather than serve a gallery
    # of broken images.
    if app.static_url_path != STATIC_PREFIX or not os.path.isdir(app.static_folder or ""):
        raise RuntimeError(
            f"app/content.py builds gallery defaults under {STATIC_PREFIX!r}, but this app "
            f"serves {app.static_url_path!r} from {app.static_folder!r}."
        )
    app.jinja_env.globals["responsive_image"] = responsive_image
    app.jinja_env.globals["media_src"] = media_src
    app.jinja_env.globals["editable_media"] = editable_media

    with app.app_context():
        # Import models so SQLAlchemy/Migrate can discover them.
        from app import models  # noqa: F401
        from app.routes import register_routes

        register_routes(app)
        if auto_schema():
            db.create_all()
            sitecopy.ensure_schema()

    return app
