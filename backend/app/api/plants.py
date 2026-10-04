"""GET /api/plants/{plant_code} (SPEC section 5.2)."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import get_connection, rows_to_dicts
from app.engine.priority import compute_priority
from app.engine.reliability import compute_reliability
from app.engine.replay import DEFAULT_REPLAY_DATE
from app.scope import RoleScope, get_role_scope
from app.visibility import redact_money

router = APIRouter()


def _downtime_by_cause(conn: sqlite3.Connection, plant_code: str, replay_date: str) -> list[dict]:
    """Phase 10 plant manager widget: 'downtime causes grouped by F Mechanism and Component'."""
    rows = conn.execute(
        """
        SELECT COALESCE(component_family, component, 'Unknown') AS component,
               COALESCE(mechanism_norm, f_mechanism, 'Unknown') AS mechanism,
               COUNT(*) AS incident_count,
               COALESCE(SUM(downtime_hrs), 0) AS downtime_hrs
        FROM incidents
        WHERE plant_code = ? AND date_of_occur <= ?
        GROUP BY component, mechanism
        ORDER BY downtime_hrs DESC
        LIMIT 8
        """,
        (plant_code, replay_date),
    ).fetchall()
    return rows_to_dicts(rows)


def _rca_summaries(conn: sqlite3.Connection, plant_code: str, replay_date: str) -> list[dict]:
    """Only RCAs whose failure date is on or before the replay date (replay rule)."""
    rows = conn.execute(
        """
        SELECT r.equipment_tag, r.ar_no, r.root_cause, e.name AS equipment_name
        FROM rca_reports r
        JOIN equipment e ON e.tag = r.equipment_tag
        WHERE e.plant_code = ? AND e.failure_date <= ?
        ORDER BY r.equipment_tag
        """,
        (plant_code, replay_date),
    ).fetchall()
    return rows_to_dicts(rows)


@router.get("/plants/{plant_code}")
def get_plant(
    plant_code: str,
    replay_date: str = Query(DEFAULT_REPLAY_DATE),
    conn: sqlite3.Connection = Depends(get_connection),
    scope: RoleScope = Depends(get_role_scope),
):
    plant = conn.execute("SELECT * FROM plants WHERE plant_code = ?", (plant_code,)).fetchone()
    if plant is None:
        raise HTTPException(status_code=404, detail=f"Unknown plant_code: {plant_code}")

    kpis = conn.execute(
        "SELECT COUNT(*) AS incident_count, COALESCE(SUM(downtime_hrs), 0) AS downtime_hrs, "
        "COALESCE(SUM(total_loss_kusd), 0) AS loss_kusd "
        "FROM incidents WHERE plant_code = ? AND date_of_occur <= ?",
        (plant_code, replay_date),
    ).fetchone()

    sensor_equipment = [
        p for p in compute_priority(conn, replay_date) if p["plant_code"] == plant_code
    ]
    for row in sensor_equipment:
        row["reliability"] = compute_reliability(conn, row["equipment_tag"], replay_date)
    sensor_tags = {e["equipment_tag"] for e in sensor_equipment}

    incident_only_tags = [
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT tag_number FROM incidents "
            "WHERE plant_code = ? AND tag_number IS NOT NULL AND date_of_occur <= ?",
            (plant_code, replay_date),
        ).fetchall()
        if row[0] not in sensor_tags
    ]

    incident_history = rows_to_dicts(
        conn.execute(
            "SELECT serial_no, ar_no, tag_number, date_of_occur, risk_case_title_display, "
            "overall_status, downtime_hrs, total_loss_kusd "
            "FROM incidents WHERE plant_code = ? AND date_of_occur <= ? ORDER BY date_of_occur DESC",
            (plant_code, replay_date),
        ).fetchall()
    )

    open_actions = rows_to_dicts(
        conn.execute(
            "SELECT * FROM actions WHERE equipment_tag IN "
            "(SELECT tag FROM equipment WHERE plant_code = ?) AND status IN ('Open', 'In progress') "
            "AND (as_of_date IS NULL OR as_of_date <= ?)",
            (plant_code, replay_date),
        ).fetchall()
    )

    body = {
        "plant_code": plant_code,
        "plant_name": plant["plant_name"],
        "has_sensor_equipment": bool(plant["has_sensor_equipment"]),
        "replay_date": replay_date,
        "kpis": dict(kpis),
        "equipment": sensor_equipment,
        "incident_only_tags": incident_only_tags,
        "incident_history": incident_history,
        "open_actions": open_actions,
        "downtime_by_cause": _downtime_by_cause(conn, plant_code, replay_date),
        "rca_summaries": _rca_summaries(conn, plant_code, replay_date),
    }
    return redact_money(body, scope.role, scope.plant)
