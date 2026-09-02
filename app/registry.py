"""The catalogue of editable strings: every user-facing text the site renders.

This is the content model for ``flask-sitecopy``. Each string the templates render
through ``t('…')`` is declared here once, with a human label and the default the code
ships with. The database stores *overrides only*, so a fresh install renders exactly
these defaults — no seeding step, and adding copy never needs a migration.

Adding a new text is two lines: a :class:`~sitecopy.TextField` here and a ``t('<key>')``
in the template. ``tests/test_content_registry.py`` fails if one of them is missing.

The gallery is the one group built rather than typed out: ``app/content.py`` owns the
*shape* (how many pieces, in what order, at what aspect ratio) and :func:`_gallery_group`
turns each piece into the fields that edit it — the file it points at, and its
description. Adding a picture there is all it takes for the editor to offer it.
"""
from __future__ import annotations

from sitecopy import Group, Registry, Section, TextField

from app.content import get_collaborators, get_gallery, static_url

# --- Global: brand, links, and the words reused across the page ----------------------

GLOBAL = Group(
    key="global",
    title="Marca y redes",
    description="Textos que se reutilizan en todo el sitio.",
    preview_path="/",
    category="Global",
    sections=(
        Section(
            key="brand",
            title="Marca",
            note=(
                "El nombre se puede escribir dentro de cualquier otro texto como "
                "{brand}, la ciudad como {city} y la bajada como {tagline}."
            ),
            fields=(
                # A token field never renders on its own — it is spliced into other
                # strings — so there is no element of its own to resize. Same for the
                # city; the mail only ever lands inside a `mailto:`.
                TextField("global.brand", "Nombre de la marca", "Track Produce",
                          max_length=60, resizable=False),
                TextField(
                    "global.tagline",
                    "Bajada de la marca",
                    "Productora audiovisual & musical",
                    max_length=120,
                ),
                TextField("global.city", "Ciudad", "Buenos Aires", max_length=60,
                          resizable=False),
            ),
        ),
        Section(
            key="wordmark",
            title="Logo",
            note=(
                "El logo se dibuja en dos partes: la segunda se pinta con el color de "
                "marca. Es el lettering; el nombre que se usa dentro de los textos es "
                "«Nombre de la marca», arriba."
            ),
            fields=(
                TextField("global.wordmark.start", "Logo — primera parte", "Track", max_length=30),
                TextField("global.wordmark.end", "Logo — segunda parte", "Produce", max_length=30),
            ),
        ),
        Section(
            key="links",
            title="Contacto y redes",
            fields=(
                TextField(
                    "global.instagram_url",
                    "Link de Instagram",
                    "https://www.instagram.com/trackproduce/",
                    type="url",
                ),
                TextField("global.instagram_handle", "Usuario de Instagram", "@trackproduce"),
                # A `line`, not a `url`: the url type validates http(s) and refuses a
                # bare mailto:, and this value is spliced into `mailto:` in the template.
                TextField("global.email", "Casilla de contacto", "hola@trackproduce.com",
                          resizable=False),
            ),
        ),
    ),
)

# --- Inicio: the single public page --------------------------------------------------

