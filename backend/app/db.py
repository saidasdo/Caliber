import os
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


# The build is written beside the live database and swapped in only when complete (see
# publish_built_db). Rebuilding the live file in place let a request made during a reset read a
# half-built database, which is the intermittent reset-test failure this fixes.
BUILD_PATH = DB_PATH.with_name(DB_PATH.stem + ".building.sqlite")


def build_fresh_db() -> sqlite3.Connection:
    if BUILD_PATH.exists():
        BUILD_PATH.unlink()
    BUILD_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(BUILD_PATH)
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    return conn


def publish_built_db() -> None:
    """Move the finished build over the live database in one step."""
    os.replace(BUILD_PATH, DB_PATH)


def insert_many(conn: sqlite3.Connection, table: str, rows: list[dict]) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in columns)
    col_list = ", ".join(columns)
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
    conn.executemany(sql, [tuple(row.get(c) for c in columns) for row in rows])
