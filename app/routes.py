"""HTTP routes for the Track Produce site."""
from __future__ import annotations

from flask import Flask, Response, render_template, send_from_directory

from app.content import get_gallery


def register_routes(app: Flask) -> None:
    """Register all HTTP routes on the given Flask app."""

    @app.route("/")
    def index() -> str:
        return render_template("index.html", gallery=get_gallery())

    @app.route("/uploads/<path:filename>")
    def serve_upload(filename: str) -> Response:
        """Serve media uploaded from the content editor.

        The files live in ``UPLOAD_FOLDER`` (a mounted volume) rather than under
        ``static/`` so an image rebuild does not wipe them. Their names are content
        hashes, so a name always denotes the same bytes and they cache forever.
        """
        return send_from_directory(
            app.config["UPLOAD_FOLDER"], filename, max_age=31_536_000
        )
