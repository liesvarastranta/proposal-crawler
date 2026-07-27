import sqlite3
from pathlib import Path

_connection: sqlite3.Connection | None = None

SCHEMA_PATH = Path(__file__).parent.parent.parent / "db" / "schema.sql"


def init_db(db_path: str) -> sqlite3.Connection:
    global _connection
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    schema = SCHEMA_PATH.read_text()
    conn.executescript(schema)
    conn.commit()
    _connection = conn
    return conn


def get_db() -> sqlite3.Connection:
    if _connection is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _connection
