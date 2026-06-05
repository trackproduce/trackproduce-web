"""HTTP routes for the Track Produce site."""
from __future__ import annotations

from flask import Flask, render_template

from app.content import get_collaborators, get_gallery


def register_routes(app: Flask) -> None:
    """Register all HTTP routes on the given Flask app."""

    @app.route("/")
    def index() -> str:
        return render_template(
            "index.html",
            gallery=get_gallery(),
            collaborators=get_collaborators(),
        )
