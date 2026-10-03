"""Suggested actions from the diagnosis engine (SPEC section 5.7).

"Suggested actions from the diagnosis (mapped per rule, taken from CAPA of the RCA with the
same failure mode first, then generic defaults) only become tracked actions after an
engineer clicks Approve." A suggestion is never persisted on its own; it is computed fresh
from the current diagnosis every time this is called, and only Approve/Reject write anything
to the database (see api/actions.py).
"""

import sqlite3

from app.engine.diagnosis import _match_rule, diagnose

# Fallback when no RCA matches the fired rule (never hit by the 5 RCA-linked equipment in this
# dataset, since each rule has exactly one matching RCA here, but kept for equipment of the
# same type with no RCA of its own, per SPEC 5.5's "also work for other equipment").
GENERIC_DEFAULTS = {
    "Seal leakage (pump)": "Inspect seal flush flow system and schedule seal replacement.",
    "Lube oil water ingress, bearing distress (compressor)": (
        "Inspect lube oil cooler for leaks and sample lube oil water content."
    ),
    "Motor bearing lubrication failure": "Inspect motor DE bearing lubrication and schedule re-grease.",
    "Exchanger fouling": "Schedule tube bundle cleaning and inspect fouling rate.",
    "Coupling misalignment": "Perform a laser alignment check on the coupling.",
}


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


def get_suggested_actions(conn: sqlite3.Connection, tag: str, replay_date: str) -> dict:
    diagnosis = diagnose(conn, tag, replay_date)
    if not diagnosis["confidence"]:
        return {"rule_name": None, "confidence": None, "suggestions": []}

    rule_name = diagnosis["rule_name"]
    rca_id = _rule_name_to_rca_id(conn).get(rule_name)

    suggestions = []
    if rca_id is not None:
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
                    "suggested_pic": pic,
                    "suggested_due_date": plan_date,
                    "source": "rca_capa",
                }
            )

    if not suggestions:
        default_text = GENERIC_DEFAULTS.get(rule_name)
        if default_text:
            suggestions.append(
                {
                    "source_capa_action_id": None,
                    "action_text": default_text,
                    "suggested_pic": None,
                    "suggested_due_date": None,
                    "source": "generic_default",
                }
            )

    return {"rule_name": rule_name, "confidence": diagnosis["confidence"], "suggestions": suggestions}
