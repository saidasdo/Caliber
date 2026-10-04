"""GET /api/overview (SPEC section 5.1). All figures respect the replay clock (section 4):
incidents only count if dated on or before the replay date.
"""

import sqlite3
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query

from app.db import get_connection, rows_to_dicts
from app.engine.energy_proxy import get_emission, motor_load_week
from app.engine.gauges import compute_gauges
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

    previous_date = (date.fromisoformat(replay_date) - timedelta(days=7)).isoformat()
    emission_now, emission_rows = _emission_breakdown(conn, replay_date)
    _, emission_prev_rows = _emission_breakdown(conn, previous_date)
    # Compare like with like: only machines with data in both weeks, or the change is a coverage gap.
    both = {r["equipment_tag"] for r in emission_rows} & {r["equipment_tag"] for r in emission_prev_rows}
    emission_rows = [r for r in emission_rows if r["equipment_tag"] in both]
    emission_now = round(sum(r["week_kg"] for r in emission_rows), 1) if emission_rows else None
    emission_prev = round(sum(r["week_kg"] for r in emission_prev_rows if r["equipment_tag"] in both), 1) if both else None

    return {
        "production_vs_normal": _production_vs_normal_kpi(conn, replay_date),
        "energy_proxy": _energy_proxy_kpi(conn, replay_date),
        "emission_kg": {"value": emission_now, "previous": emission_prev, "breakdown": emission_rows},
        "incidents": {"value": current_incidents, "previous": previous_incidents},
        "downtime_hours": {"value": round(current_downtime, 1), "previous": round(previous_downtime, 1)},
        "loss_kusd": {"value": round(current_loss, 2), "previous": round(previous_loss, 2)},
        "open_follow_ups": {"value": open_now, "previous": open_prev},
        "equipment_in_alarm": {"value": alarm_now, "previous": alarm_prev},
        "period_days": PERIOD_DAYS,
    }


def _production_vs_normal_kpi(conn: sqlite3.Connection, replay_date: str) -> dict:
    """Average production vs normal (PLANT_RATE vs the equipment's normal ON-hour rate) across the
    equipment with hourly data on the replay date. Value is None (shown as "No hourly data") when
    none has hourly data on that date."""
    tags = [row[0] for row in conn.execute("SELECT tag FROM equipment WHERE has_sensor_data = 1 ORDER BY tag")]
    breakdown = []
    for tag in tags:
        plant = conn.execute("SELECT plant_code FROM equipment WHERE tag = ?", (tag,)).fetchone()[0]
        now = compute_gauges(conn, tag, replay_date)["production_vs_normal"]
        if not now["data_available"]:
            continue
        previous_date = (date.fromisoformat(replay_date) - timedelta(days=7)).isoformat()
        previous = compute_gauges(conn, tag, previous_date)["production_vs_normal"]
        breakdown.append(
            {
                "equipment_tag": tag,
                "plant_code": plant,
                "value": now["value"],
                "previous": previous["value"],
                "baseline_plant_rate": now.get("baseline"),
            }
        )
    if not breakdown:
        return {"value": None, "previous": None, "count": 0, "breakdown": [], "message": "No hourly data"}
    value = round(sum(b["value"] for b in breakdown) / len(breakdown), 1)
    previous_values = [b["previous"] for b in breakdown if b["previous"] is not None]
    previous = round(sum(previous_values) / len(previous_values), 1) if previous_values else None
    return {"value": value, "previous": previous, "count": len(breakdown), "breakdown": breakdown, "message": None}


