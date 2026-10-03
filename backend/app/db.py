import sqlite3
from collections.abc import Iterator

from app.config import DB_PATH, SCHEMA_PATH


def get_connection() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency: one row-dict-capable connection per request.

    check_same_thread=False: FastAPI runs sync dependencies and sync path functions via
    anyio's threadpool, which does not guarantee the connection is opened and used on the
    same OS thread. Each request still gets its own connection (opened and closed here), so
    there is no concurrent cross-request sharing, which is what check_same_thread actually
    guards against.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]


def build_fresh_db() -> sqlite3.Connection:
    if DB_PATH.exists():
        DB_PATH.unlink()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    return conn


def insert_many(conn: sqlite3.Connection, table: str, rows: list[dict]) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in columns)
    col_list = ", ".join(columns)
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
    conn.executemany(sql, [tuple(row.get(c) for c in columns) for row in rows])
