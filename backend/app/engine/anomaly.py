"""Hourly anomaly detection (SPEC section 5.5, second part).

Rolling 24h mean vs a baseline (first 7 days of the window, ON hours only). Flag when the
deviation exceeds 3 standard deviations for 3 consecutive hours. OFF hours are ignored
entirely (not zero-filled, not interpolated) so a maintenance outage cannot look like a spike.
"""

import sqlite3
import statistics

BASELINE_DAYS = 7
DEVIATION_SIGMA = 3
MIN_CONSECUTIVE_HOURS = 3
ROLLING_WINDOW = 24


def detect_anomalies(conn: sqlite3.Connection, tag: str, signal: str, replay_date: str | None = None) -> list[dict]:
    """replay_date=None is the retrospective view (backtest, full history). Live views always pass
    the replay date, so nothing after it can flag an anomaly (SPEC section 4)."""
    sql = (
        "SELECT ts, value FROM sensor_hourly "
        "WHERE equipment_tag = ? AND signal = ? AND run_status = 'ON' AND value IS NOT NULL"
    )
    params: list = [tag, signal]
    if replay_date is not None:
        sql += " AND ts <= ?"
        params.append(replay_date + " 23:59:59")
    rows = conn.execute(sql + " ORDER BY ts", params).fetchall()
    if len(rows) < ROLLING_WINDOW + MIN_CONSECUTIVE_HOURS:
        return []

    first_ts_date = rows[0][0][:10]
    baseline_values = [v for ts, v in rows if _days_between(first_ts_date, ts[:10]) < BASELINE_DAYS]
    if len(baseline_values) < 2:
        return []
    baseline_mean = statistics.mean(baseline_values)
    baseline_std = statistics.pstdev(baseline_values) or 1e-9

    values = [v for _, v in rows]
    timestamps = [ts for ts, _ in rows]

    flags = [False] * len(values)
    for i in range(ROLLING_WINDOW - 1, len(values)):
        window = values[i - ROLLING_WINDOW + 1 : i + 1]
        rolling_mean = sum(window) / len(window)
        deviation = abs(rolling_mean - baseline_mean) / baseline_std
        flags[i] = deviation > DEVIATION_SIGMA

    anomalies = []
    run_start = None
    run_len = 0
    for i, flagged in enumerate(flags):
        if flagged:
            if run_start is None:
                run_start = i
            run_len += 1
        else:
            if run_len >= MIN_CONSECUTIVE_HOURS:
                anomalies.append(_build_anomaly(timestamps, values, baseline_mean, run_start, i - 1))
            run_start, run_len = None, 0
    if run_len >= MIN_CONSECUTIVE_HOURS:
        anomalies.append(_build_anomaly(timestamps, values, baseline_mean, run_start, len(flags) - 1))

    return anomalies


def _build_anomaly(timestamps, values, baseline_mean, start_idx, end_idx) -> dict:
    return {
        "start_ts": timestamps[start_idx],
        "end_ts": timestamps[end_idx],
        "baseline_mean": round(baseline_mean, 3),
        "peak_value": max(values[start_idx : end_idx + 1], key=lambda v: abs(v - baseline_mean)),
    }


def _days_between(date_a: str, date_b: str) -> int:
    from datetime import date

    a = date.fromisoformat(date_a)
    b = date.fromisoformat(date_b)
    return (b - a).days
