"""GET /api/problems: the Problem Tank (SPEC section 5.7)."""

import sqlite3

from fastapi import APIRouter, Depends, Query

from app.db import get_connection, rows_to_dicts
from app.engine.priority import compute_priority
from app.engine.replay import DEFAULT_REPLAY_DATE

router = APIRouter()


def _alert_problems(conn: sqlite3.Connection, replay_date: str) -> list[dict]:
    """SPEC 5.7: Problem Tank sources include "alerts". An equipment in ALARM/TRIP is a live
    problem from the moment it first alarms, which is usually weeks before its RCA exists (the
    RCA problem only opens on the failure date). Computed fresh each call, never stored, since
    it is entirely a function of the replay date; synthetic ids so the frontend can still key
    on them, offset well clear of the real autoincrement range.
    """
    rca_opened = dict(
        conn.execute(
            "SELECT source_ref, opened_date FROM problems WHERE source_type = 'rca'"
        ).fetchall()
    )
    alerts = []
    for row in compute_priority(conn, replay_date):
        if row["health_status"] not in ("ALARM", "TRIP"):
            continue
        tag = row["equipment_tag"]
        rca_date = rca_opened.get(tag)
        if rca_date and rca_date <= replay_date:
            continue  # already represented by its own RCA-case problem
        first_alarm = conn.execute(
            "SELECT MIN(week_date) FROM health_weekly WHERE equipment_tag = ? "
            "AND health_status IN ('ALARM', 'TRIP') AND week_date <= ?",
            (tag, replay_date),
        ).fetchone()[0]
        alerts.append(
            {
                "id": f"alert-{tag}",
                "plant_code": row["plant_code"],
                "source_type": "alert",
                "source_ref": tag,
                "title": row["reason"],  # already starts with the tag, e.g. "KO-3201: ALARM, ..."
                "opened_date": first_alarm or replay_date,
                "status": "open",
                "priority_label": row["priority_label"],
            }
        )
    return alerts


@router.get("/problems")
def list_problems(
    replay_date: str = Query(DEFAULT_REPLAY_DATE),
    source_type: str | None = Query(None),
    plant_code: str | None = Query(None, description="Only problems at this plant"),
    conn: sqlite3.Connection = Depends(get_connection),
):
    """SPEC 4: "Incidents and actions only count if dated on or before it [the replay date]."
    RCA-case problems get a live priority_label from the priority engine (section 5.4); their
    stored priority_label is always null since severity changes with the replay date.
    """
    # Each problem's plant: an RCA case through its equipment, an incident through its incident row.
    plant_expr = "COALESCE(e.plant_code, i.plant_code)"
    join = (
        "FROM problems p "
        "LEFT JOIN equipment e ON p.source_type = 'rca' AND e.tag = p.source_ref "
        "LEFT JOIN incidents i ON p.source_type = 'incident' AND CAST(i.serial_no AS TEXT) = p.source_ref"
    )
    sql = f"SELECT p.*, {plant_expr} AS plant_code {join} WHERE p.opened_date <= ?"
    params: list = [replay_date]
    if source_type:
        sql += " AND p.source_type = ?"
        params.append(source_type)
    if plant_code:
        sql += f" AND {plant_expr} = ?"
        params.append(plant_code)
    sql += " ORDER BY p.opened_date DESC"
    rows = rows_to_dicts(conn.execute(sql, params).fetchall())

    priority_by_tag = {p["equipment_tag"]: p["priority_label"] for p in compute_priority(conn, replay_date)}
    for row in rows:
        if row["source_type"] == "rca":
            row["priority_label"] = priority_by_tag.get(row["source_ref"])

    if source_type in (None, "alert"):
        alerts = _alert_problems(conn, replay_date)
        if plant_code:
            alerts = [a for a in alerts if a.get("plant_code") == plant_code]
        rows = alerts + rows

    count_sql = f"SELECT p.source_type, COUNT(*) {join} WHERE p.opened_date <= ?"
    count_params: list = [replay_date]
    if plant_code:
        count_sql += f" AND {plant_expr} = ?"
        count_params.append(plant_code)
    counts_by_source: dict[str, int] = dict(
        conn.execute(count_sql + " GROUP BY p.source_type", count_params).fetchall()
    )
    alert_count = sum(1 for r in rows if r["source_type"] == "alert")
    if alert_count:
        counts_by_source["alert"] = alert_count

    return {"results": rows, "counts_by_source_type": counts_by_source}
