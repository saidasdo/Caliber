"""Equipment-detail gauges (SPEC section 5.3): Availability, Health margin, Production vs normal.

Each gauge returns {value, previous, sparkline, data_available}. "Previous period" is not
defined numerically in SPEC for these gauges; one week earlier is used here, for consistency
with how the Overview KPI band already defines "previous period" (documented assumption).
"""

import sqlite3
import statistics
from datetime import date, datetime, timedelta

PREVIOUS_PERIOD_DAYS = 7
SPARKLINE_WEEKS = 8
SPARKLINE_DAYS = 14
BASELINE_WINDOW_DAYS = 7


def _shift_date(iso_date: str, days: int) -> str:
    return (date.fromisoformat(iso_date[:10]) + timedelta(days=days)).isoformat()


def _window_bounds(conn: sqlite3.Connection, tag: str) -> tuple[str, str] | None:
    row = conn.execute(
        "SELECT MIN(ts), MAX(ts) FROM sensor_hourly WHERE equipment_tag = ? AND signal = 'plant_rate'",
        (tag,),
    ).fetchone()
    if row is None or row[0] is None:
        return None
    return row[0], row[1]


def _in_window(replay_date: str, window: tuple[str, str] | None) -> bool:
    """SPEC section 4: hourly-derived gauges must show the 'no hourly data' state when the
    replay date is outside the equipment's own hourly window, same as the status timeline and
    hourly trend chart. A gauge must never silently clip to a stale in-window value instead."""
    if window is None:
        return False
    window_start, window_end = window
    return window_start[:10] <= replay_date <= window_end[:10]


def _no_data_gauge(extra: dict | None = None) -> dict:
    base = {"value": None, "previous": None, "sparkline": [], "data_available": False}
    if extra:
        base.update(extra)
    return base


def _availability_gauge(conn: sqlite3.Connection, tag: str, replay_date: str, window: tuple[str, str] | None) -> dict:
    if not _in_window(replay_date, window):
        return _no_data_gauge()
    window_start, window_end = window

    def availability_to_date(as_of: str) -> float | None:
        cutoff = min(as_of, window_end[:10]) + " 23:59:59"
        if cutoff < window_start:
            return None
        rows = conn.execute(
            "SELECT COUNT(*), SUM(CASE WHEN run_status = 'OFF' THEN 1 ELSE 0 END) "
            "FROM sensor_hourly WHERE equipment_tag = ? AND signal = 'plant_rate' AND ts <= ?",
            (tag, cutoff),
        ).fetchone()
        elapsed, off = rows
        if not elapsed:
            return None
        return round((elapsed - off) / elapsed * 100, 2)

    value = availability_to_date(replay_date)
    previous = availability_to_date(_shift_date(replay_date, -PREVIOUS_PERIOD_DAYS))

    sparkline = []
    cursor = date.fromisoformat(min(replay_date, window_end[:10]))
    for i in range(SPARKLINE_DAYS - 1, -1, -1):
        day = (cursor - timedelta(days=i)).isoformat()
        v = availability_to_date(day)
        if v is not None:
            sparkline.append(v)

    return {"value": value, "previous": previous, "sparkline": sparkline, "data_available": value is not None}


