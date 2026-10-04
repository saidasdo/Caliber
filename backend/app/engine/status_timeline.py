"""Machine status timeline (SPEC section 5.3): Running / Alarm / Trip-Off / No data lanes.

Hourly run_status tells us ON/OFF directly; ALARM/TRIP only exists at weekly resolution
(Condition History), so an ON hour is colored by the health_status of the week it falls in
(the latest week on or before that hour's date, same rule `resolve_week` uses). This is a
documented simplification: SPEC does not define an hourly alarm/trip classification.
"""

import sqlite3
from bisect import bisect_right

LANES = ("running", "alarm", "trip_off", "no_data")


def _day_health_status(days: list[str], weeks: list[tuple[str, str]]) -> dict[str, str | None]:
    """weeks: sorted [(week_date, health_status), ...]. Maps each day to the latest week's status."""
    week_dates = [w[0] for w in weeks]
    result = {}
    for day in days:
        idx = bisect_right(week_dates, day) - 1
        result[day] = weeks[idx][1] if idx >= 0 else None
    return result


def build_status_timeline(conn: sqlite3.Connection, tag: str, replay_date: str | None = None) -> dict:
    """Segments up to the replay date only (replay_date=None is the retrospective full record)."""
    sql = "SELECT ts, run_status FROM sensor_hourly WHERE equipment_tag = ? AND signal = 'plant_rate'"
    params: list = [tag]
    week_sql = "SELECT week_date, health_status FROM health_weekly WHERE equipment_tag = ?"
    week_params: list = [tag]
    if replay_date is not None:
        sql += " AND ts <= ?"
        params.append(replay_date + " 23:59:59")
        week_sql += " AND week_date <= ?"
        week_params.append(replay_date)
    hourly = conn.execute(sql + " ORDER BY ts", params).fetchall()
    if not hourly:
        return {"segments": [], "distribution": []}

    weeks = conn.execute(week_sql + " ORDER BY week_date", week_params).fetchall()
    weeks = [(w[0], w[1]) for w in weeks]

    days = sorted({ts[:10] for ts, _ in hourly})
    day_status = _day_health_status(days, weeks) if weeks else {d: None for d in days}

    def lane_for(ts: str, run_status: str) -> str:
        if run_status == "OFF":
            return "trip_off"
        status = day_status.get(ts[:10])
        if status in ("ALARM", "TRIP"):
            return "alarm"
        if status == "NORMAL":
            return "running"
        return "no_data"

    segments = []
    current_lane, seg_start, seg_start_idx = None, None, 0
    for i, (ts, run_status) in enumerate(hourly):
        lane = lane_for(ts, run_status)
        if lane != current_lane:
            if current_lane is not None:
                segments.append(
                    {
                        "lane": current_lane,
                        "start_ts": hourly[seg_start_idx][0],
                        "end_ts": hourly[i - 1][0],
                        "hours": i - seg_start_idx,
                    }
                )
            current_lane, seg_start_idx = lane, i
    segments.append(
        {
            "lane": current_lane,
            "start_ts": hourly[seg_start_idx][0],
            "end_ts": hourly[-1][0],
            "hours": len(hourly) - seg_start_idx,
        }
    )

    distribution = []
    for lane in LANES:
        lane_segments = [s for s in segments if s["lane"] == lane]
        distribution.append(
            {
                "lane": lane,
                "duration_hours": sum(s["hours"] for s in lane_segments),
                "occurrences": len(lane_segments),
            }
        )

    return {"segments": segments, "distribution": distribution}
