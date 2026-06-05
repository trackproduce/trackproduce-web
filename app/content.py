"""Static site content: curated gallery grouped by category.

This is presentation data (no persistence), kept out of ``routes.py`` so route
handlers stay thin. Each category exposes a list of media items (images and
videos) already optimized for the web under ``static/assets/gallery/``.
"""
from __future__ import annotations

from typing import Literal, TypedDict


class MediaItem(TypedDict):
    """A single image or video shown in the gallery."""

    type: Literal["image", "video"]
    src: str
    poster: str
    width: int
    height: int
    alt: str


class Category(TypedDict):
    """A titled group of media items."""

    slug: str
    title: str
    items: list[MediaItem]


def _image(src: str, width: int, height: int, alt: str) -> MediaItem:
    return {"type": "image", "src": src, "poster": "", "width": width, "height": height, "alt": alt}


def _video(src: str, poster: str, width: int, height: int, alt: str) -> MediaItem:
    return {"type": "video", "src": src, "poster": poster, "width": width, "height": height, "alt": alt}


GALLERY: list[Category] = [
    {
        "slug": "destacados",
        "title": "Destacados",
        "items": [
            _video("assets/gallery/destacados-v1.mp4", "assets/gallery/destacados-v1-poster.webp", 1080, 720, "Silueta en luz roja — pieza cinematográfica"),
            _image("assets/gallery/destacados-01.webp", 1080, 1437, "Retrato cinematográfico en luz azul"),
            _image("assets/gallery/destacados-02.webp", 1440, 1800, "Artista en luz violeta"),
            _video("assets/gallery/destacados-v2.mp4", "assets/gallery/destacados-v2-poster.webp", 540, 360, "Rostro en luz cálida — pieza cinematográfica"),
            _image("assets/gallery/destacados-03.webp", 1440, 960, "Silueta cantando bajo un spotlight"),
        ],
    },
    {
        "slug": "estudios",
        "title": "Estudios & Equipos",
        "items": [
            _image("assets/gallery/estudios-01.webp", 1440, 1800, "Operadora en la consola de grabación"),
            _image("assets/gallery/estudios-02.webp", 1440, 1800, "Teclado y controladores en estudio"),
            _image("assets/gallery/estudios-03.webp", 1440, 1920, "Micrófono de estudio"),
            _image("assets/gallery/estudios-04.webp", 1440, 1920, "Sala de control y operadores"),
            _video("assets/gallery/estudios-v1.mp4", "assets/gallery/estudios-v1-poster.webp", 360, 480, "Sesión de grabación en estudio"),
        ],
    },
    {
        "slug": "shows",
        "title": "Shows en vivo",
        "items": [
            _image("assets/gallery/shows-01.webp", 1440, 1920, "Show en vivo — banda y público"),
            _image("assets/gallery/shows-02.webp", 1440, 1919, "Cantante en vivo"),
            _image("assets/gallery/shows-03.webp", 1440, 1919, "Banda en escenario"),
            _image("assets/gallery/shows-04.webp", 1440, 1919, "Guitarrista en vivo"),
            _video("assets/gallery/shows-v1.mp4", "assets/gallery/shows-v1-poster.webp", 720, 1280, "Detrás de cámara de un rodaje de Track"),
        ],
    },
    {
        "slug": "arte",
        "title": "Dirección de Arte",
        "items": [
            _image("assets/gallery/arte-01.webp", 1440, 1920, "Velas — ambiente cálido"),
            _image("assets/gallery/arte-02.webp", 1440, 1920, "Lounge iluminado en rojo"),
            _image("assets/gallery/arte-03.webp", 1440, 960, "Interior con lámpara cálida"),
            _image("assets/gallery/arte-04.webp", 960, 1260, "Set de dirección de arte — vestido rojo"),
        ],
    },
    {
        "slug": "casting",
        "title": "Casting & Moda",
        "items": [
            _image("assets/gallery/casting-01.webp", 1440, 1440, "Sesión de moda — grupo"),
            _image("assets/gallery/casting-02.webp", 1440, 1440, "Moda en estudio"),
            _image("assets/gallery/casting-03.webp", 1440, 1440, "Detrás de cámara — green screen"),
        ],
    },
    {
        "slug": "campanas",
        "title": "Campañas",
        "items": [
            _image("assets/gallery/campanas-01.webp", 1600, 2000, "Retrato de campaña"),
            _image("assets/gallery/campanas-02.webp", 1600, 2000, "Retrato de campaña"),
            _image("assets/gallery/campanas-03.webp", 1600, 2000, "Retrato de campaña"),
        ],
    },
    {
        "slug": "eventos",
        "title": "Eventos",
        "items": [
            _image("assets/gallery/eventos-01.webp", 1440, 1920, "Evento Halloween — público"),
            _image("assets/gallery/eventos-02.webp", 1440, 1920, "Evento — haz de luz azul"),
        ],
    },
]


def get_gallery() -> list[Category]:
    """Return the curated gallery grouped by category."""
    return GALLERY


# Real collaborators / clients, derived from the brand's published work.
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
    """Return the list of collaborators for the marquee."""
    return COLLABORATORS
