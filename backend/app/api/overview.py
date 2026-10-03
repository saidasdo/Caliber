"""GET /api/overview (SPEC section 5.1). All figures respect the replay clock (section 4):
incidents only count if dated on or before the replay date.
"""

import sqlite3
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query

from app.db import get_connection, rows_to_dicts
from app.engine.priority import compute_priority
from app.engine.replay import DEFAULT_REPLAY_DATE
from app.scope import RoleScope, get_role_scope
from app.visibility import redact_money

router = APIRouter()

# "Previous period" is not defined numerically in SPEC; a trailing 90-day window compared to
# the 90 days before it is used here and documented as an assumption.
PERIOD_DAYS = 90


def _period_bounds(replay_date: str) -> tuple[str, str, str]:
    end = date.fromisoformat(replay_date)
    start = end - timedelta(days=PERIOD_DAYS)
    prev_start = start - timedelta(days=PERIOD_DAYS)
    return prev_start.isoformat(), start.isoformat(), end.isoformat()


def _kpi_band(conn: sqlite3.Connection, replay_date: str) -> dict:
    prev_start, start, end = _period_bounds(replay_date)

    def window_sum(select: str, lo: str, hi: str):
        row = conn.execute(
            f"SELECT {select} FROM incidents WHERE date_of_occur > ? AND date_of_occur <= ?",
            (lo, hi),
        ).fetchone()
        return row[0] or 0

    current_incidents = window_sum("COUNT(*)", start, end)
    previous_incidents = window_sum("COUNT(*)", prev_start, start)
    current_downtime = window_sum("SUM(downtime_hrs)", start, end)
    previous_downtime = window_sum("SUM(downtime_hrs)", prev_start, start)
    current_loss = window_sum("SUM(total_loss_kusd)", start, end)
    previous_loss = window_sum("SUM(total_loss_kusd)", prev_start, start)

    open_statuses = ("RISK CLOSED", "RISK CANCELED")
    open_now = conn.execute(
        "SELECT COUNT(*) FROM incidents WHERE date_of_occur <= ? AND overall_status NOT IN (?, ?)",
        (end, *open_statuses),
    ).fetchone()[0]
    open_prev = conn.execute(
        "SELECT COUNT(*) FROM incidents WHERE date_of_occur <= ? AND overall_status NOT IN (?, ?)",
        (start, *open_statuses),
    ).fetchone()[0]

    priority_now = compute_priority(conn, end)
    priority_prev = compute_priority(conn, start)
    alarm_now = sum(1 for p in priority_now if p["health_status"] == "ALARM")
    alarm_prev = sum(1 for p in priority_prev if p["health_status"] == "ALARM")

    return {
        "incidents": {"value": current_incidents, "previous": previous_incidents},
        "downtime_hours": {"value": round(current_downtime, 1), "previous": round(previous_downtime, 1)},
        "loss_kusd": {"value": round(current_loss, 2), "previous": round(previous_loss, 2)},
        "open_follow_ups": {"value": open_now, "previous": open_prev},
        "equipment_in_alarm": {"value": alarm_now, "previous": alarm_prev},
        "period_days": PERIOD_DAYS,
    }


def _loss_by_plant(conn: sqlite3.Connection, replay_date: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT p.plant_code, p.has_sensor_equipment,
               COALESCE(SUM(i.total_loss_kusd), 0) AS loss_kusd,
               COALESCE(SUM(i.downtime_hrs), 0) AS downtime_hrs,
               COUNT(i.serial_no) AS incident_count
        FROM plants p
        LEFT JOIN incidents i ON i.plant_code = p.plant_code AND i.date_of_occur <= ?
        GROUP BY p.plant_code
        ORDER BY loss_kusd DESC
        """,
        (replay_date,),
    ).fetchall()
    return rows_to_dicts(rows)


def _heatmap(conn: sqlite3.Connection, replay_date: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT plant_code, month_year, COUNT(*) AS incident_count, SUM(total_loss_kusd) AS loss_kusd
        FROM incidents
        WHERE date_of_occur <= ?
        GROUP BY plant_code, month_year
        """,
        (replay_date,),
    ).fetchall()
    return rows_to_dicts(rows)


def _follow_up_pipeline(conn: sqlite3.Connection, replay_date: str) -> dict:
    rows = conn.execute(
        "SELECT overall_status, COUNT(*) FROM incidents WHERE date_of_occur <= ? GROUP BY overall_status",
        (replay_date,),
    ).fetchall()
    by_status = {status: count for status, count in rows}
    overdue = conn.execute(
        "SELECT COUNT(*) FROM incidents WHERE date_of_occur <= ? AND overall_status = 'RCA PROCESS' "
        "AND rca_due_date IS NOT NULL AND rca_due_date < ?",
        (replay_date, replay_date),
    ).fetchone()[0]
    return {"by_status": by_status, "rca_process_overdue": overdue}


@router.get("/overview")
def get_overview(
    replay_date: str = Query(DEFAULT_REPLAY_DATE),
    conn: sqlite3.Connection = Depends(get_connection),
    scope: RoleScope = Depends(get_role_scope),
):
    priority_queue = compute_priority(conn, replay_date)
    body = {
        "replay_date": replay_date,
        "kpi_band": _kpi_band(conn, replay_date),
        "priority_queue": priority_queue,
        "loss_by_plant": _loss_by_plant(conn, replay_date),
        "heatmap": _heatmap(conn, replay_date),
        "follow_up_pipeline": _follow_up_pipeline(conn, replay_date),
    }
    return redact_money(body, scope.role, scope.plant)
