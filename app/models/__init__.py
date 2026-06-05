"""SQLAlchemy models package.

Convention: one file per domain entity (e.g. ``contact_message.py``) whose class
subclasses ``db.Model`` imported from ``app.factory``. Re-export each model here
so the rest of the app can do ``from app.models import ContactMessage``.

Example::

    from app.models.contact_message import ContactMessage

    __all__ = ["ContactMessage"]

Models hold schema only — no queries or persistence logic (that lives in
``app/repositories/``).
"""
