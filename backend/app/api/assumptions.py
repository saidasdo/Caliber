"""GET /api/assumptions (SPEC section 1: "every assumption is documented")."""

import sqlite3

from fastapi import APIRouter, Depends, Query

from app.db import get_connection, rows_to_dicts

router = APIRouter()


@router.get("/assumptions")
def list_assumptions(
    area: str | None = Query(None),
    conn: sqlite3.Connection = Depends(get_connection),
):
    sql = "SELECT * FROM assumptions"
    params: list = []
    if area:
        sql += " WHERE area = ?"
        params.append(area)
    sql += " ORDER BY id"
    return {"results": rows_to_dicts(conn.execute(sql, params).fetchall())}
