"""Similar incidents scoring (SPEC section 5.6), as known on the replay date.

The query is built from the diagnosis for the replay date, not from the equipment's own
incident row: the diagnosed failure mode maps to an eq_type_family, component_family and
mechanism_norm (DIAGNOSIS_PROFILES). Only incidents dated before the replay date are candidates,
so the equipment's own later failure never shows up as its own "similar" case.

Scoring (SPEC 5.6): +3 same eq_type_family, +3 same component_family, +2 same mechanism_norm,
+1 same plant. The discipline point from the spec is dropped: the diagnosis profile does not
define a discipline, and the equipment's own row is no longer used as the anchor.
"""

import sqlite3

from app.engine.diagnosis import diagnose

# Failure mode per diagnosis rule, mapped to incident categories. None means "any" for that
# field, so that field earns no points. Chosen from the category values present in the
# incident database (see SPEC 6, DQ9 and DQ10).
DIAGNOSIS_PROFILES = {
    "Seal leakage (pump)": {"eq_type_family": "pump", "component_family": "Seal", "mechanism_norm": "Leakage"},
    "Lube oil water ingress, bearing distress (compressor)": {
        "eq_type_family": "compressor",
        "component_family": "Bearing",
        "mechanism_norm": "High Vibration",
    },
    "Motor bearing lubrication failure": {
        "eq_type_family": "motor",
        "component_family": "Bearing",
        "mechanism_norm": "Worn Out",
    },
    "Exchanger fouling": {
        "eq_type_family": "heat_exchanger",
        "component_family": "Tube Bundle",
        "mechanism_norm": "Fouling",
    },
    "Coupling misalignment": {"eq_type_family": None, "component_family": "Coupling", "mechanism_norm": "High Vibration"},
}


def _profile(conn: sqlite3.Connection, tag: str, replay_date: str, diagnosis: dict | None) -> dict | None:
    if diagnosis is None:
        diagnosis = diagnose(conn, tag, replay_date)
    if diagnosis.get("rule_name") and diagnosis["rule_name"] in DIAGNOSIS_PROFILES:
        return DIAGNOSIS_PROFILES[diagnosis["rule_name"]]
    # No confident diagnosis: fall back to the equipment's own type family, still date-filtered.
    row = conn.execute("SELECT eq_type_family FROM equipment WHERE tag = ?", (tag,)).fetchone()
    if row is None:
        return None
    return {"eq_type_family": row[0], "component_family": None, "mechanism_norm": None}


def find_similar(
    conn: sqlite3.Connection,
    tag: str,
    replay_date: str,
    diagnosis: dict | None = None,
    top_n: int = 5,
) -> list[dict]:
    equipment = conn.execute("SELECT plant_code FROM equipment WHERE tag = ?", (tag,)).fetchone()
    if equipment is None:
        return []
    plant_code = equipment[0]
    profile = _profile(conn, tag, replay_date, diagnosis)
    if profile is None:
        return []

    rows = conn.execute(
        "SELECT serial_no, ar_no, tag_number, date_of_occur, downtime_hrs, total_loss_kusd, "
        "overall_status, eq_type_family, component_family, mechanism_norm, plant_code, "
        "component, risk_case_title_display "
        "FROM incidents WHERE date_of_occur < ?",
        (replay_date,),
    ).fetchall()

    scored = []
    for row in rows:
        (serial_no, ar_no, row_tag, date_of_occur, downtime_hrs, total_loss_kusd, overall_status,
         row_eq_type_family, row_component_family, row_mechanism_norm, row_plant_code,
         component, title_display) = row

        score = 0
        breakdown = {}
        if profile["eq_type_family"] and row_eq_type_family == profile["eq_type_family"]:
            score += 3
            breakdown["eq_type_family"] = 3
        if profile["component_family"] and row_component_family == profile["component_family"]:
            score += 3
            breakdown["component_family"] = 3
        if profile["mechanism_norm"] and row_mechanism_norm == profile["mechanism_norm"]:
            score += 2
            breakdown["mechanism_norm"] = 2
        if row_plant_code == plant_code:
            score += 1
            breakdown["plant_code"] = 1

        if score == 0:
            continue

        scored.append(
            {
                "serial_no": serial_no,
                "ar_no": ar_no,
                "tag_number": row_tag,
                "risk_case_title": title_display,
                "date_of_occur": date_of_occur,
                "downtime_hrs": downtime_hrs,
                "total_loss_kusd": total_loss_kusd,
                "overall_status": overall_status,
                "eq_type_family": row_eq_type_family,
                "component": component,
                "plant_code": row_plant_code,
                "score": score,
                "score_breakdown": breakdown,
                "dq9_flag": component == "Tube Bundle" and row_eq_type_family != "heat_exchanger",
            }
        )

    scored.sort(key=lambda r: (r["score"], r["date_of_occur"]), reverse=True)
    return scored[:top_n]
