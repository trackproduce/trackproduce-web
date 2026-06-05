"""Application factory for the Track Produce site."""
from __future__ import annotations

import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask
from flask_compress import Compress
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

# Extensions are created at module level so models and repositories can import
# them (e.g. ``from app.factory import db``).
db: SQLAlchemy = SQLAlchemy()
migrate: Migrate = Migrate()


def create_app() -> Flask:
    """Create, configure and return the Flask application."""
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///local.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", "uploads")
    app.config["UMAMI_WEBSITE_ID"] = os.environ.get("UMAMI_WEBSITE_ID")

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

    @app.context_processor
    def inject_globals() -> dict[str, object]:
        """Expose global variables to every template."""
        return {
            "current_year": datetime.now().year,
            "project_name": "Track Produce",
        }

    with app.app_context():
        # Import models so SQLAlchemy/Migrate can discover them.
        from app import models  # noqa: F401
        from app.routes import register_routes

        register_routes(app)
        db.create_all()

    return app