HOME = Group(
    key="home",
    title="Inicio",
    description="La única página del sitio, de arriba a abajo.",
    preview_path="/",
    category="Sitio",
    sections=(
        Section(
            key="nav",
            title="Menú",
            note="Estos tres nombres se usan en el menú, en los títulos de sección y en el pie.",
            fields=(
                TextField("home.nav.services", "Sección 01", "Servicios", max_length=40),
                TextField("home.nav.work", "Sección 02", "Trabajo", max_length=40),
                TextField("home.nav.contact", "Sección 03", "Contacto", max_length=40),
                TextField(
                    "home.nav.open_label",
                    "Botón del menú, cerrado (lectores de pantalla)",
                    "Abrir menú",
                    resizable=False,
                ),
                TextField(
                    "home.nav.close_label",
                    "Botón del menú, abierto (lectores de pantalla)",
                    "Cerrar menú",
                    resizable=False,
                ),
            ),
        ),
        Section(
            key="hero",
            title="Portada",
            note="Lo primero que se ve al entrar, sobre el video de fondo.",
            fields=(
                TextField(
                    "home.hero.subtitle",
                    "Bajada",
                    "Creamos, grabamos y producimos. Desde la idea hasta el resultado "
                    "final, en {city}.",
                    type="text",
                ),
                TextField("home.hero.cta_primary", "Botón principal", "Ver el trabajo"),
                TextField("home.hero.cta_secondary", "Botón secundario", "Contacto"),
                TextField(
                    "home.hero.video",
                    "Video de fondo",
                    "/static/assets/gallery/hero-bg.mp4",
                    type="video",
                    hint="Subí un mp4/webm o pegá un link. Conviene que sea corto y liviano.",
                ),
                TextField(
                    "home.hero.poster",
                    "Imagen mientras carga el video",
                    "/static/assets/gallery/hero-bg-poster.webp",
                    type="image",
                    hint="Se ve durante el primer instante, antes de que arranque el video.",
                ),
                TextField(
                    "home.hero.scroll_label",
                    "Flecha para bajar (lectores de pantalla)",
                    "Bajar",
                    resizable=False,
                ),
            ),
        ),
        Section(
            key="marquee",
            title="Colaboradores",
            note="La tira que se desplaza debajo de la portada. Un nombre por línea.",
            fields=(
                TextField(
                    "home.marquee.items",
                    "Artistas y marcas, uno por línea",
                    "\n".join(get_collaborators()),
                    type="lines",
                ),
                TextField(
                    "home.marquee.label",
                    "Nombre de la tira (lectores de pantalla)",
                    "Artistas y marcas con los que trabajamos",
                    resizable=False,
                ),
            ),
        ),
        Section(
            key="services",
            title="Servicios",
            note="El título de la sección sale de «Sección 01», en Menú.",
            fields=(
                TextField("home.services.title", "Título", "Hacemos casi todo."),
                TextField("home.services.item1.title", "Servicio 01 — título", "Producción audiovisual"),
                TextField(
                    "home.services.item1.text",
                    "Servicio 01 — texto",
                    "Videoclips, publicidades y contenido de marca de principio a fin.",
                    type="text",
                ),
                TextField("home.services.item2.title", "Servicio 02 — título", "Estudios de grabación"),
                TextField(
                    "home.services.item2.text",
                    "Servicio 02 — texto",
                    "Espacios de música, foto, stream y podcast equipados y adaptables.",
                    type="text",
                ),
                TextField("home.services.item3.title", "Servicio 03 — título", "Dirección de arte"),
                TextField(
                    "home.services.item3.text",
                    "Servicio 03 — texto",
                    "Ambientación y puesta en escena para que cada idea encuentre forma.",
                    type="text",
                ),
                TextField("home.services.item4.title", "Servicio 04 — título", "Shows & eventos"),
                TextField(
                    "home.services.item4.text",
                    "Servicio 04 — texto",
                    "Producción integral de shows en vivo y eventos temáticos.",
                    type="text",
                ),
            ),
        ),
        Section(
            key="work",
            title="Trabajo",
            note="Las piezas y los nombres de las categorías se editan en «Galería».",
            fields=(
                TextField("home.work.title", "Título", "Una selección."),
                TextField("home.work.link", "Link a Instagram", "Ver más en Instagram"),
                TextField("home.work.filter_all", "Filtro «todo»", "Todo", max_length=30),
                TextField(
                    "home.work.filters_label",
                    "Nombre de los filtros (lectores de pantalla)",
                    "Filtrar trabajos",
                    resizable=False,
                ),
            ),
        ),
        Section(
            key="contact",
            title="Contacto",
            fields=(
                TextField(
                    "home.contact.title",
                    "Título",
                    "¿Tenés un proyecto<br>en mente?",
                    type="rich",
                    hint="Se permite un salto de línea para partir el título en dos.",
                ),
                TextField(
                    "home.contact.text",
                    "Texto",
                    "Contanos tu idea y la hacemos realidad. Track nunca para.",
                    type="text",
                ),
                TextField("home.contact.cta_email", "Botón de mail", "Escribinos"),
            ),
        ),
        Section(
            key="footer",
            title="Pie de página",
            fields=(
                TextField("home.footer.instagram", "Link a Instagram", "Instagram"),
                TextField("home.footer.note", "Línea de copyright", "© {year} {brand} · {city}"),
            ),
        ),
        Section(
            key="lightbox",
            title="Visor de imágenes",
            note="Los botones del visor que se abre al tocar una pieza. No se leen en pantalla.",
            fields=(
                TextField("home.lightbox.close", "Cerrar", "Cerrar", resizable=False),
                TextField("home.lightbox.prev", "Anterior", "Anterior", resizable=False),
                TextField("home.lightbox.next", "Siguiente", "Siguiente", resizable=False),
            ),
        ),
        Section(
            key="meta",
            title="Buscadores y redes",
            note="Lo que ve Google y lo que aparece al compartir el link. No se ve en la página.",
            fields=(
                TextField(
                    "home.meta.title",
                    "Título en Google",
                    "{brand} — Productora audiovisual y musical",
                    max_length=120,
                    resizable=False,
                ),
                TextField(
                    "home.meta.description",
                    "Descripción en Google",
                    "{brand} — productora audiovisual y musical en {city}. Videoclips, "
                    "estudios de grabación, dirección de arte, shows en vivo y eventos.",
                    type="text",
                    max_length=320,
                    resizable=False,
                ),
                TextField(
                    "home.meta.image_alt",
                    "Descripción de la imagen que se comparte",
                    "{brand} — productora audiovisual y musical",
                    resizable=False,
                ),
            ),
        ),
    ),
)


