"""Expose the Flask application instance."""
from app.factory import create_app

app = create_app()
