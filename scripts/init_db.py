"""Create the site's tables in a database, once.

The deployed app does not do this at boot: on Vercel every cold start would re-check a
schema that only ever changes on deploy (see ``auto_schema()`` in ``app/factory.py``).
So a fresh database — a new Neon branch, a restored backup — gets its tables from here.

Usage:
    DATABASE_URL=postgresql://…  python scripts/init_db.py

Safe to re-run: both steps create what is missing and leave what exists alone. Run it
after upgrading flask-sitecopy, which is when its tables can gain a column.
"""
from __future__ import annotations

import os
import sys

# Running a file inside scripts/ puts scripts/ on the path, not the repo root, so the
# ``app`` package would not import. Put the root first and it runs from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set — nothing to initialize.", file=sys.stderr)
        return 1

    # Force the bootstrap on: the whole point of this script is to run the DDL that the
    # app skips, and it may well be pointed at a deployed database from a laptop.
    os.environ["DB_AUTO_SCHEMA"] = "1"
    from sqlalchemy import inspect

    from app import app  # imported late: creating the app is what runs the DDL
    from app.factory import db

    with app.app_context():
        tables = sorted(inspect(db.engine).get_table_names())

    # A connection URL carries the password; print only what identifies the target.
    host = url.split("@")[-1].split("?")[0]
    print(f"Schema ready on {host}")
    print(f"Tables: {', '.join(tables) or '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
