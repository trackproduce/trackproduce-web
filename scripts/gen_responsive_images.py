"""Generate responsive image variants for the landing-page grids.

For each base image (given without extension) it writes downscaled WebP + JPEG
variants at the target widths, next to the originals, named `<base>-<width>.<ext>`.
Only widths smaller than the source are generated (never upscale).

Usage:
    python scripts/gen_responsive_images.py
"""

from __future__ import annotations

import os

from PIL import Image

STATIC = os.path.join(os.path.dirname(__file__), "..", "public", "static")

# EDIT for your project: the images flagged by `test_images_are_not_oversized`,
# as paths under public/static WITHOUT extension. These are card/grid images shown
# small but served at full resolution. Here: every still-image in the gallery
# grid (videos use posters and aren't <img>, so they don't trip the test).
BASES = [
    "assets/gallery/destacados-01",
    "assets/gallery/destacados-02",
    "assets/gallery/destacados-03",
    "assets/gallery/estudios-01",
    "assets/gallery/estudios-02",
    "assets/gallery/estudios-03",
    "assets/gallery/estudios-04",
    "assets/gallery/shows-01",
    "assets/gallery/shows-02",
    "assets/gallery/shows-03",
    "assets/gallery/shows-04",
    "assets/gallery/arte-01",
    "assets/gallery/arte-02",
    "assets/gallery/arte-03",
    "assets/gallery/arte-04",
    "assets/gallery/casting-01",
    "assets/gallery/casting-02",
    "assets/gallery/casting-03",
    "assets/gallery/campanas-01",
    "assets/gallery/campanas-02",
    "assets/gallery/campanas-03",
    "assets/gallery/eventos-01",
    "assets/gallery/eventos-02",
]

# Variant widths — pick from how the images are displayed (CSS px) so the browser
# serves ~1x/~2x without over-serving. 400/600 fit cards shown at ~270-365 CSS px.
# The oversized test flags natural > displayed * dpr * 2, so with accurate `sizes`
# the browser picks a variant well under the budget.
WIDTHS = [400, 600]


def _source(base: str) -> str:
    for ext in (".webp", ".jpg", ".jpeg", ".png"):
        path = os.path.join(STATIC, base + ext)
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"No source image for {base}")


def main() -> None:
    for base in BASES:
        src = _source(base)
        img = Image.open(src)
        for width in WIDTHS:
            if width >= img.width:
                continue
            height = round(img.height * width / img.width)
            resized = img.resize((width, height), Image.LANCZOS)
            # WebP-only: every gallery source is already WebP and the template's
            # srcset references the .webp variants, so a JPEG fallback would be
            # dead weight. Add one back if you ever need <picture> JPEG fallbacks.
            webp_out = os.path.join(STATIC, f"{base}-{width}.webp")
            resized.save(webp_out, "WEBP", quality=80, method=6)
            print(f"{base}-{width}: {width}x{height}")


if __name__ == "__main__":
    main()
