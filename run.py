"""Local entry point: the Flask app on a development server.

Deployed environments never run this. Vercel loads ``wsgi.py`` and the Docker image
runs gunicorn against it, so anything added here is a development convenience only.
"""
from __future__ import annotations

import os

from app import app

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "1") not in ("0", "false", "False", "")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7015)), debug=debug)
