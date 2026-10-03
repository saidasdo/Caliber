"""Resolve "as of replay date" state for one equipment (SPEC section 4)."""

import sqlite3

DEFAULT_REPLAY_DATE = "2026-04-08"

REPLAY_PRESETS = {
    "PU-2101B": "2026-03-05",   # 1 week before failure (12-Mar-2026)
    "KO-3201": "2026-04-22",    # 1 week before failure (29-Apr-2026)
    "PM-4405B": "2026-07-01",   # 1 week before failure (08-Jul-2026)
    "HE-3301": "2026-05-14",    # 1 week before failure (21-May-2026)
    "BL-5702": "2026-06-10",    # 1 week before failure (17-Jun-2026)
}


def resolve_week(conn: sqlite3.Connection, tag: str, replay_date: str) -> dict | None:
    """Latest weekly reading on or before replay_date, with each parameter's limits and trend."""
    health = conn.execute(
        "SELECT week, week_date, health_status FROM health_weekly "
        "WHERE equipment_tag = ? AND week_date <= ? ORDER BY week_date DESC LIMIT 1",
        (tag, replay_date),
    ).fetchone()
    if health is None:
        return None
    week, week_date, health_status = health

    param_rows = conn.execute(
        "SELECT parameter, unit, value, remark_display FROM condition_weekly "
        "WHERE equipment_tag = ? AND week = ?",
        (tag, week),
    ).fetchall()

    limits = {
        row[0]: {"unit": row[1], "alarm": row[2], "trip": row[3], "direction": row[4]}
        for row in conn.execute(
            "SELECT parameter, unit, alarm, trip, direction FROM param_limits WHERE equipment_tag = ?",
            (tag,),
        ).fetchall()
    }

    parameters = []
    for parameter, unit, value, remark_display in param_rows:
        limit = limits.get(parameter, {})
        trend_rows = conn.execute(
            "SELECT value FROM condition_weekly WHERE equipment_tag = ? AND parameter = ? "
            "AND week <= ? ORDER BY week DESC LIMIT 4",
            (tag, parameter, week),
        ).fetchall()
        trend_values = [r[0] for r in reversed(trend_rows) if r[0] is not None]
        slope = _slope(trend_values)
        parameters.append(
            {
                "parameter": parameter,
                "unit": unit,
                "value": value,
                "alarm": limit.get("alarm"),
                "trip": limit.get("trip"),
                "direction": limit.get("direction"),
                "trend_slope": slope,
                "trend": _trend_label(slope),
                "remark": remark_display,
            }
        )

    return {
        "week": week,
        "week_date": week_date,
        "health_status": health_status,
        "parameters": parameters,
    }


def has_hourly_coverage(conn: sqlite3.Connection, tag: str, replay_date: str) -> bool:
    row = conn.execute(
        "SELECT MIN(ts), MAX(ts) FROM sensor_hourly WHERE equipment_tag = ?", (tag,)
    ).fetchone()
    if row is None or row[0] is None:
        return False
    return row[0][:10] <= replay_date <= row[1][:10]


def _slope(values: list[float]) -> float | None:
    """Simple least-squares slope over up to 4 points (per-week change)."""
    n = len(values)
    if n < 2:
        return None
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values))
    den = sum((x - mean_x) ** 2 for x in xs)
    return num / den if den else 0.0


def _trend_label(slope: float | None, flat_threshold: float = 1e-6) -> str:
    if slope is None:
        return "flat"
    if slope > flat_threshold:
        return "rising"
    if slope < -flat_threshold:
        return "falling"
    return "flat"
