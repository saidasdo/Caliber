"""MTBF and MTTR as of the replay date (SPEC 5.9 KPI dictionary; committee's Equipment
Performance KPIs).

Replay rule: built only from data dated on or before the replay date. The equipment's
performance_summary is NOT used here, because it covers the whole monitoring period and so
includes failures that happen after the replay date.

Definitions:
- failures: TRIP episodes in health_weekly on or before the replay date. Consecutive TRIP weeks
  count as one episode.
- observed_hours: hourly rows (plant_rate) on or before the replay date, which is the elapsed
  time covered by the hourly record, same base as the availability gauge.
- downtime_hours: OFF hours in run_status on or before the replay date.
- MTBF = observed_hours / failures; MTTR = downtime_hours / failures.
If there is no failure yet, MTBF and MTTR are None and the message says "No failure in period".
"""

import sqlite3


def _trip_episodes(conn: sqlite3.Connection, tag: str, replay_date: str) -> int:
    rows = conn.execute(
        "SELECT health_status FROM health_weekly WHERE equipment_tag = ? AND week_date <= ? "
        "ORDER BY week_date",
        (tag, replay_date),
    ).fetchall()
    episodes = 0
    previous = None
    for (status,) in rows:
        if status == "TRIP" and previous != "TRIP":
            episodes += 1
        previous = status
    return episodes


def compute_reliability(conn: sqlite3.Connection, tag: str, replay_date: str) -> dict:
    window = conn.execute(
        "SELECT MIN(ts), MAX(ts) FROM sensor_hourly WHERE equipment_tag = ? AND signal = 'plant_rate'",
        (tag,),
    ).fetchone()
    if window is None or window[0] is None or replay_date < window[0][:10]:
        return _empty("No hourly data for this date")

    cutoff = min(replay_date, window[1][:10]) + " 23:59:59"
    observed_hours, downtime_hours = conn.execute(
        "SELECT COUNT(*), SUM(CASE WHEN run_status = 'OFF' THEN 1 ELSE 0 END) "
        "FROM sensor_hourly WHERE equipment_tag = ? AND signal = 'plant_rate' AND ts <= ?",
        (tag, cutoff),
    ).fetchone()
    downtime_hours = downtime_hours or 0
    failures = _trip_episodes(conn, tag, replay_date)
    if failures == 0:
        return {
            "failures": 0,
            "observed_hours": observed_hours,
            "downtime_hours": downtime_hours,
            "mtbf_hours": None,
            "mttr_hours": None,
            "message": "No failure in period",
        }
    return {
        "failures": failures,
        "observed_hours": observed_hours,
        "downtime_hours": downtime_hours,
        "mtbf_hours": round(observed_hours / failures, 1),
        "mttr_hours": round(downtime_hours / failures, 1),
        "message": None,
    }


def _empty(message: str) -> dict:
    return {
        "failures": None,
        "observed_hours": None,
        "downtime_hours": None,
        "mtbf_hours": None,
        "mttr_hours": None,
        "message": message,
    }