# --- Galería: one field per piece, built from the list in app/content.py -------------

UPLOAD_HINT = (
    "Subí un archivo o pegá un link. La pieza se recorta al alto y ancho que ya tiene "
    "en la grilla, así que conviene una proporción parecida a la actual."
)


def _piece_fields(item: dict, position: int) -> list[TextField]:
    """The fields that edit one gallery piece: the file it points at, and its description."""
    label = f"Pieza {position:02d}"
    fields: list[TextField] = []
    if item["type"] == "video":
        fields.append(
            TextField(f"{item['key']}.src", f"{label} — video", static_url(item["src"]),
                      type="video", hint=UPLOAD_HINT)
        )
        fields.append(
            TextField(f"{item['key']}.poster", f"{label} — imagen mientras carga",
                      static_url(item["poster"]), type="image",
                      hint="Se ve en la grilla hasta que el video arranca.")
        )
    else:
        fields.append(
            TextField(f"{item['key']}.src", f"{label} — imagen", static_url(item["src"]),
                      type="image", hint=UPLOAD_HINT)
        )
    fields.append(
        # Lands in `alt` and `aria-label` only, so there is no text on the page to resize.
        TextField(f"{item['key']}.alt", f"{label} — descripción", item["alt"],
                  resizable=False,
                  hint="Lo que lee quien no ve la imagen, y lo que muestra el visor.")
    )
    return fields


def _gallery_group() -> Group:
    """Every piece of the gallery, one section per category.

    Derived from ``app/content.py`` rather than typed out here: that list is where a
    piece is added or removed, and this walks it so the two can never disagree about
    how many pieces there are.
    """
    sections = tuple(
        Section(
            key=category["slug"],
            title=category["title"],
            note="Tocá una pieza en el editor visual para cambiarla en el lugar.",
            fields=(
                TextField(category["title_key"], "Nombre de la categoría",
                          category["title"], max_length=60),
                *(field
                  for position, item in enumerate(category["items"], start=1)
                  for field in _piece_fields(item, position)),
            ),
        )
        for category in get_gallery()
    )
    return Group(
        key="gallery",
        title="Galería",
        description="Las piezas de la sección Trabajo, por categoría.",
        preview_path="/",
        category="Sitio",
        icon="◲",
        sections=sections,
    )


GALLERY_GROUP: Group = _gallery_group()


REGISTRY: Registry = Registry(
    groups=(HOME, GALLERY_GROUP, GLOBAL),
    # Order matters: each token may use the ones declared before it. None of these
    # mention another today, but brand-first keeps that door open. {year} comes free.
    tokens=("global.brand", "global.city", "global.tagline"),
)
