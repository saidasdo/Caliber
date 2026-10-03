"""GET /api/kpi-dictionary (SPEC section 5.9)."""

import sqlite3

from fastapi import APIRouter, Depends

from app.db import get_connection, rows_to_dicts

router = APIRouter()


@router.get("/kpi-dictionary")
def get_kpi_dictionary(conn: sqlite3.Connection = Depends(get_connection)):
    return {"results": rows_to_dicts(conn.execute("SELECT * FROM kpi_dictionary ORDER BY kpi_name").fetchall())}
