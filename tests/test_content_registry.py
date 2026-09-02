"""The site's copy and the registry that declares it must agree.

``app/registry.py`` is the source of truth for every user-facing string, and the
templates reach it through ``t('…')``. Two files that have to stay in step is exactly
the kind of thing that drifts silently — a renamed key renders an empty heading in
production — so these tests fail the build instead.
"""
from __future__ import annotations

import base64
import io
import os
import pathlib
import re
from collections.abc import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sitecopy.resolver import EDIT_END, EDIT_SEP, EDIT_START
from sitecopy.testing import check_registry, check_response_pipeline, check_templates

from app.content import get_gallery
from app.registry import REGISTRY

PASSWORD = "test-only-password"
CSRF_FIELD = re.compile(r'name="_sitecopy_csrf"\s+value="([^"]+)"')
CSRF_DATA = re.compile(r'data-csrf="([^"]+)"')


def login(client: "FlaskClient") -> str:
    """Sign in to the panel the way the browser does, and return the session's CSRF token.

    Every state-changing panel request carries one, so the token is what a test needs
    next. It has to be read AFTER logging in: authenticating rotates the session.
    """
    form = client.get("/admin/content/login").get_data(as_text=True)
    token = CSRF_FIELD.search(form)
    assert token is not None, "the login form carried no CSRF token"
    response = client.post(
        "/admin/content/login",
        data={"password": PASSWORD, "_sitecopy_csrf": token.group(1)},
        follow_redirects=True,
    )
    assert response.status_code == 200

    editor = CSRF_DATA.search(client.get("/admin/content/").get_data(as_text=True))
    assert editor is not None, "the editor carried no CSRF token"
    return editor.group(1)


