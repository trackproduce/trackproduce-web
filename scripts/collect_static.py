"""Copy ``app/static`` to ``public/static`` so Vercel's CDN serves it.

Vercel serves whatever is in ``public/`` from its CDN, which is where a static file
should be answered from — but it also strips that directory out of the function bundle,
and ``app/content.py`` reads those same files at render time to decide which responsive
variants exist and to stamp each URL with the file's mtime. Neither location alone can
do both jobs, so the files live in the package (bundled with the code, as any other
package data) and this build step publishes a copy for the edge.

Run by the Build Command (``vercel.json``), which is why ``public/`` is generated rather
than committed. Nothing outside a Vercel build needs it: locally and in Docker, Flask
serves ``app/static`` itself.
"""
from __future__ import annotations

import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "app", "static")
TARGET = os.path.join(ROOT, "public", "static")


def main() -> None:
    # Copy onto a clean directory: a stale file left from an earlier build would keep
    # being served, and the CDN would hold it for a year.
    shutil.rmtree(TARGET, ignore_errors=True)
    os.makedirs(os.path.dirname(TARGET), exist_ok=True)
    shutil.copytree(SOURCE, TARGET)

    files = sum(len(names) for _, _, names in os.walk(TARGET))
    print(f"Collected {files} static files into public/static")


if __name__ == "__main__":
    main()
