"""GET /api/audit-log; POST .../role-switch, .../view-money (SPEC section 5.11:
"Log role switches and views of money values to audit_log.")
"""

import sqlite3

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.audit import write_audit_log
from app.db import get_connection, rows_to_dicts

router = APIRouter()


@router.get("/audit-log")
def list_audit_log(
    action_type: str | None = Query(None),
    limit: int = Query(200, le=1000),
    conn: sqlite3.Connection = Depends(get_connection),
):
    sql = "SELECT * FROM audit_log WHERE 1=1"
    params: list = []
    if action_type:
        sql += " AND action_type = ?"
        params.append(action_type)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    return {"results": rows_to_dicts(conn.execute(sql, params).fetchall())}


class RoleSwitchEvent(BaseModel):
    from_role: str | None = None
    to_role: str
    selected_plant: str | None = None


@router.post("/audit-log/role-switch")
def log_role_switch(body: RoleSwitchEvent, conn: sqlite3.Connection = Depends(get_connection)):
    write_audit_log(
        conn,
        "role_switch",
        {"from_role": body.from_role, "to_role": body.to_role, "selected_plant": body.selected_plant},
        body.to_role,
    )
    conn.commit()
    return {"status": "logged"}


class ViewMoneyEvent(BaseModel):
    actor_role: str
    page: str
    plant_code: str | None = None


@router.post("/audit-log/view-money")
def log_view_money(body: ViewMoneyEvent, conn: sqlite3.Connection = Depends(get_connection)):
    write_audit_log(
        conn,
        "view_money",
        {"page": body.page, "plant_code": body.plant_code},
        body.actor_role,
    )
    conn.commit()
    return {"status": "logged"}
