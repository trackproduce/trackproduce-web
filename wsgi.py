"""Vercel entrypoint.

Vercel's Python runtime looks for a top-level ``app`` in one of a handful of file
names (``wsgi.py`` among them) and runs it as a single Vercel Function. ``run.py``
is the local entrypoint instead: it adds a dev server that nothing on Vercel uses.
"""
from app import app

__all__ = ["app"]
