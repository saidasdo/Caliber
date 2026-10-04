"""GET /api/equipment/{tag}... (SPEC section 5.3, 5.5, 5.6)."""

import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import get_connection, rows_to_dicts
from app.engine.anomaly import detect_anomalies
from app.engine.diagnosis import diagnose
from app.engine.energy_proxy import get_emission, get_energy_proxy
from app.engine.gauges import compute_gauges
from app.engine.impact import estimate_impact
from app.engine.reliability import compute_reliability
from app.engine.replay import DEFAULT_REPLAY_DATE, hourly_axis, has_hourly_coverage, replay_end, resolve_week
from app.engine.similar_incidents import find_similar
from app.engine.status_timeline import build_status_timeline
from app.engine.suggested_actions import get_suggested_actions
from app.scope import RoleScope, get_role_scope
from app.visibility import redact_money

router = APIRouter()


def _get_equipment_or_404(conn: sqlite3.Connection, tag: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM equipment WHERE tag = ?", (tag,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Unknown equipment tag: {tag}")
    return row


@router.get("/equipment/{tag}")
def get_equipment(
    tag: str,
    replay_date: str = Query(DEFAULT_REPLAY_DATE),
    conn: sqlite3.Connection = Depends(get_connection),
    scope: RoleScope = Depends(get_role_scope),
):
    equipment = _get_equipment_or_404(conn, tag)
    week_state = resolve_week(conn, tag, replay_date)
    diagnosis = diagnose(conn, tag, replay_date)
    similar = find_similar(conn, tag, replay_date, diagnosis=diagnosis)

    # Replay rule: an RCA is shown only once its failure date is on or before the replay date.
    # Before that the panel says "No RCA yet" and can list RCAs of similar past incidents.
    rca = conn.execute(
        "SELECT r.* FROM rca_reports r JOIN equipment e ON e.tag = r.equipment_tag "
        "WHERE r.equipment_tag = ? AND e.failure_date <= ?",
        (tag, replay_date),
    ).fetchone()
    rca_summary = None
    if rca:
        capa = rows_to_dicts(
            conn.execute(
                "SELECT action_category, item_code, action_text, plan_date, pic, status, extra_json "
                "FROM capa_actions WHERE equipment_tag = ? ORDER BY action_category, id",
                (tag,),
            ).fetchall()
        )
        rca_summary = {
            "rca_id": rca["rca_id"],
            "ar_no": rca["ar_no"],
            "problem_statement": rca["problem_statement"],
            "chronology": json.loads(rca["chronology_json"] or "[]"),
            "root_cause": rca["root_cause"],
            "four_p": json.loads(rca["four_p_json"] or "null"),
            "four_m_1e": json.loads(rca["four_m_1e_json"] or "null"),
            "capa_actions": capa,
        }

    similar_ar_nos = sorted({s["ar_no"] for s in similar if s["ar_no"]})
    past_rcas = []
    if rca_summary is None and similar_ar_nos:
        placeholders = ",".join("?" * len(similar_ar_nos))
        past_rcas = rows_to_dicts(
            conn.execute(
                f"SELECT r.rca_id, r.equipment_tag, r.ar_no, r.root_cause FROM rca_reports r "
                f"JOIN equipment e ON e.tag = r.equipment_tag "
                f"WHERE r.ar_no IN ({placeholders}) AND e.failure_date < ? ORDER BY r.rca_id",
                (*similar_ar_nos, replay_date),
            ).fetchall()
        )

    body = {
        "tag": equipment["tag"],
        "name": equipment["name"],
        "eq_type": equipment["eq_type"],
        "eq_type_family": equipment["eq_type_family"],
        "eq_class": equipment["eq_class"],
        "plant_code": equipment["plant_code"],
        "criticality": equipment["criticality"],
        "dominant_failure_mode": equipment["dominant_failure_mode"],
        "replay_date": replay_date,
        "has_hourly_coverage": has_hourly_coverage(conn, tag, replay_date),
        "hourly_signals": [
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT signal FROM sensor_hourly WHERE equipment_tag = ? ORDER BY signal",
                (tag,),
            ).fetchall()
        ],
        "weekly_state": week_state,
        "reliability": compute_reliability(conn, tag, replay_date),
        "emission": get_emission(conn, tag, replay_date),
        "gauges": compute_gauges(conn, tag, replay_date),
        "diagnosis": diagnosis,
        "impact": estimate_impact(conn, tag, replay_date),
        "similar_incidents": similar,
        "linked_rca": rca_summary,
        "past_rcas": past_rcas,
    }
    return redact_money(body, scope.role, scope.plant)