def _energy_proxy_kpi(conn: sqlite3.Connection, replay_date: str) -> dict:
    """Total motor load index for the replay week vs the week before, with the direction of the
    7-day forecast against the replay week."""
    tags = [row[0] for row in conn.execute("SELECT tag FROM equipment WHERE has_sensor_data = 1 ORDER BY tag")]
    breakdown = []
    for tag in tags:
        plant = conn.execute("SELECT plant_code FROM equipment WHERE tag = ?", (tag,)).fetchone()[0]
        week = motor_load_week(conn, tag, replay_date)
        if week["week"] is None:
            continue
        breakdown.append({"equipment_tag": tag, "plant_code": plant, **week})
    if not breakdown:
        return {"value": None, "previous": None, "forecast_next_7_days": None, "forecast_direction": None,
                "breakdown": [], "message": "No motor current data"}
    # Compare like with like: the totals and the change use only machines with data in both weeks.
    both = [b for b in breakdown if b["previous_week"] is not None]
    week_total = round(sum(b["week"] for b in both), 2) if both else None
    previous_total = round(sum(b["previous_week"] for b in both), 2) if both else None
    forecast_values = [b["forecast_next_7_days"] for b in both if b["forecast_next_7_days"] is not None]
    forecast_total = round(sum(forecast_values), 2) if forecast_values else None
    from app.engine.energy_proxy import _direction

    return {
        "value": week_total,
        "previous": previous_total,
        "forecast_next_7_days": forecast_total,
        "forecast_direction": _direction(forecast_total, week_total),
        "breakdown": breakdown,
        "message": None,
    }


def _emission_week_kg(conn: sqlite3.Connection, as_of: str) -> float | None:
    """Sum of the 7-day CO2e estimate over the motor-driven equipment (heat exchangers excluded)."""
    return _emission_breakdown(conn, as_of)[0]


def _emission_breakdown(conn: sqlite3.Connection, as_of: str) -> tuple[float | None, list[dict]]:
    tags = [row[0] for row in conn.execute("SELECT tag FROM equipment WHERE has_sensor_data = 1 ORDER BY tag").fetchall()]
    rows = []
    for tag in tags:
        emission = get_emission(conn, tag, as_of)
        if emission["week_kg"] is None:
            continue
        plant = conn.execute("SELECT plant_code FROM equipment WHERE tag = ?", (tag,)).fetchone()[0]
        rows.append({"equipment_tag": tag, "plant_code": plant, "week_kg": emission["week_kg"], "today_kg": emission["today_kg"]})
    total = round(sum(r["week_kg"] for r in rows), 1) if rows else None
    return total, rows


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


def _action_statuses_by_tag(conn: sqlite3.Connection, replay_date: str) -> dict[str, set]:
    """Statuses of the actions each machine has, among those known on the replay date."""
    by_tag: dict[str, set] = {}
    rows = conn.execute(
        "SELECT equipment_tag, status FROM actions "
        "WHERE equipment_tag IS NOT NULL AND (as_of_date IS NULL OR as_of_date <= ?)",
        (replay_date,),
    ).fetchall()
    for tag, status in rows:
        by_tag.setdefault(tag, set()).add(status)
    return by_tag


def _action_status_label(statuses: set) -> str:
    """Plain label for the Needs attention list: the most advanced open state wins."""
    if "Proposed" in statuses:
        return "Proposed"
    if "In progress" in statuses:
        return "In progress"
    if "Open" in statuses:
        return "Open"
    return "No owner yet"


@router.get("/overview")
def get_overview(
    replay_date: str = Query(DEFAULT_REPLAY_DATE),
    conn: sqlite3.Connection = Depends(get_connection),
    scope: RoleScope = Depends(get_role_scope),
):
    priority_queue = compute_priority(conn, replay_date)
    action_statuses = _action_statuses_by_tag(conn, replay_date)
    for row in priority_queue:
        row["action_status"] = _action_status_label(action_statuses.get(row["equipment_tag"], set()))
    body = {
        "replay_date": replay_date,
        "kpi_band": _kpi_band(conn, replay_date),
        "priority_queue": priority_queue,
        "follow_up_health": {
            "awaiting_approval": conn.execute(
                "SELECT COUNT(*) FROM actions WHERE status = 'Proposed' AND (as_of_date IS NULL OR as_of_date <= ?)",
                (replay_date,),
            ).fetchone()[0],
        },
        "loss_by_plant": _loss_by_plant(conn, replay_date),
        "heatmap": _heatmap(conn, replay_date),
        "follow_up_pipeline": _follow_up_pipeline(conn, replay_date),
    }
    return redact_money(body, scope.role, scope.plant)
