"""The site's copy and the registry that declares it must agree.

``app/registry.py`` is the source of truth for every user-facing string, and the
templates reach it through ``t('…')``. Two files that have to stay in step is exactly
the kind of thing that drifts silently — a renamed key renders an empty heading in
production — so these tests fail the build instead.
"""
from __future__ import annotations

import os
import pathlib
import re
from collections.abc import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sitecopy.resolver import EDIT_END, EDIT_SEP, EDIT_START
from sitecopy.testing import check_registry, check_templates

from app.registry import REGISTRY

PASSWORD = "test-only-password"
CSRF_FIELD = re.compile(r'name="_sitecopy_csrf"\s+value="([^"]+)"')
CSRF_DATA = re.compile(r'data-csrf="([^"]+)"')


def login(client: "FlaskClient") -> None:
    """Sign in to the panel the way the browser does — CSRF token and all."""
    form = client.get("/admin/content/login").get_data(as_text=True)
    token = CSRF_FIELD.search(form)
    assert token is not None, "the login form carried no CSRF token"
    response = client.post(
        "/admin/content/login",
        data={"password": PASSWORD, "_sitecopy_csrf": token.group(1)},
        follow_redirects=True,
    )
    assert response.status_code == 200


@pytest.fixture
def app(tmp_path: pathlib.Path) -> Iterator[Flask]:
    """A second app instance on a throwaway database, so tests never touch real copy.

    Per test, not per module: one of these publishes an override, and a shared database
    would make the others depend on the order they happen to run in.
    """
    database = tmp_path / "test.sqlite"
    previous = {
        key: os.environ.get(key) for key in ("DATABASE_URL", "SECRET_KEY", "SITECOPY_PASSWORD")
    }
    os.environ.update(
        DATABASE_URL=f"sqlite:///{database}",
        SECRET_KEY="test-only-secret-key",
        SITECOPY_PASSWORD=PASSWORD,
    )
    try:
        # Imported here, not at module scope: create_app reads the environment above.
        from app.factory import create_app

        yield create_app()
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_registry_is_sound() -> None:
    """Unique keys, defaults that fit their own max_length, tokens that point somewhere."""
    assert check_registry(REGISTRY) == []


def test_every_key_is_rendered_and_every_rendered_key_exists() -> None:
    """No template asks for a key nobody declared, and no declared key goes unrendered."""
    assert check_templates(REGISTRY, "app") == []


def test_the_public_page_renders_the_registry_defaults(app: Flask) -> None:
    """A fresh database renders exactly what the code says — no seeding step."""
    html = app.test_client().get("/").get_data(as_text=True)
    assert REGISTRY.defaults["home.services.title"] in html
    assert REGISTRY.defaults["home.hero.cta_primary"] in html
    # {city} resolved from the global token rather than shipping as a literal brace.
    assert "en Buenos Aires." in html
    assert "{city}" not in html


def test_the_marquee_reads_the_collaborators_from_the_registry(app: Flask) -> None:
    """The `lines` field becomes one item per line, not one blob."""
    html = app.test_client().get("/").get_data(as_text=True)
    for name in REGISTRY.defaults["home.marquee.items"].split("\n"):
        assert f'<span class="marquee__item">{name}</span>' in html


def test_the_public_page_carries_no_editor_markup(app: Flask) -> None:
    """Markers exist only for a logged-in admin; a visitor's HTML is untouched."""
    html = app.test_client().get("/").get_data(as_text=True)
    assert not any(marker in html for marker in (EDIT_START, EDIT_SEP, EDIT_END))
    assert "<ct-t" not in html


def test_the_editor_rewrite_still_sees_the_html(app: Flask) -> None:
    """Guards the hook order in the factory: SiteCopy must be wired AFTER Compress.

    Flask runs ``after_request`` hooks in reverse registration order. Wire compression
    last and the rewrite reads an already-gzipped body: the private-use markers it was
    going to replace ship to the browser as empty boxes instead.
    """
    client = app.test_client()
    login(client)
    response = client.get("/?edit=1")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "<ct-t" in html, "edit mode rendered no editable blocks"
    assert not any(
        marker in html for marker in (EDIT_START, EDIT_SEP, EDIT_END)
    ), "the response was rewritten or compressed before sitecopy could read it"


def test_a_published_edit_reaches_the_public_page(app: Flask) -> None:
    """The whole loop on a real table: draft, publish, and the site says the new thing.

    Also the proof that ``sitecopy.ensure_schema()`` in the factory built a usable
    overrides table — every step here writes to it.
    """
    client = app.test_client()
    login(client)

    editor = client.get("/admin/content/").get_data(as_text=True)
    csrf = CSRF_DATA.search(editor)
    assert csrf is not None, "the editor carried no CSRF token"
    headers = {"X-Sitecopy-CSRF": csrf.group(1)}

    saved = client.post(
        "/admin/content/save",
        json={"changes": {"home.services.title": "Hacemos todo, en serio."}},
        headers=headers,
    )
    assert saved.status_code == 200, saved.get_data(as_text=True)
    assert saved.get_json()["ok"] is True

    # A draft is invisible to the public and visible in preview — that is the point.
    assert "Hacemos todo, en serio." not in client.get("/").get_data(as_text=True)
    assert "Hacemos todo, en serio." in client.get("/?preview=1").get_data(as_text=True)

    client.post("/admin/content/publish", data={"_sitecopy_csrf": csrf.group(1)})
    assert "Hacemos todo, en serio." in client.get("/").get_data(as_text=True)


def test_the_editor_is_closed_to_the_public(app: Flask) -> None:
    """Preview and edit mode are gated on the admin session, not on a query string."""
    client = app.test_client()
    assert "<ct-t" not in client.get("/?edit=1").get_data(as_text=True)
    assert client.get("/admin/content/", follow_redirects=False).status_code in (301, 302)