@router.get("/equipment/{tag}/series")
def get_equipment_series(
    tag: str,
    signal: str = Query(..., description="feed | discharge_pressure | vibration | temperature | motor_current | plant_rate"),
    replay_date: str = Query(DEFAULT_REPLAY_DATE, description="Hours after this date are never returned"),
    start: str | None = Query(None, description="ISO datetime, inclusive"),
    end: str | None = Query(None, description="ISO datetime, inclusive"),
    conn: sqlite3.Connection = Depends(get_connection),
):
    _get_equipment_or_404(conn, tag)
    has_record = conn.execute(
        "SELECT 1 FROM sensor_hourly WHERE equipment_tag = ? AND signal = ? LIMIT 1", (tag, signal)
    ).fetchone()
    if has_record is None:
        raise HTTPException(status_code=404, detail=f"No '{signal}' series for {tag}")
    sql = "SELECT ts, value, run_status FROM sensor_hourly WHERE equipment_tag = ? AND signal = ?"
    params: list = [tag, signal]
    # Replay rule (SPEC 4): nothing after the replay date. Always applied. A replay date before the
    # record gives an empty point list, not an error: the chart shows "no hourly data for this date".
    sql += " AND ts <= ?"
    params.append(replay_end(replay_date))
    if start:
        sql += " AND ts >= ?"
        params.append(start.replace("T", " "))  # stored as "YYYY-MM-DD HH:MM:SS"
    if end:
        sql += " AND ts <= ?"
        params.append(end.replace("T", " "))
    sql += " ORDER BY ts"
    rows = rows_to_dicts(conn.execute(sql, params).fetchall())
    return {
        "tag": tag,
        "signal": signal,
        "replay_date": replay_date,
        "display_unit": _display_unit(conn, tag, signal),
        **hourly_axis(conn, tag, signal),
        "points": rows,
    }


def _display_unit(conn: sqlite3.Connection, tag: str, signal: str) -> str | None:
    """Unit shown on the chart. The raw PI Tag label is kept in the database, but for KO-3201
    vibration the values match micron data, so the chart shows micron as an applied assumption
    (see DQ1, data quality page)."""
    if tag == "KO-3201" and signal == "vibration":
        return "µm (assumed, see DQ1)"
    row = conn.execute(
        "SELECT unit FROM pi_tag_meta WHERE equipment_tag = ? AND signal = ?", (tag, signal)
    ).fetchone()
    return row[0] if row else None


@router.get("/equipment/{tag}/anomalies")
def get_equipment_anomalies(
    tag: str,
    signal: str = Query(..., description="feed | discharge_pressure | vibration | temperature | motor_current | plant_rate"),
    replay_date: str = Query(DEFAULT_REPLAY_DATE),
    conn: sqlite3.Connection = Depends(get_connection),
):
    """Hourly anomaly markers (SPEC section 5.5): rolling 24h mean vs a 7-day ON-hour
    baseline, flagged at 3 standard deviations for 3+ consecutive hours. Computed on data up to
    the replay date only."""
    _get_equipment_or_404(conn, tag)
    return {
        "tag": tag,
        "signal": signal,
        "replay_date": replay_date,
        "anomalies": detect_anomalies(conn, tag, signal, replay_date),
    }


@router.get("/equipment/{tag}/status-timeline")
def get_equipment_status_timeline(
    tag: str,
    replay_date: str = Query(DEFAULT_REPLAY_DATE),
    conn: sqlite3.Connection = Depends(get_connection),
):
    _get_equipment_or_404(conn, tag)
    return {
        "tag": tag,
        "replay_date": replay_date,
        **hourly_axis(conn, tag, "plant_rate"),
        **build_status_timeline(conn, tag, replay_date),
    }


