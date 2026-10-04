"""Backtest: warning lead time per equipment (SPEC section 5.8). Computed, never hardcoded."""

import sqlite3

from app.engine.anomaly import detect_anomalies

# The vibration signal is present in hourly data for all 5 equipment (HE-3301 has one despite
# being a heat exchanger, see DQ3), so it is used as the common anomaly-detection signal here.
BACKTEST_SIGNAL = "vibration"


def run_backtest(conn: sqlite3.Connection) -> list[dict]:
    equipment = conn.execute(
        "SELECT tag, failure_date, plant_code FROM equipment WHERE has_sensor_data = 1"
    ).fetchall()

    results = []
    for tag, failure_date, plant_code in equipment:
        weeks = conn.execute(
            "SELECT week, week_date, health_status FROM health_weekly "
            "WHERE equipment_tag = ? ORDER BY week",
            (tag,),
        ).fetchall()
        first_alarm = next((w for w, d, s in weeks if s == "ALARM"), None)
        first_alarm_date = next((d for w, d, s in weeks if s == "ALARM"), None)
        first_trip = next((w for w, d, s in weeks if s == "TRIP"), None)
        first_trip_date = next((d for w, d, s in weeks if s == "TRIP"), None)
        lead_weeks = (first_trip - first_alarm) if (first_alarm is not None and first_trip is not None) else None

        first_off_ts = conn.execute(
            "SELECT MIN(ts) FROM sensor_hourly WHERE equipment_tag = ? AND run_status = 'OFF'",
            (tag,),
        ).fetchone()[0]

        anomalies = detect_anomalies(conn, tag, BACKTEST_SIGNAL)
        first_anomaly = anomalies[0] if anomalies else None
        lead_hours = None
        first_anomaly_week = None
        if first_anomaly and first_off_ts:
            lead_hours = _hours_between(first_anomaly["start_ts"], first_off_ts)
            first_anomaly_week = _week_containing(weeks, first_anomaly["start_ts"][:10])

        perf = conn.execute(
            "SELECT total_downtime_hours, estimated_loss_kusd FROM performance_summary "
            "WHERE equipment_tag = ?",
            (tag,),
        ).fetchone()
        downtime_hours, loss_kusd = perf if perf else (None, None)

        message = None
        if lead_weeks is not None:
            message = f"Warning was available {lead_weeks} weeks before the trip (weekly ALARM to TRIP)."

        results.append(
            {
                "equipment_tag": tag,
                "plant_code": plant_code,
                "failure_date": failure_date,
                "first_alarm_week": first_alarm,
                "first_alarm_date": first_alarm_date,
                "first_trip_week": first_trip,
                "first_trip_date": first_trip_date,
                "lead_time_weeks": lead_weeks,
                "first_off_ts": first_off_ts,
                "first_hourly_anomaly_ts": first_anomaly["start_ts"] if first_anomaly else None,
                "first_hourly_anomaly_week": first_anomaly_week,
                "lead_time_hours": lead_hours,
                "downtime_hours": downtime_hours,
                "loss_kusd": loss_kusd,
                # Downtime and loss are outcomes after the trip, not known at the time of the
                # warning. The backtest is an after-the-fact analysis, so they are labeled as such.
                "outcome_basis": "Actual outcome (after the trip)",
                "weekly_health": [
                    {"week": w, "week_date": d, "health_status": s} for w, d, s in weeks
                ],
                "message": message,
                "assumption": (
                    f"Hourly anomaly lead time uses the '{BACKTEST_SIGNAL}' signal (rolling 24h mean "
                    "vs a 7-day ON-hour baseline, flagged at 3 standard deviations for 3+ consecutive "
                    "hours) for all 5 equipment, for a consistent cross-equipment comparison."
                ),
            }
        )
    return results


def _hours_between(ts_a: str, ts_b: str) -> float:
    from datetime import datetime

    a = datetime.fromisoformat(ts_a)
    b = datetime.fromisoformat(ts_b)
    return round((b - a).total_seconds() / 3600, 1)


def _week_containing(weeks: list[tuple[int, str, str]], day: str) -> int | None:
    """Latest week on or before `day` (same rule as replay.resolve_week), so the hourly
    anomaly can be plotted on the same weekly x-axis as the swimlane."""
    candidates = [w for w, week_date, _ in weeks if week_date <= day]
    return max(candidates) if candidates else None
