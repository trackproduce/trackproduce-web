"""Data-access layer (repositories).

Convention: one module per aggregate/entity (e.g. ``contact_repository.py``)
exposing a class with static methods (``get_all``, ``get_by_id``, ``save`` ...).
Routes call repositories; repositories own all ``db.session`` access.

Repositories import models from ``app.models`` and ``db`` from ``app.factory``,
and must not import Flask ``request`` or ``app`` — the route layer passes in
plain Python data.

Example::

    from app.factory import db
    from app.models import ContactMessage


    class ContactRepository:
        @staticmethod
        def save(name: str, email: str, message: str) -> ContactMessage:
            entity = ContactMessage(name=name, email=email, message=message)
            db.session.add(entity)
            db.session.commit()
            return entity
"""