@router.get("/equipment/{tag}/weekly-series")
def get_equipment_weekly_series(
    tag: str,
    replay_date: str = Query(DEFAULT_REPLAY_DATE),
    conn: sqlite3.Connection = Depends(get_connection),
):
    """Weeks up to the replay date for all monitored parameters, each with its alarm/trip/direction,
    for the weekly small-multiple charts (SPEC section 5.3). axis_weeks is the number of weeks in the
    whole record, so the chart keeps its full width; no week after the replay date is returned."""
    _get_equipment_or_404(conn, tag)
    axis_weeks = conn.execute(
        "SELECT COUNT(*) FROM health_weekly WHERE equipment_tag = ?", (tag,)
    ).fetchone()[0]
    limits = {
        row["parameter"]: dict(row)
        for row in conn.execute(
            "SELECT parameter, unit, alarm, trip, direction FROM param_limits WHERE equipment_tag = ?",
            (tag,),
        ).fetchall()
    }
    rows = conn.execute(
        "SELECT cw.parameter, cw.week, cw.week_date, cw.value, cw.remark_display, hw.health_status "
        "FROM condition_weekly cw "
        "LEFT JOIN health_weekly hw ON hw.equipment_tag = cw.equipment_tag AND hw.week = cw.week "
        "WHERE cw.equipment_tag = ? AND cw.week_date <= ? ORDER BY cw.parameter, cw.week",
        (tag, replay_date),
    ).fetchall()

    series: dict[str, dict] = {}
    for row in rows:
        parameter = row["parameter"]
        if parameter not in series:
            limit = limits.get(parameter, {})
            series[parameter] = {
                "parameter": parameter,
                "unit": limit.get("unit"),
                "alarm": limit.get("alarm"),
                "trip": limit.get("trip"),
                "direction": limit.get("direction"),
                "points": [],
            }
        series[parameter]["points"].append(
            {
                "week": row["week"],
                "week_date": row["week_date"],
                "value": row["value"],
                "remark": row["remark_display"],
                "health_status": row["health_status"],
            }
        )

    return {
        "tag": tag,
        "replay_date": replay_date,
        "axis_weeks": axis_weeks,
        "parameters": list(series.values()),
    }


@router.get("/equipment/{tag}/diagnosis")
def get_equipment_diagnosis(
    tag: str,
    replay_date: str = Query(DEFAULT_REPLAY_DATE),
    conn: sqlite3.Connection = Depends(get_connection),
):
    _get_equipment_or_404(conn, tag)
    return {"tag": tag, "replay_date": replay_date, **diagnose(conn, tag, replay_date)}


@router.get("/equipment/{tag}/similar-incidents")
def get_equipment_similar_incidents(
    tag: str,
    replay_date: str = Query(DEFAULT_REPLAY_DATE),
    conn: sqlite3.Connection = Depends(get_connection),
):
    _get_equipment_or_404(conn, tag)
    return {"tag": tag, "results": find_similar(conn, tag, replay_date)}


@router.get("/equipment/{tag}/suggested-actions")
def get_equipment_suggested_actions(
    tag: str,
    replay_date: str = Query(DEFAULT_REPLAY_DATE),
    conn: sqlite3.Connection = Depends(get_connection),
):
    _get_equipment_or_404(conn, tag)
    return {"tag": tag, "replay_date": replay_date, **get_suggested_actions(conn, tag, replay_date)}


@router.get("/equipment/{tag}/energy-proxy")
def get_equipment_energy_proxy(
    tag: str,
    replay_date: str = Query(DEFAULT_REPLAY_DATE),
    conn: sqlite3.Connection = Depends(get_connection),
):
    _get_equipment_or_404(conn, tag)
    return {"tag": tag, "replay_date": replay_date, **get_energy_proxy(conn, tag, replay_date)}


@router.get("/equipment/{tag}/emission")
def get_equipment_emission(
    tag: str,
    replay_date: str = Query(DEFAULT_REPLAY_DATE),
    conn: sqlite3.Connection = Depends(get_connection),
):
    """Emission estimate up to the replay date only (motor-driven equipment)."""
    _get_equipment_or_404(conn, tag)
    return {"tag": tag, "replay_date": replay_date, **get_emission(conn, tag, replay_date)}
