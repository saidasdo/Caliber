"""Alert priority scoring (SPEC section 5.4).

priority_score = 0.4 * severity + 0.3 * class + 0.3 * loss_exposure, each normalized 0 to 1.
Thresholds for the Critical/High/Medium/Low labels are not specified in SPEC; documented here
as an assumption pending product feedback.
"""

import sqlite3

from app.engine.diagnosis import diagnose
from app.engine.replay import resolve_week

CLASS_SCORE = {"A": 1.0, "B": 0.6, "C": 0.3}

LABEL_THRESHOLDS = [
    (0.8, "Critical"),
    (0.6, "High"),
    (0.4, "Medium"),
]


def _label(score: float) -> str:
    for threshold, label in LABEL_THRESHOLDS:
        if score >= threshold:
            return label
    return "Low"


def _weeks_in_current_status(conn: sqlite3.Connection, tag: str, replay_date: str) -> int | None:
    """Consecutive weeks (counting back from the replay date) the equipment has held its
    current health_status, for the plant manager alert wording ('in ALARM for 8 weeks')."""
    rows = conn.execute(
        "SELECT health_status FROM health_weekly WHERE equipment_tag = ? AND week_date <= ? "
        "ORDER BY week_date DESC",
        (tag, replay_date),
    ).fetchall()
    if not rows:
        return None
    current = rows[0][0]
    count = 0
    for (status,) in rows:
        if status != current:
            break
        count += 1
    return count


def _severity(week_state: dict | None) -> tuple[float, str]:
    if week_state is None:
        return 0.0, "no data"
    status = week_state["health_status"]
    if status == "TRIP":
        return 1.0, "TRIP"
    if status == "ALARM":
        return 0.7, "ALARM"
    rising_toward_alarm = any(
        p["trend"] == "rising" and p["alarm"] is not None and p["direction"] == "higher_is_worse"
        or p["trend"] == "falling" and p["alarm"] is not None and p["direction"] == "lower_is_worse"
        for p in week_state["parameters"]
    )
    if rising_toward_alarm:
        return 0.4, "rising trend toward alarm"
    return 0.0, "normal"


def compute_priority(conn: sqlite3.Connection, replay_date: str) -> list[dict]:
    equipment = conn.execute(
        "SELECT tag, name, plant_code, eq_class FROM equipment WHERE has_sensor_data = 1"
    ).fetchall()

    loss_by_tag = dict(
        conn.execute(
            "SELECT equipment_tag, estimated_loss_kusd FROM performance_summary"
        ).fetchall()
    )
    losses = [v for v in loss_by_tag.values() if v is not None]
    loss_min, loss_max = (min(losses), max(losses)) if losses else (0, 1)
    loss_span = (loss_max - loss_min) or 1

    results = []
    for tag, name, plant_code, eq_class in equipment:
        week_state = resolve_week(conn, tag, replay_date)
        severity, severity_reason = _severity(week_state)
        class_score = CLASS_SCORE.get(eq_class, 0.3)
        loss_exposure = (loss_by_tag.get(tag, loss_min) - loss_min) / loss_span
        diagnosis = diagnose(conn, tag, replay_date)

        score = 0.4 * severity + 0.3 * class_score + 0.3 * loss_exposure
        worst_parameter = None
        if week_state and week_state["parameters"]:
            worst_parameter = max(
                week_state["parameters"],
                key=lambda p: (
                    (p["value"] - p["alarm"]) if p["direction"] == "higher_is_worse" and p["alarm"] is not None
                    else (p["alarm"] - p["value"]) if p["direction"] == "lower_is_worse" and p["alarm"] is not None
                    else float("-inf")
                ),
            )

        results.append(
            {
                "equipment_tag": tag,
                "equipment_name": name,
                "plant_code": plant_code,
                "priority_score": round(score, 4),
                "priority_label": _label(score),
                "breakdown": {
                    "severity": severity,
                    "severity_reason": severity_reason,
                    "class_score": class_score,
                    "eq_class": eq_class,
                    "loss_exposure": round(loss_exposure, 4),
                },
                "health_status": week_state["health_status"] if week_state else None,
                "weeks_in_status": _weeks_in_current_status(conn, tag, replay_date),
                "estimated_loss_kusd": loss_by_tag.get(tag),
                "diagnosis_rule_name": diagnosis["rule_name"],
                "diagnosis_confidence": diagnosis["confidence"],
                "worst_parameter": (
                    {
                        "parameter": worst_parameter["parameter"],
                        "value": worst_parameter["value"],
                        "unit": worst_parameter["unit"],
                        "alarm": worst_parameter["alarm"],
                        "trip": worst_parameter["trip"],
                        "direction": worst_parameter["direction"],
                    }
                    if worst_parameter
                    else None
                ),
                "reason": (
                    f"{tag}: {severity_reason}"
                    + (
                        f", {worst_parameter['parameter']} {worst_parameter['value']} "
                        f"vs alarm {worst_parameter['alarm']}"
                        if worst_parameter and worst_parameter["alarm"] is not None
                        else ""
                    )
                ),
            }
        )

    results.sort(key=lambda r: r["priority_score"], reverse=True)
    return results
