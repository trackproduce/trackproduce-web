"""Application factory for the Track Produce site."""
from __future__ import annotations

import os
import secrets

from dotenv import load_dotenv
from flask import Flask
from flask_compress import Compress
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sitecopy import LocalFileStore, SiteCopy, t

from app.registry import REGISTRY

load_dotenv()

DEFAULT_SITE_URL = "https://trackproduce.nexttech.com.ar"

# Extensions are created at module level so models and repositories can import
# them (e.g. ``from app.factory import db``).
db: SQLAlchemy = SQLAlchemy()
migrate: Migrate = Migrate()
sitecopy: SiteCopy = SiteCopy()


def editor_pages() -> list[dict[str, str]]:
    """The pages the visual editor may open in its canvas.

    Also the allow-list of pages it can START on, so the editor can never be loaded
    into its own frame. One entry, because the site is one page.
    """
    return [{"path": "/", "label": "Inicio"}]


def create_app() -> Flask:
    """Create, configure and return the Flask application."""
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///local.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
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
        """Append ``?v=<mtime>`` to ``static`` URLs so the long cache never stales."""
        if endpoint != "static" or "filename" not in values:
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
        # Uploads land in the mounted UPLOAD_FOLDER volume, not under static/, so they
        # survive an image rebuild. ``serve_upload`` in routes.py serves them back.
        files=LocalFileStore(app.config["UPLOAD_FOLDER"], "/uploads"),
        external_content={
            "selector": '.card, .filter:not([data-filter="all"])',
            "message": (
                "Las piezas de la galería y los nombres de las categorías viajan con "
                "los archivos, en app/content.py. Se cambian con un deploy."
            ),
        },
    )

    with app.app_context():
        # Import models so SQLAlchemy/Migrate can discover them.
        from app import models  # noqa: F401
        from app.routes import register_routes

        register_routes(app)
        db.create_all()
        sitecopy.ensure_schema()

    return app
