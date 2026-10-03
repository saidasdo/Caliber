"""GET /api/backtest (SPEC section 5.8)."""

import sqlite3

from fastapi import APIRouter, Depends

from app.db import get_connection
from app.engine.backtest import run_backtest
from app.scope import RoleScope, get_role_scope
from app.visibility import redact_money

router = APIRouter()


@router.get("/backtest")
def get_backtest(
    conn: sqlite3.Connection = Depends(get_connection),
    scope: RoleScope = Depends(get_role_scope),
):
    body = {"results": run_backtest(conn)}
    return redact_money(body, scope.role, scope.plant)