def _health_margin_gauge(conn: sqlite3.Connection, tag: str, replay_date: str) -> dict:
    week_row = conn.execute(
        "SELECT week FROM health_weekly WHERE equipment_tag = ? AND week_date <= ? "
        "ORDER BY week_date DESC LIMIT 1",
        (tag, replay_date),
    ).fetchone()
    if week_row is None:
        return {"value": None, "previous": None, "sparkline": [], "data_available": False, "worst_parameter": None}
    week = week_row[0]

    rows = conn.execute(
        "SELECT cw.parameter, cw.value, pl.trip, pl.direction "
        "FROM condition_weekly cw "
        "JOIN param_limits pl ON pl.equipment_tag = cw.equipment_tag AND pl.parameter = cw.parameter "
        "WHERE cw.equipment_tag = ? AND cw.week = ?",
        (tag, week),
    ).fetchall()

    def margin_pct(value: float, trip: float, direction: str) -> float | None:
        if value is None or trip in (None, 0):
            return None
        if direction == "higher_is_worse":
            return round((trip - value) / trip * 100, 1)
        return round((value - trip) / trip * 100, 1)

    margins = [
        (parameter, margin_pct(value, trip, direction))
        for parameter, value, trip, direction in rows
    ]
    margins = [m for m in margins if m[1] is not None]
    if not margins:
        return {"value": None, "previous": None, "sparkline": [], "data_available": False, "worst_parameter": None}

    worst_parameter, worst_value = min(margins, key=lambda m: m[1])

    history = conn.execute(
        "SELECT cw.week, cw.value, pl.trip, pl.direction "
        "FROM condition_weekly cw "
        "JOIN param_limits pl ON pl.equipment_tag = cw.equipment_tag AND pl.parameter = cw.parameter "
        "WHERE cw.equipment_tag = ? AND cw.parameter = ? AND cw.week <= ? "
        "ORDER BY cw.week DESC LIMIT ?",
        (tag, worst_parameter, week, SPARKLINE_WEEKS + 1),
    ).fetchall()
    history = list(reversed(history))
    sparkline = [margin_pct(v, trip, direction) for _, v, trip, direction in history]
    previous = sparkline[-2] if len(sparkline) >= 2 else None

    return {
        "value": worst_value,
        "previous": previous,
        "sparkline": [s for s in sparkline if s is not None],
        "data_available": True,
        "worst_parameter": worst_parameter,
    }


def _production_vs_normal_gauge(
    conn: sqlite3.Connection, tag: str, replay_date: str, window: tuple[str, str] | None
) -> dict:
    if not _in_window(replay_date, window):
        return _no_data_gauge({"baseline": None})
    window_start, _ = window

    baseline_end = (datetime.fromisoformat(window_start) + timedelta(days=BASELINE_WINDOW_DAYS)).isoformat(sep=" ")
    baseline_rows = [
        r[0]
        for r in conn.execute(
            "SELECT value FROM sensor_hourly WHERE equipment_tag = ? AND signal = 'plant_rate' "
            "AND run_status = 'ON' AND ts < ? AND value IS NOT NULL",
            (tag, baseline_end),
        ).fetchall()
    ]
    if not baseline_rows:
        return _no_data_gauge({"baseline": None})
    baseline = statistics.median(baseline_rows)

    def latest_value_at_or_before(as_of: str) -> float | None:
        row = conn.execute(
            "SELECT value FROM sensor_hourly WHERE equipment_tag = ? AND signal = 'plant_rate' "
            "AND ts <= ? ORDER BY ts DESC LIMIT 1",
            (tag, as_of + " 23:59:59"),
        ).fetchone()
        return row[0] if row else None

    def ratio_at(as_of: str) -> float | None:
        v = latest_value_at_or_before(as_of)
        return round(v / baseline * 100, 1) if v is not None and baseline else None

    value = ratio_at(replay_date)
    previous = ratio_at(_shift_date(replay_date, -PREVIOUS_PERIOD_DAYS))

    sparkline_rows = conn.execute(
        "SELECT substr(ts, 1, 10) AS day, AVG(value) FROM sensor_hourly "
        "WHERE equipment_tag = ? AND signal = 'plant_rate' AND ts <= ? AND value IS NOT NULL "
        "GROUP BY day ORDER BY day DESC LIMIT ?",
        (tag, replay_date + " 23:59:59", SPARKLINE_DAYS),
    ).fetchall()
    sparkline = [round(v / baseline * 100, 1) for _, v in reversed(sparkline_rows)] if baseline else []

    return {
        "value": value,
        "previous": previous,
        "sparkline": sparkline,
        "data_available": value is not None,
        "baseline": round(baseline, 2),
    }


def compute_gauges(conn: sqlite3.Connection, tag: str, replay_date: str) -> dict:
    window = _window_bounds(conn, tag)
    return {
        "availability": _availability_gauge(conn, tag, replay_date, window),
        "health_margin": _health_margin_gauge(conn, tag, replay_date),
        "production_vs_normal": _production_vs_normal_gauge(conn, tag, replay_date, window),
    }
