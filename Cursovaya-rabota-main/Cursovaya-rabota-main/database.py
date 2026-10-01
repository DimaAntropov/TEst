import sqlite3
from pathlib import Path

from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
            timeout=10,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA busy_timeout = 10000")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    schema = Path(current_app.root_path, "schema.sql").read_text(encoding="utf-8")
    db.executescript(schema)

    # Простая миграция для баз, созданных предыдущими версиями проекта.
    user_columns = {row["name"] for row in db.execute("PRAGMA table_info(users)")}
    if "is_active" not in user_columns:
        db.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
    db.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
