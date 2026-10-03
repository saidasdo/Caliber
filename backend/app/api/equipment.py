"""GET /api/equipment/{tag}... (SPEC section 5.3, 5.5, 5.6)."""

import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import get_connection, rows_to_dicts
from app.engine.anomaly import detect_anomalies
from app.engine.diagnosis import diagnose
from app.engine.energy_proxy import get_energy_proxy
from app.engine.gauges import compute_gauges
from app.engine.replay import DEFAULT_REPLAY_DATE, has_hourly_coverage, resolve_week
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
    performance = conn.execute(
        "SELECT * FROM performance_summary WHERE equipment_tag = ?", (tag,)
    ).fetchone()
    rca = conn.execute("SELECT * FROM rca_reports WHERE equipment_tag = ?", (tag,)).fetchone()
    capa = rows_to_dicts(
        conn.execute(
            "SELECT action_category, item_code, action_text, plan_date, pic, status, extra_json "
            "FROM capa_actions WHERE equipment_tag = ? ORDER BY action_category, id",
            (tag,),
        ).fetchall()
    )

    rca_summary = None
    if rca:
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
        "performance_summary": dict(performance) if performance else None,
        "gauges": compute_gauges(conn, tag, replay_date),
        "diagnosis": diagnose(conn, tag, replay_date),
        "similar_incidents": find_similar(conn, tag),
        "linked_rca": rca_summary,
    }
    return redact_money(body, scope.role, scope.plant)


@router.get("/equipment/{tag}/series")
def get_equipment_series(
    tag: str,
    signal: str = Query(..., description="feed | discharge_pressure | vibration | temperature | motor_current | plant_rate"),
    start: str | None = Query(None, description="ISO datetime, inclusive"),
    end: str | None = Query(None, description="ISO datetime, inclusive"),
    conn: sqlite3.Connection = Depends(get_connection),
):
    _get_equipment_or_404(conn, tag)
    sql = "SELECT ts, value, run_status FROM sensor_hourly WHERE equipment_tag = ? AND signal = ?"
    params: list = [tag, signal]
    if start:
        sql += " AND ts >= ?"
        params.append(start.replace("T", " "))  # stored as "YYYY-MM-DD HH:MM:SS"
    if end:
        sql += " AND ts <= ?"
        params.append(end.replace("T", " "))
    sql += " ORDER BY ts"
    rows = rows_to_dicts(conn.execute(sql, params).fetchall())
    if not rows:
        raise HTTPException(status_code=404, detail=f"No '{signal}' series for {tag}")
    return {"tag": tag, "signal": signal, "points": rows}


@router.get("/equipment/{tag}/anomalies")
def get_equipment_anomalies(
    tag: str,
    signal: str = Query(..., description="feed | discharge_pressure | vibration | temperature | motor_current | plant_rate"),
    conn: sqlite3.Connection = Depends(get_connection),
):
    """Hourly anomaly markers (SPEC section 5.5): rolling 24h mean vs a 7-day ON-hour
    baseline, flagged at 3 standard deviations for 3+ consecutive hours."""
    _get_equipment_or_404(conn, tag)
    return {"tag": tag, "signal": signal, "anomalies": detect_anomalies(conn, tag, signal)}


@router.get("/equipment/{tag}/status-timeline")
def get_equipment_status_timeline(
    tag: str,
    conn: sqlite3.Connection = Depends(get_connection),
):
    _get_equipment_or_404(conn, tag)
    return {"tag": tag, **build_status_timeline(conn, tag)}


@router.get("/equipment/{tag}/weekly-series")
def get_equipment_weekly_series(
    tag: str,
    conn: sqlite3.Connection = Depends(get_connection),
):
    """All 26 weeks for all 4 monitored parameters, each with its alarm/trip/direction, for
    the weekly small-multiple charts (SPEC section 5.3)."""
    _get_equipment_or_404(conn, tag)
    limits = {
        row["parameter"]: dict(row)
        for row in conn.execute(
            "SELECT parameter, unit, alarm, trip, direction FROM param_limits WHERE equipment_tag = ?",
            (tag,),
        ).fetchall()
    }
    rows = conn.execute(
        "SELECT parameter, week, week_date, value, remark_display FROM condition_weekly "
        "WHERE equipment_tag = ? ORDER BY parameter, week",
        (tag,),
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
            }
        )

    return {"tag": tag, "parameters": list(series.values())}


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
    conn: sqlite3.Connection = Depends(get_connection),
):
    _get_equipment_or_404(conn, tag)
    return {"tag": tag, "results": find_similar(conn, tag)}


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
    conn: sqlite3.Connection = Depends(get_connection),
):
    _get_equipment_or_404(conn, tag)
    return {"tag": tag, **get_energy_proxy(conn, tag)}