@pytest.fixture
def app(tmp_path: pathlib.Path) -> Iterator[Flask]:
    """A second app instance on a throwaway database, so tests never touch real copy.

    Per test, not per module: one of these publishes an override, and a shared database
    would make the others depend on the order they happen to run in.
    """
    database = tmp_path / "test.sqlite"
    previous = {
        key: os.environ.get(key)
        for key in ("DATABASE_URL", "SECRET_KEY", "SITECOPY_PASSWORD", "UPLOAD_FOLDER")
    }
    os.environ.update(
        DATABASE_URL=f"sqlite:///{database}",
        SECRET_KEY="test-only-secret-key",
        SITECOPY_PASSWORD=PASSWORD,
        # Uploads too: the default is a directory in the working tree, and the upload
        # test would leave a stray file in it on every run.
        UPLOAD_FOLDER=str(tmp_path / "uploads"),
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


def gallery_keys() -> list[str]:
    """The gallery's keys, which the template builds at runtime from the piece's slug.

    A literal scan cannot see `t(item.key ~ '.src')`, so they are declared here instead —
    and because this walks the same list the registry does, a piece that stops being
    rendered still cannot slip through unnoticed.
    """
    keys: list[str] = []
    for category in get_gallery():
        keys.append(category["title_key"])
        for item in category["items"]:
            keys += [f"{item['key']}.src", f"{item['key']}.alt"]
            if item["type"] == "video":
                keys.append(f"{item['key']}.poster")
    return keys


def test_every_key_is_rendered_and_every_rendered_key_exists() -> None:
    """No template asks for a key nobody declared, and no declared key goes unrendered."""
    assert check_templates(REGISTRY, "app", dynamic=gallery_keys()) == []


def test_the_registry_declares_exactly_the_gallery_that_exists() -> None:
    """The generated fields and app/content.py cannot drift: one is built from the other."""
    assert set(gallery_keys()) <= set(REGISTRY.fields)
    assert len(get_gallery()) == len(REGISTRY.groups_by_key["gallery"].sections)


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
    csrf = login(client)
    headers = {"X-Sitecopy-CSRF": csrf}

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

    client.post("/admin/content/publish", data={"_sitecopy_csrf": csrf})
    assert "Hacemos todo, en serio." in client.get("/").get_data(as_text=True)


def test_a_size_reaches_the_public_page(app: Flask) -> None:
    """With text sizes on, the rewrite must reach every visitor, not just an admin.

    A size is rendered by rewriting the finished response, so anything that compresses
    or rewrites the body has to be wired BEFORE SiteCopy. Without sizes that mistake was
    only visible to an admin in ``?edit=1``; with them on, every visitor would see the
    markers as empty boxes. This stages a real size and fetches the page as a visitor.
    """
    assert check_response_pipeline(app, "/", key="home.services.title") == []


def test_media_and_attribute_only_copy_offer_no_size(app: Flask) -> None:
    """A size wraps text in a span, so it is meaningless where no text is rendered.

    Media fields hold a location, and an alt or aria-label never becomes visible text —
    offering a size control on either is a button that silently does nothing.
    """
    not_resizable = {
        key for key, field in REGISTRY.fields.items() if not field.is_resizable
    }
    # Copy that never becomes visible text on its own: it lands in an attribute, or it
    # is only ever spliced into another string as a token. `global.tagline` is a token
    # too but the hero and the footer also render it directly, so it stays resizable.
    for key in (
        "home.meta.title",
        "home.meta.description",
        "home.lightbox.close",
        "home.hero.scroll_label",
        "home.hero.video",
        "home.hero.poster",
        "global.brand",
        "global.city",
        "global.email",
    ):
        assert key in not_resizable, f"{key} renders no text of its own to resize"
    assert "global.tagline" not in not_resizable
    for category in get_gallery():
        for item in category["items"]:
            assert f"{item['key']}.src" in not_resizable
            assert f"{item['key']}.alt" in not_resizable


def test_an_uploaded_image_is_served_without_the_responsive_variants(app: Flask) -> None:
    """A picture the editor uploads has no -400/-600 twins, so it gets no srcset.

    Pointing srcset at variants that were never generated is two 404s per image and a
    blank grid; the upload is served as it was uploaded instead.
    """
    from app.content import responsive_image

    with app.app_context():
        shipped = responsive_image("/static/assets/gallery/arte-01.webp")
        uploaded = responsive_image("/uploads/0123456789abcdef.webp")

    assert "400w" in shipped["srcset"] and "600w" in shipped["srcset"]
    assert re.fullmatch(r"/static/assets/gallery/arte-01-600\.webp\?v=\d+", shipped["src"])
    # An upload is already content-addressed, so it needs no stamp and has no variants.
    assert uploaded == {"src": "/uploads/0123456789abcdef.webp", "srcset": ""}


def test_every_static_media_url_carries_a_cache_stamp(app: Flask) -> None:
    """Static files are cached for a year, so every URL has to change when the file does.

    ``url_for`` stamps the ones it builds, but a value resolved from the registry never
    goes through it. Without a stamp of its own, replacing a shipped picture or clip at
    the same path in a deploy keeps serving the old bytes for up to a year.
    """
    html = app.test_client().get("/").get_data(as_text=True)
    served = re.findall(r'(?:src|poster|data-src)="(/static/[^"]*)"', html)
    assert served, "the page rendered no static media at all — the check proves nothing"
    unstamped = sorted({url for url in served if not re.search(r"\?v=\d+$", url)})
    assert unstamped == [], f"static media served without a cache stamp: {unstamped}"
    # And the stamp is on the responsive variants too, not just the plain src.
    assert re.search(r'srcset="/static/[^"]+\?v=\d+ 400w', html)


def test_the_public_page_has_no_editor_only_attributes(app: Flask) -> None:
    """The keys the editor needs on a picture are emitted for the editor only."""
    client = app.test_client()
    assert "data-ct-key-" not in client.get("/").get_data(as_text=True)

    login(client)
    edit = client.get("/?edit=1").get_data(as_text=True)
    assert 'data-ct-keys' in edit, "edit mode recorded no keys on any element"


def test_every_picture_is_editable_in_place(app: Flask) -> None:
    """The editor hangs "cambiar imagen" off an <img>/<video> carrying a media key.

    It looks for `img[data-ct-keys], video[data-ct-keys]`, so a key recorded on the
    surrounding <figure> instead would leave the piece with no control on the canvas —
    silently, and only in the editor, which no other test would notice.
    """
    client = app.test_client()
    login(client)
    edit = client.get("/?edit=1").get_data(as_text=True)

    carriers = len(re.findall(r"<(?:img|video)[^>]*\bdata-ct-keys=", edit))
    pieces = sum(len(category["items"]) for category in get_gallery())
    assert carriers == pieces + 1, "every gallery piece, plus the hero clip"


def test_a_changed_gallery_piece_reaches_the_public_page(app: Flask) -> None:
    """Publishing a new picture for a gallery piece swaps it, srcset included."""
    client = app.test_client()
    csrf = login(client)

    key = f"{get_gallery()[0]['items'][1]['key']}.src"
    saved = client.post(
        "/admin/content/save",
        json={"changes": {key: "/uploads/deadbeefdeadbeef.webp"}},
        headers={"X-Sitecopy-CSRF": csrf},
    )
    assert saved.status_code == 200, saved.get_data(as_text=True)
    assert saved.get_json()["ok"] is True
    client.post("/admin/content/publish", data={"_sitecopy_csrf": csrf})

    html = client.get("/").get_data(as_text=True)
    assert "/uploads/deadbeefdeadbeef.webp" in html
    # The replaced picture is gone, and took its stale srcset with it.
    assert "destacados-01-600.webp" not in html
    assert "destacados-01-400.webp" not in html


def test_an_upload_is_stored_and_served_back(app: Flask) -> None:
    """The upload path this site wires by hand: into UPLOAD_FOLDER, out via serve_upload.

    The library's default writes under ``static/``, which a rebuild wipes. This app points
    the store at the mounted volume instead, which only works if the route that serves it
    back agrees about the URL prefix — so check the round trip rather than just the store.

    This is the development half of :func:`app.factory.file_store`; deployed, uploads go to
    Vercel Blob instead (``tests/test_media_store.py``) because the filesystem is read-only
    there.
    """
    client = app.test_client()
    csrf = login(client)
    key = f"{get_gallery()[0]['items'][1]['key']}.src"

    # A one-pixel PNG. The endpoint sniffs the real type from the bytes, so the bytes
    # have to be a real PNG — a renamed text file is refused, which is the point.
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmM"
        "IQAAAABJRU5ErkJggg=="
    )
    uploaded = client.post(
        "/admin/content/upload",
        data={"key": key, "file": (io.BytesIO(png), "photo.png")},
        content_type="multipart/form-data",
        headers={"X-Sitecopy-CSRF": csrf},
    )
    assert uploaded.status_code == 200, uploaded.get_data(as_text=True)
    body = uploaded.get_json()
    assert body["ok"] is True and body["type"] == "image"

    url = body["url"]
    assert url.startswith("/uploads/"), f"stored outside the mounted volume: {url}"
    served = client.get(url)
    assert served.status_code == 200
    assert served.get_data() == png


def test_an_upload_that_is_not_really_an_image_is_refused(app: Flask) -> None:
    """The filename is not evidence: an HTML polyglot named .png is stored XSS."""
    client = app.test_client()
    csrf = login(client)
    refused = client.post(
        "/admin/content/upload",
        data={
            "key": f"{get_gallery()[0]['items'][1]['key']}.src",
            "file": (io.BytesIO(b"<html><script>alert(1)</script>"), "photo.png"),
        },
        content_type="multipart/form-data",
        headers={"X-Sitecopy-CSRF": csrf},
    )
    assert refused.status_code == 400
    assert refused.get_json()["ok"] is False


def test_the_editor_is_closed_to_the_public(app: Flask) -> None:
    """Preview and edit mode are gated on the admin session, not on a query string."""
    client = app.test_client()
    assert "<ct-t" not in client.get("/?edit=1").get_data(as_text=True)
    assert client.get("/admin/content/", follow_redirects=False).status_code in (301, 302)
