"""Similar incidents scoring (SPEC section 5.6)."""

import sqlite3


def find_similar(conn: sqlite3.Connection, tag: str, top_n: int = 5) -> list[dict]:
    anchor = conn.execute(
        "SELECT serial_no, eq_type_family, component_family, mechanism_norm, plant_code, discipline "
        "FROM incidents WHERE tag_number = ? ORDER BY serial_no LIMIT 1",
        (tag,),
    ).fetchone()
    if anchor is None:
        return []
    anchor_serial, eq_type_family, component_family, mechanism_norm, plant_code, discipline = anchor

    rows = conn.execute(
        "SELECT serial_no, ar_no, tag_number, date_of_occur, downtime_hrs, total_loss_kusd, "
        "overall_status, eq_type_family, component_family, mechanism_norm, plant_code, discipline, "
        "component, risk_case_title_display "
        "FROM incidents WHERE serial_no != ?",
        (anchor_serial,),
    ).fetchall()

    scored = []
    for row in rows:
        (serial_no, ar_no, row_tag, date_of_occur, downtime_hrs, total_loss_kusd, overall_status,
         row_eq_type_family, row_component_family, row_mechanism_norm, row_plant_code,
         row_discipline, component, title_display) = row

        score = 0
        breakdown = {}
        if row_eq_type_family == eq_type_family:
            score += 3
            breakdown["eq_type_family"] = 3
        if row_component_family == component_family:
            score += 3
            breakdown["component_family"] = 3
        if row_mechanism_norm == mechanism_norm:
            score += 2
            breakdown["mechanism_norm"] = 2
        if row_plant_code == plant_code:
            score += 1
            breakdown["plant_code"] = 1
        if row_discipline == discipline:
            score += 1
            breakdown["discipline"] = 1

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

    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored[:top_n]
