"""Suggested actions from the diagnosis engine (SPEC section 5.7), as known on the replay date.

"Suggested actions from the diagnosis (mapped per rule, taken from CAPA of the RCA with the
same failure mode first, then generic defaults) only become tracked actions after an
engineer clicks Approve." A suggestion is never persisted on its own; it is computed fresh
from the diagnosis for the replay date, and only Approve/Reject/Propose write anything to the
database (see api/actions.py).

Replay rule: CAPA actions are only used from an RCA whose equipment failure date is before the
replay date. Otherwise the generic action library (catalog/action_library.py) is used.
Each suggestion says where it came from: "rca_capa" or "action_library".
"""

import sqlite3

from app.catalog.action_library import ACTION_LIBRARY
from app.engine.diagnosis import _match_rule, diagnose


def _rule_name_to_rca_id(conn: sqlite3.Connection) -> dict[str, int]:
    """Which RCA's own equipment fires each rule, found by matching parameter names (not by
    tag), so this stays correct even if equipment/rules are added later."""
    mapping: dict[str, int] = {}
    equipment = conn.execute(
        "SELECT tag, rca_id FROM equipment WHERE rca_id IS NOT NULL"
    ).fetchall()
    for tag, rca_id in equipment:
        parameter_names = [
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT parameter FROM param_limits WHERE equipment_tag = ?", (tag,)
            ).fetchall()
        ]
        rule = _match_rule(parameter_names)
        if rule:
            mapping[rule["name"]] = rca_id
    return mapping


def _rca_known_at(conn: sqlite3.Connection, rca_id: int, replay_date: str) -> bool:
    row = conn.execute(
        "SELECT e.failure_date FROM equipment e WHERE e.rca_id = ?", (rca_id,)
    ).fetchone()
    return row is not None and row[0] is not None and row[0] < replay_date


def get_suggested_actions(
    conn: sqlite3.Connection, tag: str, replay_date: str, diagnosis: dict | None = None
) -> dict:
    if diagnosis is None:
        diagnosis = diagnose(conn, tag, replay_date)
    if not diagnosis["confidence"]:
        return {"rule_name": None, "confidence": None, "suggestions": []}

    rule_name = diagnosis["rule_name"]
    rca_id = _rule_name_to_rca_id(conn).get(rule_name)

    suggestions = []
    if rca_id is not None and _rca_known_at(conn, rca_id, replay_date):
        rows = conn.execute(
            "SELECT id, action_text, pic, plan_date FROM capa_actions "
            "WHERE rca_id = ? AND action_category = 'corrective' ORDER BY id",
            (rca_id,),
        ).fetchall()
        for capa_id, action_text, pic, plan_date in rows:
            suggestions.append(
                {
                    "source_capa_action_id": capa_id,
                    "action_text": action_text,
                    "category": "corrective",
                    "suggested_pic": pic,
                    "suggested_due_date": plan_date,
                    "source": "rca_capa",
                }
            )

    if not suggestions:
        for item in ACTION_LIBRARY.get(rule_name, []):
            suggestions.append(
                {
                    "source_capa_action_id": None,
                    "action_text": item["text"],
                    "category": item["category"],
                    "suggested_pic": None,
                    "suggested_due_date": None,
                    "source": "action_library",
                }
            )

    return {"rule_name": rule_name, "confidence": diagnosis["confidence"], "suggestions": suggestions}
