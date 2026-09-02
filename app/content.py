"""Static site content: the shape of the gallery, and the copy it ships with.

This is presentation data (no persistence), kept out of ``routes.py`` so route
handlers stay thin. Each category exposes a list of media items (images and
videos) already optimized for the web under ``static/assets/gallery/``.

What lives here is the **structure**: how many pieces there are, in what order, in
which category, and at what aspect ratio. The *values* — which file each piece points
at, its description, the category's name — are registry defaults: ``app/registry.py``
builds one editable field per item from this list, so the content editor can swap a
picture or a clip without a deploy. Add a piece here and it becomes editable on the
next boot; the keys are derived from the category slug and the item's position.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal, TypedDict

from flask import current_app

# Flask's default ``static_url_path``; ``create_app`` checks the app still uses it.
STATIC_PREFIX = "/static"


class MediaItem(TypedDict):
    """A single image or video shown in the gallery."""

    type: Literal["image", "video"]
    key: str
    src: str
    poster: str
    width: int
    height: int
    alt: str


class Category(TypedDict):
    """A titled group of media items."""

    slug: str
    title: str
    title_key: str
    items: list[MediaItem]


def _image(src: str, width: int, height: int, alt: str) -> MediaItem:
    return {"type": "image", "key": "", "src": src, "poster": "", "width": width, "height": height, "alt": alt}


def _video(src: str, poster: str, width: int, height: int, alt: str) -> MediaItem:
    return {"type": "video", "key": "", "src": src, "poster": poster, "width": width, "height": height, "alt": alt}


def _category(slug: str, title: str, items: list[MediaItem]) -> Category:
    """A category, with the registry keys its pieces are edited through.

    Keys are derived from the slug and the piece's position, so adding a picture here
    is all it takes for the editor to offer it — there is no second list to keep in
    step. The flip side is that keys are positional: inserting a piece in the MIDDLE
    of a category shifts every key below it onto the previous piece's overrides. Append
    at the end, or migrate the rows.
    """
    for position, item in enumerate(items, start=1):
        item["key"] = f"gallery.{slug}.{position:02d}"
    return {"slug": slug, "title": title, "title_key": f"gallery.{slug}.title", "items": items}


GALLERY: list[Category] = [
    _category("destacados", "Destacados", [
        _video("assets/gallery/destacados-v1.mp4", "assets/gallery/destacados-v1-poster.webp", 1080, 720, "Silueta en luz roja — pieza cinematográfica"),
        _image("assets/gallery/destacados-01.webp", 1080, 1437, "Retrato cinematográfico en luz azul"),
        _image("assets/gallery/destacados-02.webp", 1440, 1800, "Artista en luz violeta"),
        _video("assets/gallery/destacados-v2.mp4", "assets/gallery/destacados-v2-poster.webp", 540, 360, "Rostro en luz cálida — pieza cinematográfica"),
        _image("assets/gallery/destacados-03.webp", 1440, 960, "Silueta cantando bajo un spotlight"),
    ]),
    _category("estudios", "Estudios & Equipos", [
        _image("assets/gallery/estudios-01.webp", 1440, 1800, "Operadora en la consola de grabación"),
        _image("assets/gallery/estudios-02.webp", 1440, 1800, "Teclado y controladores en estudio"),
        _image("assets/gallery/estudios-03.webp", 1440, 1920, "Micrófono de estudio"),
        _image("assets/gallery/estudios-04.webp", 1440, 1920, "Sala de control y operadores"),
        _video("assets/gallery/estudios-v1.mp4", "assets/gallery/estudios-v1-poster.webp", 360, 480, "Sesión de grabación en estudio"),
    ]),
    _category("shows", "Shows en vivo", [
        _image("assets/gallery/shows-01.webp", 1440, 1920, "Show en vivo — banda y público"),
        _image("assets/gallery/shows-02.webp", 1440, 1919, "Cantante en vivo"),
        _image("assets/gallery/shows-03.webp", 1440, 1919, "Banda en escenario"),
        _image("assets/gallery/shows-04.webp", 1440, 1919, "Guitarrista en vivo"),
        _video("assets/gallery/shows-v1.mp4", "assets/gallery/shows-v1-poster.webp", 720, 1280, "Detrás de cámara de un rodaje de Track"),
    ]),
    _category("arte", "Dirección de Arte", [
        _image("assets/gallery/arte-01.webp", 1440, 1920, "Velas — ambiente cálido"),
        _image("assets/gallery/arte-02.webp", 1440, 1920, "Lounge iluminado en rojo"),
        _image("assets/gallery/arte-03.webp", 1440, 960, "Interior con lámpara cálida"),
        _image("assets/gallery/arte-04.webp", 960, 1260, "Set de dirección de arte — vestido rojo"),
    ]),
    _category("casting", "Casting & Moda", [
        _image("assets/gallery/casting-01.webp", 1440, 1440, "Sesión de moda — grupo"),
        _image("assets/gallery/casting-02.webp", 1440, 1440, "Moda en estudio"),
        _image("assets/gallery/casting-03.webp", 1440, 1440, "Detrás de cámara — green screen"),
    ]),
    _category("campanas", "Campañas", [
        _image("assets/gallery/campanas-01.webp", 1600, 2000, "Retrato de campaña"),
        _image("assets/gallery/campanas-02.webp", 1600, 2000, "Retrato de campaña"),
        _image("assets/gallery/campanas-03.webp", 1600, 2000, "Retrato de campaña"),
    ]),
    _category("eventos", "Eventos", [
        _image("assets/gallery/eventos-01.webp", 1440, 1920, "Evento Halloween — público"),
        _image("assets/gallery/eventos-02.webp", 1440, 1920, "Evento — haz de luz azul"),
    ]),
]


def get_gallery() -> list[Category]:
    """Return the curated gallery grouped by category."""
    return GALLERY


def static_url(src: str) -> str:
    """The public URL of a file under ``static/``, as a registry default.

    Registry defaults are plain strings built at import time, with no application to
    ask, so the prefix is a constant. ``create_app`` asserts it still matches the app's
    real ``static_url_path``, since a mismatch would 404 every gallery piece at once.
    """
    return f"{STATIC_PREFIX}/{src}"


@lru_cache(maxsize=512)
def _variants(src: str, static_folder: str) -> tuple[str, str] | None:
    """``(src, srcset)`` for an image with responsive variants on disk, else None."""
    prefix = f"{STATIC_PREFIX}/"
    if not src.startswith(prefix):
        return None
    base = src[len(prefix):].rsplit(".", 1)[0]
    names = {width: f"{base}-{width}.webp" for width in (400, 600)}
    if not all(os.path.isfile(os.path.join(static_folder, name)) for name in names.values()):
        return None
    urls = {width: f"{prefix}{name}" for width, name in names.items()}
    return urls[600], f"{urls[400]} 400w, {urls[600]} 600w"


def responsive_image(src: str) -> dict[str, str]:
    """How to render a gallery image: its responsive variants when they exist.

    The pre-generated ``-400``/``-600`` webp variants (``scripts/gen_responsive_images.py``)
    only exist for the files that ship with the repo. A picture the content editor
    uploads has none, so it is served as it was uploaded rather than through a ``srcset``
    pointing at two URLs that would 404.
    """
    found = _variants(src, current_app.static_folder or "")
    return {"src": src, "srcset": ""} if found is None else {"src": found[0], "srcset": found[1]}


# Real collaborators / clients, derived from the brand's published work.
#
# This list is the *default* of the ``home.marquee.items`` registry field (see
# ``app/registry.py``): the marquee renders whatever the content editor has published,
# falling back to exactly these names while there is no override.
COLLABORATORS: list[str] = [
    "Lourdes Annoni",
    "Comuna 15",
    "DJ O Time",
    "Nacho Q",
    "Majo Chicar",
    "Foxes Music Group",
    "Manfiu",
    "Eve Faguaga",
    "Victtoria Luna",
    "Joyze",
    "Doble Vara",
    "Nahuel Villarreal",
]


def get_collaborators() -> list[str]:
    """Return the collaborators the marquee falls back to with no override."""
    return COLLABORATORS
